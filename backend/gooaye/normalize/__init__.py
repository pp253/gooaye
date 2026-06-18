"""個股正規化：把 LLM 抽出的原始名稱統一成標準代號，並判定資產類型。"""

from gooaye.normalize.canonical import ResolvedStock, resolve

__all__ = ["ResolvedStock", "resolve"]
