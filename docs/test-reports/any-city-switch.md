# Any-city switch: ON/OFF suite record and the switch-ON CI jobs (TC-490, IMP-730)

- Run: RUN-092 (Batch C3, Sprint 7, inserted under IMD-215)
- Owner: Krrish (IMP-730)
- Base commit: 818c1d8 (on `main`); the branch commits of RUN-092 up to IMP-730 (P0 to P3)
- Amendment A2 §2 (d), §3.4, §13.2 TC-490; acceptance ACC-23

## How the switch-ON run is made

The API, unit, contract and authz suites run once with `ANY_CITY_SUITE_ON=1`. The autouse fixture `any_city_suite_on` in `apps/api/tests/conftest.py` then sets `FEATURES_DISABLED=!any_city_mode` for every test:

- every `Settings` a test builds from the environment sees the switch ON;
- a value a test passes itself still wins;
- `clean_settings_env` still gives a test the empty environment it asks for.

Without the variable (every normal run, CI included), nothing changes.

## Commands

Switch ON, with the inventory tests that A2 §3.4 names deselected: the original four, plus the two of IMD-219 (PD-730-1, agreed 24 November 2026, RUN-093):

```sh
ANY_CITY_SUITE_ON=1 make test-unit
ANY_CITY_SUITE_ON=1 make test-contract ARGS='--deselect tests/contract/test_openapi_contract.py::test_committed_contract_is_current --deselect tests/contract/test_openapi_contract.py::test_every_mvp_endpoint_maps_to_exactly_one_operation --deselect tests/contract/test_openapi_contract.py::test_no_path_outside_the_mvp_set'
ANY_CITY_SUITE_ON=1 make test-authz ARGS='--deselect tests/authz/test_ownership.py::test_tc_065_every_implemented_owned_route_is_in_the_matrix --deselect tests/authz/test_ownership.py::test_tc_065_an_unlisted_route_fails_the_check --deselect tests/authz/test_route_inventory.py::test_inventory_docs_companions_are_only_fastapi_doc_pages'
ANY_CITY_SUITE_ON=1 make test-api
```

Switch OFF: the same four targets without the variable and without deselects.

## Result lines (RUN-092, local, migrated pgvector test database)

| Suite | Switch OFF | Switch ON (four §3.4 deselects) |
| --- | --- | --- |
| unit | 1851 passed, 1 warning in 9.72s | 1851 passed, 1 warning in 8.68s |
| contract | 99 passed, 2 deselected, 1 warning in 19.85s | 96 passed, 5 deselected, 1 warning in 20.05s |
| authz | 87 passed, 14 skipped, 1 warning in 21.72s | 2 failed, 84 passed, 14 skipped, 1 deselected, 1 warning in 25.23s |
| api | 678 passed, 1 warning in 125.33s (0:02:05) | 678 passed, 1 warning in 138.70s (0:02:18) |

The 2 deselected contract tests in both columns are the `live` tests that `make test-contract` always leaves out (`-m "not live"`).

### The two switch-ON authz failures (not product defects)

1. **`tests/authz/test_ownership.py::test_tc_065_an_unlisted_route_fails_the_check`** builds the app and walks it with `unlisted_routes` (`route_matrix.py:212-219`), the same walk as the §3.4-named `test_tc_065_every_implemented_owned_route_is_in_the_matrix`. With the switch ON it also lists API-76 to API-79, which by design are not in `route_matrix.py` (§3.4; their ON counterpart is `test_any_city_routes.py`, TC-487). It is a fifth inventory test that pins the OFF route set.
2. **`tests/authz/test_route_inventory.py::test_inventory_docs_companions_are_only_fastapi_doc_pages`** builds a *production* app. With the switch ON, start-up refuses `LIVE_DATA_PROVIDER=FAKE` in production ("LIVE_DATA_PROVIDER: FAKE is refused in staging and production when any_city_mode is on", TC-462). That is the start-up rule working as specified; the test's production settings have no live-data configuration.

With these two also deselected, switch ON authz gives **84 passed, 14 skipped, 3 deselected, 1 warning in 21.55s**. PD-730-1 proposed adding both tests to A2 §3.4's switch-ON deselect list. The team agreed, recorded as **IMD-219** (RUN-093), and A2 §3.4 now names them. The authz command above includes them. The result table keeps the RUN-092 lines, measured with the four §3.4 deselects. No test was changed.

## Switch-ON CI jobs (one added job per workflow; existing jobs unchanged)

- **`.github/workflows/ci.yml` job `any-city`**:
  - environment: `FEATURES_DISABLED` and `NEXT_PUBLIC_FEATURES_DISABLED` = `!any_city_mode`, `LIVE_DATA_PROVIDER=FAKE`, `APP_ENV=test`, MOCK;
  - runs `make test-api ARGS='-m any_city'` and `make test-unit ARGS='-m any_city'`;
  - not a required check.
- **`.github/workflows/e2e.yml` job `live`**:
  - the local Supabase stack, `make seed`, the API with MOCK and the web build, both with the switch ON and the fake providers;
  - runs `live-city.spec.ts` (E2E-10 `@live`, TC-486) at `chromium-360` and `chromium-1280` with the dispatch's `repeat_each`;
  - uploads the artifacts `live-city-screenshots` and `playwright-report-live`.
  - It does not run for a floor (`features_disabled`) or staging (`base_url`) dispatch.
- **Repeat runs (RUN-093).** In dispatch 45228887894 (`repeat_each=3`), the `e2e` job's itinerary-edit step got 429 `RATE_LIMITED`. Every parallel test reaches the local API from one address, so together they used up the per-address window of `RATE_LIMIT_PER_MIN` (default 60 a minute, `app/core/rate_limit.py`). Each test already signs in as its own user. `e2e.yml` therefore sets `RATE_LIMIT_PER_MIN=1000` in its workflow environment, the IMD-203 pattern, for the E2E stacks only. The Settings default and the staging value stay 60.

## Screenshots

The `@live` spec takes them at 360 and 1280 px:

- `1-city-search` (search with its result);
- `2-import-progress`;
- `3-not-enough-data`;
- `4-live-itinerary`;
- `5-live-costs`.

They are written to `apps/web/test-results/live-city-screens/` and uploaded as the artifact **`live-city-screenshots`** of the RUN-092 E2E dispatch on `feat/S7-C3-any-city-verify`. The run link is in the pull request and in the SYNC REPORT of RUN-092. They are not committed.
