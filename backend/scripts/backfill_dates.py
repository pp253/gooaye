"""從 RSS 取得發布日期，更新 episodes.published_at。

用法：
    python scripts/backfill_dates.py
"""

from __future__ import annotations

from gooaye.db import get_client
from gooaye.scraper.rss import fetch_ep_dates


def main() -> None:
    print("抓取 RSS 發布日期 …")
    dates = fetch_ep_dates()
    print(f"RSS 共 {len(dates)} 集有日期")

    client = get_client()
    rows = client.table("episodes").select("id, ep_no").execute().data
    updated = 0
    for row in rows:
        date = dates.get(row["ep_no"])
        if not date:
            print(f"  EP{row['ep_no']}: RSS 無對應日期，略過")
            continue
        client.table("episodes").update({"published_at": date}).eq(
            "id", row["id"]
        ).execute()
        print(f"  EP{row['ep_no']} → {date}")
        updated += 1
    print(f"完成：更新 {updated} 集")


if __name__ == "__main__":
    main()
