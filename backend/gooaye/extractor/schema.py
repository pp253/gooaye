"""抽取結果的 Pydantic schema（同時作為 OpenAI Structured Outputs 的 json_schema）。

注意：Structured Outputs strict 模式下，所有欄位皆為必填；可選值用 `X | None` 表達。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Direction = Literal["看多", "看空", "中性"]
Market = Literal["TW", "US", "OTHER", "UNKNOWN"]


class StockMention(BaseModel):
    """一集裡對某一檔股票（或標的）的一次提及。"""

    name_raw: str = Field(description="逐字稿中出現的名稱，原樣保留（如『台積電』『輝達』『Nvidia』）")
    market: Market = Field(description="研判所屬市場：TW 台股 / US 美股 / OTHER 其他 / UNKNOWN 無法判斷")
    ticker_guess: str | None = Field(
        description="若能確定股票代號則填（台股如 2330、美股如 NVDA），不確定填 null"
    )
    direction: Direction = Field(description="謝孟恭對此標的的整體傾向")
    confidence: float = Field(description="對 direction 判斷的信心，0 到 1")
    has_position: bool = Field(description="謝孟恭是否自述持有/操作此標的的部位")
    quote: str = Field(description="支持上述判斷、最具代表性的一句原文引用")
    note: str = Field(description="一句話補充背景或理由")


class EpisodeExtraction(BaseModel):
    """單集逐字稿的抽取輸出。"""

    summary: list[str] = Field(description="該集重點，條列 3~8 點，每點一句話")
    topics: list[str] = Field(description="該集涵蓋的主題標籤，如『半導體』『聯準會』『財報』")
    mentions: list[StockMention] = Field(
        description="該集明確提到的可投資標的清單；純粹閒聊未涉投資觀點者不列入"
    )
