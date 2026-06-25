-- 使用者角色：ADMIN / USER
-- 只有 pp.pp253@gmail.com 是 ADMIN；其他被邀請加入的一律是 USER。
-- 只有 ADMIN 能新增使用者（invite_email）、移除使用者（revoke_email）、查看登入紀錄。

alter table public.allowed_emails
  add column if not exists role text not null default 'user'
  check (role in ('admin', 'user'));

update public.allowed_emails set role = 'admin' where email = 'pp.pp253@gmail.com';
update public.allowed_emails set role = 'user'  where email <> 'pp.pp253@gmail.com';

-- ── is_admin()：目前登入者是否為 ADMIN ──────────────────────
create or replace function public.is_admin()
returns boolean
language sql
security invoker
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

-- ── 成員清單只給 ADMIN 看（一般使用者只能透過既有 self-read policy 看自己那列）──
drop policy if exists "allowed read allowed_emails" on allowed_emails;
create policy "admin read allowed_emails" on allowed_emails
  for select
  to authenticated
  using (public.is_admin());

-- ── 邀請 / 移除：只有 ADMIN 能執行 ──────────────────────────
create or replace function public.invite_email(target_email text)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  _caller_email text := lower(auth.jwt() ->> 'email');
  _clean_email  text := lower(trim(target_email));
begin
  if not public.is_admin() then
    raise exception 'not authorized';
  end if;

  if _clean_email is null or _clean_email = '' then
    raise exception 'email required';
  end if;

  if _clean_email !~ '^[^@\s]+@[^@\s]+\.[^@\s]+$' then
    raise exception 'invalid email format';
  end if;

  insert into public.allowed_emails (email, note, role)
  values (_clean_email, 'invited by ' || coalesce(_caller_email, 'unknown'), 'user')
  on conflict (email) do nothing;
end;
$$;

create or replace function public.revoke_email(target_email text)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  _caller_email text := lower(auth.jwt() ->> 'email');
  _clean_email  text := lower(trim(target_email));
begin
  if not public.is_admin() then
    raise exception 'not authorized';
  end if;

  if _clean_email = _caller_email then
    raise exception 'cannot revoke your own access';
  end if;

  delete from public.allowed_emails where email = _clean_email;
end;
$$;

revoke execute on function public.invite_email(text) from public;
revoke execute on function public.revoke_email(text)  from public;
grant execute on function public.invite_email(text) to authenticated;
grant execute on function public.revoke_email(text)  to authenticated;

-- ── 登入紀錄只給 ADMIN 看 ────────────────────────────────────
drop policy if exists "allowed read login_logs" on login_logs;
create policy "admin read login_logs" on login_logs
  for select
  to authenticated
  using (public.is_admin());
