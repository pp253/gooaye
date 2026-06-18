"""從 whatmkreallysaid.com 抓取並解析單集股癌逐字稿。

頁面結構（經實測）：
  URL:   https://whatmkreallysaid.com/seo/{ep}.html  （{ep} 即 EP 編號）
  title: <title>股癌逐字稿 EP500：🦀</title>
  正文:  <h2>逐字稿內容</h2> 之後一連串 <p>…</p>
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx
from selectolax.parser import HTMLParser

BASE_URL = "https://whatmkreallysaid.com/seo/{ep}.html"
RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

_TITLE_RE = re.compile(r"EP\s*(\d+)\s*[:：]\s*(.*)$")
_USER_AGENT = "gooaye-tracker/0.1 (personal research)"


@dataclass(slots=True)
class Episode:
    """單集逐字稿的結構化結果。"""

    ep_no: int
    title: str  # 標題尾端的 emoji / 副標
    source_url: str
    transcript: str  # 純文字，段落以 \n 分隔
    paragraph_count: int
    char_count: int


def _parse(ep_no: int, source_url: str, html: str) -> Episode:
    """將單集 HTML 解析為 Episode。"""
    tree = HTMLParser(html)

    title_node = tree.css_first("title")
    title_text = title_node.text() if title_node else ""
    match = _TITLE_RE.search(title_text)
    if match:
        parsed_ep, subtitle = int(match.group(1)), match.group(2).strip()
        if parsed_ep != ep_no:
            raise ValueError(f"EP 編號不符：URL={ep_no} 但標題為 {parsed_ep}")
    else:
        subtitle = ""

    # 逐字稿正文：定位 h2「逐字稿內容」，取其後同層的 <p>。
    paragraphs: list[str] = []
    heading = next(
        (h for h in tree.css("h2") if "逐字稿內容" in h.text()), None
    )
    if heading is not None:
        node = heading.next
        while node is not None:
            if node.tag == "p":
                text = node.text(strip=True)
                if text:
                    paragraphs.append(text)
            elif node.tag in ("h1", "h2"):
                break  # 進入下一段落區塊就停
            node = node.next

    # 後備：若上面抓不到（DOM 結構變動），退而求其次抓全部 <p>。
    if not paragraphs:
        paragraphs = [
            p.text(strip=True) for p in tree.css("p") if p.text(strip=True)
        ]

    transcript = "\n".join(paragraphs)
    return Episode(
        ep_no=ep_no,
        title=subtitle,
        source_url=source_url,
        transcript=transcript,
        paragraph_count=len(paragraphs),
        char_count=len(transcript),
    )


def fetch_episode(ep_no: int, *, client: httpx.Client | None = None) -> Episode:
    """抓取並解析指定集數。失敗（404 等）會 raise httpx.HTTPStatusError。"""
    url = BASE_URL.format(ep=ep_no)
    owns_client = client is None
    client = client or httpx.Client(
        follow_redirects=True,
        timeout=30,
        headers={"User-Agent": _USER_AGENT},
    )
    try:
        resp = client.get(url)
        resp.raise_for_status()
        return _parse(ep_no, url, resp.text)
    finally:
        if owns_client:
            client.close()


def save_episode(episode: Episode, *, raw_dir: Path = RAW_DIR) -> Path:
    """把單集存成 JSON（data/raw/EP{n}.json）。"""
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"EP{episode.ep_no}.json"
    path.write_text(
        json.dumps(asdict(episode), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def fetch_range(
    start: int, end: int, *, delay: float = 1.0, raw_dir: Path = RAW_DIR
) -> list[Episode]:
    """抓取 [start, end]（含端點）區間的集數，禮貌性延遲 delay 秒。"""
    episodes: list[Episode] = []
    with httpx.Client(
        follow_redirects=True, timeout=30, headers={"User-Agent": _USER_AGENT}
    ) as client:
        for ep_no in range(start, end + 1):
            try:
                episode = fetch_episode(ep_no, client=client)
            except httpx.HTTPStatusError as exc:
                print(f"  EP{ep_no}: 略過（HTTP {exc.response.status_code}）")
                continue
            save_episode(episode, raw_dir=raw_dir)
            episodes.append(episode)
            print(
                f"  EP{ep_no}: {episode.paragraph_count} 段 / "
                f"{episode.char_count} 字 → 已存"
            )
            time.sleep(delay)
    return episodes
