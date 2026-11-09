# IMP-406 · must-visit-constraints part

- Run id: RUN-057 (grouped, IMD-121, with IMP-401, IMP-402 and FIX IMD-126)
- Owner: Manya (manyarana)
- Status: PR open
- Base commit: 16839a0
- Branch: feat/IMP-401-402-406-generation-reliability
- Reviewer: Manasvi (Manasvi1704)
- Traces to: US-056, US-057; FR-034, FR-035; NFR-016; IMD-42
- Card steps built: 1 to 4

## Changed files

- `apps/api/app/generation/pipeline.py`: after step 9, `plan_findings` runs the merged `validate()` (IMP-404, used as it is) on the recalculated plan, model or rule-based, with the trip dates, the active place names, the must-visit IDs, the shortlist and the pace limits. Each MUST_VISIT_MISSING finding gets its reason and fix appended (see `retrieval.py`). The findings are saved with the plan, and their counts go into the version's `validation_summary` and are added to step 8's counts on the generation record.
- `apps/api/app/generation/retrieval.py`: `must_visit_reasons(session, trip, prefs)` gives (reason, suggested fix) per must-visit place: its hard-filter conflict (not step-free, category not planned, not for children, closed on every trip day, over the activity budget) or "No day of the plan had room for it." The module docstring records that every must-visit place stays in the shortlist whatever its rank or the cap.
- `apps/api/app/itinerary/service.py`: `save_generated_plan(..., findings=)` saves the findings in the same transaction (§8.2 step 11).
- `apps/api/app/itinerary/repository.py`: `insert_warnings` writes `itinerary_warnings` rows: `item_ref` becomes `item_id`; MUST_VISIT_MISSING keeps `place_id` with `item_id` null (IMD-42).
- Tests: `apps/api/tests/unit/generation/test_must_visit.py` (created); `apps/api/tests/api/test_generations.py` (five tests: TC-141, the shortlist beyond the cap, TC-142, a filter-conflict reason, TC-143/TC-144); `apps/api/tests/fixtures/pipeline.py` (the stand-ins record the saved findings, return place names, and stub the reason lookup).

Card step by step:

1. Must-visit IDs in the shortlist regardless of rank or cap: already true on main (`ranking.rank_shortlist` appends every must-visit place past the cap and keeps excluded categories for them; `limits.enforce_input_limit` never drops them). No code change; asserted by `test_must_visit_place_is_forced_into_the_shortlist_beyond_the_cap`.
2. An absent must-visit place gives MUST_VISIT_MISSING (error) with the reason and a fix, through `validate()` and the rules.py catalogue; it is saved, never dropped silently.
3. Explicit constraints: pace limits reach `validate()` (`pace_limits`), so DAY_TOO_LONG appears when IMP-309 adds its rule. Step-free and excluded categories are hard filters before generation (§8.9): a place failing them is not in the shortlist, so the model cannot plan it (step 8 drops it as UNKNOWN_PLACE). The one exception is a conflicting must-visit place, which stays by FR-027 AC2; see PD-IMP-406-1.
4. Model text: only `itinerary_days.theme` and `itinerary_items.note` (note_origin ai) hold model text; times, travel and costs are backend columns (unchanged, asserted). Citations (`source_chunk_ids`, A1 §6.10) pass through unchanged.

## Commands and results

| Command | Result |
| --- | --- |
| `make test-unit ARGS='-k "must_visit or ai_text"'` | `33 passed, 952 deselected, 1 warning` |
| `make test-unit` | `985 passed, 1 warning` |
| `make test-web` | `Tests  119 passed (119)` |
| `make lint` | exit 0 |
| `make typecheck` | `Success: no issues found in 112 source files` |
| `make imports` | `Contracts: 6 kept, 0 broken.` |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |
| `make test-api ARGS='-k "must_visit or ai_text"'` | not run to a result: no PostgreSQL or Docker on this machine (connection refused on port 5432). The five API tests are collected (`5/34 tests collected`); evidence comes from the CI `api` job |

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-034 AC1 / TC-141: three must-visit places that fit are all in the plan | not verified locally (CI) | `test_tc_141_must_visit_places_that_fit_are_all_in_the_plan` (mode rule_based); unit `test_must_visit_a_plan_holding_every_must_visit_place_has_no_finding`. In mode ai it depends on the model until IMP-502's deterministic repair inserts a missing place (§8.13) |
| FR-034 AC2 / TC-142: a must-visit place that cannot fit gives a visible warning naming it and the reason | verified (unit); API in CI | `test_must_visit_a_place_the_model_left_out_is_saved_as_must_visit_missing`, `test_must_visit_the_reason_of_a_filter_conflict_is_named`; API `test_tc_142_must_visit_missing_names_the_place_and_the_reason`, `test_must_visit_missing_gives_a_filter_conflict_as_the_reason` |
| With MOCK dropping a must-visit place, the saved plan has MUST_VISIT_MISSING naming it | verified (unit); API in CI | MOCK `flawed` in the tests above; `place_id` set, `item_id` null |
| FR-035 AC1-AC2 / TC-143, TC-144: AI note and retrieved fact are distinct columns and labels | verified (unit); API in CI | `test_must_visit_ai_text_only_in_theme_and_note`; `test_tc_143_tc_144_ai_text_and_retrieved_facts_are_separate_columns_and_labels` |
| Citations of A1 §6.10 intact | verified | `make test-unit` (the TC-455 citation tests pass unchanged) |

## Blockers

none

## Proposed decisions

- **PD-IMP-406-1: a planned must-visit place that breaks a constraint.** A must-visit place that fails step-free or an excluded category stays in the shortlist with a conflict note (FR-027 AC2), so the model may plan it. No finding code in the §8.12 catalogue says "breaks the step-free requirement", and adding one changes the contract, so no finding is emitted for it. The team should decide whether such an item needs a code (a contract change) or whether the conflict note is enough.
- **PD-IMP-406-2: TC-141 in mode ai.** Without the deterministic repair of §8.13 (IMP-502), a model may leave out a must-visit place that fits; the pipeline then reports it (AC2) but does not insert it. TC-141 is therefore shown with the rule-based plan here, and should be repeated in mode ai once IMP-502 lands.

## Open issues

- MUST_VISIT_MISSING reasons are derived from the hard-filter conflict notes; a place left out by the model with no conflict is reported as "No day of the plan had room for it."
