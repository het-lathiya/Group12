# IMP-316 · saved-sources part

- Run id: RUN-051 (one branch for the card, IMD-66, with the IMP-316 grounding part)
- Owner: Het (het-lathiya)
- Status: PR_OPEN
- Base commit: 85137d3
- Branch: feat/IMP-316-grounded-generation
- Reviewer: Nidhi (Nidhi9864)
- Traces to: US-165; FR-138, FR-139; TC-456; IMD-110; Amendment A1 §5.5, §6.10, §7.1
- Card steps built: 9 and Het's tests of step 10

## Changed files

- `apps/api/app/itinerary/schemas.py`: `PlannedItem.source_chunk_ids`. `SourceRef` and `Item` are unchanged, so contract v1 is too.
- `apps/api/app/generation/schedule.py`: step 9 carries the citations that step 8 validated (not in the card's file list, see PD-IMP-316-6).
- `apps/api/app/itinerary/repository.py`: `replace_plan` writes `source_chunk_ids` to the item and to the `snap-1` item as strings; only a plan with origin `model` keeps its notes.
- `apps/api/app/itinerary/service.py`: API-24 fills `sources[]` from one `resolve_sources` call for the whole plan, in the saved citation order.
- `apps/api/app/rag/service.py`, `apps/api/app/rag/repository.py`: `resolve_sources` and `source_rows`, one query over chunk, document and data source.
- `apps/api/tests/api/test_itinerary.py`: TC-456 and the tests below. `tests/unit/validation/test_injection_cases.py`: the item field list gains `source_chunk_ids`.

## Commands

`make db-up`, then these commands with both parts of the card in the tree and `TEST_DATABASE_URL` on `pgvector/pgvector:pg16`.

| Command | Result |
| --- | --- |
| `make test-api ARGS='-k itinerary'` (TC-456) | `29 passed, 305 deselected, 1 warning` |
| `make check` | exit 0: unit `795 passed, 1 warning`; contract `87 passed, 2 deselected, 1 warning`; api `334 passed, 1 warning`; authz `31 passed`; web `Tests  105 passed (105)` |
| `make e2e ARGS='journey'` (steps of `.github/workflows/e2e.yml`, `BASE_URL=http://localhost:3000`, `PROMPT_TEMPLATE_VERSION=v2`) | `4 passed (7.3s)` |

## Acceptance

| Criterion | Status | How |
| --- | --- | --- |
| FR-139 AC1, TC-456: API-24 returns `sources` with all `SourceRef` fields | verified | `test_tc_456_the_itinerary_returns_sources_with_every_source_ref_field` |
| TC-456: saved IDs are a subset of the passages supplied to that generation | verified | `test_tc_456_saved_ids_are_a_subset_of_the_passages_supplied` |
| TC-456: a foreign trip still answers 404 | verified | `test_tc_456_a_foreign_trip_still_answers_404_with_sources_saved` |
| FR-138 AC3: the saved plan records each item's citations | verified | The two tests above, `test_the_snapshot_items_carry_their_citations` |
| Inactive chunks resolve, missing IDs are skipped | verified | `test_an_inactive_chunk_resolves_and_a_missing_id_is_skipped` |
| No N+1: one query however many items cite | verified | `test_sources_are_read_in_one_query_however_many_items_cite` |
| A snapshot without `source_chunk_ids` reads as `[]` | not verified | Nothing reads snapshots yet (IMP-610 builds restore and API-24 by version, which answers 501 today) |
| Edits keep citations; replacing a place clears them | not verified | Those routes answer 501 today (IMP-407, IMP-505); no code path to change |

## API-24 response with sources

From `test_tc_456`'s set-up on the SAMPLE index, with MOCK; the first two items of day 1. All place and source values are the synthetic SAMPLE fixture.

<details><summary>Response</summary>

```json
{
  "trip_id": "21abdd40-d3cc-40ed-b03f-ad72c561efc9",
  "plan_revision": 1,
  "version_id": "ac68582d-b155-4a46-8843-2c612df8d4b2",
  "is_current": true,
  "plan_stale": false,
  "source": {
    "generation_id": "4ea809c1-b231-42b5-9771-aa097e2d7f2f",
    "provider": "MOCK",
    "outcome": "model"
  },
  "days": [
    {
      "day_number": 1,
      "date": "2026-12-04",
      "theme": "SAMPLE day 1: Sample Museum of Small Things (sample)",
      "theme_origin": "ai",
      "items": [
        {
          "id": "183915b5-1696-44c7-8b5d-b14e9c868d60",
          "position": 1,
          "place": {
            "id": "8eded052-d915-4544-aa5f-30aeefe2e81a",
            "name": "Sample Museum of Small Things (sample)",
            "category": "museum",
            "lat": 53.9,
            "lon": 2.135,
            "hours_label": "estimate"
          },
          "slot_type": "activity",
          "start_time": "09:00",
          "duration_min": 90,
          "end_time": "10:30",
          "origin": "model",
          "is_locked": false,
          "must_visit": false,
          "note": "SAMPLE note from the mock provider: visit Sample Museum of Small Things (sample).",
          "note_origin": "ai",
          "cost": {
            "min": "12.00",
            "max": "18.00",
            "currency": "GBP",
            "label": "estimate"
          },
          "travel_from_previous": null,
          "sources": [
            {
              "chunk_id": "cc1f49b4-27ac-4b2e-a651-9dcc62919ad5",
              "kind": "place",
              "title": "Sample Museum of Small Things (sample)",
              "source_name": "SAMPLE fixture (synthetic)",
              "licence": "synthetic test data",
              "attribution_text": "Synthetic SAMPLE data for automated tests; not a real place.",
              "url": null,
              "retrieved_on": "2026-10-31"
            }
          ]
        },
        {
          "id": "73381fc9-c199-44a2-8b7f-276c8bb302b0",
          "position": 2,
          "place": {
            "id": "aeb8b3dd-693c-4750-a2a2-4381a2055b88",
            "name": "Sample Maritime Museum (sample)",
            "category": "museum",
            "lat": 53.908,
            "lon": 2.14,
            "hours_label": "estimate"
          },
          "slot_type": "activity",
          "start_time": "11:02",
          "duration_min": 120,
          "end_time": "13:02",
          "origin": "model",
          "is_locked": false,
          "must_visit": false,
          "note": "SAMPLE note from the mock provider: visit Sample Maritime Museum (sample).",
          "note_origin": "ai",
          "cost": {
            "min": "16.00",
            "max": "24.00",
            "currency": "GBP",
            "label": "estimate"
          },
          "travel_from_previous": {
            "minutes": 17,
            "distance_m": 948,
            "mode": "walking",
            "source": "fallback_estimate"
          },
          "sources": [
            {
              "chunk_id": "c1fb876b-d27f-4e63-8c5a-af5f1320940d",
              "kind": "place",
              "title": "Sample Maritime Museum (sample)",
              "source_name": "SAMPLE fixture (synthetic)",
              "licence": "synthetic test data",
              "attribution_text": "Synthetic SAMPLE data for automated tests; not a real place.",
              "url": null,
              "retrieved_on": "2026-10-31"
            }
          ]
        }
      ],
      "day_cost": {
        "min": "52.00",
        "max": "84.00",
        "currency": "GBP",
        "complete": false
      }
    }
  ],
  "findings": [],
  "totals": {
    "currency": "GBP",
    "estimate": {
      "min": "154.00",
      "max": "296.00"
    },
    "planning_total": "325.60",
    "complete": false,
    "incomplete_count": 2
  }
}
```

</details>

## note_origin risk of IMP-309-read-fields

Fixed here, because it lives in `replace_plan`, the save path this part changes. An item from a plan whose origin is not `model` is saved with a null note and `note_origin` `none` (`test_a_fallback_plan_is_saved_without_an_ai_note_or_citation`). The note goes too because of the migration 0004 CHECK `(note is null) = (note_origin = 'none')`: a template note cannot be stored with origin `none`.

## Blockers

None.

## Proposed decisions

- **PD-IMP-316-6: `schedule.py` is left out of the card's files.** Step 9 rebuilds every item, so the citations would be lost without it. Proposed: add it.
- **PD-IMP-316-7: `resolve_sources` takes the session and returns rows.** The card writes `resolve_sources(chunk_ids)`. The session keeps the read in the request's transaction, and rows keep `app.rag` from importing `SourceRef` from `app.itinerary`, a higher module (A1 §6.10).
- **PD-IMP-316-8: template notes of the fallback planner.** IMP-402 step 2 allows "note_origin none or template marker", but that CHECK refuses a note with origin `none`, and no marker column exists. As built, fallback items have no note. If IMP-402 needs notes, it needs a decision: a day-level message (as IMP-606 step 4 does for a missing lunch) or a new `note_origin` value with a migration.

## Open issues

- The contract descriptions of `SourceRef` and `Item.sources` still say "(IMP-316)" and "Empty until retrieval is built". Changing them changes `openapi.v1.json`, which this run must keep unchanged. The next contract change should correct them, with PD-IMP-315-2.
- IMP-317 shows the sources on the screen; nothing in `apps/web` changed here.
