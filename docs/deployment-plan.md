# 部署計畫 — GitHub Pages + Cloudflare 網域 + Actions 排程

> 目標：把 frontend build 部署到 GitHub Pages，自訂網域 `stocks.keep.party`（DNS 走 Cloudflare），
> 在 pp253 個人 GitHub 建立 public repo `gooaye`，並用 GitHub Actions 做 podcast 定期增量抓取。
> 建立日期：2026-06-24。

## 既定決策

| 項目 | 決定 |
|---|---|
| Repo | `pp253/gooaye`，**public**（免費方案 Pages + 自訂網域） |
| 推送範圍 | 整個 monorepo（backend + frontend + supabase + scripts） |
| Actions 資料管線 | **建置並啟用排程**（每日 cron + 手動觸發） |
| 自訂網域 | `stocks.keep.party`，DNS 由 Cloudflare 管理，先 DNS-only（灰雲） |

## 既有設定盤點

- `vite.config.ts` 未設 `base`（預設 `/`）→ 自訂網域走 root，不需改。
- Router 為 `createWebHistory`（HTML5 history）→ Pages 深層連結重整會 404 → 需 `404.html` fallback。
- 專案目前**無任何 git remote**；`.env`、`backend/data/raw|extracted/`、`frontend/dist`、`node_modules` 皆已 gitignore。
- `gh` 已登入 pp253（含 `repo` 權限）。
- frontend 讀 `VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY`（build 時注入）。anon key 設計上即為公開、且有 RLS 白名單保護。

## 階段

### A. 安全掃描（public 前置）
- `git grep` 與掃描 git 歷史，確認 service_role / OpenAI key 未被 commit 進任何追蹤檔。
- 確認 `.env`、`data/` 不在版控中。

### B. 建 repo + 推送
- `gh repo create pp253/gooaye --public --source=. --remote=origin`
- 推 `main`。

### C. SPA 調整
- 新增 `frontend/public/CNAME`，內容 `stocks.keep.party`（隨 build 進 dist，維持自訂網域）。
- build 後 `cp dist/index.html dist/404.html`（在 deploy workflow 內做），解決 history-mode 深層連結 404。
- `base` 維持 `/`。

### D. Pages 部署 workflow（`.github/workflows/deploy.yml`）
- 觸發：push 到 `main`（`frontend/**`）+ `workflow_dispatch`。
- 步驟：checkout → setup node → `npm ci` → `npm run build`（注入 `VITE_SUPABASE_*` secrets）→ `cp dist/index.html dist/404.html` → `upload-pages-artifact` → `deploy-pages`。
- 權限：`pages: write`、`id-token: write`。
- 用 `gh api` 設定 Pages build_type=`workflow` 與 custom domain（cname）。
- Secrets：`VITE_SUPABASE_URL`、`VITE_SUPABASE_ANON_KEY`。

### E. 資料管線
- 新增 `backend/scripts/update_all.py`：
  1. 由 pack 取得最新 EP 編號。
  2. 查 Supabase 取得 DB 內最大 ep_no。
  3. 對缺口集數依序 scrape → extract → load_db。
  4. 一律執行 fetch_prices（含重試、失敗不致命）+ run_analytics。
- 新增 `.github/workflows/update-data.yml`：
  - 觸發：`schedule`（cron `0 1 * * *`，UTC 01:00 = 台灣 09:00）+ `workflow_dispatch`。
  - 用 `astral-sh/setup-uv`，`uv sync`，執行 `update_all.py`。
  - Secrets：`OPENAI_API_KEY`、`OPENAI_EXTRACT_MODEL`、`SUPABASE_URL`、`SUPABASE_SERVICE_ROLE_KEY`、`SUPABASE_ANON_KEY`。
- 風險：yfinance 從 GitHub 雲端 IP 可能被 Yahoo 限流 → 加重試；prices 失敗不阻斷 analytics。OpenAI 僅在有新集才產生成本。

### F. Cloudflare DNS（透過 Chrome）
- 確認 `keep.party` 在使用者 Cloudflare 帳號。
- 新增 CNAME：`stock` → `pp253.github.io`，**DNS-only（灰雲）**，讓 GitHub 簽 HTTPS 憑證。

### G. 自訂網域 + HTTPS
- repo Settings → Pages 設 custom domain `stocks.keep.party`。
- DNS 生效、憑證簽好後開 Enforce HTTPS。

### H. Supabase Auth redirect
- `supabase/config.toml` 的 `site_url` / `additional_redirect_urls` 加入 `https://stocks.keep.party`。
- `set -a && . ./.env && set +a && npx supabase config push`。
- Google OAuth callback 不變（仍指向 supabase callback）。

## 驗證
- Pages 部署成功、`https://stocks.keep.party` 可開、登入流程正常。
- 手動觸發 `update-data.yml` 跑一次，確認增量管線可在 CI 完成。
