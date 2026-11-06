# IMP-306 · output-validation part

- Run id: RUN-048 (grouped, IMD-121, with IMP-306 injection-cases and IMP-313)
- Owner: Manya (manyarana)
- Status: PR_OPEN
- Base commit: 654b4f7
- Branch: feat/IMP-306-313-wave3
- Reviewer: Nidhi (Nidhi9864)
- Traces to: US-050; FR-032; NFR-016; IMD-22; TC-136, TC-137, TC-138, TC-022, TC-023, TC-011
- Card steps built: 1 to 4

## Changed files

- `apps/api/app/schemas/ai.py`: `ItineraryOutput` checks the limits that depend on the trip (day count, a day twice, items per day) when validation context is passed. The other io-1 limits were already on the model. Without context nothing changes, so an adapter's parse and the exported schema stay the same.
- `apps/api/app/validation/output_check.py` (created): `apply_limits`, `check_output` -> `OutputCheckResult`, and `summary`.
- `apps/api/app/generation/pipeline.py`: `output_problem` is replaced by step 8 through `output_check`. `ProviderInvalidOutput` from an adapter and every rejected answer go through one function, `end_invalid_output`, which IMP-402 fills. The active place IDs are read again after the provider call.
- Tests: `tests/unit/validation/test_output_check.py` (created); `tests/fixtures/pipeline.py` (created, holds `Journal` and `recorded_gemini`, moved from `test_pipeline.py` so the validation tests can use them); `tests/api/test_generations.py`, `tests/unit/generation/test_pipeline.py` (modified).

## Evidence: MOCK scenario `unknown_place` on the test database

`tests/api/test_generations.py::test_tc_135_...`, on `pgvector/pgvector:pg16`, with the row printed once:

```text
failed invalid_output {'kind': None, 'infos': 0, 'errors': 1, 'warnings': 0, 'invalid_ids': 1, 'rejected_items': 1}
```

## Commands and results

| Command | Result line |
| --- | --- |
| `make test-unit ARGS='-k output_check'` | `23 passed, 662 deselected, 1 warning in 1.87s` |
| `make test-api ARGS='-k invalid_output'` | `1 passed, 297 deselected, 1 warning in 2.16s` |
| `make lint` | `All checks passed!` |
| `make typecheck` | `Success: no issues found in 100 source files` |
| `make imports` | `Contracts: 6 kept, 0 broken.` |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |
| `make check` (all three parts of RUN-048 in the tree, `TEST_DATABASE_URL` on `pgvector/pgvector:pg16`) | exit 0: unit `685 passed, 1 warning`; contract `87 passed, 2 deselected, 1 warning`; api `298 passed, 1 warning`; authz `29 passed`; web `Tests  88 passed (88)` |
| `make e2e ARGS='journey'` (steps of `.github/workflows/e2e.yml`; web on port 3100 because an older server held 3000) | `4 passed (6.9s)` |

Not run: `make live-smoke` (no key, by instruction).

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-032 AC1: malformed JSON is classified as invalid output (TC-136, TC-022) | verified | `test_tc_136_tc_022_tc_023_...` on the recorded Gemini answer. Handling by FR-057 waits for IMP-502 |
| FR-032 AC2: a day outside the trip is rejected (TC-137) | verified | `test_tc_137_...` |
| FR-032 AC3: an invented place ID fails validation (TC-138) | verified | `test_tc_138_...`, `test_tc_135_...` on the database |
| Schema violations are classified (TC-023) | verified | `test_tc_023_...` and the recorded `schema_violation` answer |
| Invalid output goes to repair or fallback, never retried blindly (TC-011) | partly verified | `test_tc_011_...` shows one provider call, the kind recorded and nothing saved. The `repairing` status and `model_repaired` or `fallback_rule_based` outcome wait for IMP-402 and IMP-502 |
| An invented ID never reaches `itinerary_items` (TC-138 part) | verified | `test_tc_135_...` finds no plan rows |
| With no usable plan the job ends `fallback_rule_based` (TC-307) | not verified | Needs IMP-402; until then the job ends `failed` |
| Counts in `ai_generations.validation_summary` | verified | `test_tc_135_...` compares the stored value exactly; `test_the_counts_reach_the_completed_record_...` |
| `contracts/ai/io-1.schema.json` unchanged | verified | `make openapi-check` |

## Blockers

None.

## Proposed decisions

- **PD-IMP-306-1: invalid output before IMP-402.** The specification gives no outcome for invalid output without a fallback planner, so `end_invalid_output` ends the job `failed` with `failure_reason` `invalid_output` and the kind in `validation_summary`. IMP-402 replaces this body.
- **PD-IMP-306-2: "day count = trip days" is enforced as an upper limit.** Exact equality would refuse a plan that runs out of places. §8.4 tells MOCK to fill the first days first, and `sample_request` (2 days, 3 places, 5 per day) gives one day. §8.7 also allows 1 to 14 entries and §8.12 calls a plan usable with at least one item. More entries than trip days is `schema_violation`, so `[1, 2, 3]` on a 2-day trip stops as a whole, while `[1, 3]` reaches `check_output` as OUTSIDE_TRIP_DATES. §8.11 step 2 would drop day 3 in the first case too; the team should say whether the limit stays once repair exists.
- **PD-IMP-306-3: any UNKNOWN_PLACE or OUTSIDE_TRIP_DATES makes the answer unusable.** This follows §8.12 (usable means none of these remain) and keeps TC-135. The items are not simply dropped and saved, because repair (IMP-502) has not arrived.
- **PD-IMP-306-4: duplicates.** The card rejects a repeat anywhere in the plan; §8.11 says only on the same day. This follows the card. There is no finding code for a repeat and none is added, so it counts in `rejected_items`, has no finding and leaves the plan usable.
- **PD-IMP-306-5: `kind` is null for a place check.** `kind` holds a `ProviderInvalidOutput` kind only; a place-check rejection shows in `invalid_ids` and `rejected_items`.

## Open issues

- §13.3 has no TC-136 row. The card maps TC-136 to TC-138 onto FR-032 AC1 to AC3, so TC-136 is taken as AC1.
- Day scope (API-30) is not handled: §8.11 also drops days other than the requested one, and `check_output` has no scope argument. The API-30 card must add it, along with the re-insertion of locked items (§8.11 step 4).
- An answer the adapter refuses has its token usage dropped, because `ProviderInvalidOutput` carries none.
