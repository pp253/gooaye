-- 縱深防禦修正：函式建立時預設對 PUBLIC 授予 EXECUTE，
-- 先前只 revoke ... from anon 對 anon 角色無效（仍透過 PUBLIC 繼承）。
-- 明確 revoke from public，再重新 grant 給 authenticated，
-- 確保 anon 真的無法呼叫 invite_email / revoke_email
-- （函式內部的 is_allowed() 檢查仍保留作為第二層防護）。

revoke execute on function public.invite_email(text) from public;
revoke execute on function public.revoke_email(text)  from public;

grant execute on function public.invite_email(text) to authenticated;
grant execute on function public.revoke_email(text)  to authenticated;
