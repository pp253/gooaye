"""股價載入與查詢工具（供績效與回測共用）。"""

from __future__ import annotations

import bisect
from dataclasses import dataclass

from supabase import Client


@dataclass(slots=True)
class Series:
    """單一標的的日收盤序列（依日期升冪）。"""

    dates: list[str]
    closes: list[float]

    def __len__(self) -> int:
        return len(self.dates)

    def on_or_after(self, date: str) -> tuple[str, float] | None:
        """回傳 date（含）之後第一個有收盤的 (date, close)。"""
        i = bisect.bisect_left(self.dates, date)
        if i >= len(self.dates):
            return None
        return self.dates[i], self.closes[i]

    def on_or_before(self, date: str) -> tuple[str, float] | None:
        i = bisect.bisect_right(self.dates, date) - 1
        if i < 0:
            return None
        return self.dates[i], self.closes[i]

    def latest(self) -> tuple[str, float] | None:
        if not self.dates:
            return None
        return self.dates[-1], self.closes[-1]


class PriceBook:
    """所有標的的股價集合，外加依市場對應的基準序列與具名基準序列。"""

    def __init__(
        self,
        by_stock: dict[int, Series],
        benchmark_by_market: dict[str, Series],
        named_benchmarks: dict[str, Series] | None = None,
    ) -> None:
        self.by_stock = by_stock
        self.benchmark_by_market = benchmark_by_market
        # 具名基準（供因子拆解/嚴格對標用）：SPY=大盤、QQQ=科技、SOXX=費半、0050=台股大盤
        self.named_benchmarks = named_benchmarks or {}

    def series(self, stock_id: int) -> Series | None:
        return self.by_stock.get(stock_id)

    def benchmark(self, market: str) -> Series | None:
        # TW→0050、US→SPY、其他→SPY（fallback）
        return self.benchmark_by_market.get(market) or self.benchmark_by_market.get("US")

    def bench(self, ticker: str) -> Series | None:
        """以代號取得具名基準序列（如 SPY/QQQ/SOXX/0050）。"""
        return self.named_benchmarks.get(ticker)


def _fetch_all_prices(client: Client) -> dict[int, Series]:
    """一次撈出 prices 全表，組成 {stock_id: Series}。"""
    rows: list[dict] = []
    page = 0
    size = 1000
    while True:
        chunk = (
            client.table("prices")
            .select("stock_id,date,close")
            .order("stock_id")
            .order("date")
            .range(page * size, page * size + size - 1)
            .execute()
            .data
        )
        rows.extend(chunk)
        if len(chunk) < size:
            break
        page += 1

    by_stock: dict[int, tuple[list[str], list[float]]] = {}
    for r in rows:
        sid = r["stock_id"]
        d, c = r["date"], float(r["close"])
        if sid not in by_stock:
            by_stock[sid] = ([], [])
        by_stock[sid][0].append(d)
        by_stock[sid][1].append(c)
    return {sid: Series(ds, cs) for sid, (ds, cs) in by_stock.items()}


def load_price_book(client: Client) -> PriceBook:
    """載入全部股價，並建立市場→基準序列對應。"""
    by_stock = _fetch_all_prices(client)

    # 找基準標的的 stock_id（市場對應 0050/SPY + 具名 QQQ/SOXX 供因子拆解）
    bm_rows = (
        client.table("stocks")
        .select("id,ticker,market")
        .in_("ticker", ["0050", "SPY", "QQQ", "SOXX"])
        .execute()
        .data
    )
    benchmark_by_market: dict[str, Series] = {}
    named_benchmarks: dict[str, Series] = {}
    for b in bm_rows:
        s = by_stock.get(b["id"])
        if not s:
            continue
        named_benchmarks[b["ticker"]] = s
        if b["ticker"] == "0050":
            benchmark_by_market["TW"] = s
        elif b["ticker"] == "SPY":
            benchmark_by_market["US"] = s
    return PriceBook(by_stock, benchmark_by_market, named_benchmarks)
