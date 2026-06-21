"""把 data/extracted/ 的 JSON 寫入 Supabase。

用法：
    python scripts/load_db.py 569 583
    python scripts/load_db.py          # 全部 extracted/EP*.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from gooaye.db import get_client, upsert_episode
from gooaye.extractor.schema import EpisodeExtraction

EXTRACTED_DIR = Path(__file__).resolve().parents[1] / "data" / "extracted"
RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"


def _load_raw(ep_no: int) -> dict:
    """讀 data/raw/EP{n}.json（逐字稿來源）；缺檔回空 dict。"""
    path = RAW_DIR / f"EP{ep_no}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    if len(sys.argv) == 3:
        eps = list(range(int(sys.argv[1]), int(sys.argv[2]) + 1))
    else:
        eps = sorted(int(p.stem[2:]) for p in EXTRACTED_DIR.glob("EP*.json"))

    client = get_client()
    print(f"寫入 Supabase，共 {len(eps)} 集 …")
    for ep_no in eps:
        path = EXTRACTED_DIR / f"EP{ep_no}.json"
        if not path.exists():
            print(f"  EP{ep_no}: 無抽取檔，略過")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        extraction = EpisodeExtraction.model_validate(data)
        raw = _load_raw(ep_no)  # 逐字稿 + 站方摘要
        result = upsert_episode(
            client,
            ep_no=ep_no,
            title=data.get("title", ""),
            source_url=data.get("source_url", ""),
            extraction=extraction,
            published_at=data.get("published_at") or None,
            transcript=raw.get("transcript") or None,
            site_desc=raw.get("site_desc") or None,
        )
        tx_n = result.get("transcript_chars")
        tx_info = f" tx={tx_n}字" if tx_n else " tx=無"
        print(
            f"  EP{ep_no}: episode_id={result['episode_id']} "
            f"stocks={result['stock_count']} mentions={result['mention_count']}{tx_info}"
        )
    print("完成")


if __name__ == "__main__":
    main()
