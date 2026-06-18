"""三種跟單規則的回測引擎 + 命中率統計，結果寫入 backtest_runs。

交易假設（簡化、避免前視偏誤）：
  - 進場價＝該集發布日「隔日（含）起」第一個有收盤的價格
  - 報酬＝收盤對收盤
  - 基準＝各市場對應（TW→0050、US→SPY、其他→SPY）
"""

from __future__ import annotations

import datetime as dt
import statistics
from dataclasses import dataclass

from supabase import Client

from gooaye.analytics.prices import PriceBook, Series, load_price_book

HOLD_DAYS_DEFAULT = 60
HIT_HORIZONS = (30, 60, 90)


@dataclass(slots=True)
class Trade:
    stock_id: int
    market: str
    ep_date: str  # 觸發進場的集發布日
    entry_date: str
    entry_price: float
    exit_date: str
    exit_price: float
    ret: float
    bm_ret: float | None


def _plus_days(date: str, days: int) -> str:
    return (dt.date.fromisoformat(date) + dt.timedelta(days=days)).isoformat()


def _bm_return(book: PriceBook, market: str, entry_date: str, exit_date: str) -> float | None:
    bm = book.benchmark(market)
    if bm is None:
        return None
    e = bm.on_or_after(entry_date)
    x = bm.on_or_before(exit_date)
    if not e or not x or e[1] == 0:
        return None
    return round(x[1] / e[1] - 1, 4)


def _make_trade(
    book: PriceBook, stock_id: int, market: str,
    entry: tuple[str, float], exit_: tuple[str, float],
    ep_date: str,
) -> Trade:
    ret = round(exit_[1] / entry[1] - 1, 4) if entry[1] else 0.0
    return Trade(
        stock_id=stock_id, market=market, ep_date=ep_date,
        entry_date=entry[0], entry_price=entry[1],
        exit_date=exit_[0], exit_price=exit_[1], ret=ret,
        bm_ret=_bm_return(book, market, entry[0], exit_[0]),
    )


# ── 三種策略：輸入單檔的 mentions（依日期升冪）與股價序列，輸出 trades ──

def _strategy_hold_until_flip(
    book, stock_id, market, series: Series, mentions: list[dict],
    *, require_position: bool,
) -> list[Trade]:
    """看多進場，轉中性/看空出場（require_position=True 時只跟『有部位的看多』）。"""
    trades: list[Trade] = []
    holding = False
    entry: tuple[str, float] | None = None
    entry_ep_date = ""
    for m in mentions:
        bull = m["direction"] == "看多" and (not require_position or m["has_position"])
        bearish = m["direction"] in ("中性", "看空")
        if not holding and bull:
            e = series.on_or_after(_plus_days(m["date"], 1))
            if e:
                entry, holding, entry_ep_date = e, True, m["date"]
        elif holding and bearish:
            x = series.on_or_after(_plus_days(m["date"], 1))
            if x and entry:
                trades.append(_make_trade(book, stock_id, market, entry, x, entry_ep_date))
                holding, entry, entry_ep_date = False, None, ""
    if holding and entry:  # 尚未平倉 → 以最新價結算
        last = series.latest()
        if last and last[0] > entry[0]:
            trades.append(_make_trade(book, stock_id, market, entry, last, entry_ep_date))
    return trades


def _strategy_hold_n_days(
    book, stock_id, market, series: Series, mentions: list[dict], *, n: int,
) -> list[Trade]:
    """每次看多即進場，持有 n 天後出場（交易可重疊）。"""
    trades: list[Trade] = []
    for m in mentions:
        if m["direction"] != "看多":
            continue
        e = series.on_or_after(_plus_days(m["date"], 1))
        if not e:
            continue
        x = series.on_or_after(_plus_days(e[0], n)) or series.latest()
        if x and x[0] > e[0]:
            trades.append(_make_trade(book, stock_id, market, e, x, m["date"]))
    return trades


def _aggregate(trades: list[Trade], scope: str) -> dict:
    sel = trades if scope == "ALL" else [t for t in trades if t.market == scope]
    if not sel:
        return {"scope": scope, "n_trades": 0}
    rets = [t.ret for t in sel]
    with_bm = [t for t in sel if t.bm_ret is not None]
    alphas = [t.ret - t.bm_ret for t in with_bm]  # type: ignore[operator]
    return {
        "scope": scope,
        "n_trades": len(sel),
        "win_rate": round(sum(r > 0 for r in rets) / len(rets), 4),
        "avg_return": round(statistics.mean(rets), 4),
        "median_return": round(statistics.median(rets), 4),
        "avg_bm_return": round(statistics.mean([t.bm_ret for t in with_bm]), 4) if with_bm else None,
        "avg_alpha": round(statistics.mean(alphas), 4) if alphas else None,
        "beat_bm_rate": round(sum(a > 0 for a in alphas) / len(alphas), 4) if alphas else None,
    }


def _hit_rate(book: PriceBook, stocks: dict, mentions_by_stock: dict) -> list[dict]:
    """所有『看多』訊號，N 天後的上漲比例與平均報酬（含對基準的超額）。"""
    buckets: dict[int, dict[str, list]] = {h: {"ret": [], "alpha": []} for h in HIT_HORIZONS}
    for stock_id, mlist in mentions_by_stock.items():
        series = book.series(stock_id)
        market = stocks.get(stock_id, {}).get("market", "US")
        if not series:
            continue
        for m in mlist:
            if m["direction"] != "看多":
                continue
            e = series.on_or_after(_plus_days(m["date"], 1))
            if not e:
                continue
            for h in HIT_HORIZONS:
                x = series.on_or_after(_plus_days(e[0], h))
                if not x or x[0] <= e[0] or e[1] == 0:
                    continue
                ret = x[1] / e[1] - 1
                buckets[h]["ret"].append(ret)
                bm = _bm_return(book, market, e[0], x[0])
                if bm is not None:
                    buckets[h]["alpha"].append(ret - bm)
    out = []
    for h in HIT_HORIZONS:
        rets = buckets[h]["ret"]
        alphas = buckets[h]["alpha"]
        if not rets:
            out.append({"horizon": h, "n": 0})
            continue
        out.append({
            "horizon": h,
            "n": len(rets),
            "pct_positive": round(sum(r > 0 for r in rets) / len(rets), 4),
            "avg_return": round(statistics.mean(rets), 4),
            "avg_alpha": round(statistics.mean(alphas), 4) if alphas else None,
            "beat_bm_rate": round(sum(a > 0 for a in alphas) / len(alphas), 4) if alphas else None,
        })
    return out


def run_backtest(
    client: Client, book: PriceBook | None = None, *, hold_days: int = HOLD_DAYS_DEFAULT,
) -> dict:
    """執行三種策略 + 命中率，結果寫入 backtest_runs 並回傳。"""
    book = book or load_price_book(client)

    stock_rows = (
        client.table("stocks").select("id,ticker,name_zh,market,asset_type")
        .in_("asset_type", ["個股", "ETF"]).execute().data
    )
    stocks = {s["id"]: s for s in stock_rows}

    mrows = (
        client.table("mentions")
        .select("stock_id,direction,has_position,episodes(published_at)")
        .not_.is_("stock_id", "null").execute().data
    )
    mentions_by_stock: dict[int, list[dict]] = {}
    for m in mrows:
        if m["stock_id"] not in stocks:
            continue
        pub = (m.get("episodes") or {}).get("published_at")
        if not pub:
            continue
        mentions_by_stock.setdefault(m["stock_id"], []).append(
            {"date": pub, "direction": m["direction"], "has_position": m["has_position"]}
        )
    for v in mentions_by_stock.values():
        v.sort(key=lambda x: x["date"])

    # 對每檔跑三種策略
    strat_defs = [
        ("S1", "看多進、轉中性/看空出", "flip", {}),
        ("S2", f"看多即進、持有{hold_days}天", "ndays", {"n": hold_days}),
        ("S3", "只跟『他有部位』的看多", "flip_pos", {}),
    ]
    strategies = []
    for sid_, label, kind, kw in strat_defs:
        all_trades: list[Trade] = []
        for stock_id, mlist in mentions_by_stock.items():
            series = book.series(stock_id)
            if not series:
                continue
            market = stocks[stock_id]["market"]
            if kind == "flip":
                t = _strategy_hold_until_flip(book, stock_id, market, series, mlist, require_position=False)
            elif kind == "flip_pos":
                t = _strategy_hold_until_flip(book, stock_id, market, series, mlist, require_position=True)
            else:
                t = _strategy_hold_n_days(book, stock_id, market, series, mlist, n=kw["n"])
            all_trades.extend(t)
        sorted_trades = sorted(all_trades, key=lambda t: t.exit_date)
        trade_log = [
            {
                "ticker": stocks[t.stock_id].get("ticker", ""),
                "name_zh": stocks[t.stock_id].get("name_zh") or "",
                "market": t.market,
                "ep_date": t.ep_date,
                "entry_date": t.entry_date,
                "exit_date": t.exit_date,
                "ret": t.ret,
                "bm_ret": t.bm_ret,
                "alpha": round(t.ret - t.bm_ret, 4) if t.bm_ret is not None else None,
            }
            for t in sorted_trades
        ]
        cum_ret = 0.0
        equity_curve: list[dict] = []
        for i, tr in enumerate(sorted_trades):
            cum_ret += tr.ret
            equity_curve.append({"date": tr.exit_date, "value": round(cum_ret / (i + 1), 4)})
        strategies.append({
            "id": sid_, "label": label,
            "scopes": [_aggregate(all_trades, sc) for sc in ("ALL", "TW", "US")],
            "trades": trade_log,
            "equity_curve": equity_curve,
        })

    results = {
        "hold_days": hold_days,
        "strategies": strategies,
        "hit_rate": _hit_rate(book, stocks, mentions_by_stock),
    }

    ref = max(
        (m["date"] for ms in mentions_by_stock.values() for m in ms), default=None
    )
    client.table("backtest_runs").insert(
        {"reference_date": ref, "results": results}
    ).execute()
    return results
