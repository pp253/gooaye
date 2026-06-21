-- 登入閘門：只有白名單 email 的登入者可讀資料
-- 配合 Supabase Auth（Google / Email magic link）

-- ── 白名單表 ──────────────────────────────────────────────
create table if not exists allowed_emails (
  email      text primary key,
  note       text,
  created_at timestamptz not null default now()
);
alter table allowed_emails enable row level security;
-- 不開任何 public/authenticated select policy；只透過下方 security definer 函式存取

-- 先放使用者本人（之後要加人就 insert 一列）
insert into allowed_emails (email) values ('pp.pp253@gmail.com')
  on conflict (email) do nothing;

-- ── 判斷目前登入者 email 是否在白名單 ──────────────────────
-- security definer：以函式擁有者身分執行，繞過 allowed_emails 的 RLS
create or replace function public.is_allowed()
returns boolean
language sql
security definer
stable
set search_path = public
as $$
  select exists (
    select 1 from public.allowed_emails
    where email = lower(auth.jwt() ->> 'email')
  );
$$;

-- 前端登入後可呼叫此函式判斷要顯示 app 還是「無權限」
grant execute on function public.is_allowed() to anon, authenticated;

-- ── 把所有資料表的「public 可讀」換成「白名單登入者可讀」 ──
drop policy if exists "public read episodes"          on episodes;
drop policy if exists "public read stocks"            on stocks;
drop policy if exists "public read mentions"          on mentions;
drop policy if exists "public read prices"            on prices;
drop policy if exists "public read stock_performance" on stock_performance;
drop policy if exists "public read backtest_runs"     on backtest_runs;

create policy "allowed read episodes"          on episodes          for select using (public.is_allowed());
create policy "allowed read stocks"            on stocks            for select using (public.is_allowed());
create policy "allowed read mentions"          on mentions          for select using (public.is_allowed());
create policy "allowed read prices"            on prices            for select using (public.is_allowed());
create policy "allowed read stock_performance" on stock_performance for select using (public.is_allowed());
create policy "allowed read backtest_runs"     on backtest_runs     for select using (public.is_allowed());
