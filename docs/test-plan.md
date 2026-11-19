# Test plan: AI Travel Planner

| Item | Value |
| --- | --- |
| Document | Test plan (summary of specification §13 with links to the test reports) |
| Owner | Mohammad Junaid Kureshi (IMP-707 part "Test plan") |
| Version | 1.0 (draft for SG-7), 19 November 2026 |
| Card | IMP-707, US-145 |
| Built from | `docs/spec/IMPLEMENTATION_SPEC.md` §13 (and §14.1 for gates), `docs/spec/AMENDMENT_A1_AWS_RAG.md` §5.4 and §9.3, `Makefile`, `.github/workflows/`, `apps/api/tests/`, `apps/web/`, `docs/test-reports/`, `docs/progress/gates.md`, on `main` at `f75aa94` |
| Related documents | [SRS](srs.md), [Architecture](architecture.md), [API](api.md), [authorization suite guide](guides/authz-suite.md) |

**Precedence.** The specification §13 is binding; where this summary and §13 differ, §13 wins. Section 9 lists where the built test set-up differs from §13. The full test case catalogue (TC-001 to TC-398) is in blueprint §28, which is not in the repository; the RAG cases TC-433 to TC-459 are in A1 §9.3; the extension cases TC-399 to TC-432 belong to cut cards (IMD-65).

## 1. Rules (specification §13.1)

| Rule | In practice |
| --- | --- |
| Tests are written with the code | A task is done only when the tests its card names exist and pass; a bug fix adds a regression test that fails before and passes after the fix |
| Report only what ran | A result is the command, its exit code and its summary line; a skipped test is reported as skipped with the reason |
| Mock and live are different results | Automated runs use the MOCK provider, recorded responses or mocked HTTP; live calls are marked `live`, skipped without a key, never run in pull-request CI and are reported separately |
| No credential without a mock path | Pull-request CI holds no provider key; a socket guard in `apps/api/tests/conftest.py` fails any test that connects to a provider host unless it is marked `live` |
| Synthetic data only | The Sampleton fixture, generated users and trips; no real personal data, keys or prompt bodies |
| Evidence is recorded | Part records in `docs/progress/parts/`, gate results in `docs/progress/gates.md`, reports in `docs/test-reports/` |
| Disabled features | A cut-list feature switched off with `FEATURES_DISABLED` has its tests skipped with the reason; the floor journey (TC-372) must still pass. A cut extension is skipped with its reason, except TC-432, which checks that its routes answer 404 |
| RAG tests | MOCK embeddings only; tests never call the Gemini embedding API (CLAUDE.md §8) |

## 2. Test levels and suites

| Level | Scope | Location | Tool | Command | Provider |
| --- | --- | --- | --- | --- | --- |
| Unit and deterministic calculation | Pure rules: validator, budget engine, routing estimate, ranking, grouping, request builder, settings checks, prompt registry, RAG chunker, guide gate, query, MMR | `apps/api/tests/unit/<module>/` (53 `test_*.py` files) | pytest | `make test-unit` | MOCK; no database, no network |
| AI provider contract | One suite for every adapter: operations, result shape, error mapping, metadata, health; Gemini against recorded responses; API contract and AI schema checks | `apps/api/tests/contract/` (2 files), recordings in `apps/api/tests/fixtures/provider_recordings/` | pytest, respx | `make test-contract` (runs `-m "not live"`) | MOCK and recorded GEMINI |
| API contract | Exported OpenAPI and AI schemas equal the committed `contracts/`; web types current | Makefile target | export and diff | `make openapi-check` | none |
| API and database integration | Every endpoint over HTTP with a migrated PostgreSQL 16 + pgvector database: status codes, bodies, error envelope, database effects, generation lifecycle, schema drift, seed, RAG index and retrieval | `apps/api/tests/api/` (24 files), including `test_schema_drift.py` | pytest, httpx | `make test-api` | MOCK scenarios |
| Authentication and authorization | 401 token rules, two-user ownership (404) on every owned route, body user ID refused (422), CORS, row-level security, route inventory | `apps/api/tests/authz/` (4 files) | pytest, minted HS256 test tokens | `make test-authz` | MOCK |
| Frontend component | Components and hooks: forms, labels, states, warnings, move controls, error mapping, sources | `apps/web/tests/unit/<area>/` (43 test files) | Vitest, Testing Library | `make test-web` | API mocked at the client boundary |
| End to end | E2E-01 to E2E-08 and the journey in a browser with axe scans, at 360, 768, 1280 and 1920 px, plus the `provider-failure` and `floor-journey` projects | `apps/web/e2e/` (13 spec files) | Playwright, @axe-core/playwright | `make e2e` | MOCK scenarios, Supabase CLI local stack |
| Deployment smoke | Health, readiness, auth wall, one read and (staging) one generation on a deployed URL | `apps/api/tests/smoke/test_deployed.py`, `apps/web/e2e/smoke.spec.ts` | pytest, Playwright | `make smoke URL=<api url>` | The environment's provider |
| Live provider smoke | One real Gemini call through the adapter | `apps/api/tests/contract/` (marker `live`) | pytest | `make live-smoke` (needs a key) | GEMINI, live |
| AI evaluation | Fixed datasets scored by the harness: `trips/v1` (15 trips) and the retrieval suite `retrieval/v1` | `eval/`, `apps/api/app/evaluation/` | `python -m app.evaluation.run` | `make eval PROVIDER=MOCK DATASET=trips/v1`; `make eval DATASET=retrieval/v1 ARGS='--suite retrieval'` | MOCK in CI; GEMINI by hand |

`make test` runs `test-unit`, `test-contract`, `test-api`, `test-authz` and `test-web`; `make check` runs `lint`, `typecheck`, `imports`, `openapi-check` and `test` (`Makefile`). File counts above were taken from the repository in this run.

## 3. Latest results

Counts of this run (RUN-083, base commit `f75aa94`, Linux container, compose test database, proxy variables unset), run by the integration lead and quoted exactly:

| Suite | Command | Result |
| --- | --- | --- |
| Unit | `make test-unit` | `1210 passed, 1 warning in 19.46s` |
| Provider and API contract | `make test-contract` | `91 passed, 2 deselected, 1 warning in 20.46s` |
| API and database integration | `make test-api` | `590 passed, 1 warning in 276.11s (0:04:36)` |
| Authorization | `make test-authz` | `87 passed, 14 skipped, 1 warning in 55.38s` |
| Frontend component | `make test-web` | `Tests  288 passed (288)` |

- The 2 deselected contract tests are the `live` tests, which `make test-contract` excludes with `-m "not live"` (`Makefile`).
- The 14 skipped authorization tests are the extension-route ownership cases (TC-431), skipped because the extensions are cut (IMD-65; `docs/test-reports/security-sprint7.md`).
- This part also ran, in the same run without a database: `make test-unit` → `1210 passed, 1 warning in 20.91s`; `make test-contract` → `91 passed, 2 deselected, 1 warning in 20.26s`; `make test-web` → `Tests  288 passed (288)`; `make openapi-check` → `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date`; `make lint` → `All checks passed!`; `make typecheck` → `Success: no issues found in 123 source files`; `make imports` → `Contracts: 6 kept, 0 broken.`
- **E2E is not part of these counts.** The latest E2E evidence is in [e2e-sprint7.md](test-reports/e2e-sprint7.md): three consecutive local full runs at code head `b6051a8`, each `37 skipped`; `82 passed`, with the provider quota follow-up `1 skipped`; `1 passed` after each (RUN-081d, 18 November 2026). The 37 skips are the 36 cut-extension cases (nine at each width) and the quota case while the provider API runs the timeout scenario. Earlier E2E and gate evidence is in [gates.md](progress/gates.md).

## 4. Critical tests (specification §13.3)

The rules that most often break integrations, each with its test case and command (§13.3 gives the inputs and expected results):

| Area | Test cases | Command |
| --- | --- | --- |
| Trip validation | TC-071, TC-072, TC-073, V-01 | `make test-api ARGS='-k trips'` |
| Overlap and transfer | TC-176, TC-177, TC-306, TC-178 | `make test-unit ARGS='-k overlap'`, `ARGS='-k transfer'` |
| Opening hours (closed day, past midnight, time zone) | TC-180, TC-301, TC-302 | `make test-unit ARGS='-k hours'` |
| Place IDs and trip dates | TC-138, TC-137, TC-305 | `make test-unit ARGS='-k place_id'`, `make test-api ARGS='-k generations'` |
| Must-visit places | TC-186, TC-142 | `make test-unit ARGS='-k must_visit'` |
| Budget and cost formulas | TC-184, TC-304, TC-221, TC-296, TC-297 | `make test-unit ARGS='-k budget'` |
| Recalculation ignores model numbers | TC-139 | `make test-unit ARGS='-k recalc'` |
| Money serialisation | M-01 | `make test-api ARGS='-k money'` |
| RAG (A1 §9.3) | TC-441 to TC-458 (store, embeddings, chunker, gate, index, retrieval, MMR, injection through passages, citations, `ItemSources`, retrieval suite) | in `make test-unit`, `make test-contract`, `make test-api`, `make test-web` |

These narrowed commands are listed as §13.3 gives them; they were **not run** separately in this run (the full suites that contain them ran, section 3).

## 5. End-to-end acceptance scenarios (specification §13.4)

| ID | Scenario | Spec file | Provider |
| --- | --- | --- | --- |
| E2E-01 | Create or sign in to an account | `auth.spec.ts` | none |
| E2E-02 | Create a trip | `trip-create.spec.ts` | none |
| E2E-03 | Generate an itinerary | `generate.spec.ts` | MOCK |
| E2E-04 | Validate the itinerary and its costs | `validate-costs.spec.ts` | MOCK `flawed` |
| E2E-05 | Edit or remove an activity (with lock, regenerate, version restore, TC-376) | `itinerary-edit.spec.ts` | MOCK |
| E2E-06 | Save and reopen the trip (with 409 `STALE_PLAN`) | `reopen.spec.ts` | MOCK |
| E2E-07 | Handle an AI provider failure (timeout, then quota) | `provider-failure.spec.ts`, project `provider-failure` (API 8001, web 3001) | MOCK scenarios |
| E2E-08 | Another user cannot access a private trip | `ownership.spec.ts` | MOCK |
| E2E-09 | Smoke-test the deployed application | `smoke.spec.ts`, `tests/smoke/test_deployed.py` | environment's provider |
| TC-369 / TC-372 | Whole journey; floor journey with the nine cut-list switches off | `journey.spec.ts`, project `floor-journey` (API 8002, web 3002) | MOCK |
| TC-373 / TC-374 | 360 px width; keyboard only | project `chromium-360`; `keyboard.spec.ts` | MOCK |
| TC-432 | Cut extension routes answer 404 and their UI is hidden | `extensions.spec.ts` (tag `@ext`) | MOCK |

Every scenario runs an axe scan on each page; a serious or critical violation fails the run. `map.spec.ts` covers the map and its list fallback. The status of each scenario after IMP-701 is in [e2e-sprint7.md](test-reports/e2e-sprint7.md) §5.

## 6. Regression policy (specification §13.5)

| Change | Re-run before merge |
| --- | --- |
| Any change | `make check` |
| Prompt template, `PROMPT_TEMPLATE_VERSION`, request builder, output schema | Contract suite; generation API tests; `make eval DATASET=trips/v1 PROVIDER=MOCK`; a Gemini evaluation by hand before the next gate (`eval/reports/`) |
| `GEMINI_MODEL_ID` or adapter settings | Contract suite with recordings; new recordings with `make live-smoke`; Gemini evaluation |
| Validator, repair, finding codes or severities | `tests/unit/validation`; generation and edit API tests; E2E-04 and E2E-05; evaluation regression subset |
| Budget engine, labels, rounding | `tests/unit/budget`; costs API tests; E2E-04 |
| Migrations or ORM models | Schema drift; full `make test-api` and `make test-authz` |
| A new endpoint | Its API tests; an ownership case in `tests/authz/` (the route inventory fails otherwise); OpenAPI regenerated |
| Before each gate and before release | `make check`, `make e2e`, `make eval DATASET=trips/v1 PROVIDER=MOCK`, deployment smoke on staging |

Under the feature freeze (IMD-201) no contract, table, finding code, error code or variable name changes, so the contract and migration rows apply only to defect fixes.

## 7. Test data and CI

**Test data (§13.6).** Sampleton (`data/fixtures/sampleton/`: 30 SAMPLE places, three synthetic guides, saved sample itineraries); a migrated PostgreSQL 16 test database with the auth stub (`apps/api/tests/fixtures/db.py`, `TEST_DATABASE_URL`, image `pgvector/pgvector:pg16`, A1 §5.4); HS256 test tokens for users A and B (`apps/api/tests/fixtures/auth.py`) and E2E users created per run on the local stack (`apps/web/e2e/fixtures/users.ts`); the MOCK provider with seven scenarios `ok`, `flawed`, `timeout`, `rate_limited`, `quota`, `invalid_json`, `unknown_place` (`apps/api/app/core/config.py`); Gemini and ORS recordings in `apps/api/tests/fixtures/provider_recordings/`; the prompt-injection corpus `apps/api/tests/fixtures/injection_corpus.json`; evaluation datasets `eval/datasets/trips/v1/` and `eval/datasets/retrieval/v1/`.

**CI as built** (`.github/workflows/`):

| Workflow and job | Trigger | Contents |
| --- | --- | --- |
| `ci.yml` lint-types | Pull request, push to `main` | `make lint`, `make typecheck`, `make imports`, `make openapi-check`, web production build with placeholder `NEXT_PUBLIC_*` values |
| `ci.yml` unit | Pull request, push to `main` | Place quality gate in check mode, `make test-unit`, `make eval PROVIDER=MOCK DATASET=trips/v1`, `make test-contract`, `make test-web` |
| `ci.yml` guards | Pull request, push to `main` | Fails on a tracked real env file; gitleaks (pinned, checksum verified) over the pull-request commits or the full history on `main` |
| `ci.yml` attribution | Pull request only | `scripts/check_attribution.sh` |
| `ci.yml` audit | Pull request, push to `main` | pip-audit (any known vulnerability fails), npm audit (critical findings fail) |
| `ci.yml` api | Pull request, push to `main` | Service `pgvector/pgvector:pg16`; auth stub; `make db-migrate`; one Alembic head; round trip `downgrade base` and `upgrade head`; `make test-api` and `make test-authz` with a coverage report (report only) |
| `e2e.yml` | Push to `main`, manual dispatch | Supabase CLI stack, migrate, seed, Playwright projects (journey, map, itinerary-edit, regression specs, floor journey, provider failure timeout and quota); `repeat_each` input; optional staging job |
| `deploy-staging.yml` | After `ci.yml` succeeds on `main`, manual dispatch | Images, release task, service updates, `make smoke` and CORS check |
| `deploy-production.yml` | Manual, from a tag | The same steps in the protected `production` environment |

## 8. Reports and evidence

| Report | Content | Status |
| --- | --- | --- |
| [e2e-sprint7.md](test-reports/e2e-sprint7.md) | IMP-701 regression suite: gap list, fixes, three consecutive local full runs, acceptance | Local evidence complete; the CI dispatch of RUN-081d is not recorded in the report |
| [security-sprint7.md](test-reports/security-sprint7.md) | IMP-702 security pass: TC-344 to TC-358, TC-028, TC-431, TC-432; finding F-1 fixed (IMD-204) | TC-352, TC-433, TC-434, TC-436 and the ECR scan not verified until the staging window (IMD-137) |
| [journey-sprint4.md](test-reports/journey-sprint4.md) | IMP-414 journey on the local stack in CI (`4 passed (36.7s)` at four widths, 13 November 2026) | Staging with MOCK and with Gemini not run yet (IMD-137) |
| [label-review.md](test-reports/label-review.md) | MVP label review (TC-282, TC-385), 14 November 2026 | Live-stack screenshots and the full visual TC-385 review not verified |
| [gates.md](progress/gates.md) | SG-1 to SG-6 results with commands, CI runs and open items | SG-7 and SG-8 not run |
| `eval/reports/` | Gemini baseline-1 (`baseline-1.md`), prompt v3 evaluations (`RUN-077-prompt-v3-mock.md`, `RUN-079-prompt-v3.md`), retrieval suite runs on MOCK (`20261113T114752Z-retrieval-mock.md`, `20261113T114756Z-retrieval-mock.md`) | The final evaluation baseline and cost report (IMP-705) have no part record at `f75aa94` |

## 9. Differences between §13 and the built test set-up

| # | §13 says | Built at `f75aa94` | Source |
| --- | --- | --- | --- |
| T-01 | §13 opening: "No test has been run yet" | Suites run on every pull request and in recorded local runs (section 3, gates SG-1 to SG-6) | `docs/progress/gates.md` |
| T-02 | §13.2 and §13.7: E2E on merge to `main` and nightly | `e2e.yml` runs on push to `main` and by manual dispatch on pull-request branches; no nightly run | IMD-185, `.github/workflows/e2e.yml` |
| T-03 | §13.7: `make openapi-check` in `guards`; a separate `build` job with a bundle check and an API container build (TC-338) | `make openapi-check` and the web build run in `lint-types`; no separate `build` job; the bundle check was run by hand for TC-355; the API image is built by the deploy workflows | `.github/workflows/ci.yml`, `docs/test-reports/security-sprint7.md` |
| T-04 | §13.7: CI test database "PostgreSQL 16 service" | `pgvector/pgvector:pg16` (PostgreSQL 16 with pgvector) | A1 §5.4, IMD-115 |
| T-05 | §13.8: coverage thresholds 85 and 70 percent | Coverage is reported in the CI `api` job but no threshold fails the build (thresholds still Proposed) | `.github/workflows/ci.yml` (TC-334 comment) |
| T-06 | §13.6: `tests/fixtures/factories.py` | No such file; fixtures are `tests/fixtures/ai.py`, `auth.py`, `db.py`, `pipeline.py`, the injection corpus and the recordings | `apps/api/tests/fixtures/` |
| T-07 | §13.6 and §13.5: extension recordings, packing vocabulary, extension evaluation cases | Not created; the extensions are cut | IMD-65 |
| T-08 | §13.2 deployment smoke after every deploy; live smoke once per sprint review | Staging is off between windows; staging smoke, staging journey and the live E2E-03 variant (TC-370) are open staging items | IMD-137, `docs/progress/deferred.md` |
| T-09 | E2E-07 preconditions: "a trip that has an earlier saved version" | Timeout and quota specs start from a fresh trip with no itinerary (API-22 refuses a trip that already has one) | IMD-206 |

## 10. Commands named in this document

Run in this run (RUN-083, `f75aa94`): `make test-unit`, `make test-contract`, `make test-web`, `make openapi-check`, `make lint`, `make typecheck`, `make imports` by this part (results in section 3); `make test-api` and `make test-authz` by the integration lead (results in section 3).

**Not verified** in this run (they need a database, Docker, the Supabase stack, a deployed URL, a provider key or write evaluation files): `make test`, `make check` as one command, `make e2e` (and its `ARGS` selectors), `make smoke URL=<api url>`, `make live-smoke`, `make eval PROVIDER=MOCK DATASET=trips/v1`, `make eval DATASET=retrieval/v1 ARGS='--suite retrieval'`, `make db-migrate`, and the narrowed `ARGS='-k …'` commands of section 4 and section 6.
