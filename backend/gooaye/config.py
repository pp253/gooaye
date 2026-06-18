"""集中讀取環境變數（從專案根目錄的 .env）。"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_ENV_PATH)


def get(name: str, default: str | None = None, *, required: bool = False) -> str | None:
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(
            f"缺少環境變數 {name}；請在 {_ENV_PATH} 設定（可參考 .env.example）。"
        )
    return value


OPENAI_API_KEY = get("OPENAI_API_KEY")
OPENAI_EXTRACT_MODEL = get("OPENAI_EXTRACT_MODEL", "gpt-5.4-mini")
SUPABASE_URL = get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = get("SUPABASE_SERVICE_ROLE_KEY")
