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
