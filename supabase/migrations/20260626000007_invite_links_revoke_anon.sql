-- 修復：create/revoke/accept_invite_link 因 schema 預設權限被自動授予 anon 可執行。
-- 同模式如 is_admin()/invite_email()：邀請連結相關函式只能由已登入使用者呼叫。

revoke execute on function public.create_invite_link(int) from anon;
revoke execute on function public.revoke_invite_link(uuid) from anon;
revoke execute on function public.accept_invite_link(uuid) from anon;
