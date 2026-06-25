-- 修正 Supabase Security Advisor + Performance Advisor 可處理的警告。
--
-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ SECURITY                                                               │
-- ├──────────────────────────────────────────────────────────────────────────┤
-- │ 0028 handle_new_session() — anon 可執行 SECURITY DEFINER              │
-- │ 0029 handle_new_session() — authenticated 可執行 SECURITY DEFINER     │
-- │                                                                        │
-- │ handle_new_session() 是 trigger 函式（由 auth.sessions INSERT 觸發），  │
-- │ 不應被任何使用者透過 PostgREST /rpc/handle_new_session 直接呼叫。       │
-- │ 解法：revoke EXECUTE from public（涵蓋 anon + authenticated 繼承）。    │
-- ├──────────────────────────────────────────────────────────────────────────┤
-- │ 刻意保留的 SECURITY DEFINER 警告（不修）：                               │
-- │ • invite_email() / revoke_email() — authenticated 可執行是設計需要，    │
-- │   函式內部有 is_admin() 權限檢查，且已 revoke from public + anon。       │
-- │ • auth_leaked_password_protection — 本專案無密碼登入，不適用。           │
-- ├──────────────────────────────────────────────────────────────────────────┤
-- │ PERFORMANCE                                                            │
-- ├──────────────────────────────────────────────────────────────────────────┤
-- │ 0003 allowed_emails 的 self read policy 裸呼叫 auth.jwt()，逐列評估     │
-- │ 0006 allowed_emails 同時有兩條 permissive SELECT policy（admin + self） │
-- │                                                                        │
-- │ 解法：合併 admin read + self read 為單一 policy，                        │
-- │   使用 (select ...) initplan 包裝 auth 函式呼叫。                       │
-- │   語意：admin 看全部 OR 一般使用者只看自己那列（與先前完全一致）。        │
-- └──────────────────────────────────────────────────────────────────────────┘

-- ══════════════════════════════════════════════════════════════════════════
-- 1. SECURITY: 封鎖 handle_new_session() 的 RPC 入口
-- ══════════════════════════════════════════════════════════════════════════
-- revoke from public 會連帶影響繼承的 anon + authenticated。
-- trigger 執行不需要 EXECUTE 權限（Postgres trigger 機制直接呼叫，不經 role check）。
revoke execute on function public.handle_new_session() from public;
revoke execute on function public.handle_new_session() from anon;
revoke execute on function public.handle_new_session() from authenticated;

-- ══════════════════════════════════════════════════════════════════════════
-- 2. PERFORMANCE: 合併 allowed_emails 的兩條 SELECT policy
-- ══════════════════════════════════════════════════════════════════════════
-- 先清掉舊的兩條
drop policy if exists "admin read allowed_emails" on allowed_emails;
drop policy if exists "self read allowed_emails"  on allowed_emails;

-- 合併為一條，用 (select ...) initplan 避免逐列評估
create policy "read allowed_emails" on allowed_emails
  for select
  to authenticated
  using (
    (select public.is_admin())                                    -- admin 看全部
    or email = lower((select auth.jwt()) ->> 'email')             -- 一般使用者只看自己
  );
