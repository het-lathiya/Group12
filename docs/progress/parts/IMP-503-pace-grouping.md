# IMP-503 · pace-grouping part

- Run id: RUN-068 (Sprint 5 batch A)
- Owner: Manya (Manya Rana)
- Status: committed on the part branch, not pushed (the lead integrates)
- Base commit: 26bac9d
- Branch: part/IMP-503-pace-grouping
- Traces to: US-054, US-055; FR-029, FR-030; NFR-030
- Card steps built: 1, 2, 3, 5 and 6. Step 4 (PreferenceForm, apps/web) is Manasvi's part and is not touched.

## Changed files

- `apps/api/app/generation/presets.py` (created): `PACE_PRESETS` (IMD-29; relaxed 3 / 300, balanced 5 / 480, busy 7 / 600) and the one accessor `pace_limits(pace)`. The numbers are read from pm-2's `PACE_LIMITS` so they are written once (PD-IMP-503-1).
- `apps/api/app/generation/grouping.py` (created, pure): `group_days(shortlist, must_visit, num_days, max_items) -> list[DayHint]`. Farthest-point seeding (must-visit first, then the shortlist), then each remaining place (must-visit first, then descending score) to the open day (< pace max items) whose centroid is nearest by haversine; seed ties break on place_id, day ties on day number; a place with no room is left out.
- `apps/api/app/generation/request_builder.py`: `build_generation_request` takes its limits from `presets.pace_limits` and fills gr-1 `day_hints` from `group_days`, capped at the pace maximum per day.
- `apps/api/app/evaluation/metrics.py` (step 6): `avg_daily_travel_min`, the mean over every planned day of all attempts of the day's summed travel minutes (FR-030 AC2).
- `apps/api/app/evaluation/run.py` (step 6; not in the card's file list, needed to feed the metric): each score carries `daily_travel_min`; a frozen request with no `day_hints` gets them from `group_days` with its own `limits.max_items_per_day`, so the scored plans are grouped as in production.
- `apps/api/.importlinter`: `app.generation.grouping` added to the Pure domain contract (§4.4 lists it; the file's convention is that the card creating a pure module adds it). Not in the card's file list.
- `apps/api/tests/unit/generation/test_pace.py`, `apps/api/tests/unit/generation/test_grouping.py` (created).
- `apps/api/app/core/config.py`: not changed. IMD-29 makes the presets code constants, and the card names no setting (PD-IMP-503-2).

## Commands and results

Run from `apps/api` with `PYTHONPATH=.` (the shared virtual environment's editable install points at the main checkout; without it `make test-unit` imports the main checkout's `app` and fails to collect the new tests).

| Command | Result |
| --- | --- |
| `.venv/bin/pytest tests/unit -k pace` (= `make test-unit ARGS='-k pace'`) | `31 passed, 1021 deselected, 1 warning` |
| `.venv/bin/pytest tests/unit -k grouping` (= `make test-unit ARGS='-k grouping'`) | `6 passed, 1046 deselected, 1 warning` |
| `.venv/bin/pytest tests/unit` | `1052 passed, 1 warning` |
| `.venv/bin/ruff check .` | `All checks passed!` |
| `.venv/bin/ruff format --check .` | `218 files already formatted` |
| `.venv/bin/mypy app` | `Success: no issues found in 120 source files` |
| `.venv/bin/lint-imports --config .importlinter` | `Contracts: 6 kept, 0 broken.` |
| `python -m app.evaluation.run --dataset trips/v1 --provider MOCK --out <scratch dir>` | `evaluation 20261114T055624Z-mock: 45 attempts, written to <scratch dir>`; `metrics.avg_daily_travel_min = 160.8` (not committed; the committed MOCK record is IMP-514 run-records) |
| `make test-api`, `make test-authz`, `make e2e` | not run: deferred to integration (no PostgreSQL in this run; this part adds no route or table) |

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-029 AC1 / TC-129: relaxed pace, no day exceeds the relaxed limit | verified | `test_pace_tc_129_relaxed_mock_days_keep_to_3_items_and_300_minutes` (MOCK over the relaxed dataset case) and `test_pace_presets_cap_items_per_day` |
| FR-029 AC2 / TC-130: a changed pace applies the new limit | verified (unit level) | `test_pace_tc_130_a_changed_pace_applies_the_new_limit`; the regeneration journey and `plan_stale` belong to step 4 / IMP-510 |
| FR-030 AC1 / TC-131: two distant areas fall on separate days | verified | `test_grouping_tc_131_two_distant_areas_fall_on_separate_days` |
| TC-132 / two runs give byte-identical day_hints | verified | `test_grouping_tc_132_the_same_input_twice_gives_byte_identical_day_hints` |
| With a relaxed pace no MOCK day exceeds 3 items or 300 active minutes | verified | as TC-129 (active minutes counted as the items' durations) |
| FR-030 AC2: the evaluation output contains avg_daily_travel_min | verified | `test_grouping_fr_030_ac2_metrics_record_avg_daily_travel_min` and the MOCK run above |
| make check green | not verified | not run as a whole; the unit, lint, type and import parts above pass; DB-backed suites deferred to integration |

## Blockers

none

## Proposed decisions

- **PD-IMP-503-1: where the pace numbers live.** IMD-29 puts the presets in `app/generation/presets.py`, but pm-2's `PACE_LIMITS` in `app/trips/preference_mapping.py` (IMP-315) already holds them and ranking and `itinerary/service.py` read it. Moving the literals into `presets.py` would make `app.trips` import `app.generation`, a cycle (CLAUDE.md §4 rule 6). `PACE_PRESETS` is therefore derived from `PACE_LIMITS`, so the numbers are written once. The team may instead move the literals and have trips read presets if it accepts that dependency, or amend IMD-29 to name preference_mapping as the source.
- **PD-IMP-503-2: config.py.** The card lists `core/config.py` (modify), but IMD-29 says the presets are not environment settings and no setting is named in the specification; nothing was added.
- **PD-IMP-503-3: metric definition file.** `avg_daily_travel_min` is added to metrics version v1, but `eval/metrics_v1.md` (hashed into each run record) is not in this part's files; it should get one line defining the metric, or the metric should start v2.

## Open issues

- The MOCK adapter ignores `day_hints` (it spreads the shortlist in order), so the MOCK `avg_daily_travel_min` does not reflect the grouping; only GEMINI and the rule-based fallback use the hints.
- The DAY_TOO_LONG rule is not on main yet (only `ValidationContext.pace_limits`); when IMP-309 builds it, it reads the limits the pipeline passes from `request.limits`, which come from `presets.pace_limits`.
- `run.py` and `.importlinter` are outside the card's file list (see Changed files).
