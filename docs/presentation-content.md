# Six-slide content draft

Content only. No official editable template was supplied. Paste into the organizer's unchanged template; do not present this Markdown as an official template.

## 1. Team information and track

DEPENDIQ — AI-Powered Dependency Intelligence and Migration Assistant.
Hacktoberfest 2026, Hackday Mumbai × ISTE KJSSE. Track 1: Gemma 4 — Dependency Resilience.
Team: [Integrator to supply team name and member names/roles].
Repository: https://github.com/techwings0710/iste/tree/astra-complete-build.
Naming/starter-fork compliance pending organizer confirmation.

## 2. Solution and workflow

Dependency drift makes migrations uncertain. DEPENDIQ turns a local repository into evidence a developer can inspect and reuse.
Scan manifests → trace source usage → reason with local Gemma 4 → compare explicit migration → export Exit Capsule.
Three visible evidence classes: OBSERVED, AI-SUGGESTED, EXECUTION-VERIFIED.

## 3. Technical approach

React/Vite/Tailwind command centre; FastAPI/Pydantic contract; packaging-based constraint reasoning; TOML and Python AST analysis; local Ollama/Gemma 4 structured JSON.
Approved read-only source paths. Disposable migration copies. Opt-in network-disabled Docker verification. Canonical server-side evidence sessions.
Actual target: LinkWatch, dynamically scanned. No hardcoded package findings or simulated model output.

## 4. Feasibility and viability

Runs locally without paid APIs or cloud deployment. Scanner and capsule work without Ollama. AI failure and unavailable verification remain usable states.
Gemma 4 e2b live structured inference demonstrated; digest recorded in evidence artifact.
34 backend tests passed at final validation; use docs/validation.md for final count and actual API/build evidence.
Docker tests and browser visual QA unavailable in build environment. Do not claim runtime migration safety.

## 5. Impact and benefits

Developers can locate impacted code before changing a dependency, understand which installer declarations disagree, and share one portable evidence artifact.
Privacy: repository stays local. Auditability: observations, suggestions, and execution results are separate.
Future: richer binding analysis, offline advisory snapshots, wheel provenance, and independently reviewed source patches.

## 6. Research and references

LinkWatch target: https://github.com/rishrek/LinkWatch
Gemma 4 model card / Apache 2.0: https://ai.google.dev/gemma/docs/core/model_card_4
Ollama Gemma 4 library: https://ollama.com/library/gemma4
Structured output: https://docs.ollama.com/capabilities/structured-outputs
Python packaging specifications: https://packaging.python.org/en/latest/specifications/
Python AST: https://docs.python.org/3/library/ast.html
Organizer rules: supplied DEPENDIQ GitHub-Safe guide, referencing the Hacktober Handbook (original handbook not independently supplied).
