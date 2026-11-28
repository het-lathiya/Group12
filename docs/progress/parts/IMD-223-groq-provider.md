# IMD-223 · Groq provider, chain and decision

- Run: RUN-108 · Owner: Nidhi Chauhan · Points: 0
- Status: implemented for the combined `feat/groq-provider` pull request
- Base commit: `8e7dd4fb6471cf3e7108e2d3e7410b448e4c78ca` (`origin/main`)
- Prerequisites verified: D3 paced embedding (`1a69b7b`), D2 retry after failed city import (`dbd852f`), IMD-222 (`1bcdf30`), IMP-512
- Traces: IMD-223, IMD-33, IMD-112, IMD-222; FR-040–FR-046, FR-047, FR-057; TC-001–TC-008, TC-156–TC-158, TC-337

## Changes

- Adapter: `apps/api/app/ai/providers/groq.py`; `httpx` only, no dependency added. Same versioned prompt and original io-1/io-2 parser; strict schema conversion stays in the adapter. Model choice `openai/gpt-oss-20b`, with official sources dated 2026-11-28 in `docs/decisions/accounts.md`.
- Configuration: `apps/api/app/core/config.py`, `apps/api/app/schemas/ai.py`, `apps/api/app/ai/providers/base.py`, `apps/api/app/ai/factory.py`, `.env.example`, `apps/api/.importlinter`; both Groq settings default empty. Direct GROQ selection and the evaluation provider list (`apps/api/app/evaluation/run.py`) recognize the new provider. Gemini embeddings are delegated unchanged. The factory cache also distinguishes Gemini fallback-model settings.
- Chain: `apps/api/app/generation/pipeline.py`, `repository.py`; Gemini primary/retries → Gemini fallback → optional Groq → labelled rule-based plan. Outage, rate-limit, quota and timeout are the switch triggers. Both vendors share the 70 s generation budget; one existing repair call, with no vendor switch during repair. Groq failures, including auth/quota, use the labelled rule-based plan. With Groq off existing Gemini outcomes remain unchanged, including failed quota/configuration outcomes.
- Persistence: the same generation row records the actual attempted provider, actual returned model and safe settings. Gemini's breaker keeps its failure after Groq succeeds. A paused Groq breaker makes no request and keeps Gemini's identity. `tests/fixtures/pipeline.py` records these observations.
- Migration required: 0004's provider CHECK excludes GROQ. New upgrade SQL `apps/api/migrations/sql/0009_groq_provider.sql`, downgrade SQL `sql/down/0009_groq_provider.down.sql`, Alembic revision `versions/0009_groq_provider.py`; no old migration edited. ORM CHECK and readiness head updated in `app/db/models/generation.py`, `app/core/health.py`. Downgrade refuses while GROQ rows exist, preserving history.
- Tests: `tests/unit/ai/test_groq_adapter.py`, `tests/unit/generation/test_provider_chain.py`, `tests/fixtures/groq.py`, `tests/unit/ai/test_factory.py`, `tests/api/test_generation_records.py`, `tests/api/test_schema_drift.py`, `tests/conftest.py`. The socket guard blocks Groq and local Groq credentials cannot enable calls during offline tests.
- Contracts: health provider/name enums add GROQ. `make openapi` regenerated `contracts/openapi.v1.json`, `contracts/openapi.any-city.v1.json` and both `apps/web/lib/api/*schema.d.ts` files. AI schemas and published prompts are unchanged.
- Documentation: `docs/spec/DECISION_REGISTER.md` IMD-223, specification env table/§8, `docs/secrets.md`, `docs/decisions/accounts.md`.

## Verification

All pytest commands below ran from `apps/api`; database commands used a dedicated local container
on port 55408, with `TEST_DATABASE_URL` explicitly set. RUN-107 and its database were untouched.

| Command | Result line |
| --- | --- |
| `.venv/bin/pytest -q tests/unit/ai tests/unit/generation tests/unit/core tests/unit/evaluation tests/contract tests/api/test_schema_drift.py tests/api/test_generation_records.py tests/api/test_health.py -m 'not live'` | `1062 passed, 2 deselected, 1 warning in 84.26s (0:01:24)` |
| `.venv/bin/pytest -q tests/unit/core/test_groq_deploy.py tests/unit/generation/test_provider_chain.py` (final breaker case and wiring) | `28 passed in 3.52s` |
| `alembic downgrade 0008` then `alembic upgrade head` (dedicated test DB) | `Running downgrade 0009 -> 0008, 0009 allow GROQ generation records (IMD-223).` then `Running upgrade 0008 -> 0009, 0009 allow GROQ generation records (IMD-223).` |
| `.venv/bin/pytest -q tests/api/test_schema_drift.py tests/api/test_generation_records.py::test_groq_switch_updates_one_generation_and_counts_the_caps_once` (after round trip) | `37 passed in 1.83s` |
| `make lint` | `All checks passed!`; `All matched files use Prettier code style!` |
| `make typecheck` | `Success: no issues found in 140 source files`; `✓ Types generated successfully` (exit 0) |
| `make imports` | `Contracts: 8 kept, 0 broken.` |
| `make openapi-check` | `openapi-check: contracts/, apps/web/lib/api/schema.d.ts and apps/web/lib/api/any-city-schema.d.ts are up to date` |
| Final API `ruff check .`, `ruff format --check .`, `mypy app` | `All checks passed!`; `282 files already formatted`; `Success: no issues found in 140 source files` |

The warning is the existing FastAPI/Starlette httpx TestClient deprecation.

## Acceptance

| Criterion | Status and evidence |
| --- | --- |
| Gemini 503 and fallback 503 → Groq OK, GROQ/model recorded | Verified: `test_two_gemini_models_fail_then_groq_is_recorded_and_validated` |
| Groq 429 → labelled rule-based plan | Verified: `test_groq_failure_always_ends_in_labelled_rule_based[429]`; retries bounded |
| Groq off → no construction or HTTP call | Verified: optional-setting tests and `test_groq_off_makes_no_call_and_preserves_todays_path` |
| Groq bad JSON → invalid-output path and one repair only | Verified: invalid-output adapter cases and both JSON repair pipeline tests |
| Caps count once across provider/model switches | Verified against PostgreSQL: `test_groq_switch_updates_one_generation_and_counts_the_caps_once` yields `(1, 1)` |
| No third attempt, unsafe vendor error text, or extra repair loop | Verified: adapter retry/error tests, pipeline repair tests, import boundaries |
| Migration, ORM provider CHECK and readiness agree | Verified: 0009 round trip and drift/health tests |
| Live Groq response | Not verified: no key; see Manya's part record |

Not run: full `make check` and E2E (operator fast mode; CI covers), account provisioning or AWS
deploy (Kirtan's operational step), a live provider call (no Groq key). Production service templates
are still pending IMP-801, as in RUN-103; Kirtan's runbook records the required settings.

Blockers: none. Proposed decisions: none; IMD-223 was explicitly authorized by RUN-108.

## RUN-108b · migration-head test follows the chain

- Owner: Nidhi Chauhan · Points: 0 · Base commit: `23390e18f80e963d39270a16db83f3cdcec3330a`
- The previous API CI run failed only the test that still required 0008 to be the head.
- `apps/api/tests/api/test_live_destinations_schema.py`: renamed the test to
  `test_live_destinations_schema_migration_0008_present_and_chain_linear`. It requires the 0008
  file in Alembic's chain, 0009's `down_revision == "0008"`, one head, all revision files in the
  chain and consecutive links from the base to the newest revision. The newest file and readiness
  must agree with Alembic's current head. All destination schema assertions are preserved.
- `apps/api/tests/api/test_health.py`: the migrated-database response expectation derives its head
  from Alembic, independently of the production readiness constant.
- Audit: no other 0008-as-current-head pins in `apps/api/tests`, `apps/api/app`, `scripts` or
  `.github`. Remaining matches describe the historical migration, validate its link or are UUIDs.
- Changed documentation: this part record. No schema, migration, contract or application change.

| Command (from `apps/api`) | Result line |
| --- | --- |
| `.venv/bin/pytest -q tests/unit` | `1989 passed, 1 warning in 30.23s` |
| `.venv/bin/pytest -q tests/api/test_live_destinations_schema.py tests/api/test_schema_drift.py tests/api/test_health.py` | `90 passed, 1 warning in 6.76s` |
| Ruff check and format check on both changed test files | `All checks passed!`; `2 files already formatted` |

Docker was reachable; API tests used a dedicated disposable database on port 55408. The warning
is the existing TestClient deprecation. Local acceptance is verified. PR #311 checks are monitored
after push and their terminal results are reported at run completion. Blockers: none. Proposed
decisions: none.
