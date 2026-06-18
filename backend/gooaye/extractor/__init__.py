"""逐字稿抽取模組：用 OpenAI Structured Outputs 把單集轉成結構化資料。"""

from gooaye.extractor.schema import EpisodeExtraction, StockMention
from gooaye.extractor.extract import extract_episode

__all__ = ["EpisodeExtraction", "StockMention", "extract_episode"]
