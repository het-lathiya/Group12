# RUN-075 · prompt-v2 part (itinerary_generate v3)

- Part: new prompt version of itinerary_generate (0 points)
- Run id: RUN-075 (Sprint 6 batch A)
- Owner: Manya (Manya Rana)
- Status: PR_OPEN once the lead opens the pull request; committed on `part/g`, not pushed
- Base commit: a6307c3
- Traces to: IMD-180, IMD-181, IMP-606 (FR-083)

## Version number

The run asked for "itinerary_generate v2", but v2 already exists (gr-2 / io-2, IMP-316) and a published version is never edited (§8.5, TC-170). The new version is therefore **v3**, with the same input and output schemas as v2 (gr-2, io-2). The record keeps the requested slug `RUN-075-prompt-v2`.

## Changed files

- `apps/api/app/ai/prompts/templates/itinerary_generate/v3/` (created): `system.txt` is v2's text with rule 10 changed and rules 11 and 12 added, and the meal detail extended:
  - rule 10: the model keeps text short and factual and does not write "AI-written" or any other label; the application adds the label (IMD-180);
  - rule 11 and a detail line: a place at most once in the whole plan, meal stops included, never on two days and never twice on one day (IMD-181);
  - rule 12 and the meal detail: meal slots only with food places from the shortlist; no meal item when `limits.meal_slots` is empty; `slot_type` meal only for a food place (IMP-606).
  `user.txt` and `repair.txt` are v2's, byte for byte; `meta.json` names v3, dated 2026-11-15, with the change note.
- `apps/api/tests/fixtures/prompt_hashes.json`: the four v3 hashes added; v1 and v2 lines unchanged.
- `apps/api/tests/unit/ai/test_registry.py`: `test_prompt_v3_states_the_label_unique_place_and_meal_rules`.
- `apps/api/app/evaluation/run.py`: `duplicate_places(answer, trip_days)` (items on the trip's days whose place came earlier in the plan, meals included); each attempt's score holds `duplicate_places` and `no_duplicate_places`; the run record hashes `eval/metrics_v2.md`.
- `apps/api/app/evaluation/metrics.py`: `METRICS_VERSION = "v2"`, count `no_duplicate_places`; `compute` reads a missing score field as not counted.
- `eval/metrics_v2.md` (created): v1's definitions plus `no_duplicate_places`. `eval/metrics_v1.md` is unchanged, as that file says a changed definition is a new version.
- `apps/api/tests/unit/evaluation/test_harness.py`: `test_duplicate_places_count_a_repeated_place_and_meal_stops_imd_181`.

## Active version

v2 stays active. The active version is `PROMPT_TEMPLATE_VERSION` (§4.5): the Settings default `v2`, `.env.example` (`PROMPT_TEMPLATE_VERSION=v2`, an append-only file for this run) and `infra/aws/services/api.staging.json.tmpl` (account owner only). Switching needs those three values changed and, under IMD-176, an evaluation run from a clean tree at a commit on main. No contract, io-2 or recorded-response fixture changes with v3. See PD-RUN-075-G3.

## Commands

Run from the worktree root with `PYTHONPATH=$PWD/apps/api`. API tests used a throwaway local PostgreSQL 16 with pgvector (`travel_test_g` on 127.0.0.1:55432).

- `make test-unit ARGS='-q'` → `1163 passed, 1 warning in 18.77s`
- `make test-contract ARGS='-q'` → `91 passed, 2 deselected, 1 warning in 19.98s`
- `make test-api ARGS='-q'` → `470 passed, 1 warning in 157.09s (0:02:37)`
- `make lint` (ruff) → `All checks passed!`; `make typecheck` (mypy) → `Success: no issues found in 122 source files`; `make imports` → `Contracts: 6 kept, 0 broken.`
- `make eval PROVIDER=MOCK DATASET=trips/v1 ARGS="--out <scratch directory outside the repository>"` → `evaluation 20261115T165739Z-mock: 45 attempts, written to <scratch>`; counts `no_duplicate_places 45/45, place_ids_valid 45/45, schema_valid 45/45, usable 45/45`, metrics version v2. Nothing was written into the repository; this is not a recorded evaluation run (IMD-176).

Not run: a recorded evaluation run of v3 (IMD-176: clean tree at a commit on main); any Gemini call.

## Acceptance criteria

- The new version tells the model not to write the "AI-written" label (IMD-180): **verified** by `test_prompt_v3_states_the_label_unique_place_and_meal_rules`.
- A place at most once per generated plan, meal stops included, stated in the prompt (IMD-181): **verified** by the same test.
- Meals come from food places in the shortlist (IMP-606): **verified** by the same test.
- v1 and v2 stay in the registry unchanged: **verified** by `test_prompt_tc_170_template_files_match_the_committed_hash_list`.
- Duplicate count is an evaluation check (IMD-181): **verified** by `test_duplicate_places_count_a_repeated_place_and_meal_stops_imd_181` and the MOCK dry run above.

## Blockers

none

## Proposed decisions

- **PD-RUN-075-G3: activate itinerary_generate v3.** Set `PROMPT_TEMPLATE_VERSION=v3` (Settings default, `.env.example`, staging service template) after an evaluation of v3 against v2 recorded from main (IMD-176). Until then v2 stays active and IMD-180 and IMD-181 rely on the application's own checks (label added by the API; step 8 drops a repeated place).
- **PD-RUN-075-G4: metrics version v2.** The duplicate count makes the metric definitions v2 (`eval/metrics_v2.md`); runs recorded with v1 are not comparable on this count. Confirm v2 as the metrics version for Sprint 6 evaluation runs.

## Open issues

- The lead's request named the new version v2; it is v3 because v2 was taken.
