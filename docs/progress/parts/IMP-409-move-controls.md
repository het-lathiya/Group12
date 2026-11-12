# IMP-409 · move-controls part

- Run id: RUN-062 (grouped with IMP-408; parts remove-retime-ops, move-op, item-editor, move-controls)
- Owner: Manasvi (Manasvi1704)
- Status: PR open
- Base commit: d7625c7
- Branch: feat/IMP-408-409-remove-retime-move
- Reviewers: Assassin-byte, manalPatel2557
- Traces to: US-069; FR-060; NFR-003, NFR-025; IMD-118
- Card steps built: 2 to 4 (dnd-kit drag and drop, MoveControls with announcements, conflicts in WarningsPanel)

## Changed files

- `apps/web/components/itinerary/MoveControls.tsx` (created):
  - `MoveDndContext`: one DndContext for the whole plan, with pointer and keyboard sensors (`sortableKeyboardCoordinates`), so items move within and across days. It also renders the polite live region (`role="status"`).
  - `SortableDay`: a day's list as a SortableContext and a droppable, so an empty day takes drops too.
  - `SortableItem`: the draggable list item. It builds the grip button where `useSortable` runs.
  - `MoveControls`: the grip, then Move up, Move down, and a "Day to move … to" select with a "Move to day" button. Every control has an aria-label naming the place. Up is disabled at the first position and Down at the last. All controls wait while any edit of the trip is saving.
  - Every action and every drop calls API-26 through `useMoveItem`. No optimistic reordering: the order changes only when the server's answer replaces the plan.
  - After the answer, the live region says "Moved <place> to day N position M" (N and M from the response), and focus stays on the moved item's controls: the same button, or the group's first enabled control when that button is now at an edge.
  - A refused move shows the error catalogue's text in a toast and leaves the order as it was.
  - `dropMove` maps a drop to the API-26 body. Dropped on an item, the dragged item takes that slot. Dropped on another day, it goes after that day's last item. Dropped where it started, nothing is sent.
- `apps/web/components/itinerary/DayColumn.tsx`: with `edit`, the list is a SortableDay of SortableItems, and the day numbers and the item count go to each card. Without `edit` it renders as before.
- `apps/web/components/itinerary/ItineraryItemCard.tsx`: mounts MoveControls under ItemEditor. `ItemEditContext` gained `itemCount` and `dayNumbers`.
- `apps/web/lib/api/queries.ts`: `useMoveItem` on the shared edit helper of the item-editor part (the response replaces days, totals, findings and revision; `itinerary` and `costs` are invalidated together).
- `apps/web/app/(app)/trips/[tripId]/itinerary/page.tsx` (not in the part's list): wraps both day layouts in `MoveDndContext` and passes the trip's day numbers. The drag area has to span every day, and only the page holds them all.
- `apps/web/tests/unit/itinerary/ItemEditor.test.tsx` (not in the part's list): the card's `edit` prop now needs `itemCount` and `dayNumbers`.
- `apps/web/package.json`, `apps/web/package-lock.json`: `@dnd-kit/core` ^6.3.1, `@dnd-kit/sortable` ^10.0.0, `@dnd-kit/utilities` ^3.2.2 (dnd-kit is in the stack, CLAUDE.md §2; card step 2). `npm audit --omit=dev`: `found 0 vulnerabilities`.
- `apps/web/tests/unit/itinerary/MoveControls.test.tsx` (created): 8 cases on the real itinerary page with a fake API-26 that applies the move as the server does.

## Commands and results

PostgreSQL for `make check`: the same throwaway PostgreSQL 16.2 with pgvector (pip `pgserver`) on 127.0.0.1:55432, outside the repository, stopped afterwards.

| Command | Result |
| --- | --- |
| `make test-web ARGS='MoveControls'` (run as `npx vitest run MoveControls`) | `Tests  8 passed (8)` |
| `make test-web` | `Tests  186 passed (186)` (second run; see open issues) |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |
| `make check` | exit 2: lint, typecheck (`Success: no issues found in 116 source files`), imports (`Contracts: 6 kept, 0 broken.`), openapi-check, unit (`1006 passed`), contract (`87 passed, 2 deselected`), api (`421 passed`) and authz (`41 passed`) passed. test-web had `2 failed \| 184 passed (186)`: TripWizard TC-068 timed out at 5000 ms, and a PrivacyNotice heading lookup failed. Both files pass alone (`Tests  22 passed (22)`), and the next full `make test-web` passed 186 of 186 |
| `make lint` | exit 0 (one existing ESLint warning in `apps/web/lib/api/client.ts`) |

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-060 AC1 / TC-197: a drop moves the item; order, times and totals update from the server | verified (drop mapping and server round trip); pointer gesture not verified | `dropMove` cases (dnd-kit's pointer geometry does not run in jsdom); the button cases show the page re-rendering from the API-26 answer. The drag gesture itself is left to the screen recording |
| FR-060 AC2 / TC-198: keyboard move controls give the same result | verified | "moves down with the keyboard only…": Enter on the focused button, PATCH `{plan_revision: 3, day_number: 1, position: 2}`, the new order, the polite announcement, focus kept in the item's controls |
| Move to day and the next revision | verified | "moves to another day with the select…" (PATCH `{day_number: 2}`, then `{plan_revision: 4, …}`) |
| Conflicts after a move appear in WarningsPanel; not hidden or reverted | verified | "does not reorder before the server answers, then shows the conflict in WarningsPanel" |
| No optimistic reordering | verified | the same case: the order is unchanged while the answer is held |
| Keyboard-only reordering without a pointer (TC-374 path) | verified for the move controls | the TC-198 case; the full keyboard journey is IMP-513 |
| 44 px targets at 375 px | not verified | `min-h-touch` and `size-touch` on every control; a check on a device or on screen is left for the member |
| Screenshots or recording | not verified | taken on the local stack by the member after merge |

## Blockers

none

## Proposed decisions

none

## Open issues

- Below 768 px the days are tabs. A move to another day puts the item in a closed tab, so focus cannot follow it there. The announcement still says where it went. Cross-day drag needs both days visible (768 px and up); "Move to day" covers smaller screens.
- Under full-suite load on this machine, `tests/unit/trips/TripWizard.test.tsx` TC-068 sometimes hits its 5000 ms timeout, and once a PrivacyNotice case failed. Neither file is touched by this run, TC-068 also failed with this part's changes stashed, and both pass alone. They were not changed (CLAUDE.md §9).
