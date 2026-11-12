# RUN-059 · destination-404 part

- Run id: RUN-059 (grouped)
- Owner: Malhar (Malhar1112-v)
- Status: PR open
- Base commit: 8c3997b
- Branch: chore/RUN-059-decisions-and-fixes
- Traces to: IMD-127 (replaces PD-IMP-205-7); §6.2, §6.3; API-16; FR-016

## Changed files

- `apps/api/app/places/service.py`: `search_places` (API-16) first reads the destination with the existing `repository.destination_by_id`. If it is missing or inactive, it raises `NotFound`, which is the §6.3 envelope `404 NOT_FOUND`, "Not found.". Repository queries are unchanged: the place search still reads active places of active destinations only. The router is unchanged and declares no responses, so the OpenAPI contract does not change.
- `apps/api/tests/api/test_places.py`: `test_places_of_an_inactive_or_unknown_destination_are_an_empty_page` became `..._are_404`. Both the inactive and the unknown destination answer 404 `NOT_FOUND` with the same message and details.
- `docs/progress/parts/RUN-059-destination-404.md`: this record.

## Unknown destinations

§6.2 lists API-16 under "Reference data": "inactive destinations and places are invisible (404)". If an unknown `destination_id` kept the empty page while an inactive one answered 404, the response would tell whether an inactive destination exists, which "invisible" rules out. So §6.2 covers the unknown case as well, and both answer 404, the same way §6.2 treats a missing own resource. This replaces the whole of PD-IMP-205-7, which had treated both cases alike as an empty page. No proposed decision is needed. If the team reads §6.2 differently, the change is one condition in `search_places`.

## Commands and results

| Command | Result |
| --- | --- |
| `make test-api ARGS='-k places'` (throwaway local PostgreSQL 16.2 + pgvector, port 55432) | `39 passed, 382 deselected, 1 warning in 16.21s` |
| `make test-authz` (same database; the route matrix calls API-16) | `41 passed in 22.72s` |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |

## Acceptance

| Criterion | Status | How |
| --- | --- | --- |
| API-16 answers 404 `NOT_FOUND` (§6.3 envelope) for an inactive destination | verified | `test_places_of_an_inactive_or_unknown_destination_are_404` |
| Unknown destination follows §6.2 | verified | same test: 404 with the same body as the inactive case |
| Repository queries unchanged (active rows only) | verified | `git diff` touches no repository file; `test_places_hides_inactive_places_and_other_destinations` passes |

## Blockers

None.

## Proposed decisions

None.
