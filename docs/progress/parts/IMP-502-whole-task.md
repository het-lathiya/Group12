# IMP-502 · whole-task part

- Run id: RUN-068 (Sprint 5 batch A)
- Owner: Nidhi (Nidhi9864)
- Status: committed on `part/IMP-502-whole-task` with an integration fix commit, not pushed; the lead integrates
- Base commit: 26bac9d
- Traces to: US-066; FR-057; NFR-007, NFR-030; IMD-22, IMD-44, IMD-126, IMD-136
- Card steps built: 1 to 6, and the SG-3 routed fix (repair call through the adapter's retry path with `wire_schema(output_model)`, one attempt inside its own 25 s, never beyond what the job has left)

## What changed

- `apps/api/app/validation/repair.py` (created, pure): `repair(output, findings, scope, gaps)` returns the answer with the cheapest fixes and their count. Order: (1) forward shift of every unlocked item to max(own start, previous end + travel + buffer), travel and buffer from step 9 (`travel_gaps(plan)`); (2) per error finding, codes in the order UNKNOWN_PLACE, OUTSIDE_TRIP_DATES, CLOSED_ON_DAY, OUTSIDE_HOURS, OVERLAP, the first fix that works (move to the trip day with most room, swap with the next item, drop the lowest-ranked unlocked non-must-visit item); (3) each missing must-visit place appended to the trip day with most room (item count and active minutes within the pace limits). Never moves a locked item, never drops a must-visit place, never touches prices, hours, travel or budget findings. One pass, so it always ends. `scope_for(request)` reads the limits, must-visit list, locked items and the ranked shortlist. Works on io-1 and io-2 (citations kept).
- `apps/api/app/generation/pipeline.py`: step 10. `assess` = step 8 (`apply_limits`, `check_output`), step 9, the deterministic repair and step 9 again if anything changed. Repair works on step 9's times (`repair.retimed`), never on the model's: step 9 replaces the model's times anyway, so a plan it already put right counts no repair and stays `model`. A must-visit place whose MUST_VISIT_MISSING reason is a filter conflict or "closed every day" is not inserted; only one that lacked room is. Step 8's drops of unknown places and days outside the trip count as deterministic repairs (the §8.18 example counts the dropped `d1-i3`). Usable with no error left: saved `model`, or `model_repaired` after a fix. Otherwise `repair_call`: status `repairing`, one provider call with the same request plus `repair_context = {invalid_output, findings}` (invalid_output is "" when the adapter could not read the answer), inside `asyncio.timeout(min(25 s, 105 s − elapsed))`. The repaired answer goes through `assess` again: usable → `model_repaired`; not usable → rule-based plan, `unresolved_validation`; failed, unreadable or impossible repair call → rule-based plan, `invalid_output`; quota or configuration error on the repair call → `failed` (IMD-44). `repair_attempts` and `deterministic_repairs` are written on `ai_generations` and in the version's validation_summary; token counts of both calls are added. `save` now takes the step-9 plan and findings; `run_fallback` computes them first. The breaker still records the first call only.
- `apps/api/app/ai/prompts/templates/itinerary_generate/v1/repair.txt` (created): wording mirrors v2's repair.txt, without the passage rules; says what an empty `invalid_output` means.
- `apps/api/tests/unit/validation/test_repair.py` (created, 25 tests): pure repair (TC-190, TC-313) and step 10 on the `fixtures.pipeline` stand-ins with a logging mock (TC-011, TC-191, TC-192 without a database, call counts).
- `apps/api/tests/api/test_generations.py`: TC-011 (2 calls, repair_context sent, fallback `invalid_output`, repair_attempts 1), TC-191 (flawed overlap, 1 call, `model_repaired`), TC-192 (no room for a must-visit place, 2 calls, MUST_VISIT_MISSING saved as a warning); TC-135/TC-307 now expects `model_repaired` with the invented ID dropped; TC-142 expects `model_repaired`.

Necessary changes outside the card's file list (behaviour the card changes, or the routed fix):

- `apps/api/app/ai/providers/gemini.py`: a request with `repair_context` goes through `_with_retries(..., repair=True)`: one attempt, deadline 25 s (routed fix; IMP-401 record deferred it here). The wire schema was already `wire_schema(output_model)` for every call.
- `apps/api/app/core/config.py`: `REPAIR_TIME_ALLOWANCE_S = 25`, next to `GEMINI_TIME_ALLOWANCE_S`, shared by the adapter and the pipeline.
- `apps/api/tests/fixtures/prompt_hashes.json`: the line for `itinerary_generate/v1/repair.txt` (SG-1 carry-over, IMP-111 record).
- `apps/api/tests/unit/ai/test_registry.py`: TC-169 now expects v1 to have repair.txt.
- `apps/api/tests/unit/ai/test_retry.py`: one test, the repair call is one attempt of at most 25 s with the io-1 wire schema.
- `apps/api/tests/fixtures/pipeline.py`: a `mark_repairing` stand-in.
- `apps/api/tests/unit/generation/test_pipeline.py`, `test_must_visit.py`, `apps/api/tests/unit/validation/test_output_check.py`, `test_injection_cases.py`, `apps/api/tests/api/test_generation_failures.py`: an invented or inactive place, or an item outside the trip, is now dropped by repair and the answer saved as `model_repaired` instead of the rule-based plan; the must-visit stand-in tests use one item a day so there is no room and the finding stays. Each still asserts the invented ID is never saved. `unknown_place` left the fallback parametrisation of TC-148.

## Commands and results

Run from `apps/api` with `PYTHONPATH=.` (the worktree's `app` confirmed). No PostgreSQL, no E2E, no live call.

| Command | Result |
| --- | --- |
| `.venv/bin/pytest tests/unit -k repair` (= `make test-unit ARGS='-k repair'`) | `28 passed, 1038 deselected, 1 warning in 1.36s` |
| `.venv/bin/pytest tests/unit` | `1066 passed, 1 warning in 18.13s` |
| `.venv/bin/pytest tests/contract` | `87 passed, 2 skipped, 1 warning in 13.48s` |
| `.venv/bin/ruff check .` | `All checks passed!` |
| `.venv/bin/ruff format --check .` | `216 files already formatted` |
| `.venv/bin/mypy app` | `Success: no issues found in 119 source files` |
| `.venv/bin/lint-imports --config .importlinter` | `Contracts: 6 kept, 0 broken.` |
| `.venv/bin/pytest tests/api/test_generations.py tests/api/test_generation_failures.py --collect-only -q` | `65 tests collected in 0.97s` |

### Integration fix (second run, same RUN-068)

The lead's run found 11 DB-backed API tests failing on this branch. Root cause: the forward shift compared the model's own start times with step 9's travel times, so the MOCK happy path (30-minute gaps, longer real transfers) counted every re-timed item as a repair (`model_repaired`, deterministic_repairs 12 instead of 1 for unknown_place). Repair now starts from step 9's times (`repair.retimed`). A second cause showed after that: repair inserted a must-visit place that had a filter conflict (not step-free for a step-free trip); it now inserts only places that lacked room. Tests changed in that fix: my own TC-191 API test now expects `model` with 0 repairs (step 9 re-times the flawed overlap, so nothing is left to repair); `test_must_visit_place_is_forced_into_the_shortlist_beyond_the_cap` reads the first request (`sent[0]`, no repair_context) because the card's one repair call follows when no day has room; the unit flawed test expects 1 repair (the insertion), not 2. A unit test for `retimed` was added.

PostgreSQL: the lead's PostgreSQL 16 + pgvector, `TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:55432/travel_test_502`.

| Command | Result |
| --- | --- |
| `.venv/bin/pytest -q tests/api/test_generations.py tests/api/test_itinerary.py tests/api/test_rag_retrieval.py tests/api/test_generation_failures.py` (before the fix) | `11 failed, 89 passed in 51.49s` |
| same (after the fix) | `100 passed in 50.33s` |
| `.venv/bin/pytest -q tests/api` | `426 passed, 1 warning in 131.46s (0:02:11)` |
| `.venv/bin/pytest tests/unit` | `1067 passed, 1 warning in 19.64s` |
| `.venv/bin/pytest tests/unit -k repair` | `29 passed, 1038 deselected, 1 warning in 1.34s` |
| `.venv/bin/ruff check .` | `All checks passed!` |
| `.venv/bin/ruff format --check .` | `216 files already formatted` |
| `.venv/bin/mypy app` | `Success: no issues found in 119 source files` |
| `.venv/bin/lint-imports --config .importlinter` | `Contracts: 6 kept, 0 broken.` |

Not run: `make check`, `make e2e`.

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-057 AC1 / TC-190: an overlap is shifted deterministically without a model call | verified (unit) | `test_repair_tc_190_an_overlap_is_shifted_...`; `test_repair_tc_190_tc_191_flawed_overlap_and_must_visit_fixed_without_a_model_call` (1 call). API: `test_tc_191_repair_fixes_the_overlap_...` passed (1 call, outcome model, no OVERLAP) |
| FR-057 AC2 / TC-191: at most one provider call when deterministic repair cannot fix | verified (unit) | `test_repair_tc_191_tc_192_an_error_left_gets_one_call_...` (2 calls), `test_repair_tc_011_...` (2 calls). API TC-192 passed |
| FR-057 AC3 / TC-192: unresolved issues appear as warnings | verified (unit) | MUST_VISIT_MISSING saved with the plan after the repair call. API `test_tc_192_...` passed |
| TC-011: invalid output goes to repair, never a blind retry; the mock records at most 2 calls | verified (unit, API) | logging mock: invalid_json 2, unknown_place 1, flawed 1 or 2; quota-on-repair 2; no-time-left 1. API `test_tc_011_...` passed |
| TC-313 (repair part): locked items and must-visit places unchanged | verified (unit) | `test_repair_tc_313_a_locked_item_is_never_shifted`, `test_repair_tc_313_a_locked_or_must_visit_item_is_never_moved_or_dropped`, overlap against a locked item moves the other one |
| Repair terminates on every fixture; repair_attempts never above 1 | verified (unit) | single pass, `test_repair_terminates_and_a_second_pass_finds_nothing_to_fix`; repair_attempts is only ever 0 or 1 in code and every route asserts it; the DB CHECK itself not exercised (no PostgreSQL) |
| Routed fix (SG-3): wire_schema(output_model), retries bounded by the remaining allowance, no transport retry | verified (unit) | `test_retry_the_repair_call_is_one_attempt_of_at_most_25_s_with_the_wire_schema`; `test_repair_the_call_gets_at_most_25_s_and_never_more_than_the_job_has_left`; `test_repair_with_no_time_left_...` |
| Completion evidence: API-23 JSON of a model_repaired generation, make check green | not verified | needs PostgreSQL (TC-191 API test produces it in CI) |

## Proposed decisions

- PD-IMP-502-1: a repair call is made whenever an error finding remains, including MUST_VISIT_MISSING alone (card step 3 "if errors remain"). If that call then fails, §8.13 sends the generation to the rule-based plan even though the deterministic plan was usable. Confirm, or keep the deterministic plan in that case.
- PD-IMP-502-2: step 8's drops (unknown place, day outside the trip) count as deterministic repairs and give `model_repaired` (as in the §8.18 example). This changes the TC-307 route from `fallback_rule_based` to `model_repaired`; the invented ID is still never saved. Confirm, and amend the IMP-306 / IMP-402 wording that says an invented ID ends in the fallback.
- PD-IMP-502-3: an answer from the repair call that step 8 cannot read (schema or limit failure) is treated as a failed repair call (`invalid_output`), not `unresolved_validation`.
- PD-IMP-502-4: `deterministic_repairs` is the total over both passes (before and after the repair call).
- PD-IMP-502-5: repair counts only what remains after step 9's recalculation; the model's own overlapping times, which step 9 always replaces, are not a repair (a flawed answer with only an overlap is saved as `model`).
- PD-IMP-502-6: repair never inserts a must-visit place whose reason is a filter conflict or "closed every day"; it stays MUST_VISIT_MISSING with that reason.

## Open issues

- `app.validation.repair` is pure but not yet listed in the pure-domain contract of `apps/api/.importlinter` (not in this card's file list); one line to add.
- `repair_attempts` reaches the row only on `complete`; a generation that fails after the repair call (quota, or an unusable rule-based plan) keeps 0, because `repository.fail` takes no repair counts.
- The repair request is not passed through `limits.enforce_input_limit` again; `repair_context` makes it larger than the first request.
- Status goes validating → repairing and stays repairing until completed or failed (no second validating); both transitions are allowed by `records.TRANSITIONS`.
- CLOSED_ON_DAY and OUTSIDE_HOURS have no validator rule yet, so their fixes are exercised by unit tests only.
