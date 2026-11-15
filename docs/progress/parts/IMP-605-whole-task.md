# IMP-605 · whole-task part (Saved places, wishlist)

- Run id: RUN-075
- Owner: Jeel (Jeel Fefar)
- Status: PR_OPEN pending integration (committed on `part/p`; the lead integrates, regenerates OpenAPI and opens the pull request)
- Base commit: a6307c3
- Traces to: US-032; FR-020; NFR-012; TC-103, TC-104, TC-105, TC-345
- Card steps built: 1 to 5

## Changed files

- `apps/api/app/trips/router.py` (not in the card's file list): API-19 `PUT`, API-20 `DELETE` and API-21 `GET /api/v1/trips/{trip_id}/saved-places[/{place_id}]`, appended at the end. Same paths, methods and response shapes as the declared stubs (204, 204, `PlaceSummary[]`).
- `apps/api/app/trips/service.py` (not in the card's file list): `save_place`, `unsave_place`, `list_saved_places` and `place_relations` (appended). All are guarded by the IMD-11 switch `wishlist`: when it is off the routes answer 404 and `place_relations` returns None. A foreign or missing trip answers 404. An archived trip answers 409 (as API-14 does). A place that is not active in the trip's destination answers 422 (field `place_id`). Saving a must-visit place answers 409 CONFLICT and leaves it must-visit. Saving twice keeps one row (unique `trip_id, place_id`). Unsaving deletes only the `saved` row and is idempotent.
- `apps/api/app/trips/repository.py` (not in the card's file list): `place_relations`, `insert_saved` (on conflict do nothing) and `delete_saved` (relation `saved` only), appended.
- `apps/api/app/places/router.py`: the three 501 stubs are removed (they are served by trips/router.py).
- `apps/api/app/places/service.py`: `active_place_summaries` for API-21.
- `apps/api/app/generation/ranking.py`: `c_signal` returns 1 for saved, 0 for rejected and 0.5 otherwise when `RankingContext.relations` is given (wishlist on), and 0 when the switch is off. `build_context(..., relations=)`.
- `apps/api/app/generation/retrieval.py` (not in the card's file list): `ranked_shortlist` passes `trips_service.place_relations(session, trip)` to `build_context`. Must-visit and locked items still come only from relation `must_visit`, so a saved place never becomes one.
- `apps/api/tests/api/test_places.py`: TC-103 (save, idempotent, one row), TC-104 (unsave, idempotent), TC-105 (a saved place is not must-visit; a must-visit place answers 409 and stays must-visit after an unsave), 422 for a place of another destination, inactive or unknown, 404 for another user's trip, 404 with `wishlist` switched off. The tests skip with a reason when `FEATURES_DISABLED` lists `wishlist`.
- `apps/api/tests/unit/generation/test_ranking.py`: signal values with the switch on and off; the total does not change while the pm-2 signal weight is 0.
- `apps/api/tests/authz/route_matrix.py` (block appended): API-19, API-20, API-21 as `foreign` routes (TC-345). `PlaceRouteCase` also fills `{place_id}` with A's must-visit place.
- `apps/web/lib/api/queries.ts` (block `// IMP-605 saved places` appended): `savedPlacesKey`, `useSavedPlaces` (API-21) and `useToggleSavedPlace` (API-19 or API-20; invalidates `['savedPlaces', tripId]`).
- `apps/web/components/places/PlaceCard.tsx`: optional Save toggle (`aria-pressed`, 44 px target, "Save" or "Saved"). It is shown only when `onToggleSave` is passed.
- `apps/web/components/places/SavedPlacesPanel.tsx` (created): the saved list with remove buttons, plus loading, empty and error states. It says that saved places are preferred but are not must-visit places.
- `apps/web/app/(app)/trips/[tripId]/explore/page.tsx`: with `isEnabled("wishlist")` the page shows the panel and passes the toggle to each card; with the switch off neither is shown and API-21 is not called.
- `apps/web/tests/unit/places/PlaceCard.test.tsx`: the page test's fetch stub answers the saved-places path. Three new cases: save with aria-pressed (TC-103), remove from the panel (TC-104), and nothing shown with the switch off.

## Commands run

Database: a throwaway local PostgreSQL 16 with pgvector (`travel_test_p` on 127.0.0.1:55432). `PYTHONPATH=apps/api` was set (see the IMP-604 search-api record).

| Command | Result line |
| --- | --- |
| `make test-api ARGS='-k saved'` (as `.venv/bin/pytest tests/api -k saved`) | `21 passed, 468 deselected in 10.46s` |
| `.venv/bin/pytest tests/api -q` | `489 passed in 149.93s (0:02:29)` |
| `.venv/bin/pytest tests/unit -q` | `1149 passed in 17.11s` |
| `make test-authz` (as `.venv/bin/pytest tests/authz -q`) | `53 passed in 31.65s` |
| `.venv/bin/pytest tests/contract -q` | `1 failed, 90 passed, 2 skipped in 19.48s` (`test_committed_contract_is_current`: expected until `make openapi`) |
| `npx vitest run tests/unit/places` | `Tests  13 passed (13)` (3.4 s wall time) |
| `make lint` | `All checks passed!` (ruff); ESLint `0 errors, 1 warning` (existing warning in lib/api/client.ts) |
| `make typecheck` | `Success: no issues found in 122 source files`; `tsc --noEmit` exit 0 |
| `make imports` | `Contracts: 6 kept, 0 broken.` |

## Not run

- `make e2e` (TC-372, floor journey with `wishlist` off): no Docker on this machine.
- `make openapi`: the lead regenerates the contract once. The three routes now carry the `trips` tag instead of `places`.
- Screenshot of the saved-places panel: no dev server in this run.

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-020 AC1 (TC-103): a saved place appears in the trip's saved list | verified | `test_tc_103_…`; web "saves a place with an aria-pressed toggle" |
| FR-020 AC2 (TC-104): an unsaved place is removed | verified | `test_tc_104_…`; web "removes a saved place from the panel" |
| FR-020 AC3 (TC-105): a ranking signal, never must-visit | verified (signal computed; see the open issue on its weight) | `test_tc_105_…`; `test_signal_is_1_for_saved_…` |
| Duplicate saves create one row; another user's trip answers 404 | verified | `test_tc_103_…` (row count); `test_saved_places_of_another_users_trip_are_404`; authz matrix API-19 to API-21 |
| With `wishlist` off the routes answer 404 and the UI is hidden | verified (API, component); TC-372 not verified (E2E not run) | `test_saved_places_routes_are_404_when_wishlist_is_switched_off`; web "hides the toggle…" |

## Blockers

None.

## Proposed decisions

- PD-RUN-075-P4: API-19 to API-21 live in `trips/router.py` and `trips/service.py` instead of the card's `places/router.py` and `places/service.py`. trips already imports places, so places importing trips would create a module cycle (CLAUDE.md §4 rule 6). trips also owns `trip_places` (one writer). Add trips/router.py, trips/service.py, trips/repository.py and generation/retrieval.py to the file list.
- PD-RUN-075-P5: Repeated PUT. The card says "repeated PUT returns 200 with the same row"; §6.6.3 and the declared contract say 204. Built: 204 every time (no body).
- PD-RUN-075-P6: DELETE of a place that is not saved. The card says idempotent; §6.6.3 says 404. Built: 204 (idempotent).
- PD-RUN-075-P7: PUT on a must-visit place. The card says 409 CONFLICT; §6.6.3 says 204 and the place stays must-visit. Built: 409, and the place stays must-visit.

## Open issues

- The pm-2 weight of the signal is 0 in the MVP (§8.9, IMD-108), so saving a place does not move the score yet. FR-020 AC3 "treated as a preference signal" holds only in form until the team gives the signal a weight (a pm-3 decision).
- API-17's `trip_id` (fills `saved` and `must_visit`) is not built. The places module would have to read trip ownership from trips, which is the same module cycle. The explore page takes the saved state from API-21 instead. Needs a decision: drop `trip_id` from API-17, or move the read.
- `alternatives` (IMP-505, `itinerary/edits.py`) builds its ranking context without relations, so its signal stays 0. This makes no difference while the weight is 0.
