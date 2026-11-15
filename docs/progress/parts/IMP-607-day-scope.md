# IMP-607 · day-scope

- Run id: RUN-076b
- Owner: Nidhi Chauhan (4 points)
- Status: implementation complete; checks pending the controls commit.
- Base commit: ce2c63d
- Files changed: generation/request_builder.py, generation/pipeline.py, tests/unit/generation/test_request_builder.py, tests/unit/generation/test_pipeline.py, tests/api/test_generations.py, tests/fixtures/pipeline.py; this record (all API paths below apps/api/).
- Commands: `git diff --check` → empty output; final make results pending.
- Acceptance: not yet verified. Tests cover one target day, fixed constraints, other days excluded from shortlist and must-visits, remaining budget, gr-2 passages, MOCK day answers and pipeline scope for model and rule-based jobs.
- Budget: existing activity-budget formula reserves transport, accommodation and contingency, then subtracts known high costs of other days and target locks; the remainder is clamped to zero. Unknown costs remain unavailable.
- The active template stays v2; no prompt file, model contract or schema changes. MOCK already supports day scope, so no adapter change.
- Files outside the run list: tests/fixtures/pipeline.py → the shared test row now supplies the existing scope columns read by the pipeline.
- Blockers: none.
- Proposed decisions: none.
- Open issues: database verification awaits final checks or CI.

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

