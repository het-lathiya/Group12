# System testing

RUN-099 · IMD-221 · owner: Junaid. Cases follow the [traceability matrix](../spec/TRACEABILITY_MATRIX.md),
[specification §13](../spec/IMPLEMENTATION_SPEC.md) and [acceptance record](../acceptance/rc1.md).
The application is exercised through its HTTP and browser interfaces. Inputs are partitioned by
observable behavior; expected responses do not depend on inspecting an internal implementation.

## Black-box equivalence classes and boundaries

The values below are test inputs/expected behavior from the named source tests, not measured
production limits. Inclusive trip length is the externally visible rule. A valid authenticated
user and active Sampleton destination are preconditions unless a row says otherwise.

| TC / requirement | Partition or boundary input | Expected observable result | Executable evidence |
| --- | --- | --- | --- |
| TC-071 / FR-008 | End before start; end equal to start; end after start | Earlier end: validation error on `end_date`, no write. Equal dates: a one-day trip is accepted | `tests/api/test_trips.py::test_tc_071_end_before_start_returns_422_naming_end_date`; `tests/unit/trips/test_trip_validation.py::test_a_one_day_trip_is_allowed` |
| TC-072 / FR-008 | Inclusive length at the maximum and immediately above it: fourteen/fifteen days | Maximum accepted; excessive length rejected with the limit and field error | `tests/api/test_trips.py`; `tests/unit/trips/test_trip_validation.py::test_tc_072_fourteen_days_pass_fifteen_are_rejected_with_the_limit` |
| TC-073 / FR-008 | Budget omitted; positive amount with matching currency; zero/negative amount; amount/currency supplied separately | Omission and complete positive budget accepted; invalid amount or missing partner field rejected | `tests/api/test_trips.py::test_tc_073_a_budget_of_zero_or_less_is_rejected`; `tests/unit/trips/test_trip_validation.py::test_no_budget_is_allowed`, `test_budget_amount_and_currency_come_together` |
| TC-074–076 / FR-009 | Known/unknown preference values, duplicate interests, unknown must-visit IDs | Allowed choices persist; invalid choice is reported at its field; unknown place IDs do not enter the plan | `tests/api/test_preferences.py::test_api_14_rejects_values_outside_the_rules`; `tests/unit/trips/test_preference_mapping.py` |
| TC-129–130 / FR-029 | `relaxed`, `balanced`, `busy` versus an unknown pace (`sprint` in unit, `slow` through API) | Allowed presets constrain daily items/active minutes; changed pace changes limits; unknown pace rejected | `tests/unit/generation/test_pace.py::test_pace_presets_cap_items_per_day`, `test_pace_unknown_value_is_refused`, `test_pace_tc_130_a_changed_pace_applies_the_new_limit`; `tests/api/test_preferences.py` |
| TC-304 / FR-054 | Below the near-budget threshold, exactly at it, above the budget | No budget finding / `BUDGET_NEAR` / `BUDGET_EXCEEDED` | `tests/unit/validation/test_day_length_budget.py`, `tests/unit/budget/test_alerts_contingency.py` |
| TC-305 / FR-032 | Item on first/last trip day versus just outside the date range | Boundary days accepted; outside item rejected with `OUTSIDE_TRIP_DATES` | `tests/unit/validation/test_rules_references.py` |
| TC-217 / FR-069 | Current versus stale `plan_revision` in an otherwise valid edit | Current edit recalculates/saves; stale edit returns conflict and leaves the stored plan unchanged | `tests/api/test_edits.py`; `e2e/reopen.spec.ts` |

The valid-day, invalid-budget and pace input values are read from source with
`sed -n '1,180p' apps/api/tests/unit/trips/test_trip_validation.py`,
`sed -n '1,100p' apps/api/tests/unit/generation/test_pace.py` and
`sed -n '325,357p' apps/api/tests/api/test_preferences.py`.
Trip dates, budget and day count are exercised both at unit and HTTP level; pace also reaches
the browser's preference wizard. The table does not invent a TC ID for a new course example.

## Last executed offline evidence

Source: [CI on `77e52ba`](https://github.com/het-lathiya/Group12/actions/runs/45678355628),
downloaded in RUN-099 with `gh api repos/het-lathiya/Group12/actions/jobs/<job-id>/logs`.

| Job / command | Result line |
| --- | --- |
| `unit`: `make test-unit` | `1879 passed, 1 warning in 15.74s` |
| `unit`: `make test-contract` | `99 passed, 2 deselected, 1 warning in 20.52s` |
| `unit`: `make test-web` | `Test Files  51 passed (51)`; `Tests  372 passed (372)` |
| `api`: `make test-api` with coverage | `688 passed, 1 warning in 244.65s (0:04:04)` |
| `api`: `make test-authz` with coverage | `91 passed, 14 skipped, 1 warning in 48.61s` |

Authorization skips belong to cut extension cases; contract deselections are live-provider cases.
These are suite-level results, not independently timed runs of each table row.

## Acceptance-level Given / When / Then cases

The ACC source text is absent for several IDs; the acceptance record explicitly records that
gap. The rows below are operationalizations of the specification's existing cross-references,
not replacements for missing blueprint definitions. Linked offline evidence is supporting only.
Every staging/live acceptance row is **pending staging window 1 Dec**.

Latest baseline browser evidence: [E2E on `77e52ba`](https://github.com/het-lathiya/Group12/actions/runs/45678353192),
MOCK on the CI local stack. Result lines were downloaded from job `139431886144` in RUN-099.

| ACC / E2E / TC | Given | When | Then | Last CI result and link | Staging |
| --- | --- | --- | --- | --- | --- |
| ACC-01, ACC-02 / E2E-02–03 / TC-369 | Signed-in traveller with seeded places | Create a valid trip, accept privacy notice and generate | Progress completes and a costed day-wise itinerary opens | Journey: `4 passed (42.0s)`; [E2E job](https://github.com/het-lathiya/Group12/actions/runs/45678353192/job/139431886144) | pending staging window 1 Dec |
| ACC-06, ACC-07 / E2E-04 | Generated flawed itinerary and near budget | Open warnings and costs | Relevant findings/fixes appear; displayed totals equal API values and price labels appear | Regression: `12 passed (24.4s)`; `9 skipped` (cut extensions); [E2E job](https://github.com/het-lathiya/Group12/actions/runs/45678353192/job/139431886144) | pending staging window 1 Dec |
| ACC-05, ACC-16 / E2E-05 / TC-376 | Existing generated itinerary | Move, retime, remove, lock, regenerate, save and restore | Response recalculates times/costs/findings; restored saved plan survives reload | Editing/restore: `8 passed (52.0s)`; [E2E job](https://github.com/het-lathiya/Group12/actions/runs/45678353192/job/139431886144) | pending staging window 1 Dec |
| ACC-10, ACC-18 / E2E-06 / TC-217 | Saved itinerary opened in separate tabs | Reopen after sign-in; send a stale edit | Saved plan reappears; stale tab must reload without overwriting newer work | Regression: `12 passed (24.4s)`; `9 skipped`; [E2E job](https://github.com/het-lathiya/Group12/actions/runs/45678353192/job/139431886144) | pending staging window 1 Dec |
| ACC-03 / E2E-07 / TC-371 | Existing version; MOCK timeout scenario | Generate, then edit | Labelled rule-based plan is saved; previous data remains available | Timeout: `1 passed (6.7s)`; `1 skipped` (quota-only case); [E2E job](https://github.com/het-lathiya/Group12/actions/runs/45678353192/job/139431886144) | pending staging window 1 Dec |
| ACC-17 / E2E-07 / TC-371 | Existing version; MOCK quota scenario | Generate | Quota message offers the rule-based option, without replacing existing data | Quota: `1 passed (7.6s)`; `1 skipped` (timeout-only case); [E2E job](https://github.com/het-lathiya/Group12/actions/runs/45678353192/job/139431886144) | pending staging window 1 Dec |
| ACC-08 / E2E-08 / TC-375 | A private trip owned by another user | Open itinerary, costs and versions URLs | Not-found UI; no private trip data in responses | Regression: `12 passed (24.4s)`; `9 skipped`; authorization suite `91 passed, 14 skipped, 1 warning in 48.61s`; [CI](https://github.com/het-lathiya/Group12/actions/runs/45678355628), [E2E](https://github.com/het-lathiya/Group12/actions/runs/45678353192) | pending staging window 1 Dec |
| E2E-09 / TC-370, TC-377 | Deployed candidate with provider key and approved cap | Run API/web smoke and a live generation | Readiness/auth/journey pass with real environment/provider evidence | not run — latest E2E run's staging job skipped; [E2E](https://github.com/het-lathiya/Group12/actions/runs/45678353192) | pending staging window 1 Dec |
| ACC-19–23 / E2E-10 / TC-486, TC-491 | Candidate with RAG/any-city mode and real data | Generate with citations; import city; try insufficient data and provider failure | Sources/labels and graceful outcomes match amendments | FAKE/MOCK any-city supporting only: `4 passed (14.4s)`; [live-named CI job](https://github.com/het-lathiya/Group12/actions/runs/45678353192/job/139431885847). No real-provider acceptance result | pending staging window 1 Dec |

ACC-04, ACC-09, ACC-11–13 have no definitions/cross-references in the acceptance record:
**not run — source acceptance text missing**. ACC-14 reproducibility needs an explicit rerun;
ACC-15 injection has API-suite support (`tests/api/test_injection.py`) but its staging
acceptance remains **pending staging window 1 Dec**. Manual confirmation of saved-plan behavior,
accessibility, labels and failure states is listed in [GUI testing](07-gui-testing.md).

Local `make check` and E2E: **not run — operator fast mode; CI covers**.
No acceptance result was inferred from a source file, proposed target or skipped staging job.
