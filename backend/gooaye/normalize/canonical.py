"""把抽取出的原始標的名稱正規化成標準代號，並判定資產類型。

判定優先序：
  1. 人工對照表 CANONICAL（含外國股、常見別名）— 最可靠
  2. 已知 ETF / 指數 / 商品名單
  3. LLM 給了真實代號（非中文）→ 個股
  4. 其餘（只有中文 slug、無真實代號）→ 題材

資產類型：個股 | ETF | 題材 | 指數 | 商品
市場：TW | US | OTHER（含日韓等）| UNKNOWN
"""

from __future__ import annotations

import re
from dataclasses import dataclass

ASSET_STOCK = "個股"
ASSET_ETF = "ETF"
ASSET_THEME = "題材"
ASSET_INDEX = "指數"
ASSET_COMMODITY = "商品"


@dataclass(slots=True)
class ResolvedStock:
    ticker: str
    market: str
    name_zh: str
    name_en: str | None
    asset_type: str


def _key(s: str) -> str:
    return re.sub(r"\s+", "", s.strip()).lower()


def _has_cjk(s: str) -> bool:
    return any("一" <= ch <= "鿿" for ch in s)


def _slug(s: str) -> str:
    return re.sub(r"\s+", "_", s.strip()).upper()


def _norm_market(market: str) -> str:
    return market if market in ("TW", "US", "OTHER", "UNKNOWN") else "OTHER"


# ── 1. 人工對照表（別名 → 標準資料）─────────────────────────────
# key 為小寫去空白後的原始名稱。涵蓋常被點名但 LLM 容易漏代號的外國股，
# 以及需要統一市場/代號的常見台美股。
_C = ResolvedStock


def _canon() -> dict[str, ResolvedStock]:
    table: dict[str, ResolvedStock] = {}

    def add(aliases: list[str], r: ResolvedStock) -> None:
        for a in aliases:
            table[_key(a)] = r

    # 外國股（日 / 韓），統一歸 OTHER 並補交易所代號
    add(["村田", "村田製作所", "murata"], _C("6981.T", "OTHER", "村田製作所", "Murata", ASSET_STOCK))
    add(["瑞薩", "瑞薩電子", "renesas"], _C("6723.T", "OTHER", "瑞薩電子", "Renesas", ASSET_STOCK))
    add(["三星", "三星電子", "samsung"], _C("005930.KS", "OTHER", "三星電子", "Samsung", ASSET_STOCK))
    add(
        ["海力士", "sk海力士", "sk_海力士", "sk hynix", "hynix"],
        _C("000660.KS", "OTHER", "SK 海力士", "SK Hynix", ASSET_STOCK),
    )
    add(["康寧", "corning"], _C("GLW", "US", "康寧", "Corning", ASSET_STOCK))
    add(["台積電", "tsmc"], _C("2330", "TW", "台積電", "TSMC", ASSET_STOCK))
    add(["聯發科", "mediatek"], _C("2454", "TW", "聯發科", "MediaTek", ASSET_STOCK))
    add(["輝達", "nvidia", "輝達nvidia"], _C("NVDA", "US", "輝達", "NVIDIA", ASSET_STOCK))
    add(["TDK", "tdk"], _C("6762.T", "OTHER", "TDK", "TDK", ASSET_STOCK))
    add(["太陽誘電", "taiyo yuden"], _C("6976.T", "OTHER", "太陽誘電", "Taiyo Yuden", ASSET_STOCK))
    add(["panasonic", "松下", "國際牌"], _C("6752.T", "OTHER", "Panasonic", "Panasonic", ASSET_STOCK))
    add(["nichicon"], _C("6996.T", "OTHER", "Nichicon", "Nichicon", ASSET_STOCK))
    add(["nippon chemi-con", "黑金剛"], _C("6997.T", "OTHER", "Nippon Chemi-Con", "Nippon Chemi-Con", ASSET_STOCK))
    add(["三星電機", "samsung electro-mechanics", "三星電機semco"], _C("009150.KS", "OTHER", "三星電機", "Samsung Electro-Mechanics", ASSET_STOCK))
    add(["meiko", "名幸"], _C("6787.T", "OTHER", "Meiko", "Meiko", ASSET_STOCK))

    # 美股（LLM 常以英文名出現但漏代號，或與英文名重複需合併）
    add(["美光", "micron"], _C("MU", "US", "美光", "Micron", ASSET_STOCK))
    add(["sandisk"], _C("SNDK", "US", "SanDisk", "SanDisk", ASSET_STOCK))
    add(["coherent"], _C("COHR", "US", "Coherent", "Coherent", ASSET_STOCK))
    add(["lumentum"], _C("LITE", "US", "Lumentum", "Lumentum", ASSET_STOCK))
    add(["amphenol"], _C("APH", "US", "Amphenol", "Amphenol", ASSET_STOCK))
    add(["nebius"], _C("NBIS", "US", "Nebius", "Nebius", ASSET_STOCK))
    add(["klarna"], _C("KLAR", "US", "Klarna", "Klarna", ASSET_STOCK))

    # 台股（英文/別名）
    add(["廣達", "quanta"], _C("2382", "TW", "廣達", "Quanta", ASSET_STOCK))
    add(["京元電", "kyec"], _C("2449", "TW", "京元電子", "KYEC", ASSET_STOCK))
    add(["國巨", "yageo"], _C("2327", "TW", "國巨", "Yageo", ASSET_STOCK))

    # ETF
    add(["0050", "元大台灣50"], _C("0050", "TW", "元大台灣50", "Yuanta 0050", ASSET_ETF))
    add(["0056", "元大高股息"], _C("0056", "TW", "元大高股息", "Yuanta 0056", ASSET_ETF))

    return table


CANONICAL = _canon()

# ── 2. 名單式判定 ───────────────────────────────────────────────
_ETF_TICKERS = {
    "SPY", "QQQ", "VOO", "VTI", "DIA", "IWM", "SOXX", "SMH", "SOXL",
    "TQQQ", "ARKK", "XLK", "XLE", "XLF", "0050", "0056", "00878", "00919",
}
_ETF_NAME_HINTS = ("etf",)

_INDEX_NAMES = {
    "台股", "大盤", "加權指數", "台股大盤", "美股", "美股大盤", "費半",
    "費城半導體", "費半指數", "標普", "標普500", "s&p500", "sp500",
    "那斯達克", "納斯達克", "nasdaq", "道瓊", "道瓊斯",
}

_COMMODITY_NAMES = {
    "原油", "石油", "黃金", "白銀", "天然氣", "銅", "比特幣", "bitcoin", "btc",
    "以太幣", "ethereum", "eth",
}

# VIX 等視為指數
_INDEX_TICKERS = {"VIX", "SOX", "SPX", "NDX", "DJI"}

# 看起來像代號、實則是技術術語/產品/人名/私人公司 → 不是可交易個股，歸題材
_NON_SECURITY = {
    # 技術/產品術語
    "tpu", "cpu", "gpu", "npu", "cpo", "lpu", "esd", "tvs", "vr", "ar",
    "ai", "hbm", "nand", "dram", "mlcc", "ssd", "pcb", "maco", "power",
    "m-core", "llm", "rtx", "rtx spark", "aws", "aws graviton", "aws graviton5",
    "tsv", "ipu", "asic", "fpga", "edge computing", "sora", "llama",
    "meta ai", "epi memory", "old ai", "老 ai", "老_ai", "ddr5", "ufs",
    # 私人公司 / 產品 / 平台
    "openai", "anthropic", "spacex", "starlink", "sifive", "graviton",
    # 人名
    "michael burry", "jensen", "黃仁勳", "馬斯克", "musk",
}

# 真實代號樣式：英數（可含 . - 交易所後綴）且不含中文
_TICKER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.\-]{0,12}$")
# 純英文代號樣式（用於從 name_raw 回收代號）：2~5 個大寫字母
_PURE_TICKER_RE = re.compile(r"^[A-Z]{2,5}$")


def resolve(name_raw: str, ticker_guess: str | None, market: str) -> ResolvedStock:
    """把單筆提及正規化成標準個股資料。"""
    key = _key(name_raw)

    # 1. 人工對照表
    if key in CANONICAL:
        return CANONICAL[key]

    tg = (ticker_guess or "").strip().upper()
    nr = name_raw.strip().upper()

    # 非證券（技術術語/產品/人名/私人公司）→ 題材，不進個股清單
    if key in _NON_SECURITY:
        return _C(_slug(name_raw), "OTHER", name_raw.strip(), None, ASSET_THEME)

    # 指數（含 VIX 等代號，可能出現在 ticker_guess 或 name_raw）
    if key in _INDEX_NAMES or tg in _INDEX_TICKERS or nr in _INDEX_TICKERS:
        return _C(tg or nr, _norm_market(market), name_raw.strip(), None, ASSET_INDEX)

    # ETF
    if tg in _ETF_TICKERS or any(h in key for h in _ETF_NAME_HINTS):
        ticker = tg if tg and not _has_cjk(tg) else _slug(name_raw)
        return _C(ticker, _norm_market(market), name_raw.strip(), None, ASSET_ETF)

    # 商品
    if key in _COMMODITY_NAMES:
        return _C(_slug(name_raw), "OTHER", name_raw.strip(), None, ASSET_COMMODITY)

    # LLM 給了真實代號 → 個股
    if tg and _TICKER_RE.match(tg) and not _has_cjk(tg):
        return _C(tg, _norm_market(market), name_raw.strip(), None, ASSET_STOCK)

    # 從 name_raw 回收代號：原始名稱本身就是純英文代號（如 ASTS、AXTI）→ 個股
    if _PURE_TICKER_RE.match(nr):
        return _C(nr, _norm_market(market), name_raw.strip(), None, ASSET_STOCK)

    # 其餘（只有中文 slug、無真實代號）→ 視為題材
    return _C(_slug(name_raw), "OTHER", name_raw.strip(), None, ASSET_THEME)
