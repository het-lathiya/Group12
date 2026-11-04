# IMP-213 · whole-task part

- Run id: RUN-036b (fix of RUN-036, which was blocked on the 409 generation id; resolved by IMD-119)
- Owner: Krrish (Assassin-byte)
- Status: PR_OPEN
- Base commit: 3965122
- Branch: feat/IMP-213-whole-task
- Reviewer: Manasvi (Manasvi1704)
- Traces to: US-153; FR-024, FR-025; IMD-12, IMD-21, IMD-118, IMD-119
- Card steps built: 1 to 6, narrowed by the run prompt (mode `ai` only; outcome notices, privacy notice and labels are left to IMP-305, IMP-308, IMP-309 and IMP-403)

## Changed files

Card files:

- `apps/web/app/(app)/trips/[tripId]/generate/page.tsx` (created). The generate page (§7.5.6).
  - "Generate with AI" sends API-22 with `{mode: "ai"}` (IMD-21).
  - A ref stops a second click that lands before React re-renders the disabled button. The button shows `Loader2` and `aria-busy` while the request is in flight. It stays disabled while a generation is shown.
  - The generation id goes into `?generation=<id>` (`router.replace`), so a reload resumes polling.
  - A 409 `GENERATION_IN_PROGRESS` reads the `details` entry whose `field` is `generation_id` (IMD-119), puts that id in the URL and polls it.
  - If the 409 has no such entry, the page shows the envelope's message in `ErrorState` with a "Reload" button. Other errors show `ErrorState` with the request ID and "Try again".
- `apps/web/components/generation/GenerationProgress.tsx` (created). Polls API-23 through `useGeneration`.
  - Shows the steps Queued, Running and Validating. Repairing appears once the status reaches it (`status` repairing or `repair_attempts > 0`). If the status goes back to validating after a repair, Repairing shows as done.
  - The current step is in primary with a spinner, finished steps have a `Check`, and upcoming steps are muted. Each step also carries a screen-reader state.
  - "Elapsed m:ss" in tabular figures. Status changes, not the counter, are announced in an `aria-live="polite"` region.
  - `completed`: invalidates `trip`, `itinerary`, `costs` and `trips` (§7.4), shows "Plan ready. Opening your itinerary." (success soft) and navigates to the itinerary.
  - `failed`: a destructive-soft alert with API-23's `failure_message` and "Try again", which starts a new generation. Other `next_action` values are left to IMP-403.
  - Not ended 160 s after the page started watching: polling stops, and a warning-soft alert says "Connection problem. Reload the page." with "Reload" (IMD-12).
  - A read error before any status arrives shows `ErrorState` with a retry.
- `apps/web/app/(app)/trips/[tripId]/itinerary/page.tsx` (created). The read-only itinerary (§7.5.7) from API-24.
  - Below 768 px: day tabs (one day at a time).
  - From 768 px: stacked day cards.
  - From 1024 px: a sticky 240 px day index with "Day 1 · Sat 14 Nov" links that focus the day card (and so scroll to it).
  - Only one layout is rendered (`matchMedia` through `useSyncExternalStore`), so ids and headings are not repeated.
  - Loading: two skeleton day cards with three item rows each.
  - A 404, or a plan with no days: `EmptyState` "Nothing planned yet" with a link to the generate page. Other errors: `ErrorState` with the request ID and "Try again".
- `apps/web/components/itinerary/DayColumn.tsx` (created). The day card of guide §14: the overline "Day 1" and the date as the h2 ("Sat 14 Nov", read in UTC so the date-only string never shifts), then the items in API order.
- `apps/web/components/itinerary/ItineraryItemCard.tsx` (created). The guide's timeline row: a 56 px time column with `start_time` as given, a thin rule, and a card with the place name (16 px semibold) and "1 h 30 min · <slot badge>" (outline pill).
- `apps/web/tests/unit/generation/GenerationProgress.test.tsx` (created). 8 tests, listed below.

Files the run prompt adds:

- `apps/web/lib/api/queries.ts` (modified; hooks live here, PD-IMP-212-3):
  - `useStartGeneration` (API-22; seeds `['generation', id]` with the 202 body);
  - `useGeneration` (API-23; `refetchInterval` 2, 3, 4, then 5 s from `dataUpdateCount`; off when ended, when `poll` is false or after a read error with no data; `staleTime: Infinity`, so a status seeded from the 202 waits the first 2 s);
  - `useItinerary` (API-24, key `['itinerary', tripId, 'current']`; a 404 is not retried).
- `apps/web/app/globals.css` (modified): `--radius-lg: 0.5rem` (step D, see the open issues).

Extra files:

- `apps/web/app/(app)/layout.tsx` (modified): `<Suspense>` around `AuthGuard`, with the guard's own loading skeleton as the fallback. Without it, `next build` fails on both new routes (see "Commands run"). The cause is that AuthGuard reads `usePathname()`, which a dynamic route knows only at request time under `cacheComponents`. `/dashboard` and `/trips/new` stay fully static (○ in the build output).
- `apps/web/components/ui/tabs.tsx` (created): shadcn Tabs over the installed `radix-ui` package, for the day tabs. Triggers are at least 44 px high and show the guide's focus ring. No dependency was added.
- `apps/web/tests/unit/itinerary/DayColumn.test.tsx` and `ItineraryItemCard.test.tsx` (created), with the shared SAMPLE item fixture in `apps/web/tests/unit/itinerary/fixtures.ts` (created).
- `docs/progress/parts/IMP-213-screens/` (8 screenshots, below).

`EmptyState`, `ErrorState` and `LoadingSkeleton` already exist under `components/states/` and were reused unchanged. The itinerary skeleton is built in the page from `Skeleton`, because `LoadingSkeleton` has no day-card shape.

No API, contract, migration, backend or environment file changed. `make openapi-check` passes with no change.

## Screenshots

`docs/progress/parts/IMP-213-screens/`, at 360 and 1280 px:

- `1-generate-idle-{360,1280}.png`
- `2-generate-running-{360,1280}.png`
- `3-generate-completed-{360,1280}.png`
- `4-itinerary-{360,1280}.png` (day tabs at 360; day index and two columns at 1280)

They were taken with a throwaway Playwright spec against the local stack and the API with `AI_PROVIDER=MOCK`. The spec was deleted after the run, because the journey e2e belongs to IMP-216.

The MOCK job finishes within one poll. For the running frame, the spec rewrote API-23's `status` to `running`. For the completed frame, it held the itinerary navigation until the screenshot was taken. A second test in the same spec, without any interception, pressed Generate and checked the 202, the progress card, the URL `/trips/{id}/itinerary` and the "Day 1 Sat 14 Nov" heading (US-153 AC1) at both widths.

The Next.js dev indicator was hidden in the screenshots.

## Commands run

The e2e evidence used the local stack:

- `make stack-up`, `make db-migrate`, `make seed`;
- the API on port 8000 with `AI_PROVIDER=MOCK`;
- the stack's values from `supabase status -o env`, exported into each command's environment only, with `SUPABASE_JWKS_URL=<API_URL>/auth/v1/.well-known/jwks.json` as in IMP-212. Nothing was printed or written to a tracked file, and the untracked env files were not opened.

`make stack-down` was run at the end. `make db-up` was run before each `make check`, and `make db-down` after it.

| Command | Result |
| --- | --- |
| `make test-web ARGS='GenerationProgress'` | `Test Files  1 passed (1)`, `Tests  8 passed (8)` |
| `make test-web ARGS='DayColumn ItineraryItemCard'` | `Test Files  2 passed (2)`, `Tests  8 passed (8)` |
| `make seed` (local stack) | `seed sampleton: places inserted 0, updated 0, unchanged 30, deactivated 0` |
| `npx playwright test <throwaway spec> trip-create --project=chromium-360 --project=chromium-1280` | `6 passed (16.9s)` (the existing `trip-create` journey still reaches the generate page) |
| `npx playwright test <throwaway spec> --project=chromium-360 --project=chromium-1280` (final screenshots) | `4 passed (13.3s)` |
| `npx next build` (before the layout change) | failed: ``Route "/trips/[tripId]/generate": Next.js encountered URL data `usePathname()` in a Client Component outside of `<Suspense>`.`` at `components/shell/AuthGuard.tsx:41` |
| `npx next build` (with `export const instant = false` in a `trips/[tripId]` layout, since removed) | failed on both routes: `The server render could not complete because client rendering was requested outside a Suspense boundary.` |
| `npx next build` (with `<Suspense>` in `(app)/layout.tsx`) | `✓ Generating static pages using 12 workers (11/11) in 1090ms`; `/trips/[tripId]/generate` and `/trips/[tripId]/itinerary` are `◐ (Partial Prerender)` |
| `make check` (final) | exit 0. Lint: `All checks passed!`, `139 files already formatted`, `✖ 1 problem (0 errors, 1 warning)` (the existing `window.location.assign` warning in `lib/api/client.ts`), `All matched files use Prettier code style!`. Types: `Success: no issues found in 85 source files`, `✓ Types generated successfully`. Imports: `Contracts: 4 kept, 0 broken.`. Contract: `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date`. Tests: unit `385 passed, 1 warning in 9.35s`, contract `35 passed, 1 warning in 0.90s`, api `231 passed, 1 warning in 51.95s`, authz `28 passed in 12.75s`, web `Test Files  14 passed (14)`, `Tests  80 passed (80)` |

Failures on the way, all in the test harness:

- With vitest's default fake timers, every test timed out. Testing Library's `asyncWrapper` waits on a `setTimeout(0)` that it only advances for Jest.
- Fake `setTimeout` also lost TanStack Query's store notification on the 409 path: one render, never updated, while the cache held the status. The same case passed on real timers.
- The test now fakes only `setInterval`, `clearInterval` and `Date` (the clocks under test). It uses `fireEvent`, because user-event waits on timers.
- The double-click test was checked against the code: with the ref guard removed it fails (`× a double click starts one generation only`).
- The first back-off run showed an immediate poll after the 202, because the test client has `staleTime` 0. `useGeneration` now sets `staleTime: Infinity` itself instead of relying on the app's 30 s default.

## GenerationProgress tests

| Test | Shows |
| --- | --- |
| US-153 AC1: Generate shows the steps and opens the itinerary on completed | URL gets `?generation=<id>`; Queued, Running, Validating become current in turn; elapsed counter; no Repairing; success alert; `router.push('/trips/{id}/itinerary')` |
| polls 2 s after the start, then 3, 4 and 5 s, then every 5 s, and stops at the end | Gaps `[2000, 3000, 4000, 5000, 5000, 5000, 5000]` ms; no request after `completed` |
| a failed generation shows failure_message and Try again starts a new one | Alert with `failure_message`; no navigation; "Try again" sends a second API-22 and watches the new id |
| IMD-12: still running after 160 s shows the reload message and stops polling | No alert at 159 s; at 160 s "Connection problem. Reload the page." and "Reload"; no request in the next 30 s |
| a double click starts one generation only | One API-22 for two clicks; the button is disabled |
| IMD-119: a 409 GENERATION_IN_PROGRESS resumes polling the generation it names | URL gets the id from `details`; API-23 is called for that id only; its status is shown; no alert |
| a 409 without the generation id shows the message and Reload, without guessing | The envelope message, "Reload", no API-23 call, no URL change |
| a reload with ?generation= resumes polling without starting another | No API-22; API-23 for the URL id; Repairing current; button disabled |

Each API-22 body is checked to be exactly `{mode: "ai"}`.

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| Pressing Generate with MOCK shows progress and then the saved itinerary (US-153 AC1) | verified | Unit test 1; Playwright against the local stack with MOCK and no interception, at 360 and 1280 px (202, progress card, itinerary URL, "Day 1 Sat 14 Nov" heading) |
| Double click starts one generation only | verified | Unit "a double click starts one generation only" (fails when the guard is removed) |
| A failed generation shows the reason and a retry button; a status still running after 160 s shows the reload message (unit test) | verified | Unit tests "a failed generation…" and "IMD-12: still running after 160 s…" |
| No time, price or route is computed in the browser (code review checklist item) | verified | The pages render `start_time`, `duration_min`, the place name and `slot_type` as sent. `end_time`, `cost`, `day_cost`, `travel_from_previous`, `theme` and `note` are never read. Only formatting is applied (date as "Sat 14 Nov", duration as "1 h 30 min"). Component tests "never shows a cost, end time, travel time or note" and "never shows the day cost or the theme" use fixtures that carry those fields |
| 409 resume path of §7.5.6 (IMD-119) | verified | Unit "IMD-119: a 409…" and "a 409 without the generation id…" |
| FR-024 as far as this card goes (start a generation for a complete trip) | verified | Unit tests (API-22 body, 202 handling); Playwright 202 against the local API |
| FR-025 as far as this card goes (status polling until an end) | verified | Unit back-off, completed, failed and 160 s tests |
| Polling pauses while the tab is hidden (§7.4) | not verified | TanStack Query's default (`refetchIntervalInBackground` false) is relied on; no test hides the tab |
| Guide C: focus ring, 44 px targets below 640 px, one h1, headings in order | verified by review | New links, tabs and day cards use `focus-visible:ring-2 ring-ring ring-offset-2`; tab triggers and buttons are `min-h-touch`; each page has one h1, with h2 per day (or for Progress) and h3 per item. No automated axe scan (not in the repository, as IMP-212 noted) |

## Blockers

None.

## Proposed decisions

- **PD-IMP-213-1 (the 160 s start):** §7.4 says "160 s after the start". The page counts from when it started watching the generation, not from the server's `created_at`. This keeps the browser's clock out of the comparison. After a reload the count restarts, but the server reaper fails a job at 150 s, so the next poll ends it. Proposed: §7.4 should read "160 s after the page started polling".
- **PD-IMP-213-2 (Files list):** the card's Files list leaves out `lib/api/queries.ts` (as PD-IMP-212-3), `components/ui/tabs.tsx` (the §7.5.7 day tabs need it) and the `(app)/layout.tsx` Suspense boundary (needed for `next build`). Proposed: add them to the card.

## Open issues

- **Radius scale (step D).** Buttons and inputs use `rounded-lg`, which reads `--radius-lg` (12 px before this change). `--radius-md` is not read by default-size buttons or inputs, so `--radius-lg` was set to `0.5rem` (8 px), and no other token changed. Side effects:
  - `rounded-md` (still 9.6 px) is now larger than `rounded-lg`;
  - other `rounded-lg` users also become 8 px: shell nav links, the skip link, the segmented-control track, the dropdown menu panel, and some inner containers;
  - cards use `rounded-xl` (16.8 px), not the guide's 12 px.

  A token pass that sets the scale from one base would fix all three.
- **Foreign trips on the itinerary page.** API-24 answers 404 both when there is no itinerary and when the trip is not the caller's. The page shows "Nothing planned yet" for both. §7.5 asks for the not-found screen with a dashboard link for a foreign trip, which needs `['trip', tripId]` (API-10) first. No hook for it exists yet.
- **Generate after a plan exists.** API-22 answers 409 `CONFLICT` when an itinerary exists (IMD-21). The page shows that message with "Try again". A link to the itinerary, or regeneration (API-31, IMP-607), would serve better.
- **Instant-navigation warning.** `next dev` logs `Could not validate that a segment in your UI has instant navigation` for the two new routes. This is the same development-only warning recorded for `/dashboard` (PD-IMP-109-2) and `/trips/new` (IMP-212).
- **`costs` key.** The only match of `cost` in the new web code is `queryKeys.costs(tripId)`, the §7.4 invalidation on `completed`. It computes nothing.
- **Page titles.** Both pages are client components, which cannot export `metadata`, so they keep the root title "AI Travel Planner".
