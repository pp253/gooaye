-- RLS 效能修正：using (is_allowed()) → using ((select is_allowed()))
-- 用 scalar subquery 包住函式呼叫，讓 Postgres 每條 statement 只評估一次（initplan），
-- 而非在大表上逐列呼叫。解決 prices（~82 萬列）未授權/未過濾查詢的 statement timeout。
-- 授權語意完全不變（仍是「白名單登入者才可讀」）。
-- 參考：Supabase RLS 效能最佳實踐（wrap function calls in a subquery）。

drop policy if exists "allowed read episodes"          on episodes;
drop policy if exists "allowed read stocks"            on stocks;
drop policy if exists "allowed read mentions"          on mentions;
drop policy if exists "allowed read prices"            on prices;
drop policy if exists "allowed read stock_performance" on stock_performance;
drop policy if exists "allowed read backtest_runs"     on backtest_runs;

create policy "allowed read episodes"          on episodes          for select using ((select public.is_allowed()));
create policy "allowed read stocks"            on stocks            for select using ((select public.is_allowed()));
create policy "allowed read mentions"          on mentions          for select using ((select public.is_allowed()));
create policy "allowed read prices"            on prices            for select using ((select public.is_allowed()));
create policy "allowed read stock_performance" on stock_performance for select using ((select public.is_allowed()));
create policy "allowed read backtest_runs"     on backtest_runs     for select using ((select public.is_allowed()));
