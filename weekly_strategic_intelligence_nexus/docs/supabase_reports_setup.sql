create table if not exists public.intelligence_reports (
  id bigserial primary key,
  report_name text not null unique,
  html_content text not null,
  created_at timestamptz not null default now()
);

alter table public.intelligence_reports enable row level security;

drop policy if exists "service role can manage intelligence_reports" on public.intelligence_reports;
create policy "service role can manage intelligence_reports"
on public.intelligence_reports
for all
to service_role
using (true)
with check (true);
