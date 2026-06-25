-- 邀請功能：讓白名單內的使用者可以新增其他 email 到 allowed_emails。
-- 不開放直接 INSERT policy（避免任何登入者繞過白名單自行新增），
-- 改用 SECURITY DEFINER RPC，函式內部自行檢查 caller 是否在白名單。

-- ── 讓白名單使用者能看到完整的邀請清單（而非只有自己那列）──
-- 與 episodes/prices 等表一致的寫法：using (is_allowed())。
-- is_allowed() 本身仍只透過 self-read policy 讀自己那列，不會循環放大權限。
drop policy if exists "allowed read allowed_emails" on allowed_emails;
create policy "allowed read allowed_emails" on allowed_emails
  for select
  to authenticated
  using (public.is_allowed());

-- ── 邀請 RPC ──────────────────────────────────────────────
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
  -- 只有白名單使用者才能邀請別人
  if not public.is_allowed() then
    raise exception 'not authorized';
  end if;

  if _clean_email is null or _clean_email = '' then
    raise exception 'email required';
  end if;

  if _clean_email !~ '^[^@\s]+@[^@\s]+\.[^@\s]+$' then
    raise exception 'invalid email format';
  end if;

  insert into public.allowed_emails (email, note)
  values (_clean_email, 'invited by ' || coalesce(_caller_email, 'unknown'))
  on conflict (email) do nothing;
end;
$$;

-- 只給登入者（authenticated）執行；函式內部會再檢查 is_allowed()
grant execute on function public.invite_email(text) to authenticated;
revoke execute on function public.invite_email(text) from anon;

-- ── 移除邀請（讓白名單使用者也能撤銷邀請，含自我保護：不能移除自己）──
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
  if not public.is_allowed() then
    raise exception 'not authorized';
  end if;

  if _clean_email = _caller_email then
    raise exception 'cannot revoke your own access';
  end if;

  delete from public.allowed_emails where email = _clean_email;
end;
$$;

grant execute on function public.revoke_email(text) to authenticated;
revoke execute on function public.revoke_email(text) from anon;
