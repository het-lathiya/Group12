# IMP-410 · draft-latest-api

| Field | Value |
| --- | --- |
| Run | RUN-058 (grouped run, IMD-121), part 1 of 7 |
| Card | IMP-410 Drafts and reopening the latest saved itinerary |
| Part | Draft trips and latest-itinerary reopening API (2 points) |
| Owner | Manal Patel |
| Status | PR_OPEN |
| Base commit | 16839a0 |
| Branch | feat/IMP-410-411-412-trips-budget-states |

## What existed before this run (preflight step 3)

- API-09 `GET /api/v1/itineraries/latest` was already built (IMP-211) to the §6 shape `{trip_id, plan_revision, updated_at}`, with 200 and nulls when the caller has no itinerary. IMD-122 accepted this (PD-IMP-211-1).
- API-11 `PATCH /api/v1/trips/{trip_id}` was a 501 stub. §6.6.2 traces it to IMP-410 (TC-085, TC-086).
- API-34 `PATCH /api/v1/trips/{trip_id}/budget-settings` was a 501 stub (built in part 2, IMP-411).
- The wizard already saves each step (PD-IMP-212-2). Details creates the draft (API-07), and Preferences and Must-visit places save through API-14. The Details step is locked once the trip exists.
- `app/budget/repository.py` exists with `get_settings` and `upsert_settings` (IMP-308).
- The engine already applies BF-05 and BF-06, with a `traveller_input` label on the transport and accommodation lines (IMP-308, IMD-124 B2).
- The dashboard is a placeholder that shows only an empty state. There is no trip list and no TripCard (IMP-602).

## Changed files

- `apps/api/app/trips/service.py`: adds `update_trip` (API-11). The API-07 field rules move into `_validate` and are shared by API-07 and API-11.
- `apps/api/app/trips/repository.py`: adds `update_trip` (one UPDATE on a trip already read with `get_owned`).
- `apps/api/app/trips/router.py`: API-11 now calls the service instead of answering 501.
- `apps/api/tests/api/test_trips.py`: TC-085, TC-086, plus tests for ready-on-preferences, 422 field rules, 404 for another user and 409 for archived trips.
- `apps/api/tests/api/test_itinerary.py`: the existing API-09 tests are renamed to carry TC-087 and TC-088.
- `apps/api/tests/authz/route_matrix.py`: API-11 is listed as `foreign`.
- `docs/progress/parts/IMP-410-draft-latest-api.md`: this record.

## Behaviour

- API-11 changes only the fields that are sent, and checks the merged trip with the same rules as API-07: title, dates, party size, group needs, budget, an active destination and a budget in the destination's currency. A budget sent as `null` clears it.
- When an itinerary exists, changing the destination, dates, travellers, group needs or budget sets `plan_stale` (FR-011). A title change alone does not.
- An archived trip answers 409 `CONFLICT` to any change except `status`. `status: archived` archives the trip. `status: ready` restores an archived trip to `ready` if it has days, otherwise to `draft` (§5.4). On a draft it changes nothing, because a draft becomes ready only when its preferences are saved (IMD-25).
- Another user's trip answers 404 `NOT_FOUND`, never 403.

## Commands

| Command | Result |
| --- | --- |
| `make lint` | `All checks passed!` (ruff); ESLint `✖ 1 problem (0 errors, 1 warning)`, the warning is older than this run and is in `lib/api/client.ts` |
| `make typecheck` | `Success: no issues found in 110 source files` |
| `make imports` | `Contracts: 6 kept, 0 broken.` |
| `make test-unit` | `872 passed, 1 warning in 21.68s` |
| `make test-web` | `Tests  119 passed (119)` |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` (API-11 was already declared with its final shape) |
| `.venv/bin/pytest tests/authz/test_route_inventory.py` | `7 passed, 1 error`: the error is the one case that needs PostgreSQL |

Not run: `make test-api ARGS='-k draft'`, `make test-api ARGS='-k latest'` and `make test-authz`. This machine has no Docker and no PostgreSQL, so these rely on the CI `api` job.

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-013 AC1 (TC-085): a partly filled trip is stored as a draft with the fields entered so far | not verified locally | `test_tc_085_draft_stores_the_fields_entered_so_far`; runs in the CI `api` job |
| FR-013 AC2 (TC-086): a draft opened later is restored, including after sign-out | not verified locally | `test_tc_086_draft_is_restored_after_sign_out` (a new token for the same user reads API-08, API-10 and API-15); CI `api` job |
| FR-014 AC1 (TC-087): Open latest finds the newest saved itinerary | not verified locally | `test_tc_087_latest_returns_the_callers_most_recently_changed_itinerary_only`; CI `api` job |
| FR-014 AC2 (TC-088): with no itinerary, generation is offered instead of an error | not verified locally | `test_tc_088_latest_is_null_when_the_caller_has_no_itinerary` (200 with nulls); the web side is in part 3 |
| Another user's data is never visible | not verified locally | `test_draft_patch_of_another_users_trip_is_404`, the API-11 row in `route_matrix.py`; CI `api` job |

## Proposed decisions

- **PD-IMP-410-1 (API-09 shape):** card step 3 and the run prompt say 200 `{trip_id, version_id}` or 404 `NOT_FOUND`. §6 API-09 and IMD-122 (PD-IMP-211-1) say 200 `{trip_id, plan_revision, updated_at}`, with `{trip_id: null}` when there is none. The run prompt also says API-09 changes only to match §6, so §6 was kept and API-09 was not changed. The web treats `trip_id: null` as the "no saved itinerary" case. Proposed: align card step 3 with §6.
- **PD-IMP-410-2 (API-11 in IMP-410):** §6.6.2 traces API-11 to IMP-410 (TC-085, TC-086), and card step 1 says "API-11 PATCH saves each wizard step". Building it needed `trips/router.py` and `trips/repository.py`, which the card's Files list leaves out. The `status` field follows §5.4 (archive, restore to ready or draft). The `trip_management` flag guard stays with IMP-602. Proposed: add both files to the card.
- **PD-IMP-410-3 (draft fields):** the API-07 shape must not change in this run, so a draft is stored when the traveller leaves Details, with the fields Details requires. Preferences and must-visit places stay optional until the draft becomes ready (IMD-25). Proposed: FR-013 "partial fields" means a trip without preferences.

## Blockers and open issues

- None blocking.
- Open issue: when API-11 changes a trip's destination, its must-visit places still belong to the old destination. Today the wizard never changes the destination after Details. IMP-510 or IMP-602 should decide whether a destination change clears them.
