# IMP-607 · regen-api

- Run id: RUN-076b
- Owner: Het Lathiya (4 points, both endpoint and merge commits)
- Status: implementation complete; checks pending the controls commit.
- Base commit: ce2c63d
- Files changed: generation/router.py, generation/service.py, tests/api/test_generations.py, tests/contract/test_openapi_contract.py, tests/authz/route_matrix.py; this record. The save half follows in generation/pipeline.py and itinerary/service.py.
- Commands: preflight `(cd apps/api && .venv/bin/alembic heads)` → `0007 (head)`; `git diff --check` → empty output.
- Acceptance: not yet verified; API cases cover snapshot-on-start, idempotency, scope, ownership, stale revision, caps and switch-off. Transactional merge acceptance follows in the second commit. Database suites await final checks or CI.
- Files outside the run list: tests/authz/route_matrix.py → new implemented routes must enter the mandatory ownership inventory.
- Blockers: none.
- Proposed decisions: none.
- Open issues: local Docker is unavailable; database-suite availability will be recorded with final checks.

## Card steps, acceptance criteria and test commands (verbatim)

**Implementation**

1. Implement API-30 POST /api/v1/trips/{trip_id}/itinerary/days/{day_number}/regenerate and API-31 POST /api/v1/trips/{trip_id}/itinerary/regenerate with body RegenerateIn (plan_revision, mode); both handled in app/generation/router.py (IMD-13), return 202 + GenerationOut and reuse the API-22 job protocol (one active job per trip, request-hash idempotency, caps).
2. Build the day-scoped gr-1 request: the day, its locked items as fixed constraints, neighbouring days' place ids as exclusions, remaining budget share; scope day with scope_day_number in ai_generations (IMD-17).
3. Save step for scope day: in one transaction verify plan_revision, replace only that day's unlocked items (the regeneration snapshot was already written when the job was started by API-30/API-31, always, IMD-18), recompute and revalidate the whole trip, bump plan_revision, write warnings and complete the generation; other days' rows untouched.
4. Full regeneration: same transaction pattern, locked items preserved, previous plan restorable through versions (reason regeneration).
5. On failure or stale revision the plan is unchanged and the generation ends failed (or 409 STALE_PLAN at start).
6. UI: "Regenerate day" in DayColumn and "Regenerate all" with ConfirmDialog; progress via GenerationProgress; outcome notice via FallbackNotice.
7. Guard both with the IMD-11 flag 'regeneration'.

**Interfaces**

- API: API-30, API-31, API-23, API-24 · Tables: ai_generations, itinerary_days, itinerary_items, itinerary_versions, itinerary_warnings, trips · Modules: MOD-B08, MOD-B06, MOD-F04 · Components: DayColumn, GenerationProgress, ConfirmDialog, FallbackNotice · Env: FEATURES_DISABLED · Other: gr-1 scope day

**Acceptance criteria**

- FR-067 AC1-AC2 hold (TC-213, TC-214); FR-068 AC1-AC2 hold (TC-215, TC-216).
- Rows of non-target days are byte-identical before and after a day regeneration (row hash comparison in the test).
- Locked items keep day and start_time (TC-313); restore of the pre-regeneration version works (TC-376, with IMP-610).
- With 'regeneration' disabled the routes return 404 and manual editing remains (TC-372).

**Tests**

- apps/api/tests/api/test_generations.py — TC-213, TC-214, TC-215, TC-216, TC-313 — `make test-api ARGS='-k regenerate'`
- apps/web/e2e/itinerary-edit.spec.ts — TC-376 — `make e2e ARGS='itinerary-edit'`


## Transactional merge (second Het commit)

- Files changed: apps/api/app/generation/pipeline.py, apps/api/app/itinerary/service.py, apps/api/tests/api/test_generations.py, apps/api/tests/fixtures/pipeline.py; this record.
- The save verifies the start request hash against the current plan revision and compares that revision again under the trip lock. No generation_settings field, table or migration is added.
- Day scope deletes only target unlocked items. Other days and their row identities and timestamps are read only. Full regeneration merges all days around the existing locked rows. Fixed positions, local times, durations, origin, notes and citations survive; new items use the new validated citations.
- Target travel and prices are recomputed, the whole trip is validated, the revision is bumped, warnings and a regeneration version are written, and the generation completes in the same transaction. Any failure rolls back the plan; jobs.run then fails the generation.
- Acceptance not yet verified: API tests name TC-213, TC-214, TC-215, TC-216 and TC-313, compare PostgreSQL hashes of all non-target row columns, restore the pre-regeneration snapshot, check new citations and inject quota, stale revision and completion failures. TC-372 verifies manual editing with regeneration off.
- Files outside the run list: tests/fixtures/pipeline.py → supply the start hash on the shared row stand-in.
