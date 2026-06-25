-- 緊急修正：上一版 migration 把 is_admin() 包在 (select ...) initplan 裡，
-- 導致循環遞迴（is_admin() 查 allowed_emails → RLS 再呼叫 is_admin() → 無窮迴圈）。
--
-- 修法：保留單一 policy（解 0006 multiple_permissive_policies），
-- 但 is_admin() 不用 initplan（避免遞迴），只有 auth.jwt() 用 initplan（解 0003）。
-- allowed_emails 只有幾列，is_admin() 逐列呼叫無效能問題。

drop policy if exists "read allowed_emails" on allowed_emails;

create policy "read allowed_emails" on allowed_emails
  for select
  to authenticated
  using (
    public.is_admin()
    or email = lower((select auth.jwt() ->> 'email'))
  );
