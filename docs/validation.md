# Observed validation — 15 October 2026

These results were executed in the build session. They are not promises about future machines, changed checkouts, or unexecuted CI.

## Automated checks

- `python -m pytest tests -q`: **34 passed**, one upstream Starlette/httpx TestClient deprecation warning. This covers scanner/AST logic, schema/API validation, mocked model failures, verification safety and capsule structure. Mock model responses are synthetic fixtures.
- `npm --prefix frontend run build`: **passed**, Vite 6.4.4. Final build output: ~386 KB JavaScript / ~121 KB gzip, ~28 KB CSS / ~8 KB gzip. No build errors.
- `git diff --check`: passed at packaging.
- Runtime: macOS arm64, Python 3.13.5, Node 24.16.0. Python package versions are recorded in runtime-versions.json. CI is configured separately; no GitHub Actions result is claimed here.

## Real target observations

Target: https://github.com/rishrek/LinkWatch, commit `f52f393` (initial commit), cloned outside submission repository at `/private/tmp/dependiq-LinkWatch`.

The scan dynamically parsed three manifests, found **14 distinct dependencies**, inspected **15 Python files**, and identified **four test files**. The Pydantic contradiction is read from `requirements.txt:5` (`==1.10.13`) and `pyproject.toml:17` (`>=2`). Actual import/usage evidence includes BaseModel and validator in `linkwatch/config.py` plus affected-module test references in the final tracing implementation. Counts are generated, never application seed data.

## Live API and model evidence

The frontend HTTP server returned 200; FastAPI launched and `/api/health` returned ready with the installed local model. The full HTTP scan → analyze → verify → capsule path returned successful responses. See [summary](e2e-summary.json) and [complete exported capsule](linkwatch-exit-capsule.json) for exact observations and timings.

**Genuine Gemma 4 inference ran locally** through Ollama using `gemma4:e2b`, digest:

`45d11505b91d888e353859f5deeeeff3ffc9b3aa42263c00904120c53851ef96`

Standalone live Pydantic recommendation: [live-gemma-evidence.json](live-gemma-evidence.json). The initial live generation was truncated and rejected after bounded retries. Tightening the concise-output instruction and increasing the output token budget produced a schema-valid response. The full API analysis generated five flagged-dependency recommendations; per-dependency status remains inspectable in the capsule. These are AI-SUGGESTED, not verified compatibility facts.

## Verification limits

The exact-version Pydantic `2.11.7` scenario was applied only to disposable copies. Actual static checks found baseline conflict `pydantic` and no remaining declared Pydantic conflict after the change. Both copies parsed without syntax errors. Changed files: pyproject.toml and requirements.txt.

Execution was separately attempted with server execution opt-in and repository trust. **NOT RUN: Docker executable is unavailable.** See [verification-attempt.json](verification-attempt.json). Baseline and migration project tests were not executed on the host. Null test counts are deliberate. The ordinary live API capsule records execution disabled because its server was launched with the default safe setting.

Docker command hardening, subprocess errors/timeouts, runner/plugin syntax, incomplete summary handling, and manifest preservation were exercised in automated tests. Real container installation and project test execution remain unverified. Resolving declaration conflicts cannot establish API compatibility.

## UI verification limit

Vite launched and served HTTP 200. Browser automation reported “No browser is available,” so no screenshot, visual interaction pass, or mobile rendering pass is claimed. Responsive styles and reduced-motion handling are implemented; the Integrator should inspect all views in a real browser and capture screenshots before submission.

## Git boundary

The original sohampalan/ISTE-HACKATHON destination became unavailable during the build. The user supplied techwings0710/iste. It was inspected as empty, without branches or open PRs, before the feature branch was published. A remote README contribution was fast-forwarded and preserved in bootstrap-readme.md before expansion. The Integrator then created main at the initial implementation commit. The build agent never pushed to main and will not merge its PR.
