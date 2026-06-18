"""Supabase 資料庫存取層。"""

from gooaye.db.client import get_client
from gooaye.db.upsert import upsert_episode

__all__ = ["get_client", "upsert_episode"]
