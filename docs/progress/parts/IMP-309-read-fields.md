# IMP-309 · read-fields part

- Run id: RUN-050 (grouped, IMD-121, with the IMP-309 day-view part and IMP-314)
- Owner: Het (het-lathiya)
- Status: PR_OPEN
- Base commit: 1681b41
- Branch: feat/IMP-309-314-itinerary-guides
- Reviewer: Kirtan (kirtan-S111)
- Traces to: US-068; FR-059; NFR-002; TC-195
- Card steps built: 1

## Changed files

- `apps/api/app/itinerary/repository.py`: `current_warnings` reads `itinerary_warnings` of the current `plan_revision`; `latest_version_id` now filters by `plan_revision`.
- `apps/api/app/itinerary/service.py`: `findings` comes from those rows; `version_id` follows §5.9 (the newest version of the current revision, else null).
- `apps/api/app/itinerary/router.py`: docstring.
- `apps/api/tests/api/test_itinerary.py`: TC-195, findings of the current revision only, null `version_id`.

Everything else the card's step 1 lists was already built by IMP-211 and IMP-308. `schemas.py` did not need a change, so API-24 keeps its declared shape.

## Commands

`make db-up`, then `make check` with all four parts of RUN-050 in the tree, on `pgvector/pgvector:pg16`.

| Command | Result |
| --- | --- |
| `make test-api ARGS='-k itinerary'` | `21 passed, 305 deselected, 1 warning` |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |
| `make check` | exit 0: unit `755 passed, 1 warning`; contract `87 passed, 2 deselected, 1 warning`; api `326 passed, 1 warning`; authz `31 passed`; web `Tests  105 passed (105)`. Run before two comment-only edits |

## Acceptance

| Criterion | Status | How |
| --- | --- | --- |
| FR-059 AC1, TC-195: each day lists items in time order | verified | `test_tc_195_each_day_lists_its_items_in_time_order` |
| API-24 as declared in contract v1 | verified | `make openapi-check`, no contract file changed |
| Warnings of the current `plan_revision` | verified | `test_findings_are_the_warnings_of_the_current_revision_only` |
| Owner-only: another user gets 404 | verified | `test_tc_064_another_users_itinerary_answers_like_a_missing_trip`, authz suite |

## Blockers

None.

## Proposed decisions

None.

## Open issues

- **Findings are empty on real plans for now.** No code writes `itinerary_warnings` yet, so API-24 returns `[]` until IMP-405. The read path is tested with inserted rows.
- **Fallback plans and note origin.** `replace_plan` sets `origin="model"` and `note_origin="ai"` for any note. Once a fallback plan is saved through it (IMP-402, IMP-403), that needs to change, or its template notes would carry AiBadge (§7.8).
