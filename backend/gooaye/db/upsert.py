"""把單集抽取結果（EpisodeExtraction + 原始 metadata）寫入 Supabase。

策略：
  - episodes: upsert on ep_no
  - stocks:   先經正規化層取得標準 (ticker, market, asset_type)，upsert on (ticker, market)
  - mentions: 先刪該集舊 mentions，再重新 insert（冪等）
"""

from __future__ import annotations

from typing import Any

from supabase import Client

from gooaye.extractor.schema import EpisodeExtraction
from gooaye.normalize import resolve


def upsert_episode(
    client: Client,
    ep_no: int,
    title: str,
    source_url: str,
    extraction: EpisodeExtraction,
    published_at: str | None = None,
) -> dict[str, Any]:
    """將一集的所有資料 upsert 到 Supabase，回傳 {episode_id, stock_ids, mention_count}。"""

    # ── 1. episodes ──────────────────────────────────────────
    ep_row = {
        "ep_no": ep_no,
        "title": title,
        "source_url": source_url,
        "summary": extraction.summary,
        "topics": extraction.topics,
    }
    if published_at:
        ep_row["published_at"] = published_at
    ep_res = (
        client.table("episodes")
        .upsert(ep_row, on_conflict="ep_no")
        .execute()
    )
    episode_id: int = ep_res.data[0]["id"]

    # ── 2. stocks（正規化後 upsert，取得 id） ─────────────────
    stock_id_map: dict[tuple[str, str], int] = {}
    resolved_by_idx = []
    for mention in extraction.mentions:
        r = resolve(mention.name_raw, mention.ticker_guess, mention.market)
        resolved_by_idx.append(r)
        key = (r.ticker, r.market)
        if key in stock_id_map:
            continue
        stock_row = {
            "ticker": r.ticker,
            "market": r.market,
            "name_zh": r.name_zh,
            "name_en": r.name_en,
            "asset_type": r.asset_type,
        }
        res = (
            client.table("stocks")
            .upsert(stock_row, on_conflict="ticker,market")
            .execute()
        )
        stock_id_map[key] = res.data[0]["id"]

    # ── 3. mentions（先清除舊資料，再 insert） ────────────────
    client.table("mentions").delete().eq("episode_id", episode_id).execute()

    mention_rows = []
    for mention, r in zip(extraction.mentions, resolved_by_idx):
        stock_id = stock_id_map.get((r.ticker, r.market))
        mention_rows.append({
            "episode_id": episode_id,
            "stock_id": stock_id,
            "name_raw": mention.name_raw,
            "ticker_guess": mention.ticker_guess,
            "market": r.market,
            "asset_type": r.asset_type,
            "direction": mention.direction,
            "confidence": float(mention.confidence),
            "has_position": mention.has_position,
            "quote": mention.quote,
            "note": mention.note,
        })

    if mention_rows:
        client.table("mentions").insert(mention_rows).execute()

    return {
        "episode_id": episode_id,
        "stock_count": len(stock_id_map),
        "mention_count": len(mention_rows),
    }
