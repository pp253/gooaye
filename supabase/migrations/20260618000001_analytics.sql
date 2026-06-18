-- Phase 2 分析層：個股跟單績效快照 + 回測結果

-- 每檔個股的「提及後表現」快照（給列表/決策面板/詳情頁顯示）
create table if not exists stock_performance (
  stock_id              integer primary key references stocks (id) on delete cascade,
  current_price         numeric(14,4),
  currency_symbol       text,                 -- 顯示用（NT$/US$…），簡化可空
  first_bull_date       date,
  first_bull_price      numeric(14,4),
  ret_since_first_bull  numeric(8,4),         -- 首次看多至今報酬率（小數，0.12 = +12%）
  last_bull_date        date,
  last_bull_price       numeric(14,4),
  ret_since_last_bull   numeric(8,4),
  updated_at            timestamptz not null default now()
);

-- 回測執行結果（整份結果存 jsonb，前端讀最新一筆）
create table if not exists backtest_runs (
  id              serial primary key,
  reference_date  date,
  results         jsonb not null,
  created_at      timestamptz not null default now()
);

alter table stock_performance enable row level security;
alter table backtest_runs     enable row level security;
create policy "public read stock_performance" on stock_performance for select using (true);
create policy "public read backtest_runs"     on backtest_runs     for select using (true);
