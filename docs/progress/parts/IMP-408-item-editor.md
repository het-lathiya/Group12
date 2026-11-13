# IMP-408 · item-editor part

- Run id: RUN-062 (grouped with IMP-409; parts remove-retime-ops, move-op, item-editor, move-controls)
- Owner: Manasvi (Manasvi1704)
- Status: PR open
- Base commit: d7625c7
- Branch: feat/IMP-408-409-remove-retime-move
- Reviewers: Assassin-byte, manalPatel2557
- Traces to: US-070, US-072; FR-061, FR-063; NFR-003; IMD-26, IMD-118
- Card steps built: 4 and 5 (ItemEditor with ConfirmDialog and Toast; mutations apply the server response)

## Changed files

- `apps/web/components/itinerary/ItemEditor.tsx` (created): an Edit action opens Start time (HH:MM) and Duration (minutes) fields inside the card. react-hook-form with a zod schema that mirrors `ItemPatchIn` (HH:MM, whole minutes 15 to 480). Field errors sit under the field, linked by `aria-describedby`. Save sends only the changed fields to API-26; Cancel sends nothing. Server 422 details map onto the fields; other refusals show the error catalogue's text (IMP-412) in an alert. Remove is a destructive button that opens ConfirmDialog ("Remove <place> from day N?", Cancel / Remove), then calls API-27 with `?plan_revision=N`. The item stays visible and shows "Removing…" until the server answers; then a "Removed <place>" toast (sonner). The card has `aria-busy` while saving, and every edit button waits while any edit of the trip is saving. Focus returns to the card after save or cancel, and moves to the neighbouring card after a removal (the removed card no longer exists). Buttons and inputs are at least 44 px high (`min-h-touch`).
- `apps/web/components/states/ConfirmDialog.tsx` (created): the shared ConfirmDialog of §7 (`states/*.tsx`), built on `components/ui/dialog.tsx`.
- `apps/web/lib/api/queries.ts`: `useRetimeItem`, `useRemoveItem` and `useAddItem` on one `useItemEdit` helper. On success the response's changed days, totals, findings and plan_revision replace those in the `["itinerary", tripId, "current"]` cache entry, then `["itinerary", tripId]` and `["costs", tripId]` are invalidated together. No optimistic update and no client-side recalculation. On 409 STALE_PLAN both are refetched (§7.4). `EDIT_UNDO_ENABLED = false` and `editKey(tripId)` (the shared mutation key).
- `apps/web/components/itinerary/ItineraryItemCard.tsx`: an optional `edit` prop (`tripId`, `planRevision`, `dayNumber`) mounts ItemEditor in the card. Without it the card stays read-only, so the existing card tests are unchanged.
- `apps/web/components/itinerary/DayColumn.tsx` (not in the part's list): passes an optional `edit` context to each card. This is needed to mount the editor.
- `apps/web/app/(app)/trips/[tripId]/itinerary/page.tsx` (not in the part's list): passes `tripId` and the current `plan_revision` to DayColumn. This is needed to mount the editor.
- `apps/web/tests/unit/itinerary/fixtures.ts` (not in the part's list): `planWith`, `ITEM_B` and `TRIP_ID` SAMPLE fixtures, shared with the MoveControls test.
- `apps/web/tests/unit/itinerary/ItemEditor.test.tsx` (created): 8 cases.

## Commands and results

| Command | Result |
| --- | --- |
| `make test-web ARGS='ItemEditor'` (run as `npx vitest run ItemEditor`) | `Tests  8 passed (8)` |
| `make test-web` | `Tests  178 passed (178)` |
| `make lint` | exit 0 (one existing ESLint warning in `apps/web/lib/api/client.ts`, not from this part) |
| `make typecheck` | `Success: no issues found in 116 source files`; web `tsc` clean |
| `make imports` | `Contracts: 6 kept, 0 broken.` |
| `make test-unit` | `1006 passed, 1 warning` |

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-061 UI: remove with confirmation | verified | "removes only after confirmation…": no request before confirming, DELETE with `plan_revision=7`, item kept and "Removing…" shown until the answer, then the toast; "sends nothing when the removal is cancelled" |
| FR-063 UI: retime with validation | verified | "refuses a duration outside 15 to 480…" (field error linked by aria-describedby, nothing sent); "mirrors the server's rules"; "saves a retime through API-26…" (body is only the changed field) |
| Totals on the page after an edit equal the API response values | verified | the retime and remove cases assert that the itinerary cache's `totals` equal the response's `SERVER_TOTALS` after the edit |
| Server errors through the error catalogue | verified | "shows a server refusal through the error catalogue…" (409 STALE_PLAN text) |
| Focus returns to the card after save or cancel | verified | the save and cancel cases check `document.activeElement` |
| 44 px touch targets at 375 px | not verified | `min-h-touch` on every control; a check on a device or on screen is left for the member after merge |
| Screenshots or recording | not verified | taken on the local stack by the member after merge |

## Blockers

none

## Proposed decisions

- PD-IMP-408-1: removal undo. Card step 4 asks for undo through API-25 "when available". API-25 is IMP-504 (Sprint 5) and still answers 501 on main. The undo call (place_id, day_number, start_time, plan_revision from the remove response) is built behind `EDIT_UNDO_ENABLED = false` in `lib/api/queries.ts`. While it is false the toast offers no Undo. The DELETE is never delayed and the item is never hidden before the server answers. IMP-504 sets it to true.

## Open issues

- The itinerary page has no totals display yet. The totals check is on the itinerary cache the page reads, which holds the response values.

## Fix RUN-063b

| Field | Value |
| --- | --- |
| Run | RUN-063b (fix on PR #272, branch `feat/IMP-414-journey`) |
| Owner | Manasvi Rathore |
| Status | PR_OPEN |
| Base commit | ee905c7 |

**Defect.** Found by the IMP-414 journey in CI (RUN-063). After a confirmed removal, API-27 answered 200, but the toast `Removed <place>` never appeared and focus did not move. `useItemEdit`'s own `onSuccess` writes the changed day into the cache, so the removed card and its `ItemEditor` unmount while the hook awaits the refetch. TanStack Query v5 then skips the per-call `onSuccess` passed to `remove.mutate(...)`, because its observer has unmounted.

**Fix.**

- `apps/web/lib/api/queries.ts`: `useItemEdit` takes an optional `after(result, variables)`, which runs in the hook-level success path right after the cache write. That path runs even when the caller has unmounted. `useRemoveItem` accepts an `onRemoved` callback in its variables and calls it from there. The cache write is not delayed, and nothing is hidden before the server answers (IMD-157).
- `apps/web/components/itinerary/ItemEditor.tsx`: the toast and the focus move are passed as `onRemoved`. Before the request, the card records the next card's id, else the previous card's, else the day heading. After the re-render, focus goes to the first of these that exists. The error toast stays a per-call `onError`, because the card stays mounted when a removal fails. Undo stays off (`EDIT_UNDO_ENABLED = false`, IMD-157).
- `apps/web/components/itinerary/DayColumn.tsx`: the day heading `h2` gets `tabIndex={-1}`, so it can take focus when a removal empties the day.
- `apps/web/tests/unit/itinerary/ItemEditor.test.tsx`: a new case, "after a removal unmounts the card, says so and moves focus to the next card (FR-061)". It renders the day through `useItinerary`, `MoveDndContext` and `DayColumn`, as the page does. The fake refetch after the edit takes 100 ms, as a network would. The test checks that the card is gone, the toast text is shown, no Undo button exists and the next card has focus. The other eight cases, including retime save and cancel focus, are unchanged.

**Commands**

| Command | Result |
| --- | --- |
| New test on the old `queries.ts`, `ItemEditor.tsx` and `DayColumn.tsx` (`npx vitest run tests/unit/itinerary/ItemEditor.test.tsx`) | `Tests  1 failed \| 8 passed (9)`: `Unable to find an element with the text: Removed Old Mill Museum (sample)` |
| `make test-web ARGS='ItemEditor'` (with the fix) | `Tests  9 passed (9)` |
| `make test-web` | `Tests  187 passed (187)` |

**Acceptance**

| Criterion | Status | How |
| --- | --- | --- |
| FR-061 UI: after a removal, the toast shows and focus moves to the next card although the card unmounts | verified | the new unit case, which fails on the old code; the IMP-414 journey in CI (see `IMP-414-journey-staging.md`, Fix RUN-063b) |
| Focus falls back to the previous card, then to the day heading | not verified by a test | the code path is in place; only the next-card case is tested |
| Retime toast and focus unchanged | verified | the existing retime save and cancel cases pass |
