-- 一次性邀請連結：ADMIN 產生連結（預設 7 天過期），任何人用 Google 登入
-- 後可憑連結加入白名單，連結成功使用一次後即失效。
-- 若登入者已是既有成員，視同連結失效（不消耗連結，讓連結仍可給別人用）。

create table if not exists public.invite_links (
  token      uuid primary key default gen_random_uuid(),
  created_by text not null,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  used_by    text,
  used_at    timestamptz
);
alter table public.invite_links enable row level security;

create policy "admin read invite_links" on public.invite_links
  for select to authenticated
  using (public.is_admin());

-- ADMIN 產生邀請連結
create or replace function public.create_invite_link(expires_days int default 7)
returns table(token uuid, expires_at timestamptz)
language plpgsql
security definer
set search_path = public
as $$
declare
  _caller_email text := lower(auth.jwt() ->> 'email');
begin
  if not public.is_admin() then
    raise exception 'not authorized';
  end if;

  if expires_days is null or expires_days <= 0 then
    raise exception 'expires_days must be positive';
  end if;

  return query
    insert into public.invite_links (created_by, expires_at)
    values (_caller_email, now() + (expires_days || ' days')::interval)
    returning invite_links.token, invite_links.expires_at;
end;
$$;
revoke execute on function public.create_invite_link(int) from public;
grant execute on function public.create_invite_link(int) to authenticated;

-- ADMIN 撤銷尚未使用的邀請連結
create or replace function public.revoke_invite_link(target_token uuid)
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  if not public.is_admin() then
    raise exception 'not authorized';
  end if;

  delete from public.invite_links
  where token = target_token and used_at is null;
end;
$$;
revoke execute on function public.revoke_invite_link(uuid) from public;
grant execute on function public.revoke_invite_link(uuid) to authenticated;

-- 登入者憑連結加入白名單。回傳 true=成功加入，false=連結無效/過期/已使用/已是成員。
create or replace function public.accept_invite_link(target_token uuid)
returns boolean
language plpgsql
security definer
set search_path = public
as $$
declare
  _caller_email text := lower(auth.jwt() ->> 'email');
  _link record;
begin
  if _caller_email is null or _caller_email = '' then
    raise exception 'not authenticated';
  end if;

  -- 已是既有成員：視同連結失效，但不消耗連結（留給其他人使用）
  if exists (select 1 from public.allowed_emails where email = _caller_email) then
    return false;
  end if;

  select * into _link from public.invite_links
  where token = target_token
    and used_at is null
    and expires_at > now()
  for update;

  if _link is null then
    return false;
  end if;

  insert into public.allowed_emails (email, note, role)
  values (_caller_email, 'invited via link by ' || _link.created_by, 'user');

  update public.invite_links
  set used_by = _caller_email, used_at = now()
  where token = target_token;

  return true;
end;
$$;
revoke execute on function public.accept_invite_link(uuid) from public;
grant execute on function public.accept_invite_link(uuid) to authenticated;
