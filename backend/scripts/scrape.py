"""抓取指定區間的股癌逐字稿，存到 data/raw/。

用法：
    python scripts/scrape.py <起始EP> <結束EP>   # 抓取指定範圍
    python scripts/scrape.py --latest            # 查詢 pack 最新集數（不爬）
"""

from __future__ import annotations

import sys

from gooaye.scraper.pack import fetch_range, list_available_ep_nos


def main() -> None:
    args = sys.argv[1:]

    # ── 查詢最新集數 ──────────────────────────────────────────
    if args == ["--latest"]:
        print("正在從 pack 取得集數清單…")
        available = list_available_ep_nos()
        print(f"pack 共 {len(available)} 集，最新集數：EP{available[-1]}")
        return

    # ── 明確範圍模式 ──────────────────────────────────────────
    if len(args) != 2:
        print("用法:")
        print("  python scripts/scrape.py <起始EP> <結束EP>")
        print("  python scripts/scrape.py --latest")
        raise SystemExit(1)
    start, end = int(args[0]), int(args[1])
    print(f"抓取 EP{start}–EP{end} …")
    episodes = fetch_range(start, end)
    print(f"完成：成功 {len(episodes)} 集")


if __name__ == "__main__":
    main()
