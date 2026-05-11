create table if not exists public.profile_sets (
  id text primary key,
  payload jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

create or replace function public.touch_profile_sets_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_profile_sets_updated_at on public.profile_sets;
create trigger trg_profile_sets_updated_at
before update on public.profile_sets
for each row
execute function public.touch_profile_sets_updated_at();

alter table public.profile_sets enable row level security;

drop policy if exists "service role can manage profile_sets" on public.profile_sets;
create policy "service role can manage profile_sets"
on public.profile_sets
for all
to service_role
using (true)
with check (true);
