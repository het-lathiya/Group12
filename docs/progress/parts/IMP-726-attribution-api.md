# IMP-726 · attribution-api part (per-page guide attribution in API-79)

- Card: IMP-726 Live guide corpus (Amendment A2 §6.5, §9.3; 0 points)
- Part: attribution-api (follow-up of the RUN-091 open issue: page title missing from the guide attribution)
- Run id: RUN-092 (Batch C3, Sprint 7, inserted under IMD-215)
- Owner: Het (Het Lathiya)
- Status: PR_OPEN candidate on `feat/S7-C3-any-city-verify`
- Base commit: 818c1d8 (on `main`)
- Traces to: A2 §9.3, §10; TC-476

## Changed files

- `apps/api/app/places/repository.py`: `live_guide_pages(session, destination_id)`, a read-only query. It returns the source name, licence, title and page URL of the destination's active guide documents.
- `apps/api/app/places/live_service.py`:
  - `destination_detail` (API-79): for a live destination, the shared Wikivoyage and Wikipedia rows are replaced by one entry per active guide page, built by `guide_page_attribution`.
  - Each entry is `{source_name, licence "CC BY-SA 4.0", attribution_text "Guide text from <Source> (<page title>), by its contributors, under CC BY-SA 4.0; excerpts, some sections left out", url <page URL>}`.
  - The page title is read from the stored document title `<Source>: <page title> — <section>` (IMP-726): the text between the source prefix and the last " — ".
  - Entries are deduplicated per page (source and URL).
  - The OpenStreetMap entry and curated destinations are unchanged.
- `apps/api/tests/api/test_live_destinations.py`: two cases added:
  - `test_tc_476_live_detail_attributes_each_guide_page`: two documents of one Wikivoyage page give one entry, a Wikipedia page gives one, an inactive page gives none, and OpenStreetMap stays;
  - `test_tc_476_guide_page_attribution_reads_the_page_title_and_skips_other_sources`.

No migration. The response shape and all four contract files are unchanged.

## Example entry (API-79 `attribution`)

```json
{"source_name": "Wikivoyage", "licence": "CC BY-SA 4.0", "attribution_text": "Guide text from Wikivoyage (Liveton (SAMPLE)), by its contributors, under CC BY-SA 4.0; excerpts, some sections left out", "url": "https://en.wikivoyage.org/wiki/Liveton_(SAMPLE)"}
```

## Commands

| Command | Result line |
| --- | --- |
| `.venv/bin/python -m pytest tests/api/test_live_destinations.py -q` | 31 passed in 3.06s |
| `make test-api ARGS='-m any_city'` | 65 passed, 613 deselected, 1 warning in 9.83s |
| `make openapi-check` | openapi-check: contracts/, apps/web/lib/api/schema.d.ts and apps/web/lib/api/any-city-schema.d.ts are up to date |

## Acceptance

- API-79 gives one §9.3 entry per active live guide page, with its page title and page URL: **verified** (the test above).
- The shape is unchanged, and curated destinations are unchanged: **verified** by `openapi-check` and the existing `test_tc_476_destination_detail_for_curated_and_live`.

## Proposed decisions

none

## Open issues

- The page title is parsed from the stored document title. A page title that itself contains " — " is kept whole, because only the last " — " (before the section) is cut. A stored page-title column would avoid parsing, but it needs a migration.

## Blockers

none
