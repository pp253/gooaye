"""批次抽取 data/raw/ 內的逐字稿，輸出到 data/extracted/。

用法：
    python scripts/extract.py 569 583
"""

from __future__ import annotations

import sys
from pathlib import Path

from openai import OpenAI

from gooaye import config
from gooaye.extractor.extract import extract_from_raw

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"


def main() -> None:
    if len(sys.argv) == 3:
        eps = list(range(int(sys.argv[1]), int(sys.argv[2]) + 1))
    else:
        eps = sorted(
            int(p.stem[2:]) for p in RAW_DIR.glob("EP*.json")
        )
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    print(f"抽取模型：{config.OPENAI_EXTRACT_MODEL}；共 {len(eps)} 集")
    for ep in eps:
        if not (RAW_DIR / f"EP{ep}.json").exists():
            print(f"  EP{ep}: 無原始檔，略過")
            continue
        try:
            res = extract_from_raw(ep, client=client)
        except Exception as exc:  # noqa: BLE001 — 批次容錯，單集失敗不中斷
            print(f"  EP{ep}: 失敗 {type(exc).__name__}: {exc}")
            continue
        print(f"  EP{ep}: summary {len(res.summary)} 點 / mentions {len(res.mentions)} 檔 → 已存")


if __name__ == "__main__":
    main()
