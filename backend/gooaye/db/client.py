"""Supabase client（service_role，供後端寫入用）。"""

from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from gooaye import config


@lru_cache(maxsize=1)
def get_client() -> Client:
    url = config.get("SUPABASE_URL", required=True)
    key = config.get("SUPABASE_SERVICE_ROLE_KEY", required=True)
    return create_client(url, key)
