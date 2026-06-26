-- 修復：is_admin() 無限遞迴導致非 admin 使用者登入後一律「無存取權限」。
--
-- 根因：20260625000005_roles.sql 把 is_admin() 設為 SECURITY INVOKER。
-- 但 is_admin() 內部查詢 allowed_emails，而 allowed_emails 的 RLS policy
-- 「admin read allowed_emails」本身就是呼叫 is_admin() →
-- 查 allowed_emails 觸發 RLS → RLS 又呼叫 is_admin() → 無限遞迴
-- （PostgreSQL error 54001 stack depth limit exceeded）。
--
-- 實測：對 admin 帳號（pp.pp253@gmail.com）剛好不會觸發（query planner 對
-- OR 條件求值順序的不穩定行為），但對任何新邀請的帳號一律遞迴失敗。
--
-- 修法：跟 invite_email() / revoke_email() 同模式，改回 SECURITY DEFINER，
-- 讓函式內部查 allowed_emails 時繞過 RLS，徹底切斷遞迴鏈。
-- 函式只回傳呼叫者自己是否為 admin 的布林值，不會洩漏其他資料，
-- 與 invite_email/revoke_email 同樣是專案接受的「刻意保留 DEFINER 警告」設計。

create or replace function public.is_admin()
returns boolean
language sql
security definer
stable
set search_path = public
as $$
  select exists (
    select 1 from public.allowed_emails
    where email = lower(auth.jwt() ->> 'email') and role = 'admin'
  );
$$;

revoke execute on function public.is_admin() from public;
grant execute on function public.is_admin() to authenticated;
