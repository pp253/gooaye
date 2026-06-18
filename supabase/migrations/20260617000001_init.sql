-- 股癌個股追蹤系統 — 初始 schema
-- Phase 1：逐字稿抽取、個股管理、提及記錄
-- prices 表預留，Phase 2 回測時填入

-- ── episodes ──────────────────────────────────────────────────
create table if not exists episodes (
  id            serial primary key,
  ep_no         integer not null unique,
  title         text,
  source_url    text,
  published_at  date,                      -- 發布日期（從 RSS 補，Phase 2）
  summary       text[] not null default '{}',
  topics        text[] not null default '{}',
  created_at    timestamptz not null default now()
);

create index on episodes (ep_no);

-- ── stocks ────────────────────────────────────────────────────
create table if not exists stocks (
  id          serial primary key,
  ticker      text not null,               -- 代號，e.g. NVDA / 2330
  market      text not null check (market in ('TW', 'US', 'OTHER', 'UNKNOWN')),
  name_zh     text not null,               -- 中文名
  name_en     text,
  aliases     text[] not null default '{}',
  created_at  timestamptz not null default now(),
  unique (ticker, market)
);

create index on stocks (ticker);
create index on stocks (market);

-- ── mentions ──────────────────────────────────────────────────
create table if not exists mentions (
  id            serial primary key,
  episode_id    integer not null references episodes (id) on delete cascade,
  stock_id      integer references stocks (id) on delete set null,  -- null = unmatched
  name_raw      text not null,             -- 逐字稿原始名稱
  ticker_guess  text,                      -- LLM 猜的代號（未正規化）
  market        text not null check (market in ('TW', 'US', 'OTHER', 'UNKNOWN')),
  direction     text not null check (direction in ('看多', '看空', '中性')),
  confidence    numeric(3,2) not null check (confidence between 0 and 1),
  has_position  boolean not null default false,
  quote         text not null,
  note          text,
  created_at    timestamptz not null default now()
);

create index on mentions (episode_id);
create index on mentions (stock_id);
create index on mentions (direction);

-- ── prices ────────────────────────────────────────────────────
-- Phase 1 建表但不寫資料；Phase 2 回測時填入
create table if not exists prices (
  id        serial primary key,
  stock_id  integer not null references stocks (id) on delete cascade,
  date      date not null,
  close     numeric(12,4) not null,
  unique (stock_id, date)
);

create index on prices (stock_id, date);

-- ── Row Level Security（RLS）──────────────────────────────────
-- 目前全表開放讀取（前端用 anon key 查詢），寫入只透過 service_role
alter table episodes  enable row level security;
alter table stocks    enable row level security;
alter table mentions  enable row level security;
alter table prices    enable row level security;

create policy "public read episodes"  on episodes  for select using (true);
create policy "public read stocks"    on stocks    for select using (true);
create policy "public read mentions"  on mentions  for select using (true);
create policy "public read prices"    on prices    for select using (true);
