# IMP-402 · sample-itineraries part

- Run id: RUN-057s
- Owner: Jeel (jeelfefar2141)
- Status: PR open
- Base commit: 4e6bcbd
- Branch: feat/IMP-402-sample-itineraries
- Reviewer: Malhar (Malhar1112-v)
- Traces to: US-058; FR-036 AC3; TC-147 (sample half); IMD-145
- Card step built: 5, narrowed by the run prompt (Sampleton only; no endpoint)

## What was built

- `apps/api/app/generation/samples.py` (created): `list_samples(destination_slug)` and `load_sample(session, destination_slug, name)`. Samples are looked up in `data/fixtures/<slug>/sample_itineraries/` and then `data/places/<slug>/sample_itineraries/`. The slug must match `[a-z0-9][a-z0-9-]*` and the name must be a listed sample. The loader resolves each `place_ref {source_name, external_ref}` to the current active place of the active destination. It then parses io-1 (`ItineraryOutput`), runs step 9 (`schedule.recalculate` with the labelled distance estimate, no network) and runs `validate()`. It returns the plan and every finding. A missing or inactive reference raises `UnresolvedPlaceRefError`, which names each ref; no item is dropped. An unknown name or slug raises `SampleNotFoundError`.
- `apps/api/app/places/repository.py` and `service.py`: `active_places_by_refs`, a read-only lookup by `(data_sources.name, places.external_ref)`. Place queries stay in the places module.
- `data/fixtures/sampleton/sample_itineraries/two_day_walking.json` and `five_day_local_transport.json`, plus a `README.md` that explains how they were produced. Each file stores the planner's io-1 answer unchanged, except that `place_ref` replaces `place_id` (IMD-145). It also carries a wrapper: `label: SAMPLE` (§7.8), `origin: fallback_rule_based`, `model_id: rule_based_planner_v1`, the destination slug and the trip (case id, dates, pace, transport). Notes are empty and the summary is the planner's template, so there are no AI-written fields.
- `scripts/build_sample_itineraries.py`: rebuilds the files from the cases with `plan_rule_based`, mapping the cases' stable IDs (uuid5 of `external_ref`) back to `places.csv`. It checks that every planned place's name and duration match the CSV. `--check` exits 1 if a file is stale.
- `fallback_planner.py` was not changed.

### Trip cases used

| Sample | Case | Category | Days | Transport |
| --- | --- | --- | --- | --- |
| `two_day_walking` | `trips-v1-001` | standard | 2 | walking |
| `five_day_local_transport` | `trips-v1-003` | standard | 5 | local_transport |

## Changed files

- `apps/api/app/generation/samples.py` (created)
- `apps/api/app/places/repository.py`, `apps/api/app/places/service.py` (one read-only query each)
- `data/fixtures/sampleton/sample_itineraries/` (created: two JSON files, `README.md`)
- `scripts/build_sample_itineraries.py` (created)
- `apps/api/tests/unit/generation/test_samples.py` (created)
- `apps/api/tests/api/test_samples.py` (created)
- `docs/progress/parts/IMP-402-sample-itineraries.md` (this record)

## Commands and results

The database was a throwaway local PostgreSQL 16.2 with pgvector (pip `pgserver`, port 55432), migrated by the test fixtures and stopped afterwards.

| Command | Result |
| --- | --- |
| `make test-unit ARGS='-k sample'` | `57 passed, 974 deselected, 1 warning` |
| `make test-api ARGS='-k sample'` | `9 passed, 416 deselected, 1 warning` |
| `make test-api ARGS='-k fallback'` | `11 passed, 414 deselected, 1 warning` |
| `make lint` | exit 0 (`All matched files use Prettier code style!`) |
| `make typecheck` | `Success: no issues found in 117 source files` |
| `make imports` | `Contracts: 6 kept, 0 broken.` |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |
| `make test` (unit / contract / api / authz) | `1031 passed, 1 warning` / `87 passed, 2 deselected, 1 warning` / `425 passed, 1 warning` / `41 passed` |
| `make test` (web) | first run: `Tests  22 failed \| 120 passed (142)`, all timeouts with load average 45 from two stray filesystem scans; rerun after stopping them: `Tests  186 passed (186)` (`make test-web`) |
| `apps/api/.venv/bin/python scripts/build_sample_itineraries.py --check` | exit 0 |

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-036 AC3 / TC-147 (sample half): two saved samples per destination with samples load and pass validation with no error-level finding | verified (Sampleton) | `test_sample_both_samples_load_and_pass_validation`: also asserts every ref resolved to the current row and step 9 gives back the stored times |
| Still loads after a reseed | verified (test-fixture equivalent) | `test_sample_samples_still_load_after_a_reseed`: deletes Sampleton's places and seeds again, then asserts every place ID changed and both samples load clean. `make db-reset && make seed` was not run: it needs `apps/api/.env`, which this run does not read |
| Unknown external_ref fails loudly | verified | `test_sample_unknown_external_ref_fails_loudly` (DB), `test_sample_inactive_place_is_not_resolved` (DB), `test_sample_unresolved_ref_raises_and_names_it` (unit) |
| Values come only from fixture data and the planner | verified | `test_sample_files_are_the_rule_based_planners_output` (the committed files equal the builder's output); the builder checks names and durations against `places.csv` |
| Labelled SAMPLE, built without AI | verified | `test_sample_files_are_labelled_sample_and_carry_no_ai_text` |
| Contracts unchanged (io-1, validate(), places tables, §6 API) | verified | no schema, migration or router change; `make openapi-check` shows no diff |

## Blockers

none

## Proposed decisions

- **PD-IMP-402-3: sample file wrapper.** io-1 cannot carry `{source_name, external_ref}` in `place_id` without a contract change. So each file stores io-1 with `place_ref` in that position, inside a wrapper (`label`, `origin`, `model_id`, `destination_slug`, `trip`). After resolution the itinerary parses as strict io-1. This follows IMD-145 without a sidecar mapping file. Please confirm the wrapper shape when IMD-145 is recorded (PR #269).

## Open issues

- Ahmedabad samples: waiting for two trip inputs from Jeel (FR-036 AC3 for the curated destination). The loader already reads `data/places/<slug>/sample_itineraries/`, and the builder needs only the two case inputs.
- Day 2 of `two_day_walking` has no meal: no food place fits the lunch window at the planner's clock. That is the planner's merged behaviour and gives no finding.
- No endpoint or screen uses the samples yet (no API-* names them). The SampleBanner wiring (§7.8) belongs to whichever card shows them.
