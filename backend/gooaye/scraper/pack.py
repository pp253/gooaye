"""從 whatmkreallysaid.com 的官方資料 pack 取得逐字稿。

主站首頁載入的是單一 brotli 壓縮 JSON pack（每日重建，含全部集數）：
  manifest:  https://whatmkreallysaid.com/pack_manifest.json
  pack:      https://whatmkreallysaid.com/transcripts.json.br

每筆 entry 欄位：
  n   集數編號          t    標題（含描述）
  d   日期 YYYY-MM-DD   dt   格式化日期
  desc 官方摘要         tx   完整逐字稿

這是主站真正的即時來源（取代過時的 /seo/*.html SEO 靜態鏡像）。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import brotli
import httpx

MANIFEST_URL = "https://whatmkreallysaid.com/pack_manifest.json"
PACK_URL = "https://whatmkreallysaid.com/transcripts.json.br"
EPISODES_JSON_URL = "https://whatmkreallysaid.com/episodes.json"
# 新格式：episode.html?file=EP{n}_{title}.md（從 episodes.json 取 filename）
EPISODE_BASE_URL = "https://whatmkreallysaid.com/episode.html?file={filename}"
EPISODE_URL_FALLBACK = "https://whatmkreallysaid.com/episode.html?file=EP{ep}"  # 若無 filename 時的 fallback
RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

_USER_AGENT = "gooaye-tracker/0.2 (personal research)"


@dataclass(slots=True)
class Episode:
    ep_no: int
    title: str
    source_url: str
    published_at: str  # YYYY-MM-DD
    site_desc: str  # 站方摘要（非我們 LLM 產的）
    transcript: str
    char_count: int


def fetch_pack() -> list[dict]:
    """下載並解壓官方 pack，回傳 entry list。"""
    resp = httpx.get(
        PACK_URL, follow_redirects=True, timeout=120,
        headers={"User-Agent": _USER_AGENT},
    )
    resp.raise_for_status()
    # httpx 若見 Content-Encoding: br 會自動解壓；否則 content 仍是 brotli。
    raw = resp.content
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return json.loads(brotli.decompress(raw))


def get_manifest() -> dict:
    resp = httpx.get(MANIFEST_URL, follow_redirects=True, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_episode_filenames() -> dict[int, str]:
    """從 episodes.json 取得 ep_no → filename 對照表（用於組正確的 source_url）。"""
    resp = httpx.get(
        EPISODES_JSON_URL, follow_redirects=True, timeout=30,
        headers={"User-Agent": _USER_AGENT},
    )
    resp.raise_for_status()
    return {int(e["number"]): e["filename"] for e in resp.json()}


def _to_episode(entry: dict, filename: str | None = None) -> Episode:
    ep_no = int(entry["n"])
    transcript = entry.get("tx", "") or ""
    if filename:
        source_url = EPISODE_BASE_URL.format(filename=filename)
    else:
        source_url = EPISODE_URL_FALLBACK.format(ep=ep_no)
    return Episode(
        ep_no=ep_no,
        title=entry.get("t", ""),
        source_url=source_url,
        published_at=entry.get("d", ""),
        site_desc=entry.get("desc", ""),
        transcript=transcript,
        char_count=len(transcript),
    )


def save_episode(episode: Episode, *, raw_dir: Path = RAW_DIR) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"EP{episode.ep_no}.json"
    path.write_text(
        json.dumps(asdict(episode), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def list_available_ep_nos() -> list[int]:
    """回傳 pack 內所有已知集數（排序後）。"""
    pack = fetch_pack()
    return sorted(int(e["n"]) for e in pack if (e.get("tx") or "").strip())


def fetch_range(
    start: int, end: int, *, raw_dir: Path = RAW_DIR
) -> list[Episode]:
    """從 pack 取出 [start, end]（含端點）的集數並存檔。"""
    pack = fetch_pack()
    by_no = {int(e["n"]): e for e in pack}
    # 取 filename 對照表，讓 source_url 用正確格式（含標題）
    try:
        filenames = get_episode_filenames()
    except Exception as exc:
        print(f"  ⚠ 無法取得 episodes.json（{exc}），source_url 將用 fallback 格式")
        filenames = {}
    episodes: list[Episode] = []
    for ep_no in range(start, end + 1):
        entry = by_no.get(ep_no)
        if entry is None:
            print(f"  EP{ep_no}: pack 中無此集，略過")
            continue
        if not (entry.get("tx") or "").strip():
            print(f"  EP{ep_no}: pack 中無逐字稿內容，略過")
            continue
        episode = _to_episode(entry, filename=filenames.get(ep_no))
        save_episode(episode, raw_dir=raw_dir)
        episodes.append(episode)
        print(
            f"  EP{ep_no} ({episode.published_at}): "
            f"{episode.char_count} 字 → 已存"
        )
    return episodes
