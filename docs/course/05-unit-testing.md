# Unit testing and white-box testing

RUN-099 · IMD-221 · owner: Junaid. Evidence baseline: `77e52ba`; coverage baseline:
`b3248cf` (the same application source, with the optional coverage workflow).

The test boundaries follow [implementation specification §4.3 and §13](../spec/IMPLEMENTATION_SPEC.md)
and the [TC traceability matrix](../spec/TRACEABILITY_MATRIX.md). A test file's presence establishes
implementation, while the linked execution below establishes a result.

## How the suites work

| Suite | Location and tool | Isolation and purpose | Command |
| --- | --- | --- | --- |
| Unit | `apps/api/tests/unit/`, pytest | Pure validation, budget arithmetic, ranking, routing estimates, fallback and settings; no database required | `make test-unit` |
| Contract | `apps/api/tests/contract/`, pytest/respx | Adapter result/error contracts and generated OpenAPI; recorded Gemini responses under `tests/fixtures/provider_recordings/gemini/`; live tests deselected | `make test-contract` |
| API | `apps/api/tests/api/`, pytest/httpx | Actual FastAPI routes and a migrated PostgreSQL service; verifies responses, persistence and rollback | `make test-api` |
| Authorization | `apps/api/tests/authz/`, pytest | Minted users, another owner's resource returning not-found, unauthenticated routes, body-user-ID rejection and route inventory | `make test-authz` |
| Deployment smoke | `apps/api/tests/smoke/`, pytest | Health/readiness, auth wall and deployment behavior at a supplied URL; excluded from the ordinary suites | `make smoke URL=<api-url>` |
| Web unit/component | `apps/web/tests/unit/`, Vitest/Testing Library in jsdom | Render components, exercise user events, mock the API/auth boundary; shared setup in `tests/setup.ts` | `make test-web` |

`tests/conftest.py` registers shared auth/database fixtures, clears cached settings around tests,
and installs a provider socket guard. Tests marked `live` are the explicit exception, excluded
from ordinary contract CI. `tests/fixtures/db.py` supplies a migrated database and a transaction
rolled back after each test; application commits release a savepoint inside that transaction.
`tests/fixtures/auth.py` supplies synthetic identities and token fixtures. Factory helpers in
individual tests build the smallest relevant domain inputs. No fixture named `factories.py`
exists at this baseline; the specification's example filename is not an implemented fixture.

Recorded provider responses cover successful output, malformed/truncated output, schema failures,
timeouts, rate limits and quota/configuration failures. `respx` controls HTTP replies, the MOCK
adapter supplies named scenarios, and no offline pass is a claim about a live provider.

## White-box techniques in real code

These are selected statement, branch and path examples, not a claim of exhaustive path coverage.
All named files are inside the suites executed by the linked CI runs.

| Technique | Named function | Tests and exercised decisions |
| --- | --- | --- |
| Statement coverage and arithmetic | `app.budget.engine.item_cost`, `split` | `tests/unit/budget/test_engine.py::test_tc_221_per_person_cost_counts_adults_and_children`, `test_tc_297_a_group_price_is_counted_once`, `test_tc_295_a_child_half_line_rounds_half_up_once`, `test_tc_296_a_total_not_divisible_by_three_gives_the_remainder_to_the_first_shares`: price conversion, child factors, group pricing and deterministic remainder allocation (TC-221, TC-295–297) |
| Branch coverage | `app.trips.domain.validate_dates`, `validate_budget` | `tests/unit/trips/test_trip_validation.py::test_tc_071_end_before_start_names_end_date`, `test_a_one_day_trip_is_allowed`, `test_tc_072_fourteen_days_pass_fifteen_are_rejected_with_the_limit`, `test_no_budget_is_allowed`, `test_budget_amount_and_currency_come_together`, `test_tc_073_a_budget_of_zero_or_less_is_rejected`: date order/length and absent/partial/non-positive budget branches |
| Branch and normalization paths | `app.generation.ranking.c_semantic`, `rank_shortlist` | `tests/unit/generation/test_ranking.py::test_c_semantic_is_min_max_over_the_candidates_with_a_chunk`, `test_c_semantic_is_half_when_all_are_equal_and_empty_without_similarities`, `test_tc_451_a_must_visit_place_with_the_lowest_similarity_stays`: absent, tied and varying similarities, followed by shortlist preservation |
| Exception and normal paths | `app.routing.estimate.estimate`, `buffer_minutes`, `TravelEstimate.label` | `tests/unit/routing/test_estimate.py::test_an_exact_multiple_is_not_rounded_further`, `test_identical_points_give_zero`, `test_an_unknown_mode_is_refused`, `test_an_unknown_travel_source_has_no_buffer`, `test_routing_values_are_labelled_estimate_only_for_local_transport`: exact rounding, zero distance, invalid mode/source and source/mode label decisions (TC-236–237) |
| Input-security paths | `lib/auth/redirect.ts::safeNextPath` | `apps/web/tests/unit/auth/redirect.test.ts`: valid local path, query/fragment preservation and parent-segment normalization; missing/absolute/protocol-relative/backslash/control-character inputs take the safe fallback. Parse failure and origin mismatch need separate coverage review rather than assuming every defensive branch is reachable |

## Measured coverage

Source: [Course reports 46124142747](https://github.com/het-lathiya/Group12/actions/runs/46124142747),
measured commit `b3248cf`, conclusion `success`. Both `coverage-api` and `coverage-web` were
downloaded with `gh run download 46124142747 -n coverage-api -n coverage-web -D <temp-dir>`.
The temporary directory is outside the repository. Reproduce the calculations with:

```sh
python3 scripts/course_coverage_summary.py <temp-dir> \
  --run-url https://github.com/het-lathiya/Group12/actions/runs/46124142747 \
  --commit b3248cffa380fffb88f1020dc20f7751b8903d5f
```

Its exact aggregate result lines are:

```text
API_TOTAL lines=9212/9830 (93.71%); branches=1620/1938 (83.59%)
WEB_TOTAL lines=1542/1740 (88.62%); branches=1487/1759 (84.54%)
```

API packages:

| Package | Lines covered/total (%) | Branches covered/total (%) |
| --- | --- | --- |
| app | 93/115 (80.87%) | 6/12 (50.00%) |
| app/ai | 847/852 (99.41%) | 235/238 (98.74%) |
| app/auth | 200/211 (94.79%) | 27/34 (79.41%) |
| app/budget | 263/274 (95.99%) | 30/36 (83.33%) |
| app/core | 466/470 (99.15%) | 85/90 (94.44%) |
| app/db | 455/486 (93.62%) | 17/24 (70.83%) |
| app/evaluation | 289/364 (79.40%) | 46/56 (82.14%) |
| app/generation | 1217/1267 (96.05%) | 200/246 (81.30%) |
| app/itinerary | 968/1113 (86.97%) | 147/226 (65.04%) |
| app/livedata | 889/912 (97.48%) | 215/232 (92.67%) |
| app/places | 1391/1536 (90.56%) | 246/316 (77.85%) |
| app/rag | 713/740 (96.35%) | 160/170 (94.12%) |
| app/routing | 153/153 (100.00%) | 12/12 (100.00%) |
| app/schemas | 321/326 (98.47%) | 19/24 (79.17%) |
| app/trips | 534/590 (90.51%) | 58/98 (59.18%) |
| app/validation | 413/421 (98.10%) | 117/124 (94.35%) |
| TOTAL | 9212/9830 (93.71%) | 1620/1938 (83.59%) |

Web packages/areas:

| Package | Lines covered/total (%) | Branches covered/total (%) |
| --- | --- | --- |
| app | 0/3 (0.00%) | 0/0 (n/a) |
| app/(app) | 207/276 (75.00%) | 224/297 (75.42%) |
| app/(public) | 3/12 (25.00%) | 2/6 (33.33%) |
| app/auth | 0/15 (0.00%) | 0/4 (0.00%) |
| components/auth | 58/66 (87.88%) | 63/73 (86.30%) |
| components/costs | 55/57 (96.49%) | 59/69 (85.51%) |
| components/generation | 58/62 (93.55%) | 82/88 (93.18%) |
| components/itinerary | 217/230 (94.35%) | 216/251 (86.06%) |
| components/labels | 37/38 (97.37%) | 50/52 (96.15%) |
| components/map | 59/62 (95.16%) | 9/10 (90.00%) |
| components/places | 76/80 (95.00%) | 108/130 (83.08%) |
| components/profile | 23/23 (100.00%) | 17/24 (70.83%) |
| components/shell | 38/43 (88.37%) | 51/55 (92.73%) |
| components/states | 20/21 (95.24%) | 48/48 (100.00%) |
| components/trips | 316/334 (94.61%) | 357/406 (87.93%) |
| components/ui | 37/49 (75.51%) | 14/15 (93.33%) |
| components/versions | 28/28 (100.00%) | 42/43 (97.67%) |
| lib | 16/16 (100.00%) | 6/6 (100.00%) |
| lib/api | 212/229 (92.58%) | 98/127 (77.17%) |
| lib/auth | 32/46 (69.57%) | 20/33 (60.61%) |
| lib/validation | 50/50 (100.00%) | 21/22 (95.45%) |
| TOTAL | 1542/1740 (88.62%) | 1487/1759 (84.54%) |

[coverage-summary.txt](../test-reports/course/coverage-summary.txt) contains the same table,
every uncovered module's missing line/branch counts, and the original terminal summaries.
This measures the pre-mutation baseline; tests added during mutation work are not included.

The workflow runs API, authorization, unit and offline contract suites in separate pytest
processes with `--cov=app --cov-branch --cov-append` and XML/HTML/JSON/terminal reports.
Separate processes avoid duplicate test basenames across suites. Web runs `vitest run --coverage`
with explicit `app`, `components` and `lib` inclusion. Live tests are deselected in this workflow,
including the unit live-provider cases; therefore its unit count differs from ordinary CI.
Exact result lines from the downloaded artifacts:

```text
688 passed, 1 warning in 255.26s (0:04:15)
91 passed, 14 skipped, 1 warning in 52.39s
1877 passed, 2 deselected, 1 warning in 31.08s
99 passed, 2 deselected, 1 warning in 29.28s
Test Files  51 passed (51)
Tests  372 passed (372)
```

Coverage is measured over `app` with `--cov-branch`; pytest's terminal `Cover` mixes statements
and branches. The table therefore uses covered/total executable lines and branch arcs from
`coverage.json`, not that mixed percentage. Web uses V8/Istanbul's line and branch counters.
An empty branch denominator is `n/a`. Packages with no executed statements remain visible.
The web report includes `app/`, `components/` and `lib/`, including files the tests never import.
Generated declarations and tool/test configuration are outside that executable scope.

## Gaps against the course's full-coverage target

The complete machine-derived module list is in the summary, rather than hiding untested
files behind the package average. Concrete remaining work includes:

- API CLI/setup paths: `app/openapi_export.py`, `app/db/reset.py`, `app/evaluation/run.py`
  and seed/index administrative paths such as `app/places/seed.py` and `app/rag/index.py`.
- API state/error branches: `app/itinerary/edits.py`, `app/itinerary/service.py`,
  `app/itinerary/versions.py`, `app/generation/service.py`, `app/trips/service.py`,
  `app/places/live_service.py` and `app/places/live_jobs.py`.
- Lower-level failure decisions: `app/auth/service.py`, `app/budget/service.py`,
  `app/schemas/ai.py` and validation branches in `app/validation/rules.py`.
- Web unexecuted server paths: `app/auth/callback/route.ts` and `app/layout.tsx`;
  partly covered profile/sign-in/sign-up/itinerary/versions pages and shell providers.
- Web component decisions: `components/itinerary/ItemEditor.tsx`, `MoveControls.tsx`,
  `components/places/PlaceDetailDrawer.tsx`, `components/trips/TripWizard.tsx` and
  `components/costs/BudgetSettingsForm.tsx`.
- Web library paths: `lib/auth/redirect.ts`, `lib/auth/supabase.ts`, `lib/auth/useSession.ts`,
  `lib/api/client.ts`, `lib/api/queries.ts`, `lib/api/anyCityClient.ts` and
  `lib/validation/trip.ts`. Some defensive branches may be unreachable under existing guards;
  explain those before adding tests that only mirror implementation.

The original XML/JSON/HTML stays in the CI artifacts. New tests should target the actual
missing behavior, and toolchain/generated code should not be counted as tested product code.

Full coverage is a course target, not an achieved result or a required-check threshold.
The specification's proposed thresholds remain unchanged (NFR-030, TC-334). More line coverage
would still leave semantic gaps: arithmetic boundaries, equivalent mutants, concurrent behavior,
real provider failures and deployment configuration require their own evidence.

Local `make check` and E2E: **not run — operator fast mode; CI covers**.
Deployment smoke and live variants: **not run — pending staging window 1 Dec**.
