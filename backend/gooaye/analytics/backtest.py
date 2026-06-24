"""三種跟單規則的回測引擎 + 命中率統計，結果寫入 backtest_runs。

交易假設（簡化、避免前視偏誤）：
  - 進場價＝該集發布日「隔日（含）起」第一個有收盤的價格
  - 報酬＝收盤對收盤，**已扣交易成本**（見 CostModel）
  - 基準＝各市場對應（TW→0050、US→SPY、其他→SPY），以被動持有計，
    不扣每筆交易成本 → α 代表「扣掉自己的交易成本後，是否仍贏過懶人持有大盤」

成本內化原則：成本直接乘進每筆交易的進出場價，因此 trades.ret 已是淨報酬。
前端僅以 trades 為單一事實來源重算所有衍生指標（勝率/α/資金曲線/MDD），
故只要這裡的 ret 是淨值，全站數字皆為扣成本後。
"""

from __future__ import annotations

import datetime as dt
import statistics
from dataclasses import dataclass

from supabase import Client

from gooaye.analytics.prices import PriceBook, Series, load_price_book

HOLD_DAYS_DEFAULT = 60
HIT_HORIZONS = (30, 60, 90)


@dataclass(frozen=True, slots=True)
class CostModel:
    """單邊交易成本（以比例計，round-trip = 進場一次 + 出場一次）。"""

    fee_rate: float  # 券商手續費／邊
    sell_tax: float  # 證交稅（僅賣出課徵）
    slippage: float  # 估計價差／滑價／邊


# 各市場成本假設（偏保守，寧可高估成本也不低估）：
#   TW：手續費 0.1425%/邊（未折扣，上限）、證交稅 0.3% 賣出（個股；ETF 實為 0.1%，此處從嚴）
#   US：現代券商免佣金，僅估計買賣價差/滑價 0.05%/邊
COST_BY_MARKET: dict[str, CostModel] = {
    "TW": CostModel(fee_rate=0.001425, sell_tax=0.003, slippage=0.0005),
    "US": CostModel(fee_rate=0.0, sell_tax=0.0, slippage=0.0005),
}
DEFAULT_COST = COST_BY_MARKET["US"]


def _net_return(market: str, entry_price: float, exit_price: float) -> float:
    """扣交易成本後的報酬：成本乘進進出場價。

    進場實付 = price × (1 + 手續費 + 滑價)
    出場實得 = price × (1 − 手續費 − 證交稅 − 滑價)
    """
    if not entry_price:
        return 0.0
    c = COST_BY_MARKET.get(market, DEFAULT_COST)
    eff_entry = entry_price * (1 + c.fee_rate + c.slippage)
    eff_exit = exit_price * (1 - c.fee_rate - c.sell_tax - c.slippage)
    return eff_exit / eff_entry - 1


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
    ret = round(_net_return(market, entry[1], exit_[1]), 4)
    return Trade(
        stock_id=stock_id, market=market, ep_date=ep_date,
        entry_date=entry[0], entry_price=entry[1],
        exit_date=exit_[0], exit_price=exit_[1], ret=ret,
        bm_ret=_bm_return(book, market, entry[0], exit_[0]),
    )


# ── 三種策略：輸入單檔的 mentions（依日期升冪）與股價序列，輸出 trades ──

def _qualifies(m: dict, min_conf: float, require_position: bool) -> bool:
    """是否為合格的『看多』進場訊號（含信心門檻、是否要求他有部位）。"""
    if m["direction"] != "看多":
        return False
    if require_position and not m["has_position"]:
        return False
    return (m.get("confidence") or 0) >= min_conf


def _strategy_hold_until_flip(
    book, stock_id, market, series: Series, mentions: list[dict],
    *, require_position: bool, min_conf: float = 0.0,
) -> list[Trade]:
    """看多進場，轉中性/看空出場（可加信心門檻、是否只跟『有部位的看多』）。"""
    trades: list[Trade] = []
    holding = False
    entry: tuple[str, float] | None = None
    entry_ep_date = ""
    for m in mentions:
        bull = _qualifies(m, min_conf, require_position)
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
    require_position: bool = False, min_conf: float = 0.0,
) -> list[Trade]:
    """每次（合格）看多即進場，持有 n 天後出場（交易可重疊）。"""
    trades: list[Trade] = []
    for m in mentions:
        if not _qualifies(m, min_conf, require_position):
            continue
        e = series.on_or_after(_plus_days(m["date"], 1))
        if not e:
            continue
        x = series.on_or_after(_plus_days(e[0], n)) or series.latest()
        if x and x[0] > e[0]:
            trades.append(_make_trade(book, stock_id, market, e, x, m["date"]))
    return trades


# ── 日頻投組淨值（daily mark-to-market）：供前端正確計算 Sharpe/MDD/CAGR ──
#
# 模型：總資金切成 N 個等額 sleeve（各 1/N），每個 sleeve 同時只持一檔；
# 交易依進場日貪婪指派給「最早空出」的 sleeve（資金上限約束，滿倉時的訊號被略過）。
# 每日淨值＝各 sleeve 當日市值加總：持倉期間以該股每日收盤 mark-to-market，
# 出場日結算為淨報酬（1+trade.ret，含成本），空檔持現金（持平）。
# 如此曲線含持倉期間的浮動回撤 → MDD 正確；日報酬序列 → Sharpe 正確。

NAV_SLOTS = 10
NAV_SAMPLE_EVERY = 5  # 日頻 NAV 降採樣為週頻（每 5 交易日），縮小 payload；首尾必留


def _calendar(book: PriceBook, trades: list[Trade], extra: list[Series]) -> list[str]:
    """涵蓋所有交易期間的交易日曆（相關個股 + 基準序列的日期聯集）。"""
    lo = min(t.entry_date for t in trades)
    hi = max(t.exit_date for t in trades)
    dates: set[str] = set()
    seen_series: list[Series] = list(extra)
    for t in trades:
        s = book.series(t.stock_id)
        if s:
            seen_series.append(s)
    for s in seen_series:
        for d in s.dates:
            if lo <= d <= hi:
                dates.add(d)
    return sorted(dates)


def _sleeve_nav(book: PriceBook, trades: list[Trade], calendar: list[str]) -> list[float]:
    """N-sleeve 日頻淨值序列（對齊 calendar，起點 1.0）。"""
    sorted_tr = sorted(trades, key=lambda t: t.entry_date)
    # 貪婪指派交易到 sleeve
    free_after = ["1970-01-01"] * NAV_SLOTS
    assigned: list[list[Trade]] = [[] for _ in range(NAV_SLOTS)]
    for t in sorted_tr:
        cand = [i for i in range(NAV_SLOTS) if free_after[i] < t.entry_date]
        if not cand:
            continue  # 滿倉，略過此訊號
        i = min(cand, key=lambda i: free_after[i])
        assigned[i].append(t)
        free_after[i] = t.exit_date

    total = [0.0] * len(calendar)
    for sleeve in assigned:
        base = 1.0 / NAV_SLOTS
        cur: Trade | None = None
        ti = 0
        sl = sorted(sleeve, key=lambda t: t.entry_date)
        for idx, d in enumerate(calendar):
            if cur and d >= cur.exit_date:  # 結算出場（淨報酬）
                base *= 1 + cur.ret
                cur = None
            if cur is None and ti < len(sl) and d >= sl[ti].entry_date:
                cur = sl[ti]
                ti += 1
            if cur is not None:
                s = book.series(cur.stock_id)
                px = s.on_or_before(d) if s else None
                total[idx] += base * (px[1] / cur.entry_price) if px and cur.entry_price else base
            else:
                total[idx] += base
    return [round(v, 5) for v in total]


def _bm_buy_hold(series: Series, calendar: list[str]) -> list[float] | None:
    """基準買進持有的日頻淨值（起點 1.0），對齊 calendar。"""
    if not calendar:
        return None
    base = series.on_or_after(calendar[0])
    if not base or not base[1]:
        return None
    out: list[float] = []
    for d in calendar:
        px = series.on_or_before(d) or base
        out.append(round(px[1] / base[1], 5))
    return out


def _daily_block(book: PriceBook, trades: list[Trade], scope: str) -> dict | None:
    """單一市場範圍的日頻 NAV：策略曲線 + 基準買進持有曲線。"""
    sel = trades if scope == "ALL" else [t for t in trades if t.market == scope]
    if not sel:
        return None

    # 基準序列：TW→0050、US→SPY；ALL→依各市場交易數加權混合
    bm_series: list[tuple[Series, float]] = []
    if scope == "ALL":
        counts: dict[str, int] = {}
        for t in sel:
            counts[t.market] = counts.get(t.market, 0) + 1
        total_n = sum(counts.values())
        for mkt, n in counts.items():
            s = book.benchmark(mkt)
            if s:
                bm_series.append((s, n / total_n))
    else:
        s = book.benchmark(scope)
        if s:
            bm_series.append((s, 1.0))

    extra = [s for s, _ in bm_series]
    calendar = _calendar(book, sel, extra)
    if len(calendar) < 2:
        return None

    nav = _sleeve_nav(book, sel, calendar)

    # 基準：各基準買進持有後依權重混合（起點皆 1.0）
    bm_nav: list[float] | None = None
    parts = [(w, _bm_buy_hold(s, calendar)) for s, w in bm_series]
    parts = [(w, p) for w, p in parts if p]
    if parts:
        wsum = sum(w for w, _ in parts)
        bm_nav = [
            round(sum(w * p[i] for w, p in parts) / wsum, 5) for i in range(len(calendar))
        ]

    # 降採樣為週頻以縮小 payload（首尾必留）；前端依實際取樣頻率年化 Sharpe。
    keep = list(range(0, len(calendar), NAV_SAMPLE_EVERY))
    if keep[-1] != len(calendar) - 1:
        keep.append(len(calendar) - 1)
    calendar = [calendar[i] for i in keep]
    nav = [nav[i] for i in keep]
    if bm_nav is not None:
        bm_nav = [bm_nav[i] for i in keep]

    return {"dates": calendar, "nav": nav, "bm_nav": bm_nav}


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
                ret = _net_return(market, e[1], x[1])
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


def _fetch_all_mentions(client: Client) -> list[dict]:
    """分頁撈出全部 mentions（PostgREST 單次上限 1000 列，見 CLAUDE.md §6）。"""
    rows: list[dict] = []
    page, size = 0, 1000
    while True:
        chunk = (
            client.table("mentions")
            .select("stock_id,direction,has_position,confidence,episodes(published_at)")
            .not_.is_("stock_id", "null")
            .order("id")
            .range(page * size, page * size + size - 1)
            .execute()
            .data
        )
        rows.extend(chunk)
        if len(chunk) < size:
            break
        page += 1
    return rows


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

    mrows = _fetch_all_mentions(client)
    mentions_by_stock: dict[int, list[dict]] = {}
    for m in mrows:
        if m["stock_id"] not in stocks:
            continue
        pub = (m.get("episodes") or {}).get("published_at")
        if not pub:
            continue
        mentions_by_stock.setdefault(m["stock_id"], []).append(
            {
                "date": pub,
                "direction": m["direction"],
                "has_position": m["has_position"],
                "confidence": m.get("confidence"),
            }
        )
    for v in mentions_by_stock.values():
        v.sort(key=lambda x: x["date"])

    # 策略定義：kind 決定出場規則，params 傳入產生器（信心門檻、是否要求他有部位、持有天數）。
    # S1–S3 為原始基礎規則；S4–S6 為以完整資料掃描後挑出的「最佳使用」策略（見 CLAUDE.md §5）。
    strat_defs = [
        ("S1", "看多進、轉中性/看空出", "flip", {}),
        ("S2", f"看多即進、持有{hold_days}天", "ndays", {"n": hold_days}),
        ("S3", "只跟『他有部位』的看多", "flip", {"require_position": True}),
        ("S4", "精選：他有部位+高信心(≥0.9)看多，持有90天", "ndays",
         {"n": 90, "require_position": True, "min_conf": 0.9}),
        ("S5", "高信心(≥0.9)看多，持有60天", "ndays", {"n": 60, "min_conf": 0.9}),
        ("S6", "高信心(≥0.9)看多進、翻空出", "flip", {"min_conf": 0.9}),
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
                t = _strategy_hold_until_flip(
                    book, stock_id, market, series, mlist,
                    require_position=kw.get("require_position", False),
                    min_conf=kw.get("min_conf", 0.0),
                )
            else:
                t = _strategy_hold_n_days(
                    book, stock_id, market, series, mlist, n=kw["n"],
                    require_position=kw.get("require_position", False),
                    min_conf=kw.get("min_conf", 0.0),
                )
            all_trades.extend(t)
        sorted_trades = sorted(all_trades, key=lambda t: t.exit_date)
        trade_log = [
            {
                "stock_id": t.stock_id,
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
        # 日頻 NAV（每市場一條），前端對任意區間切片並重設基準為 1.0，
        # 再從日報酬序列正確計算 Sharpe(×√252)/MDD/CAGR。
        # 勝率/α/年度統計等仍由前端以 trades 即時重算（可隨篩選互動）。
        daily = {sc: _daily_block(book, all_trades, sc) for sc in ("ALL", "TW", "US")}
        strategies.append({
            "id": sid_, "label": label,
            "scopes": [_aggregate(all_trades, sc) for sc in ("ALL", "TW", "US")],
            "trades": trade_log,
            "daily": {k: v for k, v in daily.items() if v},
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
