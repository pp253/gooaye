-- Switch login_logs from client-side INSERT to server-side trigger on auth.sessions.
-- This ensures a log is written only on real sign-ins, not page refreshes.

-- 1) Drop the client-side INSERT policy (no longer needed)
drop policy if exists "insert own login_logs" on public.login_logs;

-- 2) Trigger function: runs as SECURITY DEFINER to bypass RLS
create or replace function public.handle_new_session()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  _email text;
  _provider text;
begin
  -- Look up user email and provider
  select
    raw_user_meta_data ->> 'email',
    coalesce(raw_app_meta_data ->> 'provider', 'unknown')
  into _email, _provider
  from auth.users
  where id = new.user_id;

  insert into public.login_logs (user_id, email, method, logged_in_at)
  values (new.user_id, coalesce(_email, ''), _provider, now());

  return new;
end;
$$;

-- 3) Fire on every new session row (= every real sign-in)
drop trigger if exists on_new_session_log on auth.sessions;
create trigger on_new_session_log
  after insert on auth.sessions
  for each row
  execute function public.handle_new_session();
