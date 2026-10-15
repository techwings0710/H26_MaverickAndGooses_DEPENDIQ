# Local Gemma 4 operations

Install the current macOS app from https://ollama.com/download/mac. Open it or run `ollama serve` from the CLI, then `ollama pull gemma4:e2b`. Check `ollama list`; copy its exact name to `GEMMA_MODEL`. Supported local variants are listed at https://ollama.com/library/gemma4. Cloud tags are explicitly rejected.

Gemma 4 model card and Apache 2.0 license: https://ai.google.dev/gemma/docs/core/model_card_4. Unlike older Gemma releases, the current Gemma 4 card identifies Apache 2.0. Confirm the card and chosen tag when reproducing. We do not ship weights or silently substitute another model. The validated runtime artifact records the exact model digest rather than treating a mutable tag as an immutable version.

## Troubleshooting

| Symptom | Check / remedy |
|---|---|
| Connection refused | Run `ollama serve`; check `curl http://localhost:11434/api/tags`. If the app already serves, do not start a second service. |
| Model not installed | Run `ollama list`, then pull the intended exact Gemma 4 tag. Export GEMMA_MODEL in the backend terminal and restart. |
| Insufficient RAM / model unloads | Close other large applications; choose the smallest supported local variant that fits. Inspect Ollama logs. Disk download size is not runtime RAM requirement. Do not enable cloud fallback. |
| Timeout | Warm the model with `ollama run`, shorten repository scope, or export `GEMMA_TIMEOUT=240` (cap 300 seconds per call). The UI reports timeout honestly. |
| Invalid or truncated JSON | The client requests schema-constrained output, caps prompt length, asks for concise output, and retries once. It rejects invalid output. The initial build saw truncation; a shorter instruction and larger output budget produced valid live output. |
| Forbidden endpoint/model | Only HTTP loopback endpoints and local `gemma4:<tag>` identifiers are accepted. Check .env.example. |
| Backend doesn't see exported settings | Export in the same shell that starts Uvicorn. Merely copying .env.example to .env does not load it. |
| Structured output check | Run `python -m scripts.check_model /absolute/path/to/LinkWatch` from an activated environment. Pydantic rejects unknown fields and any `verified=true` output. |

Requests are dependency-by-dependency, with at most 12 flagged dependencies per API request. This limits work; narrow the target for larger inventories. One dependency can need two generations, each bounded by GEMMA_TIMEOUT. Keep Ollama and the app on loopback.

Live output is advice: even a high model confidence is not a calibrated compatibility guarantee. Inspect the exact source and execute independently reviewed tests before accepting a migration.
