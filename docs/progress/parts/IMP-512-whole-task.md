# IMP-512 · whole-task part

- Run id: RUN-068 (Sprint 5 batch A)
- Owner: Junaid (Mohammad Junaid Kureshi)
- Status: committed on `part/IMP-512-whole-task`, for the lead to integrate
- Base commit: 26bac9d
- Traces to: US-042; FR-040; NFR-031, NFR-043
- Card steps built: 1 to 5

## Changed files

- `apps/api/tests/contract/conftest.py` (created): the adapter registry `ADAPTERS` (`double`, `mock`, `gemini_recorded`) and the `adapter` fixture. `gemini_recorded` is the real Gemini adapter replaying `provider_recordings/gemini/` through a respx router over a fake transport (no key, no network). `GEMINI_FAILURES` maps each shared error to the recording that causes it (timeout stays a transport exception, since there is no HTTP answer to record). A `gemini` fixture builds the adapter over any answer.
- `apps/api/tests/contract/test_provider_contract.py`: the registry and inline Gemini builder moved to conftest; the default Gemini answer is now `ok.json` (TC-003, TC-004 expectations follow the recording). Added `test_tc_157_tc_008_the_same_caller_runs_unchanged_on_every_adapter` (one interface-only caller, unchanged, on every adapter, including a failing one) and `test_tc_156_generation_imports_no_concrete_adapter_or_vendor_sdk` (card step 3: AST check of every `app/generation/*.py`). The shared failure test is renamed `test_tc_005_failures_surface_as_the_shared_error_types`. The live generate case `test_tc_029_gemini_live_smoke` (IMP-301) is kept and skips without `GEMINI_API_KEY`.
- `apps/api/tests/fixtures/provider_recordings/gemini/permission_denied_403.json`, `model_not_found_404.json` (created) and its `README.md` (two rows): format fixtures for the auth and bad-request cases. No key, no prompt body, no personal data.
- `apps/api/.importlinter`: a two-line comment above the `vendor-sdk` contract recording TC-002 (card step 4). The contracts themselves were already complete; lines 74 to 82 are untouched.
- `docs/guides/adding-a-provider.md` (created): how a new adapter (Stage 2 FINETUNED_MODEL) is written, registered and joins the suite by one `ADAPTERS` entry.

Step 4 confirmation: `make imports` runs `lint-imports --config .importlinter` (Makefile line 124) and CI runs `make imports` in the required job (`.github/workflows/ci.yml` line 47); `make test-contract` runs in CI (line 95) with `-m "not live"`.

## Commands and results

| Command | Result |
| --- | --- |
| `make test-contract` | `91 passed, 2 deselected, 1 warning in 20.57s` (15 `gemini_recorded` cases, 15 `mock`, 15 `double`) |
| `.venv/bin/pytest tests/contract -m live` (no key) | `2 skipped, 91 deselected, 1 warning in 0.03s` |
| `.venv/bin/pytest tests/unit/ai` | `330 passed, 1 warning in 8.63s` |
| `.venv/bin/ruff check .` | `All checks passed!` |
| `.venv/bin/ruff format --check .` | `215 files already formatted` |
| `.venv/bin/mypy app` | `Success: no issues found in 118 source files` |
| `.venv/bin/lint-imports --config .importlinter` (and `make imports`) | `Contracts: 6 kept, 0 broken.` |
| `make check`, `make test-api`, `make e2e` | not run: no PostgreSQL or Docker on this machine and the part changes no app code; evidence from CI |

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-040 AC1 / TC-156: vendor SDK imports only inside adapters | verified | `make imports` (vendor-sdk, vendor-adapters contracts) and `test_tc_156_generation_imports_no_concrete_adapter_or_vendor_sdk` |
| FR-040 AC2 / TC-157: a new adapter runs through the caller unchanged | verified | `test_tc_157_tc_008_the_same_caller_runs_unchanged_on_every_adapter[double, gemini_recorded, mock]` |
| FR-040 AC3 / TC-158: the shared suite holds for each adapter | verified | every `adapter`-parametrised test passes for `mock` and `gemini_recorded` |
| TC-001 for MOCK and recorded GEMINI | verified | `test_tc_001_adapter_implements_the_model_provider_interface[mock, gemini_recorded]` |
| TC-002 | verified | `make imports`: `Contracts: 6 kept, 0 broken.` |
| TC-003 for MOCK and recorded GEMINI | verified | `test_tc_158_..._valid_io_1_result[mock, gemini_recorded]`, `test_tc_003_gemini_answers_through_the_interface_with_a_provider_result` |
| TC-005 for MOCK and recorded GEMINI | verified | `test_tc_005_failures_surface_as_the_shared_error_types[*-mock, *-gemini_recorded]` (seven error types) and `test_tc_005_gemini_failures_map_to_the_shared_types` |
| TC-008 for MOCK and recorded GEMINI | verified at contract level | the interface-only caller test above. The DB-backed TC-008 in `tests/api/test_generations.py` was not run here (no PostgreSQL) |
| make test-contract runs with no network and no key; only make live-smoke calls Gemini | verified | `make test-contract` passed with no key set; `-m live` only skips; the socket guard blocks provider hosts outside `live` |

## Blockers

none

## Proposed decisions

none

## Open issues

- `docs/guides/README.md` does not list `adding-a-provider.md`; that file is not in the card's file list.
- The Gemini recordings are still hand-written format fixtures (see their README); replace them with scrubbed live recordings once `make live-smoke` has been run with a key.
