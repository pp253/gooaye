-- 消除 Security Advisor 警告 0028/0029：
--   public.is_allowed() 原為 SECURITY DEFINER，被 anon/authenticated 經 RPC 可執行。
-- 改用 SECURITY INVOKER：函式以「呼叫者身分」執行，不再繞過 RLS，
-- 兩個 SECURITY DEFINER 警告即消失。
-- 為此需讓登入者能讀到 allowed_emails 中「自己那一列」，is_allowed() 才能判斷。
-- （只看得到自己的 email，等同 is_allowed() 本就會回傳的資訊，無額外洩漏。）

create or replace function public.is_allowed()
returns boolean
language sql
security invoker          -- 由 definer 改為 invoker
stable
set search_path = public
as $$
  select exists (
    select 1 from public.allowed_emails
    where email = lower(auth.jwt() ->> 'email')
  );
$$;

-- 登入者只能 select 自己 email 的那一列；is_allowed()(invoker) 與
-- 各資料表 RLS policy 內呼叫 is_allowed() 時都靠這條讀到白名單。
drop policy if exists "self read allowed_emails" on allowed_emails;
create policy "self read allowed_emails" on allowed_emails
  for select to authenticated
  using (email = lower(auth.jwt() ->> 'email'));
