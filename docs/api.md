# Shared REST contract

Base URL: http://127.0.0.1:8000. OpenAPI: `/openapi.json`; interactive reference: `/docs`. Frontend `VITE_API_BASE_URL` is optional: Vite proxies `/api` by default. CORS allows localhost/127.0.0.1 port 5173 only.

`GET /api/health` returns backend readiness independently from AI availability, the configured approved roots, model readiness, and execution opt-in.

`POST /api/scan` accepts `repository_path` (absolute approved directory). Returns `scan_id`, `repository`, `repository_path`, `status`, `fingerprint`, `generated_at`, `dependencies`, `scan_errors`, `python_files`, `test_files`, `manifests`, `limitations`, `ai_status`, `model_info`.

Each dependency includes `name`, `declared_versions` (file, line, constraint, marker, active, group, URL), `risk_level`, `risk_indicators`, `usage_locations`, `evidence`, `uncertainties`, optional `ai_recommendation` and `ai_error`. Locations are AST/import/config observations with mapping provenance. `line=0` means unlocated TOML literal, not a real line. Risk levels are not vulnerability severities.

`POST /api/analyze` accepts the complete scan response for shared-contract compatibility, but reads canonical observations from the server using `scan_id`. It enriches flagged dependencies with a strict AI-SUGGESTED recommendation: proposed replacement, technical reasoning, migration steps, suggested tests, compatibility gaps, uncertainties, confidence, and verified=false. AI status: not_run, completed, partial, unavailable, or no_flagged_dependencies. A model outage returns a truthful enriched response rather than fabricated content.

`POST /api/verify` accepts:

```json
{"scan_id":"returned UUID","dependency_name":"selected scanned package","proposed_version":"2.11.7","trusted_repository":false}
```

Returns scan/scenario identifiers, verification_status, baseline, migration, static_comparison, compatibility_gaps, limitations. Outcome fields: status, classification, commands, exit_code, output, reason, python_version, duration_seconds, passed, failed, skipped, tests_completed, installation_problem. Null counts mean unexecuted/unknown. `NOT RUN` is distinct from `FAILED`, `TIMEOUT`, and `INCOMPLETE`.

`POST /api/capsule` accepts `{"scan_id":"returned UUID"}`. Returns application/json with attachment Content-Disposition. Combines current canonical scan/AI and latest stored scenario. It cannot accept client-supplied test successes.

Errors: 422 invalid schema; 400 invalid paths/scenarios or changed checkout; 404 unknown session (rescan after restart). Run the backend as one local worker. Sessions are bounded to 100 in memory; old ignored disk snapshots are retained locally but never automatically trusted/reloaded. Remove `.dependiq/` yourself when local evidence retention is no longer needed.
