# IMP-301 · gemini-adapter part

- Run id: RUN-046 (grouped, IMD-121, with IMP-303 and IMP-301)
- Owner: Nidhi (Nidhi9864)
- Status: PR_OPEN
- Base commit: 4f20bfc
- Branch: feat/IMP-303-301-gemini-request
- Reviewer: Kirtan (kirtan-S111)
- Traces to: US-037; FR-041; NFR-004, NFR-013, NFR-020, NFR-024, NFR-031, NFR-042; TC-002, TC-003, TC-004, TC-005
- Card steps built: 2 to 7

## Changed files

- `apps/api/app/ai/providers/gemini.py` (created): `GeminiProvider(settings)`.
  - `_call_vendor` is the only vendor call: Interactions API, `store=False`, io-1 wire schema, lowest thinking level, no sampling parameter.
  - `parse_output` gives the invalid-output kinds, `map_status_error` the shared errors. The error code is read before the status, and vendor text is never read.
  - It also holds usage mapping, `generation_settings`, `health_check` and `get_model_metadata`.
- `apps/api/app/ai/factory.py`: the GEMINI branch builds `GeminiProvider`, and the IMP-208 stand-in is removed.
- `apps/api/pyproject.toml`: `google-genai==2.34.0` (was `>=2.34,<3`).
- `apps/api/tests/contract/test_provider_contract.py`: `gemini_recorded` joins the suite through a fake transport; TC-003, TC-004, TC-005 and the `live` test TC-029.
- `apps/api/tests/unit/ai/test_factory.py`: the three stand-in assertions now describe the adapter, with a new test for each missing setting.

`app/core/config.py` and `app/ai/errors.py` needed no change: the settings and error types already exist. `make live-smoke` already exists and runs `tests/contract -m live`, so the Makefile is unchanged. `make test-contract` excludes the `live` test, and no other test target collects it.

The spike (part `spike-recordings`) found no fact that contradicts this part, so nothing here was changed because of it.

## Commands and results

| Command | Result line |
| --- | --- |
| `make test-contract` | `64 passed, 1 deselected, 1 warning in 3.98s` |
| `make lint` | `All checks passed!` (ruff); `All matched files use Prettier code style!` |
| `make typecheck` | `Success: no issues found in 87 source files` |
| `make imports` | `Contracts: 4 kept, 0 broken.` |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |
| `make test` (via `make check`, `TEST_DATABASE_URL` = the §4.7 default on `pgvector/pgvector:pg16`) | unit `446 passed, 1 warning`; contract `64 passed, 1 deselected, 1 warning`; api `232 passed, 1 warning`; authz `28 passed`; web `Tests  80 passed (80)` |
| `make check` | exit 0 |

Not run: `make live-smoke` (no key in this run, by instruction) and `make e2e`.

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| google-genai is imported only in gemini.py (TC-002) | verified | `make imports`, `Vendor isolation` contract kept |
| The adapter answers through the interface (TC-003) | verified | `test_tc_003_...` and the shared suite on `gemini_recorded` |
| Usage maps or stays null (TC-004) | verified | `test_tc_004_gemini_usage_is_mapped`, `test_tc_004_gemini_usage_stays_null_when_absent` |
| Each vendor error maps to its shared type (TC-005) | verified | `test_tc_005_gemini_failures_map_to_the_shared_types`, 14 cases |
| One live smoke call (TC-029) | not verified | Pending, run by the key holder |

## Blockers

None.

## Proposed decisions

- **PD-IMP-301-1: no model ID default in code.** The run asked for a default from the spike. §4.5 sets an empty default, and `tests/unit/core/test_config.py` expects a missing `GEMINI_MODEL_ID` to stop staging and production; a default would remove that check. `Settings` stays empty, and the value `gemini-3.5-flash-lite` is recorded in `docs/decisions/gemini-setup.md` for each environment.
- **PD-IMP-301-2: generation_settings.** `ProviderResult` has no such field and §8.3 fixes its shape, so the adapter exposes a `generation_settings` property, which is not on the protocol. IMP-305 needs a way to read it; adding the field to `ProviderResult` is the proposal.
- **PD-IMP-301-3: remaining allowance.** `generate_itinerary(request)` has no parameter for the time left, and the protocol must not change. Each attempt gets `min(GEMINI_TIMEOUT_S, 70)`; IMP-401, which owns the retry loop and the clock, must bound the later attempt.
- **PD-IMP-301-4: exact SDK pin and private import.** The Interactions error classes are exported only from `google.genai._gaos.lib.compat_errors`, and the SDK retries once even with `attempts=0`. The adapter depends on both, so the version is pinned exactly.
- **PD-IMP-301-5: 401.** The official code `authentication` (401) maps to `ProviderAuthError`, as §8.3 says "key missing, invalid"; the card names only 403.
- **PD-IMP-301-6: TC-029 location.** §13 names `tests/contract/test_gemini_live.py`; the card names `test_provider_contract.py`. The card is followed.

## Open issues

- Retries, backoff and the breaker are IMP-401. `health_check` uses the last call's state until then.
- `AI_TEMPERATURE` stays configured and unsent.
