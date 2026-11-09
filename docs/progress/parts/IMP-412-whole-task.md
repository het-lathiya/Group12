# IMP-412 · whole-task

| Field | Value |
| --- | --- |
| Run | RUN-058 (grouped run, IMD-121), part 5 of 7 |
| Card | IMP-412 Loading, empty and error states on every MVP screen |
| Part | Whole task (3 points) |
| Owner | Manasvi Rathore |
| Status | PR_OPEN |
| Base commit | 16839a0 |
| Branch | feat/IMP-410-411-412-trips-budget-states |

## Changed files

- `apps/web/lib/api/errors.ts` (created): `ERROR_CATALOGUE` has one entry per §6.3 code plus `NETWORK`, each with a "what happened" and a "what to do next". `describeError` turns any thrown value into catalogue text:
  - an `ApiError` is described by its code;
  - a caller's `{message}` keeps its own text;
  - any other value, such as a fetch `TypeError`, is shown as a network error without its message or stack.

  JSON or multi-line text is never shown.
- `docs/guides/error-catalogue.md` (created): the same catalogue and the display rules.
- `apps/web/components/states/ErrorState.tsx`:
  - It shows what happened (the page title or the catalogue), the API's safe message, what to do next, and one action (Retry, or `action` for navigation).
  - When the API sent a request ID, a footer shows "Reference: <request_id>" in small monospace with a Copy button.
  - `RATE_LIMITED` adds "Try again in N s".
  - `inline` drops `role="alert"` for errors inside a page that still shows content.
  - `error` now accepts any value, and `ErrorStateError` is kept for existing callers.
- `apps/web/components/states/EmptyState.tsx`: adds an icon (neutral inbox by default, `aria-hidden`) above the title, hint and action.
- `apps/web/components/states/LoadingSkeleton.tsx`: no pulse under `prefers-reduced-motion` (`motion-reduce:animate-none`); the blocks keep the card, row and text shapes.
- `apps/web/components/trips/TripWizard.tsx`, `apps/web/components/costs/BudgetSettingsForm.tsx` and `apps/web/app/(app)/dashboard/page.tsx` (states only): errors shown inside a page that keeps its content are now `inline`.
- `apps/web/tests/unit/states/ErrorState.test.tsx`: rewritten for TC-281, Copy, RATE_LIMITED, inline, no stack or JSON, and catalogue coverage. The run listed it as a new file, but it already existed from IMP-104.
- `apps/web/tests/unit/trips/TripWizard.test.tsx`: the 5xx test expects the inline error and "Reference: req-500".
- `docs/progress/parts/IMP-412-whole-task.md`: this record.

## States on the MVP screens (card step 3)

| Screen | Loading | Empty | Error |
| --- | --- | --- | --- |
| Trip wizard (`/trips/new`, `?draft=`) | skeletons for the draft, preferences, destinations and budget inputs | not applicable (a form) | ErrorState: draft load (page), save (inline), destinations, places |
| Dashboard | card skeletons | "No trips yet" and "No saved itinerary yet" | ErrorState: trips (page), latest (inline) |
| Itinerary | skeletons (IMP-309) | "Nothing planned yet", "Trip not found" | ErrorState with Retry (IMP-309); now uses the catalogue through ErrorState |
| Generate | not changed: the page and `components/generation/**` belong to RUN-057 and IMP-403. Their ErrorState calls pick up the catalogue, footer and Copy button through the shared component, and their tests pass unchanged | | |
| Explore | no explore page exists yet; it adopts the states when it is built (card step 3) | | |

## Commands

| Command | Result |
| --- | --- |
| `make test-web ARGS='ErrorState'` (run as `npx vitest run ErrorState`) | `Tests  8 passed (8)` |
| `make test-web` | `Tests  143 passed (143)` |
| `make lint` | `All checks passed!`; ESLint `✖ 1 problem (0 errors, 1 warning)`, a warning that predates this run; `All matched files use Prettier code style!` |
| `make typecheck` | `Success: no issues found in 111 source files` |

Not run: screenshots at 375 px and 1280 px, because no local stack runs here; the operator adds them.

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-116 AC1 (TC-281): a failed request states what happened and what to do | verified | `ErrorState.test.tsx` "TC-281: shows what happened, what to do next, one action and the reference" |
| No screen shows a raw error object or stack text | verified | "never renders a stack trace or a JSON body" (a TypeError with a stack, a JSON message, an object message). Every screen renders errors only through ErrorState or field messages |
| Error catalogue review recorded (TC-384) | not verified | Krrish fills in the checklist below; TC-384 stays not verified until then |

## Catalogue review checklist (card step 4, for Krrish)

Compare each app message with the catalogue entry it falls under. Fill in the last column (OK, or what to change). Leave this table as the review record in the PR.

| Message location | Code | Catalogue text | OK? |
| --- | --- | --- | --- |
| `components/trips/TripWizard.tsx` "Your draft could not be opened" | NOT_FOUND / any | We could not find that · It may have been deleted or belong to another account. Go back to your trips. | |
| `components/trips/TripWizard.tsx` "Your changes could not be saved" (inline) | INTERNAL / CONFLICT / network | per code | |
| `components/trips/TripWizard.tsx` OFFLINE "The server could not be reached. Check your connection and try again; your input is kept." | network error | The server could not be reached · Check your connection and try again; your input is kept. | |
| `components/trips/TripWizard.tsx` status line "Not saved" + Retry | any | none (status line) | |
| `components/trips/TripDetailsStep.tsx` "Destinations could not be loaded" | any | per code | |
| `components/trips/TripDetailsStep.tsx` root field error (`role="alert"`) | VALIDATION_ERROR | Some details need attention · Check the highlighted fields and try again. | |
| `components/trips/PreferenceForm.tsx` root error (`role="alert"`) | VALIDATION_ERROR | Some details need attention · Check the highlighted fields and try again. | |
| `components/trips/PlacesStep.tsx` "Places could not be searched" | any | per code | |
| `components/costs/BudgetSettingsForm.tsx` "Your budget inputs could not be loaded" | any | per code | |
| `components/costs/BudgetSettingsForm.tsx` "Your budget inputs could not be saved" (inline) | INTERNAL / CONFLICT / network | per code | |
| `components/costs/BudgetSettingsForm.tsx` field "Enter 0 or more, with at most 2 decimal places." | VALIDATION_ERROR | (field message) | |
| `app/(app)/dashboard/page.tsx` "Your trips could not be loaded" | any | per code | |
| `app/(app)/dashboard/page.tsx` "Your latest itinerary could not be found" (inline) | any | per code | |
| `app/(app)/trips/[tripId]/itinerary/page.tsx` "Your itinerary could not be loaded" | INTERNAL / network | per code | |
| `app/(app)/trips/[tripId]/generate/page.tsx` "The generation could not start" | GENERATION_IN_PROGRESS / AI_QUOTA_REACHED / RATE_LIMITED / network | per code | |
| `components/generation/GenerationProgress.tsx` "The generation status could not be read" | any / network | per code | |
| `components/generation/GenerationProgress.tsx` failed and timed-out generation messages (`role="alert"`) | none (generation outcome, §6.4) | none (not an HTTP error) | |
| `components/generation/PrivacyNotice.tsx` error (`role="alert"`) | any | per code | |
| `components/auth/SignInForm.tsx` and `SignUpForm.tsx` errors (`role="alert"`) | none (Supabase Auth, not the API) | none | |
| `lib/api/client.ts` `OFFLINE_MESSAGE` and the generic "Something went wrong. Please try again." for non-envelope responses | network error / INTERNAL | per code | |

## Proposed decisions

- **PD-IMP-412-1 (NOT_IMPLEMENTED in the catalogue):** card step 1 lists eleven codes plus network error. §6.3 also has `NOT_IMPLEMENTED` (temporary, IMD-37), and the generated `ErrorCode` type includes it, so it has an entry. Proposed: add it to the card's list until SG-6.
- **PD-IMP-412-2 (API message shown):** ErrorState shows the API's `message` (§6.3: safe to show) between the catalogue's two lines, so specific causes such as "This trip is archived" are not lost. Proposed: accept.
- **PD-IMP-412-3 (test file):** `ErrorState.test.tsx` already existed, so it was rewritten rather than created.

## Blockers and open issues

- TC-384 waits for Krrish's review of the checklist above.
