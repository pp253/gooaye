-- 讓使用者點開邀請連結時，不需要先用 Google 登入就能知道連結是否已失效
-- （過期/已使用/不存在）。只回傳布林值，不洩漏 token 以外的任何資料。

create or replace function public.is_invite_link_valid(target_token uuid)
returns boolean
language sql
security definer
stable
set search_path = public
as $$
  select exists (
    select 1 from public.invite_links
    where token = target_token
      and used_at is null
      and expires_at > now()
  );
$$;
revoke execute on function public.is_invite_link_valid(uuid) from public;
grant execute on function public.is_invite_link_valid(uuid) to anon, authenticated;
