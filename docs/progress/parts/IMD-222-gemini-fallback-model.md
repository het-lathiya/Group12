# IMD-222 · gemini-fallback-model part (PD-GEM-2 options a, b, e)

- Decision: IMD-222 (PD-GEM-2 options a, b, e; supersedes PD-GEM-1)
- Part: gemini-fallback-model
- Run id: RUN-100
- Owner: Nidhi
- Status: PR_OPEN candidate on `feat/gemini-fallback-model`
- Base commit: 77e52ba (on `main`)
- Points: 0 (IMD-210 rule)

## What changed

- `GEMINI_FALLBACK_MODEL_ID` (optional, empty = off, also off when equal to `GEMINI_MODEL_ID`): `app/core/config.py`, `.env.example`, `docs/secrets.md`, spec §H env table.
- `app/ai/providers/gemini.py`: when the retries of the configured model end in `ProviderRateLimited` (429) or `ProviderUnavailable` (503; the same kind also covers other 5xx and connection failures), one call goes to the fallback model with the same prompt, wire schema, output limit and parser, inside what is left of the 70 s allowance. Never for a repair call, never looped. A failing or unusable fallback answer re-raises the first error, so today's path (labelled rule-based plan, IMD-33) continues. Quota (`quota_exceeded`), auth and bad request never trigger it.
- `app/schemas/ai.py`: `ProviderResult.model_id` and `ProviderResult.fallback_from`, both default `None` (internal provider contract, not in `contracts/`).
- `app/generation/pipeline.py` and `repository.record_model`: a fallback answer records the configured model's failure on the breaker (it never closes it) and writes the fallback's ID to `ai_generations.model_id`. Daily caps are untouched (the generation is counted once at start).
- Embeddings unchanged: they share the retry and error path, but a second embedding model gives vectors in another space, and retrieval only matches chunks embedded with the configured `GEMINI_EMBEDDING_MODEL_ID`.
- `docs/spec/DECISION_REGISTER.md` IMD-222 row; `docs/decisions/provider-spend-limit.md` cap line (value to be filled by Nidhi; Awaiting validation).

## Commands

| Command | Result line |
| --- | --- |
| `.venv/bin/pytest -q tests/unit/ai/test_gemini_fallback_model.py` | `10 passed in 3.31s` |
| `.venv/bin/pytest -q tests/unit/ai tests/unit/generation tests/contract -m "not live"` | `668 passed, 2 deselected, 1 warning in 34.95s` |
| `.venv/bin/pytest -q tests/unit/core` | `129 passed, 1 warning in 8.23s` |
| `ruff check .` / `ruff format --check .` | `All checks passed!` / `271 files already formatted` |
| `mypy app` | `Success: no issues found in 139 source files` |
| `lint-imports --config .importlinter` | `Contracts: 7 kept, 0 broken.` |
| `python -m app.openapi_export` vs `contracts/` (diff -r) | only `contracts/README.md` differs (not generated): contracts unchanged |

Not run: `make openapi-check` web-type half (no `node_modules` in the worktree; the API document is unchanged, so the web types are too), `make check`, `make e2e` (operator fast mode; CI covers).

## Acceptance

- Primary 503 → fallback OK, `model_id` = fallback: verified (`test_fallback_answers_once_after_the_retries_of_a_503_or_429[503]`, pipeline test `recorded_model`).
- Primary 429 → fallback OK: verified (`[429]`).
- Both fail → labelled rule-based plan: verified (`test_pipeline_both_models_failing_ends_in_the_labelled_rule_based_plan`).
- Fallback unset → no second model call: verified (`test_no_second_model_call_when_the_fallback_is_off`, call log).
- Fallback called at most once: verified (call logs in every test).
- Breaker not reset by the fallback: verified (`test_pipeline_records_the_fallback_model_and_keeps_the_primary_failure`).

## Proposed decisions

- PD-RUN-100-1: the fallback triggers on the error kinds, so 500, 502 and connection failures (all `ProviderUnavailable`) trigger it as well as 503. Narrowing it to 503 alone would need a status on the error.

## Open issues

- PD-GEM-1 and PD-GEM-2 are not written anywhere in the repository; the IMD-222 row cites them as the run prompt gives them.
- The budget cap value is still to be filled by Nidhi in `docs/decisions/provider-spend-limit.md`.

## Blockers

none
