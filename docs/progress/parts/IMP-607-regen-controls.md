# IMP-607 · regen-controls

- Run id: RUN-076b
- Owner: Krrish Kamani (2 points)
- Status: implementation complete; final checks pending.
- Base commit: ce2c63d
- Files changed: apps/web/components/itinerary/DayColumn.tsx, apps/web/app/(app)/trips/[tripId]/itinerary/page.tsx, apps/web/lib/api/queries.ts (block // IMP-607), apps/web/components/generation/GenerationProgress.tsx, apps/web/tests/unit/itinerary/DayColumn.test.tsx, apps/web/tests/unit/itinerary/Regeneration.test.tsx, apps/web/e2e/itinerary-edit.spec.ts, .github/workflows/e2e.yml; this record.
- Commands: `make openapi` → `openapi: wrote openapi.v1.json`; no tracked contract changes because API-30/31 already declare the final shapes. Final make result lines pending.
- Acceptance: not yet verified. Tests cover keyboard day control, full-plan confirmation/cancellation, request revision/scope, disabled controls, progress and completion, invalidation of itinerary/costs/warnings/versions, and feature switch hiding. TC-376 regenerates a day and the whole plan, restoring each pre-regeneration version through Versions, at all configured browser widths.
- UI uses existing Button, ConfirmDialog, GenerationProgress, FallbackNotice, PrivacyNotice and ErrorState; no dependency added. Loading, focus, labels and touch targets follow docs/guides/ui-design.md.
- Files outside the run list: GenerationProgress.tsx → reuse its polling and retry states inline, invalidate derived views after completion; tests/unit/itinerary/Regeneration.test.tsx → exercise the page and real hooks beside DayColumn tests; .github/workflows/e2e.yml → the existing dispatch selected only journey/map paths, so explicitly run the required itinerary-edit file in the same dispatch.
- Screenshots: to be added by members.
- Blockers: none.
- Proposed decisions: none.
- Open issues: local E2E needs the unavailable Docker stack; the single CI dispatch supplies browser evidence.

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

