-- Login logs: record every successful sign-in

create table if not exists public.login_logs (
  id         bigint generated always as identity primary key,
  user_id    uuid not null references auth.users (id),
  email      text not null,
  method     text not null,  -- 'google', 'email', etc.
  logged_in_at timestamptz not null default now()
);

alter table public.login_logs enable row level security;

-- Authenticated users can insert their own login log
create policy "insert own login_logs"
  on public.login_logs for insert
  to authenticated
  with check (user_id = auth.uid());

-- Only whitelisted users can view all login logs
create policy "allowed read login_logs"
  on public.login_logs for select
  to authenticated
  using (public.is_allowed());

-- Index for efficient ordering
create index if not exists login_logs_logged_in_at_idx
  on public.login_logs (logged_in_at desc);
