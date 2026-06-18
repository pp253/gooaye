"""用 yfinance 抓日收盤價並寫入 Supabase prices 表。

代號映射（DB ticker → yfinance symbol）：
  TW    → 加 .TW 後綴（2330 → 2330.TW）
  US    → 原樣（NVDA）
  OTHER → 原樣（已含交易所後綴，如 6981.T、005930.KS）
"""

from __future__ import annotations

import datetime as dt
import warnings

import yfinance as yf
from supabase import Client

warnings.filterwarnings("ignore", module="yfinance")

# 可抓股價的資產類型（題材/商品略過）
PRICED_ASSET_TYPES = ("個股", "ETF", "指數")


def yf_symbol(ticker: str, market: str) -> str | None:
    """把 DB ticker 轉成 yfinance symbol；無法對應回 None。"""
    t = ticker.strip()
    if not t:
        return None
    if market == "TW":
        return t if "." in t else f"{t}.TW"
    if market == "US":
        return t
    if market == "OTHER":
        # 外國股應已帶交易所後綴（.T / .KS …）；沒有就無法可靠對應
        return t if "." in t else None
    return None


def fetch_close_series(
    symbol: str, start: str, end: str | None = None
) -> list[tuple[str, float]]:
    """抓 [start, end] 的日收盤，回傳 [(date_iso, close), ...]。"""
    end = end or (dt.date.today() + dt.timedelta(days=1)).isoformat()
    hist = yf.Ticker(symbol).history(start=start, end=end, auto_adjust=True)
    out: list[tuple[str, float]] = []
    for ts, row in hist.iterrows():
        close = row.get("Close")
        if close is None or close != close:  # NaN 檢查
            continue
        out.append((ts.date().isoformat(), round(float(close), 4)))
    return out


def _upsert_prices(
    client: Client, stock_id: int, series: list[tuple[str, float]]
) -> int:
    if not series:
        return 0
    rows = [
        {"stock_id": stock_id, "date": d, "close": c} for d, c in series
    ]
    # 分批 upsert，避免單次 payload 過大
    for i in range(0, len(rows), 500):
        client.table("prices").upsert(
            rows[i : i + 500], on_conflict="stock_id,date"
        ).execute()
    return len(rows)


def sync_prices(
    client: Client,
    *,
    only_missing: bool = False,
    verbose: bool = True,
) -> dict[str, int]:
    """為所有可定價的股票抓股價並寫入 prices 表。

    抓取區間：每檔從「首次被提及日 − 5 天」到今天。
    回傳 {stocks, rows} 統計。
    """
    stocks = (
        client.table("stocks")
        .select("id,ticker,market,name_zh,asset_type")
        .in_("asset_type", list(PRICED_ASSET_TYPES))
        .execute()
        .data
    )

    # 每檔首次被提及日（用集數日期）
    mentions = (
        client.table("mentions")
        .select("stock_id, episodes(published_at)")
        .not_.is_("stock_id", "null")
        .execute()
        .data
    )
    first_date: dict[int, str] = {}
    for m in mentions:
        sid = m["stock_id"]
        pub = (m.get("episodes") or {}).get("published_at")
        if not pub:
            continue
        if sid not in first_date or pub < first_date[sid]:
            first_date[sid] = pub

    # 全體最早提及日：給未被提及的標的（如基準 SPY/0050）當抓取起點
    global_min = min(first_date.values()) if first_date else None

    total_rows = 0
    done = 0
    for s in stocks:
        sid = s["id"]
        symbol = yf_symbol(s["ticker"], s["market"])
        if symbol is None:
            if verbose:
                print(f"  {s['ticker']} ({s['market']}): 無法對應 yf symbol，略過")
            continue
        if only_missing:
            existing = (
                client.table("prices").select("id").eq("stock_id", sid).limit(1).execute().data
            )
            if existing:
                continue
        start = first_date.get(sid) or global_min
        if not start:
            continue
        start = (dt.date.fromisoformat(start) - dt.timedelta(days=5)).isoformat()
        try:
            series = fetch_close_series(symbol, start)
        except Exception as exc:  # noqa: BLE001 — 單檔失敗不中斷批次
            if verbose:
                print(f"  {symbol}: 抓取失敗 {type(exc).__name__}: {exc}")
            continue
        n = _upsert_prices(client, sid, series)
        total_rows += n
        done += 1
        if verbose:
            print(f"  {s['ticker']:10} ({symbol}) {s['name_zh']}: {n} 筆")

    return {"stocks": done, "rows": total_rows}
