# IMP-510 · settings-api

| Field | Value |
| --- | --- |
| Run | RUN-068 (Sprint 5 batch A), part 2 of 2 |
| Card | IMP-510 Edit trip settings and flag a stale plan |
| Part | Edit trip settings and stale-plan flag (1 point), steps 1, 2, 3 and 6 |
| Owner | Manal Patel |
| Status | PR_OPEN (lead integrates) |
| Base commit | 26bac9d (stacked on the IMP-507 breakdown-api commit in the same branch) |
| Branch | part/IMP-507-breakdown-api |

## Starting point

- **Step 1:** API-11 PATCH already existed (IMP-410 draft flow, IMD-148). It applies the API-07 rules to the merged trip, refuses edits to archived trips, and returns 404 for another user's trip. It is kept as it was.
- **Step 2:** the old rule set `plan_stale` whenever a plan field was *sent*. So the edit page, which resends the whole form, would have flagged a title-only edit (against FR-011 AC2). API-14 flagged every save, even an unchanged one.
- **Step 3:** the save of a completed generation already clears the flag. `generation.jobs` calls `itinerary.service.save_generated_plan`, and that calls `itinerary.repository.mark_plan_saved` (`plan_stale=False`), in the same transaction as the plan. `tests/api/test_generations.py::test_a_second_generation_replaces_the_plan_and_clears_plan_stale` already covers it. `generation/service.py` therefore needed no change and was not edited.

## Changed files

- `apps/api/app/trips/domain.py`
  - `PLAN_AFFECTING_FIELDS` (dates, adults, children, group_needs, budget, destination).
  - `plan_affected(before, after)`, which is pure. It flags only a value that really changed. Group needs are compared as a set and budgets by value; a title change never counts.
- `apps/api/app/trips/service.py`
  - API-11 compares the stored trip with the merged draft through `domain.plan_affected`. This replaces the old sent-field check, `PLAN_FIELDS`, which is removed.
  - API-14 sets the flag only when a stored preference value or the must-visit set changes, or when no preferences existed before.
  - Step 6: changing the dates never touches itinerary days or items.
- `apps/api/tests/api/test_trips.py`, with 10 new tests, all matching `-k stale`:
  - TC-080: a date change on a planned trip makes it stale.
  - TC-081: a title-only change, and a whole form resent with only a new title, both stay fresh.
  - Each plan-affecting field makes the trip stale (6 cases).
  - Without an itinerary, nothing becomes stale.
  - Shorter dates keep the days and make the trip stale.
  - An API-14 resend leaves the trip fresh, and a pace change makes it stale.
- `docs/progress/parts/IMP-510-settings-api.md`: this record.

## Commands

| Command | Result |
| --- | --- |
| `.venv/bin/ruff check app tests` | `All checks passed!` |
| `.venv/bin/ruff format --check app tests` | `206 files already formatted` |
| `PYTHONPATH=. .venv/bin/mypy app` | `Success: no issues found in 118 source files` |
| `PYTHONPATH=. .venv/bin/lint-imports` | `Contracts: 6 kept, 0 broken.` |
| `PYTHONPATH=. .venv/bin/pytest -q tests/unit` | `1051 passed, 1 warning in 18.23s` |
| `PYTHONPATH=. .venv/bin/pytest -q --collect-only tests/api/test_trips.py -k stale` | `10/45 tests collected (35 deselected) in 0.18s` |
| `PYTHONPATH=. .venv/bin/pytest -q --collect-only tests/api/test_trips.py tests/api/test_preferences.py` | `69 tests collected in 0.12s` |

Not run (deferred to integration, needs PostgreSQL):
- `make test-api ARGS='-k stale'`
- `make test-api ARGS='-k "trips or preferences or generations"'`
- `make test-authz` (TC-345)

A one-off assert script, not committed, checked `plan_affected` for a title change, a reordered group-needs list, an equal budget, and each field change: `ok`.

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-011 AC1 (TC-080): a date change on a planned trip sets plan_stale | not verified | `test_tc_080_…` written, deferred to integration; rule checked by the assert script |
| FR-011 AC2 (TC-081): a title-only change does not | not verified | `test_tc_081_…` written, deferred to integration; rule checked by the assert script |
| plan_stale cleared after a completed regeneration | not verified (here) | existing `test_generations.py::test_a_second_generation_replaces_the_plan_and_clears_plan_stale`, not run here (needs PostgreSQL) |
| PATCH of another user's trip returns 404 NOT_FOUND | not verified (here) | unchanged path; existing `test_draft_patch_of_another_users_trip_is_404` and the authz suite (TC-345), not run here |
| Step 6: dates changed so items fall outside the trip leave the items | not verified | `test_shorter_dates_leave_the_days_outside_the_trip_…` written, deferred; OUTSIDE_TRIP_DATES itself is unit-tested in `tests/unit/validation/test_rules_references.py` (passed in the unit run) |
| Draft behaviour of API-11 kept (IMD-148) | verified (unit/static) | no change to the draft or status branches; existing draft tests unchanged and collected |

## Proposed decisions

- **PD-IMP-510-1 (API-14 stale rule):** card step 2 names pace, interests and must-visit places. The service flags any change of a stored preference value or of the must-visit set, because transport, step-free and the other preferences also feed generation. An unchanged resend flags nothing. Proposed: accept this superset.
- **PD-IMP-510-2 (step 3 location):** the flag is cleared in `itinerary.repository.mark_plan_saved` (the existing plan save of a generation, IMP-308 and IMP-401), not in `generation/service.py` as the card lists. That repository writes `trips`, which is an existing one-writer exception and was not changed by this part. Proposed: record the card's file as satisfied by the existing save step, or move the trips write behind `trips.service` in a later task.

## Blockers and open issues

- The ten new API tests and the authz suite have not run in this session. They need the integration run with PostgreSQL.
