"""抓取指定區間的股癌逐字稿，存到 data/raw/。

用法：
    python scripts/scrape.py 569 583
"""

from __future__ import annotations

import sys

from gooaye.scraper.pack import fetch_range


def main() -> None:
    if len(sys.argv) != 3:
        print("用法: python scripts/scrape.py <起始EP> <結束EP>")
        raise SystemExit(1)
    start, end = int(sys.argv[1]), int(sys.argv[2])
    print(f"抓取 EP{start}–EP{end} …")
    episodes = fetch_range(start, end)
    print(f"完成：成功 {len(episodes)} 集")


if __name__ == "__main__":
    main()
