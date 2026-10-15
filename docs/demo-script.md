# Two-minute live demo

Before presenting: start Ollama, backend, and frontend; approve the real LinkWatch path; warm the model. Keep the dated evidence capsule available as a clearly labeled fallback. Never show cached output as a new inference. Avoid last-minute model downloads.

**0:00–0:15 — Problem.** “A Python project can declare incompatible versions across installers. DEPENDIQ connects those declarations to source evidence and a migration plan.” Enter the actual LinkWatch path and scan.

**0:15–0:35 — Observations.** Open the detected Pydantic conflict. Show requirements.txt and pyproject.toml version evidence and exact lines. Explain that these were read from this checkout, not hardcoded. Note that unbounded dependencies are reproducibility concerns, not automatically vulnerabilities.

**0:35–0:55 — Usage.** Open Source explorer. Show BaseModel/validator references and their actual file locations. Explain AST mapping provenance and its limits.

**0:55–1:20 — Local intelligence.** Click Generate migration plan. If inference takes time, explain the local-only Gemma 4 pipeline while it runs. Show the returned AI-SUGGESTED label, recommended steps, compatibility gaps, and suggested tests. If unavailable, show the actual reason; optionally open the dated recorded response as past evidence, explicitly labeled.

**1:20–1:40 — Verification.** Select Pydantic and enter the reviewed exact-version scenario. Compare. Show static conflict changes separately from runtime outcomes. In this environment project tests are NOT RUN due to missing container setup; do not claim the migration works. On a prepared Docker host, show actual installation/test outcomes, including failures.

**1:40–2:00 — Capsule.** Generate and download the JSON capsule. Show observed evidence, model digest, suggested tests and recorded verification limitations. “This is a reusable dependency exit plan with explicit evidence boundaries.”
