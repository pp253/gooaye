"""計算每檔個股的「提及後表現」快照，寫入 stock_performance 表。

指標：
  current_price         最新收盤
  first_bull_*          首次「看多」當時價格與至今報酬
  last_bull_*           最近一次「看多」當時價格與至今報酬
"""

from __future__ import annotations

from supabase import Client

from gooaye.analytics.prices import PriceBook, load_price_book


def _mentions_by_stock(client: Client) -> dict[int, list[dict]]:
    rows = (
        client.table("mentions")
        .select("stock_id,direction,episodes(published_at)")
        .not_.is_("stock_id", "null")
        .execute()
        .data
    )
    out: dict[int, list[dict]] = {}
    for m in rows:
        pub = (m.get("episodes") or {}).get("published_at")
        if not pub:
            continue
        out.setdefault(m["stock_id"], []).append(
            {"date": pub, "direction": m["direction"]}
        )
    for v in out.values():
        v.sort(key=lambda x: x["date"])
    return out


def compute_performance(client: Client, book: PriceBook | None = None) -> int:
    """計算所有有股價的個股表現並 upsert，回傳處理檔數。"""
    book = book or load_price_book(client)
    mentions = _mentions_by_stock(client)

    rows = []
    for stock_id, series in book.by_stock.items():
        latest = series.latest()
        if latest is None:
            continue
        cur_price = latest[1]

        bulls = [m for m in mentions.get(stock_id, []) if m["direction"] == "看多"]
        row: dict = {"stock_id": stock_id, "current_price": cur_price}

        if bulls:
            first = series.on_or_after(bulls[0]["date"])
            if first:
                row["first_bull_date"] = bulls[0]["date"]
                row["first_bull_price"] = first[1]
                row["ret_since_first_bull"] = round(cur_price / first[1] - 1, 4)
            last = series.on_or_after(bulls[-1]["date"])
            if last:
                row["last_bull_date"] = bulls[-1]["date"]
                row["last_bull_price"] = last[1]
                row["ret_since_last_bull"] = round(cur_price / last[1] - 1, 4)

        rows.append(row)

    # upsert
    for i in range(0, len(rows), 200):
        client.table("stock_performance").upsert(
            rows[i : i + 200], on_conflict="stock_id"
        ).execute()
    return len(rows)
