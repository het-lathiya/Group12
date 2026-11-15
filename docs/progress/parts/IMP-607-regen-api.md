# IMP-607 · regen-api

- Run id: RUN-076b
- Owner: Het Lathiya (4 points, both endpoint and merge commits)
- Status: MERGED-READY (local gate passed).
- Base commit: ce2c63d
- Files changed: generation/router.py, generation/service.py, tests/api/test_generations.py, tests/contract/test_openapi_contract.py, tests/authz/route_matrix.py; this record. The save half changes generation/pipeline.py and itinerary/service.py; the integration fixture correction also changes tests/api/test_generation_failures.py.
- Commands: preflight `(cd apps/api && .venv/bin/alembic heads)` → `0007 (head)`; `git diff --check` → empty output.
- Acceptance verified by the final real-database suites: snapshot-on-start, idempotency, scope, ownership, stale revision, caps, transactional merge and switch-off. TC-376 browser execution awaits CI.
- Files outside the run list: tests/authz/route_matrix.py → new implemented routes must enter the mandatory ownership inventory.
- Blockers: none.
- Proposed decisions: none.
- Open issues: TC-376 browser execution and member screenshots await CI/member evidence; no backend blocker.

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
- Acceptance verified in PostgreSQL: API tests name TC-213, TC-214, TC-215, TC-216 and TC-313, compare PostgreSQL hashes of all non-target row columns, restore the pre-regeneration snapshot, check new citations and inject quota, stale revision and completion failures. TC-372 verifies manual editing with regeneration off.
- Files outside the run list: tests/fixtures/pipeline.py → supply the start hash on the shared row stand-in.

## Single integration fix and acceptance evidence

- Initial lint reported `Found 7 errors.` across both backend owners' assertions; the shared save had `Found 7 errors in 1 file (checked 123 source files)` from loop-variable typing and nullable warning refs. The final type/lint checks above pass.
- Initial targeted API result: `8 failed, 9 passed, 544 deselected, 1 warning in 15.81s`. Corrected this part's manual-edit fixture to send duration_min and gave the row-hash SQL parameter an explicit integer type. Nidhi corrects her destination currency separately.
- The full-suite integration result before fixture correction was `2 failed, 559 passed, 1 warning in 220.99s (0:03:40)`. Existing synthetic queued jobs now use the canonical API-31 start hash; the replacement test goes through API-31, verifies replacement item identities, and expects the pre-regeneration snapshot plus the result version. Assertions remain on replacement, revision, plan_stale and history.
- An early database attempt was interrupted (`48 passed, 1 warning, 392 errors in 84.96s (0:01:24)`): the disposable cluster had SQL_ASCII encoding, incompatible with the driver's version parsing. It was replaced by a UTF8 cluster before the successful runs; no repository change was needed for this setup error.
- FR-067 AC1 / TC-213 / row-hash: verified by `test_regenerate_tc_213_tc_214_tc_215_tc_216_tc_313_preserves_locks_and_restores_snapshot`, day scope, both first and last locked positions. Every non-target day/item column, including IDs and timestamps, is hashed in PostgreSQL before/after.
- FR-067 AC2 / TC-214: verified by the same test and the idempotent-start test; the prior-revision regeneration snapshot exists before the job runs and is written exactly once per new job, also with versions off.
- FR-068 AC1 / TC-215: verified by restoring the pre-regeneration snapshot through API-38 and comparing place/time/duration/lock/note content.
- FR-068 AC2 / TC-216 and TC-313: verified for full and day scope, first and last positions; the locked row's ID, day, position, start, duration, note origin and citations survive.
- Failure atomicity: quota, stale revision and injected completion exceptions all fail the generation with the old plan's hashes unchanged. The older injected version-write failure test also passes.
- A1 §6.10: locked citations survive; new items take only the new generation's validated passage citations (`test_regenerate_new_items_take_the_new_generation_citations`).
- Kept day themes retain their own generation provenance. `test_regenerate_rule_based_day_keeps_other_days_and_their_theme_labels` compares the complete non-target API day payloads and raw row hashes after a rule-based day regeneration.
- TC-372: verified by 404 from both switched-off routes and a successful manual retime; authorization is verified by the two-user matrix and final 71-case suite.
- Additional file outside the run list: apps/api/tests/api/test_generation_failures.py → preserve the existing fallback regression by matching the real start-hash protocol.
- No dropped parts, blockers or proposed decisions. This is this owner's only integration fix commit.

## Final batch checks (RUN-076b)

Database: disposable PostgreSQL 16.15 with pgvector 0.6.0 on loopback port 55476, extracted under a task-owned temporary directory; no system installation. It was stopped and the cluster, packages and connection settings were removed after testing. Alembic: `0007 (head)` before and after; no migration added.

| Command | Exact result lines |
| --- | --- |
| `make lint` | `All checks passed!`; `232 files already formatted`; `✖ 1 problem (0 errors, 1 warning)` (existing client navigation warning); `All matched files use Prettier code style!` |
| `make typecheck` | `Success: no issues found in 123 source files`; `✓ Types generated successfully` |
| `make imports` | `Contracts: 6 kept, 0 broken.` |
| `make test` (all five suites) | `======================= 1185 passed, 1 warning in 19.39s =======================`; `================= 91 passed, 2 deselected, 1 warning in 20.98s =================`; `================== 564 passed, 1 warning in 195.46s (0:03:15) ==================`; `============================= 71 passed in 44.04s ==============================`; `      Tests  283 passed (283)` |
| `make test-api ARGS='-k regenerate'` | `================ 21 passed, 543 deselected, 1 warning in 16.64s ================` |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |
| `make check` | `make check exit: 0`; all constituent checks passed. The final `make test` above also includes the subsequently added day-theme provenance regression. |
| `make e2e ARGS='itinerary-edit --list'` | `Total: 4 tests in 1 file` |
| `(cd apps/api && .venv/bin/alembic heads)` | `0007 (head)` |

Not run locally: `make e2e ARGS='itinerary-edit'` requires the local authentication stack, and Docker is unavailable in this WSL distro. Discovery is verified; TC-376 browser execution is not yet verified. The branch's one E2E dispatch includes this file. No live provider or recorded evaluation run was used.
