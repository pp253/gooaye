"""呼叫 OpenAI（Structured Outputs）把單集逐字稿抽成 EpisodeExtraction。"""

from __future__ import annotations

import json
from pathlib import Path

from openai import OpenAI

from gooaye import config
from gooaye.extractor.schema import EpisodeExtraction

EXTRACTED_DIR = Path(__file__).resolve().parents[2] / "data" / "extracted"

_SYSTEM_PROMPT = """\
你是協助分析《股癌》Podcast（主持人謝孟恭）的金融研究助理。
任務：閱讀單集逐字稿，產出結構化摘要與「可投資標的」清單。

規則：
1. summary：用繁體中文條列該集 3~8 個重點，聚焦市場觀點與投資相關內容，略過贊助廣告與純閒聊。
2. mentions：只收錄謝孟恭明確表達投資觀點的標的（個股、ETF、產業龍頭、商品）。
   - 純粹舉例、玩笑、或毫無方向性的提及不要列入。
   - direction 反映他的整體傾向（看多/看空/中性）；拿不準時用『中性』並調低 confidence。
   - has_position 僅在他自述有持有/操作該標的時為 true。
   - quote 必須是逐字稿中真實出現的原句，不可改寫。
   - 同一檔在整集出現多次，合併成一筆、取最具代表性的觀點。
3. 全程使用繁體中文。不要杜撰逐字稿沒有的資訊。
"""


def extract_episode(
    transcript: str,
    *,
    client: OpenAI | None = None,
    model: str | None = None,
) -> EpisodeExtraction:
    """對單集逐字稿做抽取，回傳 EpisodeExtraction。"""
    client = client or OpenAI(api_key=config.OPENAI_API_KEY)
    model = model or config.OPENAI_EXTRACT_MODEL

    response = client.responses.parse(
        model=model,
        reasoning={"effort": "low"},
        input=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"以下是單集逐字稿：\n\n{transcript}"},
        ],
        text_format=EpisodeExtraction,
    )
    result = response.output_parsed
    if result is None:
        raise RuntimeError("OpenAI 未回傳可解析的結構化結果（可能被 refusal 或截斷）。")
    return result


def extract_from_raw(ep_no: int, *, client: OpenAI | None = None) -> EpisodeExtraction:
    """讀 data/raw/EP{n}.json，抽取後存到 data/extracted/EP{n}.json。"""
    raw_path = Path(__file__).resolve().parents[2] / "data" / "raw" / f"EP{ep_no}.json"
    raw = json.loads(raw_path.read_text(encoding="utf-8"))

    extraction = extract_episode(raw["transcript"], client=client)

    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = EXTRACTED_DIR / f"EP{ep_no}.json"
    payload = {
        "ep_no": ep_no,
        "title": raw.get("title", ""),
        "source_url": raw.get("source_url", ""),
        "published_at": raw.get("published_at", ""),
        **extraction.model_dump(),
    }
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return extraction
