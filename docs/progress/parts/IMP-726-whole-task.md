# IMP-726 · whole-task part (live guide corpus from Wikivoyage and Wikipedia)

- Card: IMP-726 (0 points, Amendment A2 §6.5, §12 Batch C2)
- Run id: RUN-091 (Batch C2, Sprint 7, inserted under IMD-215)
- Owner: Nidhi (Nidhi Chauhan)
- Status: PR_OPEN candidate on `feat/S7-C2-any-city-ai-web`
- Base commit: 667c0d8 (on `main`)
- Traces to: A2 §6.5, §6.7 (source-prefixed titles), §9.3, §1.3; TC-478; IMD-107, IMD-110, IMD-112, IMD-217

## Changed files

- `apps/api/app/rag/live_guides.py` (created, pure):
  - sections become guide documents (`build_guides`), split at paragraph boundaries into documents of at most 6,000 characters;
  - Sleep, Buy, Eat, Drink, Connect and Go next are skipped;
  - paragraphs flagged by the content checks of `app/rag/guides.py` are dropped and counted, and sections under 300 characters after that are skipped;
  - synthetic front matter per §6.5;
  - source-prefixed titles (`Wikivoyage: …`, `Wikipedia: …`, `OpenStreetMap: …`);
  - the 400-chunk per-destination cap (`cap_guides`).
- `apps/api/app/rag/service.py`: new public functions:
  - `fetch_live_guides(provider, destination)`: best effort, outside any transaction;
  - `index_live_destination(session, destination, guide_sections, *, retrieved_on, now)`: writes place and guide documents in ONE load, applies both caps and runs one `deactivate_missing` over the joint key set;
  - `embed_destinations(destination_ids, *, provider, sessions)`;
  - a `LiveIndexReport` dataclass;
  - the `index()` docstring now states that it covers curated destinations only.
- `apps/api/app/rag/repository.py`:
  - added `count_active_chunks`, `expired_live_destinations` (oldest expiry first) and `deactivate_destination_documents`;
  - `deactivate_missing`'s docstring now states its one-destination scope.
- `apps/api/scripts/release.sh`: a comment and the step line "release: RAG index (curated destinations)". The index already lists curated destinations only, through API-06's `active_destinations` filter.
- `apps/api/app/places/live_jobs.py`, the call site, which goes beyond the one line the prompt allowed. Every change:
  1. The module docstring describes the one live index write.
  2. Removed the imports `ProviderError`, `get_provider` and `app.rag.documents as corpus`; added `GuideSourceProvider`.
  3. `run_import`: `live = providers or get_providers()`, and `_import(..., places=live.places, guides=live.guides, ...)`.
  4. `_import` takes a `guides: GuideSourceProvider` parameter.
  5. Before the store transaction: `sections = await rag_service.fetch_live_guides(guides, destination)`.
  6. In the store transaction, `index_live_place_documents(...)` and `_index_live_guides(...)` are replaced by `indexed = await rag_service.index_live_destination(session, destination, sections, retrieved_on=now.date(), now=now)`.
  7. The completion log line adds the counts `guides`, `dropped_paragraphs` and `guides_capped`.
  8. Deleted the helper functions `index_live_place_documents` (it used the private `rag_service._write` and `_Loaded`) and `_index_live_guides` (the placeholder).
  9. `_embed` calls the public `rag_service.embed_destinations` instead of the private `rag_service._embed`.
- `apps/api/tests/api/test_live_import_jobs.py`: the 3 assertions from the RUN-090 era, updated with the operator's approval in RUN-091 because live imports now also write guide documents:
  1. `test_tc_474_ok_import_completes_with_labelled_places`: the document query now filters `RagDocument.kind == "place"` before `len(documents) == LIVETON_USABLE`;
  2. the same test: `assert {d.kind for d in documents} == {"place"}` is removed (the kind filter replaces it);
  3. `test_tc_474_embedding_failure_leaves_the_import_completed`: the unembedded-chunk count filters `RagDocument.kind == "place"` before `== LIVETON_USABLE`.
- `apps/api/tests/unit/rag/test_live_guides.py` (created): 16 tests.
- `apps/api/tests/api/test_live_guides_index.py` (created): 9 tests.

## Attribution (A2 §9.3)

- The shared `data_sources` rows `Wikivoyage` and `Wikipedia` have `source_type = 'other'`, `licence = 'CC BY-SA 4.0'` and the generic §9.3 text without a page title: "Guide text from Wikivoyage, by its contributors, under CC BY-SA 4.0; excerpts, some sections left out". Their URLs are `https://en.wikivoyage.org/` and `https://en.wikipedia.org/`. One row serves every page, and `ensure_data_source` refuses differing terms.
- Each live guide document has its own front matter (`Guide`) with its own `attribution_text`, "Guide text from Wikivoyage ({page title}), by its contributors, under CC BY-SA 4.0; excerpts, some sections left out", and its page URL. The stored document keeps the page URL (`rag_documents.url`) and a title that contains the page title. `rag_documents` has no attribution column, and this run adds no migration, so the per-page text is rebuilt with `live_guides.attribution_text(source, page_title)` rather than stored. This is an open issue below.

## Commands

| Command | Result line |
| --- | --- |
| `.venv/bin/python -m pytest tests/unit/rag/test_live_guides.py -q` | 16 passed in 0.06s |
| `.venv/bin/python -m pytest tests/api/test_live_guides_index.py tests/api/test_live_import_jobs.py -q` | 30 passed in 4.12s |
| `make test-api` (full API suite, with the 3 updated assertions; before the guide tests were added) | 663 passed, 1 warning in 117.21s (0:01:57) |
| `make imports` | Contracts: 7 kept, 0 broken. |
| `.venv/bin/mypy app …` | Success: no issues found |

The run-wide checks (`make check`, `-k live_guides`, `-m any_city`) ran once on the branch head. Their lines are in the SYNC REPORT of RUN-091.

## Acceptance

- **No price, clock-time or hours phrase reaches a stored chunk: verified.** `test_live_guides_no_flagged_phrase_reaches_a_chunk` checks the unit build, and `test_live_guides_import_writes_places_and_guides_in_one_load` checks every stored chunk against the content rules.
- **The `doc_key` format `guide:<slug>/<wikivoyage|wikipedia>-<pageid>-<section index>` holds: verified** by `test_live_guides_doc_key_and_front_matter` and the API test. Continuation parts of a section over 6,000 characters add `-<n>` (n ≥ 2), so keys stay unique.
- **A release index run leaves live documents untouched: verified** by `test_live_guides_release_index_leaves_live_documents_untouched`. It covers `index()` over all destinations, and `index(<live slug>)` raises `UnknownDestinationError`.
- **An embedding failure leaves the import completed, with `lexical_fallback` at generation: verified** by `test_live_guides_embedding_failure_leaves_the_import_completed_on_lexical_fallback`. That test calls `rag.service.retrieve` and gets mode `lexical_fallback`.
- **Places and guides are written in one load, so neither deactivates the other: verified** by `test_live_guides_repeat_import_keeps_both_kinds_active`.
- **Front matter and attribution, per page: verified** by `test_live_guides_each_document_has_its_own_page_attribution_and_url` and `test_live_guides_shared_source_attribution_has_no_page_title`.
- **Corpus cap: verified.**
  - 400 chunks per live destination: `test_live_guides_per_destination_cap_is_400_chunks`.
  - 5,000 overall, with the oldest expired live destination deactivated first: `test_live_guides_global_cap_deactivates_the_oldest_expired_live_destination_first`.
  - Without room, places are stored without guides: `test_live_guides_global_cap_without_room_stores_places_without_guides`.

## Cut if late

- **Lexical guide passages (A2 §6.5, listed in §1.3): cut.** Live plans made without embeddings cite no guide passage, as IMD-112 does today. `app/rag/repository.py` has no lexical guide query.
- Wikipedia as the second source: built.

## Proposed decisions

- **PD-726-1:** a guide-source failure (MediaWiki timeout, rate limit or error) stores the places without guides and completes the import. It never fails the import. A2 §6.2's error list is read as covering the places provider.

## Open issues

- The per-page §9.3 text is not persisted, because `rag_documents` has no attribution column. API-79 and the citation sources show the shared row's generic text with the page URL. A column would need its own migration.
- `live_guides.flagged` reuses the private `_CONTENT_RULES` of `app/rag/guides.py`, which is in the same package. A public name there would be cleaner.
- §6.5 gives the guide title as `<page title> — <section>`, and §6.7 asks for titles that start with their source. The stored title is `<Source>: <page title> — <section>`.
- live_jobs.py changes go beyond the one call-site line the prompt allowed. All of them are listed above.

## Blockers

none
