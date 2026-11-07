# IMP-315 · whole-task part

- Run id: RUN-049 (grouped, IMD-121, with IMP-308)
- Owner: Jeel (jeelfefar2141)
- Status: merged in PR #252
- Base commit: e5f5e7a
- Branch: feat/IMP-315-308-wave4
- Reviewer: Kirtan (kirtan-S111)
- Traces to: US-164; FR-137, FR-027, FR-028; NFR-002, NFR-050; IMD-107, IMD-108, IMD-112; TC-451, TC-452, TC-453, TC-459
- Card steps built: 1 to 9

## Changed files

- `apps/api/app/rag/query.py`, `mmr.py` (created, pure): the A1 §6.7 query text, and MMR with `RetrievedChunk`.
- `apps/api/app/rag/repository.py`: `best_place_chunks` and `top_guide_chunks`, the two exact-cosine queries.
- `apps/api/app/rag/service.py`: `retrieve`, `RetrievalContext`, `RetrievalResult`.
- `apps/api/app/trips/preference_mapping.py`: pm-2 weights, and `semantic=False` for lexical fallback.
- `apps/api/app/generation/ranking.py`: `c_semantic`, `ScoreParts.semantic`.
- `apps/api/app/generation/retrieval.py`, `request_builder.py`, `pipeline.py`: retrieval before ranking, outside any transaction.
- `apps/api/.importlinter`: `app.rag.query` and `app.rag.mmr` in the pure-domain contract.
- Tests: `tests/unit/rag/test_query.py`, `test_mmr.py`, `tests/api/test_rag_retrieval.py` (created); `tests/unit/generation/test_ranking.py`, `tests/unit/trips/test_preference_mapping.py`, `tests/api/test_generations.py`, `test_generation_records.py`, `tests/fixtures/pipeline.py` (pm-2 and the new pipeline step).

## Evidence: SAMPLE shortlist with score parts

A three-day SAMPLE trip with interest `food` and the note "lantern bridge at dusk", MOCK embeddings, no budget. The first eight of 24 places in each mode. The Lantern Bridge (`sample-004`) matches the note and no interest.

vector (24 places)
| Rank | Place | interest | semantic | price | distance | pace | total |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | sample-015 Sample Night Noodle Bar (sample) | 1.000 | 0.311 | 0.500 | 0.809 | 0.950 | 0.704 |
| 2 | sample-014 Sample Harbour Fish Kitchen (sample) | 1.000 | 0.357 | 0.500 | 0.749 | 0.933 | 0.702 |
| 3 | sample-013 Sample Corner Bakery (sample) | 1.000 | 0.291 | 0.500 | 0.793 | 0.967 | 0.699 |
| 4 | sample-016 Sample Green Plate Cafe (sample) | 1.000 | 0.271 | 0.500 | 0.816 | 0.950 | 0.697 |
| 5 | sample-018 Sample Lighthouse Tea Room (sample) | 1.000 | 0.236 | 0.500 | 0.680 | 0.967 | 0.671 |
| 6 | sample-017 Sample Market Street Food Stalls (sample) | 1.000 | 0.104 | 0.500 | 0.763 | 0.956 | 0.656 |
| 7 | sample-004 Sample Lantern Bridge (sample) | 0.000 | 1.000 | 0.500 | 0.456 | 0.967 | 0.490 |
| 8 | sample-025 Sample Chapel on the Hill (sample) | 0.000 | 0.311 | 0.500 | 0.619 | 0.967 | 0.377 |
sample-004 rank: 7

lexical_fallback (24 places)
| Rank | Place | interest | semantic | price | distance | pace | total |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | sample-016 Sample Green Plate Cafe (sample) | 1.000 | 0.000 | 0.500 | 0.816 | 0.950 | 0.803 |
| 2 | sample-015 Sample Night Noodle Bar (sample) | 1.000 | 0.000 | 0.500 | 0.809 | 0.950 | 0.802 |
| 3 | sample-013 Sample Corner Bakery (sample) | 1.000 | 0.000 | 0.500 | 0.793 | 0.967 | 0.801 |
| 4 | sample-017 Sample Market Street Food Stalls (sample) | 1.000 | 0.000 | 0.500 | 0.763 | 0.956 | 0.794 |
| 5 | sample-014 Sample Harbour Fish Kitchen (sample) | 1.000 | 0.000 | 0.500 | 0.749 | 0.933 | 0.788 |
| 6 | sample-018 Sample Lighthouse Tea Room (sample) | 1.000 | 0.000 | 0.500 | 0.680 | 0.967 | 0.780 |
| 7 | sample-012 Sample Cliff Meadow (sample) | 0.000 | 0.000 | 0.500 | 0.687 | 0.917 | 0.400 |
| 8 | sample-024 Sample Arcade by the Sea (sample) | 0.000 | 0.000 | 0.500 | 0.642 | 0.933 | 0.393 |
sample-004 rank: 20
guide passages: 6; ms 20

## Commands and results

| Command | Result |
| --- | --- |
| `make test-unit ARGS='-k "rag and (query or mmr)"'` | `8 passed, 691 deselected, 1 warning` |
| `make test-unit ARGS='-k ranking'` | `30 passed, 669 deselected, 1 warning` |
| `make test-api ARGS='-k rag_retrieval'` (`TEST_DATABASE_URL` on `pgvector/pgvector:pg16`) | `12 passed, 298 deselected, 1 warning` |
| `make test-unit` | `699 passed, 1 warning` |
| `make test-api` | `310 passed, 1 warning` |
| `make imports` | `Contracts: 6 kept, 0 broken.` |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |
| `make check` (the two commits of this run in the tree, `TEST_DATABASE_URL` on `pgvector/pgvector:pg16`) | exit 0: unit `707 passed, 1 warning`; contract `87 passed, 2 deselected, 1 warning`; api `311 passed, 1 warning`; authz `29 passed`; web `Tests  88 passed (88)` |
| `make e2e ARGS='journey'` (steps of `.github/workflows/e2e.yml`; web on port 3100 because another server held 3000) | `4 passed (10.4s)` |

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| Vector mode ranks a matching place higher than lexical mode, deterministically (FR-137 AC1, AC2, TC-451) | verified | `test_tc_451_a_place_matching_the_notes_ranks_higher_in_vector_mode_and_repeats`; rank 20 to rank 7 above |
| Hard filters and must-visit places are unchanged (FR-137 AC2, FR-027 AC2) | verified | `test_tc_451_filters_and_must_visit_are_unchanged_by_the_semantic_part`, `test_tc_451_a_must_visit_place_with_the_lowest_similarity_stays` |
| A failing embedding or no embeddings: the generation completes in `lexical_fallback` (FR-137 AC3, TC-452) | verified for the mode and completion | `test_tc_452_*`. The mode reaches the log; IMP-316 writes `retrieval_mode` to the record (card step, see Open issues) |
| Guide passages hold at most two chunks per document (TC-453) | verified | `test_tc_453_at_most_two_chunks_come_from_one_document`, `test_tc_453_guide_passages_hold_at_most_two_chunks_per_document` |
| Retrieval timing is recorded for NFR-050 (TC-459) | verified for `RetrievalResult.retrieval_ms` | `test_tc_459_retrieval_ms_is_set`; the record column is written by IMP-316 |

## Blockers

None for this part.

## Proposed decisions

- **PD-IMP-315-1: a database error also falls back.** A1 §6.11 lists an embedding error and a missing index. CLAUDE.md §8 says any retrieval failure falls back, so `retrieve` also catches `SQLAlchemyError`.
- **PD-IMP-315-2: `pm-1` in a contract description.** `PreferencesOut.effects` in `app/trips/schemas.py` still says "(pm-1)". Changing that text changes `contracts/openapi.v1.json`, which this run must keep unchanged. The next change to that contract should correct it.

## Open issues

- `retrieval_mode`, `embedding_model_id` and `retrieval_ms` reach the `ai_generations` row with IMP-316 (card step 7 of IMP-315 and the IMP-316 card). Until then `pipeline.run` holds the result and logs the mode and the milliseconds.
- The pipeline's `mark_running` and request build are now separate transactions, because the embedding call sits between them (§5.8). The candidates are read twice per generation, once for retrieval and once for ranking.
