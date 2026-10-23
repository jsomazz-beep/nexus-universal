# Security update - 2026-10-23

Scope: Render service weekly-strategic-intelligence-nexus
(srv-d813dqfaqgkc73akihfg), Docker, branch codex/cloud-nexus-render.

- Require certifi >= 2026.10.19; the isolated install resolved 2026.10.23.
- Refresh ca-certificates from the base distribution during image build.
- Docker build checks both Requests/certifi and urllib/system trust against the
  two compromised-certificate test endpoints in Render's advisory. Valid HTTPS
  must also work. Network errors are not mistaken for certificate rejection.
- No Supabase keys, profiles, reports, data retention or application routes changed.

Validation: PYTHONPATH=src python -m unittest discover -s tests -v (43 tests).
Image validation must occur in Linux/Render; Windows has a different system trust
store. Local Requests rejected both hosts, but the Windows system store still
accepted the second test host. This change does not patch Windows itself.

Build logs must show a patched certifi version and four certificate rejections.
Use a fresh Docker build; existing image layers can otherwise retain old CA data.
No certificate verification is disabled or bypassed.

Reference: https://render.com/docs/advisory-emudhra

Previous deployment a55471deee8564ed3107c39f937e1bf69baf7b8c is an availability
fallback only: restoring it also restores the previous certificate configuration.
Never restore the database or delete reports to roll back application code.
