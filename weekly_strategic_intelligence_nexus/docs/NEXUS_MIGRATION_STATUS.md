# Nexus Migration Status

## Goal
Migrate `weekly_strategic_intelligence_nexus` to a Nexus-like architecture without losing feature parity from `weekly_strategic_intelligence_reporter`.

## Decisions Applied
- Added a Nexus-like orchestration facade in `src/nexus_like/`.
- Kept execution parity by delegating to the existing `news_reporter` pipeline.
- Switched runtime entrypoints to the new facade:
  - `src/main.py`
  - `src/scheduler.py`
  - `src/embedded_webapp.py`
- Improved embedded webapp responsiveness (desktop/mobile) without changing behavior.

## Functional Parity Status (current)
- Portable `.exe` build flow: preserved (`packaged_webapp_launcher.py` + `scripts/build_onefile_webapp_portable_py311.bat`).
- Webapp + filters + profiles: preserved.
- Source selection + geographic packs (`pack_country_keys`): preserved.
- News cards + image fallback + market cards: preserved in `news_reporter/report.py`.

## Next Migration Steps (safe path)
1. Move one module at a time from `news_reporter` to `nexus_like` (collectors, filters, scoring, report), keeping adapters.
2. Add equivalence tests per stage (same inputs => same counts/outputs).
3. Keep `.exe` pipeline untouched until all stage tests are green.
