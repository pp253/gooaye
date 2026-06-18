"""抓所有可定價股票（含基準 0050 / SPY）的日收盤價，填入 prices 表。

用法：
    python scripts/fetch_prices.py            # 全部
    python scripts/fetch_prices.py --missing  # 只補沒有股價的
"""

from __future__ import annotations

import sys

from gooaye.db import get_client

# 基準標的：確保存在於 stocks 表（backtest 會用到）
_BENCHMARKS = [
    {"ticker": "SPY", "market": "US", "name_zh": "SPY 標普500", "asset_type": "ETF"},
    {"ticker": "0050", "market": "TW", "name_zh": "元大台灣50", "asset_type": "ETF"},
]


def ensure_benchmarks(client) -> None:
    for b in _BENCHMARKS:
        client.table("stocks").upsert(b, on_conflict="ticker,market").execute()


def main() -> None:
    only_missing = "--missing" in sys.argv
    client = get_client()
    ensure_benchmarks(client)

    from gooaye.prices import sync_prices

    print(f"抓股價中（{'只補缺' if only_missing else '全部'}）…")
    stat = sync_prices(client, only_missing=only_missing)
    print(f"完成：{stat['stocks']} 檔 / {stat['rows']} 筆收盤價")


if __name__ == "__main__":
    main()
