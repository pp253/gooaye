-- 修正：還原 allowed_emails 為兩條獨立 permissive policy。
--
-- 單一 policy 合併 is_admin() OR email=... 會導致 is_admin() 遞迴查 allowed_emails
-- → 觸發同一條 policy → 再呼叫 is_admin() → 無窮遞迴。
-- 舊的雙 policy 設計中，PostgreSQL 獨立評估各 permissive policy，
-- self read（純欄位比對）可獨立通過而不觸發 admin read 的遞迴。
--
-- Performance 0006（multiple_permissive_policies）在 allowed_emails 上不可避免，
-- 表只有幾列，無效能影響。

drop policy if exists "read allowed_emails" on allowed_emails;

-- 一般使用者只看自己那列（加 initplan 解 Performance 0003）
create policy "self read allowed_emails" on allowed_emails
  for select
  to authenticated
  using (email = lower((select auth.jwt() ->> 'email')));

-- admin 看全部（不包 initplan，避免遞迴）
create policy "admin read allowed_emails" on allowed_emails
  for select
  to authenticated
  using (public.is_admin());
