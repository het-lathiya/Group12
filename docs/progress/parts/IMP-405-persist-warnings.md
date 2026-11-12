# IMP-405 · persist-warnings part

- Run id: RUN-060 (grouped, IMD-121, with IMP-407 whole-task and IMP-403)
- Owner: Jeel (jeelfefar2141)
- Status: PR open
- Base commit: 84d1973
- Branch: feat/IMP-403-405-407-failures-warnings-edits
- Reviewer: Kirtan (kirtan-S111)
- Traces to: US-065, US-067; FR-056, FR-058; IMD-13, IMD-42
- Card steps built: 1, 2, 3, 5 (step 4 is the warnings-panel part)

## Preflight findings (RUN-060)

- (a) `itinerary/repository.py` on main already offered `lock_trip`, `replace_plan`, `insert_warnings` (RUN-057: item_ref to item_id, MUST_VISIT_MISSING with place_id and item_id null), `current_warnings(trip, revision)`, `insert_version`, `mark_plan_saved`, `plan_days`, `plan_items`. They are reused. Added only `delete_warnings(trip, revision)` and `version_for_trip`.
- (b) API-32 was a 501 stub in `itinerary/router.py` (IMD-37). It now lives in `validation/router.py`, where §4 (IMD-13) places it, and calls `itinerary.service.revalidate`.
- (c) `apps/api/app/itinerary/edits.py` did not exist; part 2 creates it.
- (d) Closed PR #264 (`feat/IMP-405-warnings-panel`, Manasvi): four commits, all authored `Manasvi1704 <166296173+Manasvi1704@users.noreply.github.com>`, touching `WarningsPanel.tsx`, its test, the itinerary page and `ItineraryItemCard.tsx`. That author email is not the one in the run prompt, and the commits touch more than the panel files, so part 4 is built fresh (see its record).

## Changed files

- `apps/api/app/validation/validator.py`: `SUGGESTED_FIXES`, one fix per §8.12 code. `validate()` keeps a rule's own, more specific fix and fills in the catalogue's when a rule gives none, so every finding has a fix (FR-056 AC1). `summary(findings)` gives the `{errors, warnings, infos}` counts.
- `apps/api/app/validation/router.py` (created): API-32 `POST /api/v1/trips/{trip_id}/itinerary/validate`, owner only.
- `apps/api/app/itinerary/router.py`: the API-32 stub removed; docstring updated.
- `apps/api/app/main.py`: mounts the validation router.
- `apps/api/app/itinerary/service.py`: `revalidate` (lock the trip; 404 for a foreign trip or no plan; 409 STALE_PLAN for another revision; validate the stored plan; replace that revision's warnings; return `ValidateOut`), plus the shared helpers `planned_days` (stored rows as `PlannedDay`), `validation_context` (dates, active place names, must-visit IDs, pace limits; no shortlist outside generation), `stored_findings` and `version_findings` (FR-058 AC1: a stored version's warnings, i.e. those of its plan_revision, and its validation_summary). API-24 now reads its findings through `stored_findings`.
- `apps/api/app/itinerary/repository.py`: `delete_warnings(trip, revision)`, `version_for_trip`. `insert_version` always stores `deterministic_repairs` and `repair_attempts` in the version's validation_summary (0 unless the caller gives them; IMP-502 will). `insert_warnings` keeps the warnings of other revisions, so each version keeps its own.
- `apps/api/tests/unit/validation/test_findings.py` (created): TC-188, TC-189, the catalogue, a rule's fix winning, summary counts.
- `apps/api/tests/api/test_itinerary.py`: TC-194 (API-32 replaces only the revision's warnings and leaves the plan unchanged), stale revision 409, another user's trip / no plan 404, TC-193 (a version returns its own warnings and repair counts after a later revision), generation stores fixes and repair counts.
- `apps/api/tests/authz/route_matrix.py`: API-32 added as a `foreign` route.
- Contracts: `make openapi` changed nothing; API-32's shape (`ValidateOut`) was already in contract v1.

Where validation_summary lives (card step 2): the version's summary holds the counts by severity plus `deterministic_repairs` and `repair_attempts`. On `ai_generations` the counts are in `validation_summary` and the repair counts are in the existing `repair_attempts` and `deterministic_repairs` columns. Both are written inside the plan's save transaction (unchanged from IMP-305/IMP-406).

## Commands and results

PostgreSQL: a throwaway PostgreSQL 16.2 with pgvector on 127.0.0.1:55432 (scratch directory, `TEST_DATABASE_URL` set for the run). It is not part of the repository.

| Command | Result |
| --- | --- |
| `make test-unit ARGS='-k findings'` | `6 passed, 1000 deselected, 1 warning` |
| `make test-api ARGS='-k warnings'` | `9 passed, 352 deselected, 1 warning` |
| `make test-authz` | `37 passed` |
| `make test-api` | `361 passed, 1 warning` |
| `make test-unit` | `1006 passed, 1 warning` |
| `make test-web` | `Tests  151 passed (151)` |
| `make lint` | exit 0 |
| `make typecheck` | `Success: no issues found in 114 source files` (web `tsc` clean) |
| `make imports` | `Contracts: 6 kept, 0 broken.` |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-056 AC1 / TC-188: every finding names its cause and at least one suggested action | verified | `test_tc_188_every_finding_names_its_cause_and_a_suggested_fix`, `test_every_catalogue_code_has_a_suggested_fix` |
| FR-056 AC2 / TC-189: an unresolved warning is stored with the version | verified | unit `test_tc_189_...`; API `test_tc_193_...` (stored rows of the version's revision, MUST_VISIT_MISSING with place_id and item_id null) |
| FR-058 AC1 / TC-193: a saved version returns its warnings and repair summary | verified (service level) | `test_tc_193_a_saved_version_returns_its_warnings_and_repair_summary` via `itinerary.service.version_findings`; API-24 `version_id` stays 501 until IMP-610 |
| FR-058 AC2 / TC-194: revalidation is available and replaces the revision's warnings | verified | `test_tc_194_api_32_revalidates_and_replaces_the_warnings_of_the_revision` |
| API-32 by another user returns 404 | verified | `test_api_32_warnings_of_another_users_trip_or_no_plan_are_not_found`; authz matrix entry API-32 |

## Blockers

none

## Proposed decisions

- **PD-IMP-405-1: version read path.** The card's step 5 says a stored version returns its stored warnings. §6.5 (IMD-18) says API-24 with `version_id` recomputes findings from the snapshot on read. This part provides the stored warnings through `version_findings`. IMP-610 should decide which of the two API-24 returns (stored, or recomputed with the stored ones as history).

## Open issues

- A version's validation_summary records the counts at save time. A later API-32 on the same revision replaces that revision's warnings but does not rewrite the version's summary.
- Regeneration still deletes all of a trip's warnings with its items, as before; the rows of deleted items would be removed by the foreign-key cascade anyway.
