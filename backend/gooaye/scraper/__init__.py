"""逐字稿抓取模組。

主來源：whatmkreallysaid.com 官方 pack（pack.py）— 即時、含全部集數與日期。
舊版 fetch.py（/seo/*.html 靜態鏡像）已停用，僅留作參考。
"""

from gooaye.scraper.pack import Episode, fetch_pack, fetch_range, get_manifest

__all__ = ["Episode", "fetch_pack", "fetch_range", "get_manifest"]
