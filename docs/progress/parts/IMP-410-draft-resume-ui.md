# IMP-410 · draft-resume-ui

| Field | Value |
| --- | --- |
| Run | RUN-058 (grouped run, IMD-121), part 3 of 7 |
| Card | IMP-410 Drafts and reopening the latest saved itinerary |
| Part | Draft resume in wizard and dashboard (2 points) |
| Owner | Krrish Kamani |
| Status | PR_OPEN |
| Base commit | 16839a0 |
| Branch | feat/IMP-410-411-412-trips-budget-states |

## Changed files

- `apps/web/components/trips/TripWizard.tsx`: adds an optional `draftId`. It loads the trip with API-10 and the preferences with API-15. A draft reopens at Preferences, its first incomplete step, because a draft has no saved preferences (IMD-25). A ready trip reopens at Review. A polite status line under the step header shows "Saving…", then "Draft saved", or "Not saved" with a "Retry" text button. A draft that cannot be loaded shows ErrorState with Retry.
- `apps/web/components/trips/TripDetailsStep.tsx`: an `initial` prop, so the Details form of a resumed draft shows the saved values (FR-013 AC2). The fields stay read-only once the trip exists, as before.
- `apps/web/app/(app)/trips/new/page.tsx`: `?draft=<trip id>` is passed to the wizard as `draftId`.
- `apps/web/app/(app)/dashboard/page.tsx`: header with the title on the left and "Open latest" on the right. It is the primary style when API-09 returns a trip and the outline style when it does not. With a trip, the click opens `/trips/{id}/itinerary`. With none, it shows the EmptyState "No saved itinerary yet" with the action "Plan a trip"; this is not an error. Below the header is a "Drafts" list (API-08): each card shows the title, destination and dates, a neutral "Draft" badge (text and colour), and the primary action "Continue draft". At 375 px the actions are full width. The page also has a loading skeleton, an ErrorState with Retry, and the existing "No trips yet" empty state.
- `apps/web/lib/api/queries.ts`: `useTrips` (API-08) and `useLatestItinerary` (API-09, key `['latestItinerary']` of §7.4).
- `apps/web/tests/unit/trips/TripWizard.test.tsx`: a new block "TripWizard drafts" with autosave status, Not saved and Retry, resume at the first incomplete step with the form restored, and a missing draft.
- `apps/web/tests/unit/trips/dashboard.test.tsx` (created): Open latest with and without an itinerary, the Draft badge with Continue draft, and no trips.
- `docs/progress/parts/IMP-410-draft-resume-ui.md`: this record.

## Commands

| Command | Result |
| --- | --- |
| `make test-web ARGS='TripWizard'` (run as `npx vitest run tests/unit/trips`) | `Tests  14 passed (14)` |
| `make test-web ARGS='dashboard'` (run as `npx vitest run tests/unit/trips/dashboard`) | `Tests  4 passed (4)` |
| `make test-web` | `Tests  127 passed (127)` |
| `make lint` | `All checks passed!`; ESLint `✖ 1 problem (0 errors, 1 warning)`, a warning that predates this run; `All matched files use Prettier code style!` |
| `make typecheck` | `Success: no issues found in 111 source files` (web tsc clean) |

Not run: screenshots at 375 px and 1280 px, because no local stack runs here (no Docker); the operator adds them to the PR. `make e2e` was not run, because it needs the composed stack.

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-013 AC1, web side: the wizard stores the draft as each step is left and says so | verified | "TC-085: autosave reports Saving… then Draft saved in a polite status line" |
| FR-013 AC2, web side: a draft opened later is restored | verified | "TC-086: a draft reopens at its first incomplete step with the form restored"; dashboard "Continue draft" test |
| FR-014 AC1, web side: Open latest opens the newest itinerary | verified | dashboard "TC-087: Open latest opens the newest saved itinerary" |
| FR-014 AC2, web side: with none, generation is offered, not an error | verified | dashboard "TC-088: … offers Plan a trip, not an error" (no `role="alert"`) |

## Proposed decisions

- **PD-IMP-410-4 (autosave timing):** card step 2 asks for autosave "on step change, debounced 1 s", and the run design says never to block the next step on autosave. The wizard saves when a step is left (PD-IMP-212-2), and a step change already marks the save, so a 1 s debounce adds nothing. The next step still waits for its save, because Details must create the trip before Preferences can be saved, and a 422 has to be shown on the fields. The status line and Retry are built as designed. Proposed: accept "save on leaving a step" as the FR-013 autosave.
- **PD-IMP-410-5 (resume route and files):** a draft resumes at `/trips/new?draft=<id>` rather than a new route, to keep the route table unchanged. `TripDetailsStep.tsx` and `trips/new/page.tsx` are not in the card's Files list. Proposed: add them.
- **PD-IMP-410-6 (API-09 none case):** API-09 returns 200 with `trip_id: null` when there is nothing to open (§6, IMD-122; see PD-IMP-410-1), not 404. The dashboard treats `trip_id: null` as the case for the "No saved itinerary yet" EmptyState.
- **PD-IMP-410-7 (TripCard):** no TripCard exists yet (IMP-602 builds the trip list). The dashboard shows a minimal card for drafts only. IMP-602 should replace it with TripCard and keep the "Draft" badge and "Continue draft" action.

## Blockers and open issues

None.
