-- 修正 Supabase Performance Advisor 警告與優化資料庫效能。
--
-- 1. 優化 login_logs 的 select policy (rls_per_row_evaluation)
--    將 is_admin() 呼叫包裝在 (select ...) 子查詢中，使其作為 initplan 僅評估一次，避免逐列執行。
--
-- 2. 建立 login_logs (user_id) 外鍵索引 (unindexed_foreign_keys)
--    避免在刪除 auth.users 記錄時，資料庫需要對 login_logs 進行全表掃描。
--
-- 3. 移除 prices 表的重複索引 (duplicate_indexes)
--    prices (stock_id, date) 已有 UNIQUE CONSTRAINT，會自動建立唯一索引，
--    原先的 anonymous index 是多餘的，移除可加速 INSERT/UPDATE。
--
-- 4. 移除 episodes 表的重複索引 (duplicate_indexes)
--    episodes (ep_no) 已有 UNIQUE 限制，會自動建立索引，移除多餘的 anonymous index。

-- ══════════════════════════════════════════════════════════════════════════
-- 1. RLS 優化：包裝 login_logs 的 is_admin()
-- ══════════════════════════════════════════════════════════════════════════
drop policy if exists "admin read login_logs" on public.login_logs;
create policy "admin read login_logs" on public.login_logs
  for select
  to authenticated
  using ((select public.is_admin()));

-- ══════════════════════════════════════════════════════════════════════════
-- 2. 建立 login_logs.user_id 的外鍵索引
-- ══════════════════════════════════════════════════════════════════════════
create index if not exists login_logs_user_id_idx on public.login_logs (user_id);

-- ══════════════════════════════════════════════════════════════════════════
-- 3. 移除 prices 表的重複索引
-- ══════════════════════════════════════════════════════════════════════════
drop index if exists public.prices_stock_id_date_idx;

-- ══════════════════════════════════════════════════════════════════════════
-- 4. 移除 episodes 表的重複索引
-- ══════════════════════════════════════════════════════════════════════════
drop index if exists public.episodes_ep_no_idx;
