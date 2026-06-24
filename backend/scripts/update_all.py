"""一鍵增量更新：偵測新集 → scrape→extract→load → 重抓股價 → 重跑回測。

本機與 GitHub Actions 共用。流程：
  1. 由 pack 取得最新 EP 編號。
  2. 查 Supabase 取得 DB 內最大 ep_no。
  3. 對缺口集數依序執行 scrape / extract / load_db（透過既有 scripts）。
  4. 一律執行 fetch_prices（失敗不致命）+ run_analytics。

用法：
    python scripts/update_all.py            # 增量
    python scripts/update_all.py --full N   # 強制重抓 1..N（很少用）
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from gooaye.db import get_client
from gooaye.scraper.pack import list_available_ep_nos

SCRIPTS = Path(__file__).resolve().parent
PY = sys.executable


def _run(script: str, *args: str, fatal: bool = True) -> int:
    """執行 scripts/<script>，回傳 returncode。fatal=False 時失敗只警告。"""
    cmd = [PY, str(SCRIPTS / script), *args]
    print(f"\n$ {' '.join(cmd)}", flush=True)
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        msg = f"⚠ {script} 失敗（exit {proc.returncode}）"
        if fatal:
            raise SystemExit(msg)
        print(msg, flush=True)
    return proc.returncode


def _db_max_ep(client) -> int:
    """DB 內最大 ep_no；空表回 0。"""
    res = (
        client.table("episodes")
        .select("ep_no")
        .order("ep_no", desc=True)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return int(rows[0]["ep_no"]) if rows else 0


def main() -> None:
    args = sys.argv[1:]

    print("取得 pack 最新集數 …", flush=True)
    available = list_available_ep_nos()
    latest = available[-1]
    print(f"  pack 最新：EP{latest}", flush=True)

    client = get_client()

    if len(args) == 2 and args[0] == "--full":
        start, end = 1, int(args[1])
    else:
        db_max = _db_max_ep(client)
        print(f"  DB 最大：EP{db_max}", flush=True)
        start, end = db_max + 1, latest

    if start <= end:
        print(f"\n=== 增量處理 EP{start}–EP{end} ===", flush=True)
        _run("scrape.py", str(start), str(end))
        _run("extract.py", str(start), str(end))
        _run("load_db.py", str(start), str(end))
    else:
        print("\n=== 無新集，跳過 scrape/extract/load ===", flush=True)

    # 股價即使無新集也每日刷新；yfinance 偶爾被限流 → 失敗不阻斷 analytics
    print("\n=== 重抓股價 ===", flush=True)
    _run("fetch_prices.py", fatal=False)

    print("\n=== 重跑跟單績效 + 回測 ===", flush=True)
    _run("run_analytics.py")

    print("\n✅ update_all 完成", flush=True)


if __name__ == "__main__":
    main()
