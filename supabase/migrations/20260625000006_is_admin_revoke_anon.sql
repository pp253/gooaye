-- 修正：is_admin() 建立時透過專案的 ALTER DEFAULT PRIVILEGES
-- （對 schema public 內新函式自動 grant 給 anon/authenticated）直接拿到 anon 的 EXECUTE，
-- 先前只 revoke ... from public 沒擋到這個「直接授予 anon」的權限，
-- 導致 anon 仍可呼叫 is_admin()（雖然只回 false，未造成資料外洩，但違反最小權限原則）。
-- 明確 revoke from anon 補上這一層。

revoke execute on function public.is_admin() from anon;
