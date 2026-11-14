# PD-RUN-069-1 · mock-happy-path

- Run id: RUN-070
- Owner: Nidhi Chauhan
- Status: implemented; PostgreSQL API tests and E2E deferred to integration/CI
- Base commit: 15475eb
- Scope: the MOCK `ok` proposal fits the SAMPLE fixture's curated hours, so a default MOCK generation for the pinned trip needs no deterministic or model repair. Curated hours, prices, place data, validator rules and severities are unchanged.

## Cause

Step 9 (`app/generation/schedule.py`) ignores the model's times: it places a day's items back to back from 09:00 with travel plus buffer. The old `ok` proposal put up to five shortlist places on each day in rank order, so with walking travel on the SAMPLE fixture five visits ran past 17:00 (OUTSIDE_HOURS, warning because the hours are labelled estimate) and two days passed 480 active minutes (DAY_TOO_LONG). In the journey E2E (dates 30 to 32 days from today) a Monday makes sample-005, sample-007 and sample-016 CLOSED_ON_DAY (error), which the deterministic repair moved: outcome `model_repaired`.

## Files changed

- apps/api/app/ai/providers/mock.py: `ok` now builds `_fitted_days`: each day takes, in shortlist order, the remaining candidates that fit after the fallback travel estimate plus its buffer (what step 9 recalculates), within `limits.max_items_per_day`, `limits.max_active_minutes_per_day`, `limits.day_end` and the day's `hours_summary` hours (closed days and evening-only places are skipped; a place without stored hours that day is not constrained). When nothing fits, the plain spread is used. `flawed` and `unknown_place` keep the plain spread (`_build_days`) exactly as before.
- apps/api/tests/unit/ai/test_mock_provider.py: timing rule updated (15-min buffer instead of a 30-min gap); new tests for the fit rules and for the SAMPLE fixture trip.
- apps/api/tests/api/test_generations.py, apps/api/tests/api/test_itinerary.py: the expectations changed in 5ae2e52 now give the no-repair outcome; the "not from an older revision" and must-visit reference checks are kept.
- apps/web/e2e/journey.spec.ts: outcome `model` with `deterministic_repairs` 0; "at most one provider call" and "no blocking findings" kept.
- This record.

## Expected findings of the default MOCK generation (pinned trip: Sampleton, 2026-12-04 to 2026-12-06, 2 adults, museum and food, balanced, walking)

- Outcome `model`, `deterministic_repairs` 0, `repair_attempts` 0, `validation_summary` `{"errors": 0, "warnings": 1, "infos": 1}`.
- Findings: `COST_INCOMPLETE` 1 (warning; sample-007 and sample-017 have no price in the fixture) and `HOURS_UNVERIFIED` 1 (info; sample-026 Quiet Abbey Ruins has no stored hours, `hours_label` unavailable). No OUTSIDE_HOURS, DAY_TOO_LONG, CLOSED_ON_DAY or other finding.
- Plan: day 1 sample-016, 013, 017, 014, 004; day 2 sample-018, 006, 005, 007; day 3 sample-008, 012, 025, 026 (12 items instead of 15).
- API-32 after leaving out a must-visit place: `{"errors": 1, "warnings": 1, "infos": 1}` with MUST_VISIT_MISSING, COST_INCOMPLETE, HOURS_UNVERIFIED.
- The pre-ed3433a expectation (all zeros, no findings) is not reachable without changing data: COST_INCOMPLETE comes from the two unpriced fixture places, and the HOURS_UNVERIFIED place cannot be skipped by the mock without also emptying plans whose places all lack hours (the eval dataset's summaries are all "hours estimate" or "hours unavailable").

## Commands and results

- `PYTHONPATH=. <venv>/pytest tests/unit/ai/test_mock_provider.py -q` (apps/api): `43 passed in 0.36s`.
- `PYTHONPATH=. <venv>/pytest tests/unit -q` (apps/api, as make test-unit): `1148 passed, 1 warning in 20.42s`.
- `ruff check` on the four Python files: `All checks passed!`; `ruff format --check`: `4 files already formatted`.
- `mypy app` (as make typecheck): `Success: no issues found in 122 source files`.
- `lint-imports --config .importlinter` (as make imports): `Contracts: 6 kept, 0 broken.`
- `npx prettier --check e2e/journey.spec.ts`: `All matched files use Prettier code style!`; `npx eslint e2e/journey.spec.ts`: no output (clean).
- The new SAMPLE fixture unit test fails on the old `ok` proposal (checked by swapping it back): 7 of 7 parametrised cases fail.
- Not run (deferred to integration/CI): `make test-api` (test_generations.py, test_itinerary.py; PostgreSQL not used in this run) and `make e2e` (journey.spec.ts).

## Acceptance

- Default MOCK generation for the pinned trip completes with outcome `model`, 0 deterministic repairs, 0 repair attempts: verified offline by `test_the_ok_answer_for_the_sample_trip_needs_no_repair_and_fits_the_hours[0]` (fixture files, real ranking, step 9 schedule with the fallback estimate, validator and deterministic repair, no database); not verified against PostgreSQL (deferred).
- Zero error findings and zero OUTSIDE_HOURS / DAY_TOO_LONG: verified by the same test for the pinned trip and for a start on each weekday (Monday closures included); prices are not loaded there, so COST_INCOMPLETE is checked only by the API test (deferred).
- `flawed`, `unknown_place` and `invalid_json` exercise repair as before: verified; their code paths are unchanged and their unit tests pass unchanged.
- API test and E2E expectations: updated; not verified (deferred to integration/CI).

## Blockers

- none

## Proposed decisions

- PD-RUN-069-1-1: the MOCK `ok` scenario reads `hours_summary` in the request builder's format ("Fri 09:00-17:00; Mon closed") and the fallback travel estimate of `app.routing.estimate` to fit its proposal; a change to that summary format must update `mock.py` too.
- PD-RUN-069-1-2: the MOCK `ok` proposal may leave out shortlist places that fit no day (here 12 items instead of 15); places without stored hours stay plannable and give HOURS_UNVERIFIED (info).

## Open issues

- With OpenRouteService configured, step 9 uses routed times instead of the estimate, so a proposal can still drift past closing time; with estimated hours that is a warning only and never a repair.
- A must-visit place is not preferred by the `ok` proposal (unchanged behaviour): one that fits no day is still inserted by the deterministic repair.
