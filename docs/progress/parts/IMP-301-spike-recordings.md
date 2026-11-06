# IMP-301 · spike-recordings part

- Run id: RUN-046 (grouped, IMD-121, with IMP-303 and IMP-301)
- Owner: Manya (manyarana)
- Status: PR_OPEN
- Base commit: 4f20bfc
- Branch: feat/IMP-303-301-gemini-request
- Reviewer: Kirtan (kirtan-S111)
- Traces to: US-037; FR-041; OD-14; TC-013 to TC-015, TC-018 to TC-024, TC-030 to TC-032, TC-159 to TC-161
- Card steps built: 1 and 8

## Changed files

- `docs/decisions/gemini-setup.md` (created): each fact with its source, date and status, and the live smoke line.
- `apps/api/tests/fixtures/provider_recordings/gemini/` (created): ten JSON format fixtures and a README saying they are format fixtures until a live recording replaces them.
- `apps/api/tests/unit/ai/test_gemini_adapter.py` (created, 58 tests): each fixture is replayed through the real SDK over a fake HTTP transport.

## Spike result

- The official pages were read on 6 November 2026. `ai.google.dev` now redirects to `aistudio.google.com/docs/`.
- API style: the Interactions API is Generally Available, which matches the default of §8.4 and Part `gemini-adapter`. Nothing in that part had to change.
- Model: `gemini-3.5-flash-lite` is the Stable candidate. `gemini-3.8-flash` has the badge New, so it does not meet the stable-ID rule of §8.4.
- Nothing on the pages changes the card's scope.

## Commands and results

| Command | Result line |
| --- | --- |
| `make test-unit ARGS='-k gemini'` | `58 passed, 388 deselected, 1 warning in 5.87s` |
| Grep of `apps/` and `docs/` for the Google API key prefix (dependency folders excluded) | prints nothing |
| `make lint` | `All checks passed!` (ruff); `All matched files use Prettier code style!` |
| `make typecheck` | `Success: no issues found in 87 source files` |
| `make imports` | `Contracts: 4 kept, 0 broken.` |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |
| `make test` (via `make check`, `TEST_DATABASE_URL` = the §4.7 default on `pgvector/pgvector:pg16`) | unit `446 passed, 1 warning`; contract `64 passed, 1 deselected, 1 warning`; api `232 passed, 1 warning`; authz `28 passed`; web `Tests  80 passed (80)` |
| `make check` | exit 0 |

Not run: `make live-smoke` (no key in this run, by instruction).

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| The key comes from settings and never surfaces (TC-013) | verified | `test_gemini_tc_013_...` checks the error, logs, settings, metadata and health |
| Structured output, store off, no sampling (TC-014, TC-030, TC-032) | verified on the fake transport | Tests of those names read the request body |
| A valid answer parses (TC-015) | verified | `test_gemini_tc_015_...` |
| Timeout (TC-018) | verified for the adapter | Two `test_gemini_tc_018_...` tests; the job-level fallback is IMP-401 and IMP-403 |
| Blocked, empty, truncated, malformed, schema violation (TC-019 to TC-023) | verified | `test_gemini_tc_019_...`, `test_gemini_tc_020_to_023_...` |
| Usage mapping (TC-024) | verified | `test_gemini_tc_024_...` |
| The model ID is recorded exactly as configured (TC-031) | verified | `test_gemini_tc_031_...` |
| FR-041 AC1 (TC-159) and AC3 (TC-161) | verified on format fixtures | Tests of those names |
| FR-041 AC2 (TC-160) | verified in part | 429 gives `ProviderRateLimited` with `retry_after_s`; the bounded backoff is IMP-401 |
| One live smoke call dated in gemini-setup.md (TC-029) | not verified | Pending, run by the key holder before SG-3 |
| Real response shapes | not verified | Format fixtures only, no key |

## Blockers

None.

## Proposed decisions

- **PD-IMP-301-7: OD-14.** The Interactions API is proposed as the API style. The latency condition of §8.4 cannot be measured without a key, so the team confirms it after the live smoke.
- **PD-IMP-301-8: replay level.** §13 says recordings replace `_call_vendor`. They go through a fake HTTP transport instead, as the run asked, so the SDK's own parsing and retries are covered too.

## Open issues

- The token counter, the team key's limits and live thinking-token counts need the key (see the Unverified rows of `gemini-setup.md`).
- IMP-113 is not merged; this file holds the Gemini facts until then.
