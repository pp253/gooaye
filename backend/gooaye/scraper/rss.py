"""從股癌 SoundOn RSS feed 取得每集發布日期。

RSS:   https://feeds.soundon.fm/podcasts/954689a5-3096-43a4-a80b-7810b219cef3.xml
title 格式： "EP671 | 🌼" → 以正規式抽 EP 編號，pubDate 轉成 date。
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime

import httpx

RSS_URL = "https://feeds.soundon.fm/podcasts/954689a5-3096-43a4-a80b-7810b219cef3.xml"
_EP_RE = re.compile(r"EP\s*(\d+)")


def fetch_ep_dates() -> dict[int, str]:
    """回傳 {ep_no: 'YYYY-MM-DD'}。"""
    resp = httpx.get(RSS_URL, follow_redirects=True, timeout=60)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)

    result: dict[int, str] = {}
    for item in root.findall(".//item"):
        title = item.findtext("title", "")
        match = _EP_RE.search(title)
        if not match:
            continue
        ep_no = int(match.group(1))
        pub_raw = item.findtext("pubDate", "")
        try:
            dt: datetime = parsedate_to_datetime(pub_raw)
        except (TypeError, ValueError):
            continue
        result[ep_no] = dt.date().isoformat()
    return result
