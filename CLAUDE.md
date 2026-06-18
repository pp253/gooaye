# CLAUDE.md — 股癌個股追蹤系統 接手指南

> 給下一個 Claude Code session：先讀完這份再動工。這是整個專案的單一事實來源（single source of truth）。
> 對話請用**繁體中文**、比較用表格、選擇用 AskUserQuestion、執行計畫前先取得使用者明確同意。

---

## 0. 這個專案是什麼

追蹤《股癌》Podcast（主持人謝孟恭）每集提到的股票，協助使用者「靠他的 podcast 決定買哪些股票」。三大功能：
1. **每集 summary** — LLM 抽出重點與提及個股
2. **個股追蹤** — 某檔股票被提到的時間軸、方向（看多/看空/中性）、信心、他是否有部位、時效性
3. **回測** — 把「他看多」當訊號模擬進出場，跟各市場基準比較

核心理念：**時效性**。同樣「看多」，上週講的 ≫ 半年前講的。整個 UI 圍繞「現在還算不算數」設計。

---

## 1. 現況（截至 2026-06-18）

- **資料**：已抓並處理 **EP622–671（50 集，2026 年 1–6 月）**，最新一集 EP671（2026-06-17）。
- **股價**：137 檔個股/ETF + 基準，約 14 個月日收盤，共 ~32,000 筆。
- **回測**：三種規則 + 命中率已跑通，結果存在 `backtest_runs`。
- **前端**：決策面板 / 個股追蹤 / 個股詳情 / 回測 / 集數列表 全部可用，已部署為 Vite dev（`npm run dev`，port 5173）。
- 全部資料在 **Supabase cloud**（見 §4），前端用 anon key 直接查。

### 環境注意（重要）
- 這個環境的「今天」是 **2026 年 6 月**（相對訓練資料是未來）。**不要把日期當成錯誤去「修正」**，股價/集數日期都是 2026 年是正常的。
- Python 用 **uv** 管理（見 §3）。Node 26、Vue 3 + TS。

---

## 2. 專案結構

```
gooaye/
├── CLAUDE.md                    ← 本檔
├── .env                         ← 後端金鑰（gitignored，本機才有；見 §7）
├── backend/
│   ├── pyproject.toml           ← uv 依賴定義；gooaye 設為可安裝套件
│   ├── uv.lock
│   ├── gooaye/
│   │   ├── config.py            ← 讀 .env
│   │   ├── scraper/
│   │   │   ├── pack.py          ← ✅ 主來源：抓 transcripts.json.br（含日期+逐字稿）
│   │   │   ├── fetch.py         ← ⚠️ 已停用（/seo 靜態鏡像，停在 EP583）
│   │   │   └── rss.py           ← 早期 RSS 補日期，現已不需要（pack 自帶日期）
│   │   ├── extractor/
│   │   │   ├── schema.py        ← Pydantic：EpisodeExtraction / StockMention
│   │   │   └── extract.py       ← OpenAI Structured Outputs 抽取
│   │   ├── normalize/
│   │   │   └── canonical.py     ← 中文名→標準代號 + 資產類型判定（個股/ETF/題材/指數/商品）
│   │   ├── db/
│   │   │   ├── client.py        ← Supabase client（service_role）
│   │   │   └── upsert.py        ← 寫 episodes/stocks/mentions（經 normalize）
│   │   ├── prices/
│   │   │   └── fetch.py         ← yfinance 抓收盤 → prices 表
│   │   └── analytics/
│   │       ├── prices.py        ← PriceBook：載入全部股價 + 各市場基準
│   │       ├── performance.py   ← 算 stock_performance（現價、首次/最近看多至今報酬）
│   │       └── backtest.py      ← 三策略 + 命中率 + 每筆交易明細 → backtest_runs
│   ├── scripts/                 ← 全部用 `uv run python scripts/xxx.py` 執行
│   │   ├── scrape.py <start> <end>
│   │   ├── extract.py <start> <end>
│   │   ├── load_db.py <start> <end>
│   │   ├── fetch_prices.py [--missing]
│   │   ├── run_analytics.py
│   │   └── backfill_dates.py    ← 已不需要（pack 自帶日期）
│   └── data/                    ← gitignored；raw/EP*.json、extracted/EP*.json
├── frontend/
│   ├── .env                     ← VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY（gitignored）
│   └── src/
│       ├── lib/
│       │   ├── supabase.ts      ← anon client
│       │   ├── types.ts         ← Episode/Stock/Mention/StockPerformance/AssetType…
│       │   ├── signal.ts        ← 時間衰減訊號分數、freshness、relativeTime、computeSignal
│       │   ├── useData.ts       ← loadStockSignals()：組裝 stocks+mentions+performance+近30天股價
│       │   ├── format.ts        ← pct/rate/retColor
│       │   └── useQuerySync.ts  ← 篩選狀態 ↔ 網址 query 雙向同步
│       ├── components/
│       │   ├── PriceChart.vue       ← 股價走勢 + 提及點標記 + hover 提示
│       │   ├── TrajectoryChart.vue  ← 觀點演變（方向×信心 時間軸）+ hover 提示
│       │   ├── MentionTip.vue       ← 兩圖共用的 hover 浮框
│       │   ├── Sparkline.vue        ← 個股列表的近30天迷你圖
│       │   └── EquityChart.vue      ← 回測資金曲線
│       └── views/
│           ├── DecisionHome.vue ← 「/」決策面板：他有部位/高分看多/最新提及
│           ├── StockList.vue    ← 個股追蹤表（篩選、排序、現價、迷你圖、表現）
│           ├── StockDetail.vue  ← 單股：立場+現價合併卡、時間範圍選擇器、兩張圖、提及紀錄
│           ├── BacktestView.vue ← 回測：三策略表、資金曲線、區間篩選、最佳/最差、命中率
│           ├── EpisodeList.vue / EpisodeDetail.vue
│           └── router/index.ts
└── supabase/migrations/         ← 20260617000001_init / _002_asset_type / 20260618000001_analytics
```

---

## 3. 資料管線（如何更新資料）

全部在 `backend/` 下用 **uv** 執行（不需 `PYTHONPATH`，gooaye 已安裝為套件）：

```bash
cd backend
uv sync                                   # 還原環境（首次/換機）
uv run python scripts/scrape.py 622 671   # 1. 從 pack 抓逐字稿 → data/raw/
uv run python scripts/extract.py 622 671  # 2. OpenAI 抽取 → data/extracted/（有 API 成本）
uv run python scripts/load_db.py 622 671  # 3. 正規化 + 寫入 Supabase
uv run python scripts/fetch_prices.py     # 4. yfinance 抓股價 → prices 表
uv run python scripts/run_analytics.py    # 5. 算 stock_performance + 跑回測
```

- 加新套件：`uv add <pkg>`。
- **抓更多集數**：把範圍改成 `1 671` 即可（pack 有全部 671 集）。成本主要在 step 2（OpenAI）。
- **每次出新集數的增量更新**：`scrape N N` → `extract N N` → `load_db N N` →（重跑）`fetch_prices` + `run_analytics`。
- 可考慮包成一支 `update_all.py`（使用者問過，尚未做）。

---

## 4. Supabase

- Project：**gooaye**，ref `ydzqxeckreqpoydpwbtf`，region `ap-northeast-1`，org `pp253`。
- CLI：本機用 `npx supabase`（未裝全域）。已 `link` 到該 project。
- 推 migration：`npx supabase db push`（會出現 Docker 警告，那是 local dev 才需要，**cloud push 仍會成功**）。
- 連線金鑰在 `.env` / `frontend/.env`（§7）。

### Schema（表）
| 表 | 用途 | 關鍵欄位 |
|---|---|---|
| `episodes` | 一集一列 | ep_no, title, source_url, **published_at**, summary(text[]), topics(text[]) |
| `stocks` | 個股主檔 | ticker, market(TW/US/OTHER/UNKNOWN), name_zh, name_en, **asset_type**(個股/ETF/題材/指數/商品), unique(ticker,market) |
| `mentions` | 一集提到一檔一次 | episode_id, stock_id, name_raw, ticker_guess, market, asset_type, direction(看多/看空/中性), confidence(0-1), has_position, quote, note |
| `prices` | 日收盤 | stock_id, date, close, unique(stock_id,date) |
| `stock_performance` | 跟單績效快照 | current_price, first_bull_*, ret_since_first_bull, last_bull_*, ret_since_last_bull |
| `backtest_runs` | 回測結果 | reference_date, **results(jsonb)**（內含 strategies[含每筆 trades]、hit_rate） |

- 全表開 RLS、public read（前端 anon 可讀）；寫入只透過後端 service_role。

---

## 5. 關鍵決策（為什麼這樣做）

| 決策 | 內容 | 理由 |
|---|---|---|
| 逐字稿來源 | `whatmkreallysaid.com/transcripts.json.br`（brotli，單檔含全部集） | 即時、純 HTTP、自帶日期+逐字稿。**不要用 /seo/*.html（停在 EP583）** |
| 抽取模型 | **OpenAI `gpt-5.4-mini`**（Structured Outputs, strict json_schema） | 使用者的 OpenAI key 該 project **只有 gpt-5.4 系列權限**（沒有 gpt-5/gpt-5-mini）。改模型前先 `client.models.list()` 確認 |
| 個股正規化 | canonical 對照表 + 規則：真實代號→個股；中文 slug→題材；全大寫2-5字母→個股；黑名單(人名/產品/術語)→題材 | 把「被動元件」「OpenAI」「Michael Burry」這類非個股濾掉，外國股(村田 6981.T、三星 005930.KS)補代號 |
| 股價 | yfinance；TW 加 `.TW`、US 原樣、OTHER 已含後綴(.T/.KS) | 單一來源涵蓋台/美/日/韓 |
| 股價抓取起點 | min(首次提及−5天, 今天−420天) | 讓「1年/半年」時間範圍有資料 |
| 訊號分數 | Σ 方向權重 × 信心 × e^(−Δ天/半衰期)，半衰期 30 天 | 近期觀點自動浮上來 |
| 新鮮度 | fresh ≤14天 / aging ≤60天 / stale >60天 | 決策面板與列表預設隱藏 stale |
| 衰減基準日 | 資料集最新一集（前端 referenceDate）；UI 顯示用 | |
| 回測規則 | S1 看多進、轉中性/看空出；S2 看多進、持有60天；S3 只跟「他有部位」的看多 | 使用者要三種並列比較 |
| 回測基準 | TW→0050、US→SPY、其他→SPY(fallback) | 各市場對應 |

---

## 6. 重要陷阱 / 注意事項

1. **日期是 2026 年**（未來）— 不要當錯誤修。
2. **逐字稿用 pack 不用 /seo/** — /seo/ 是停更的 SEO 鏡像。
3. **OpenAI 模型限 gpt-5.4 系列** — 該 key project 沒有別的。
4. **回測報酬被高估** — 樣本是 2026 上半年大多頭，UI 已加警語；判讀看**超額 α 與勝率**，不是絕對報酬。
5. **`supabase db push` 的 Docker 警告可忽略** — cloud push 會成功。
6. **PostgREST 單次查詢上限 1000 列** — 抓全量（prices、回測）要分頁，見 `analytics/prices.py` 與 `useData.ts` 的分頁寫法。
7. **題材 vs 個股** — 個股追蹤頁預設只顯示可交易（個股+ETF），題材分流到「題材/指數」分頁。正規化邏輯集中在 `normalize/canonical.py`，要加新股/別名就往對照表加一行。
8. **兩張圖時間軸對齊靠共用 axisStart/axisEnd + 相同 PAD.left/W**，改其中一張的幾何要同步另一張。
9. **金鑰檔 gitignored** — 同一台機器的新 session 讀得到 `.env`；換機要從 `.env.example` 重建並重新填 key（見 §7）。

---

## 7. 環境變數 / 金鑰

兩個檔案，都 **gitignored**（不會進 git，但本機磁碟上存在，新 session 讀得到）：

`.env`（後端）：
```
OPENAI_API_KEY=sk-...                 # 使用者提供
OPENAI_EXTRACT_MODEL=gpt-5.4-mini
SUPABASE_URL=https://ydzqxeckreqpoydpwbtf.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_ANON_KEY=...
```

`frontend/.env`：
```
VITE_SUPABASE_URL=https://ydzqxeckreqpoydpwbtf.supabase.co
VITE_SUPABASE_ANON_KEY=...
```

> 換機/遺失時：anon、service_role key 可用 `npx supabase projects api-keys --project-ref ydzqxeckreqpoydpwbtf` 重新取得；OpenAI key 需向使用者索取。**金鑰屬機密，不要寫進任何會進 git 的檔案。**

---

## 8. 如何跑起來

```bash
# 後端（更新資料時）
cd backend && uv sync && uv run python scripts/run_analytics.py

# 前端
cd frontend && npm install && npm run dev   # http://localhost:5173
npm run build                                # 型別檢查 + 打包（改完務必跑，確保 0 TS 錯誤）
```

驗證 UI：用 preview 工具或 Claude in Chrome 開 localhost:5173 截圖。注意 hover 類互動截不到時，可用 chrome `javascript_tool` 派發 `mouseenter` 事件後截圖。

---

## 9. 可能的下一步（未做、依使用者意願）

- `update_all.py` 一鍵增量更新（scrape→extract→load→prices→analytics）。
- 擴充集數到全部 671 集（成本：約 50 集的 13 倍 OpenAI 用量）。
- 自動排程（新集出刊後自動抓取/抽取）。
- 正規化對照表擴充長尾外國股（茂聯、Nexperia 等目前歸題材）。
- 回測加入手續費/滑價、不同持有天數比較、分年份績效。
- 部署前端（目前只跑 dev server）。

---

## 10. 互動慣例（沿用至今）

- 回繁中、用表格比較、用 AskUserQuestion 問選擇、執行前等使用者說 proceed/ok。
- 不臆測：要用的事實先驗證（web search / 讀檔 / 跑指令）。
- 改前端後跑 `npm run build` 確認型別，再用瀏覽器截圖驗證。
- 誠實回報：回測數字會誠實標註多頭行情偏誤。
