# IMP-318 · whole-task part

- Run id: RUN-061
- Owner: Junaid (Junaid-Kureshi)
- Status: PR open
- Base commit: 3359b67
- Branch: feat/IMP-318-whole-task
- Reviewer: Kirtan (kirtan-S111)
- Traces to: US-167; FR-140; NFR-041, NFR-046; TC-458
- Card steps built: 1 (limited to copying, normalising and validating the member labels), 2, 3, 4

## Data input

- Source: `queries.jsonl` handed over for IMP-318. Labels written by Junaid, reviewed by Malhar Mer and Krrish Kamani; the team confirmed them through the operator het-lathiya on 12 November 2026.
- Line count 12; sha256 `c7c17f94fdbc2062d41c8c7e406af64cc72a0e4f978585301a5eaf40e3bb0abc` (matches the expected prefix c7c17f94).
- Normalisation, the only change: each bare guide stem `<stem>` in `relevant_guide_doc_keys` was written as the repository doc key `guide:<destination>/<stem>` (23 labels). Every stem names an existing file in `data/fixtures/sampleton/guides/` or `data/guides/ahmedabad/`. The run compared the copy with the input line by line: apart from those keys, every field (and its order) is the same, including the hard filter `step_free_required`. No label was added, dropped or changed. No script that came with the input was run.
- Committed copy: `eval/datasets/retrieval/v1/queries.jsonl`, sha256 `696b02f9310b30148edb611743cc416a4e8db100e9283e2f43ffc45e6f2ff589`, recorded in `manifest.json` with the source hash, author, reviewers and normalisation.
- Validation: the harness stops with exit 1 and names each label that does not resolve: a guide key without its file, an unknown destination, or a place ref that `places.service.active_places_by_refs` does not find active. In both runs below all 23 guide labels and all 23 place refs resolved.

## Changed files

- `eval/datasets/retrieval/v1/queries.jsonl`, `eval/datasets/retrieval/v1/manifest.json` (created).
- `apps/api/app/evaluation/retrieval_metrics.py` (created, pure): `recall_at_k`, `place_hit_rate`, `citation_validity`, `grounding_rate`, `mean`. A share whose denominator is empty is `None` (undefined) and `mean` leaves it out. Added to the import-linter pure-domain contract.
- `apps/api/app/evaluation/run.py` (modified): `--suite generation|retrieval` (default `generation`, unchanged). For each query, the retrieval suite:
  1. builds the trip and preferences in memory;
  2. runs `generation.retrieval.semantic_retrieval` (which calls `rag.service.retrieve`);
  3. ranks with `ranked_shortlist`, once with the vector result and once with no result. No result is the existing lexical switch (`semantic=False`, no similarity weight), so rag has no new code path.
  4. runs the grounded pipeline of steps 5 to 9 on the vector shortlist: `build_generation_request`, `ground`, `enforce_input_limit`, the MOCK `generate_itinerary`, `apply_limits`, `check_output` and `schedule.recalculate` with the distance estimate. Nothing is saved.

  It writes `eval/results/<run_id>/run.json` and `eval/reports/<run_id>.md`.
- `apps/api/app/rag/repository.py`, `apps/api/app/rag/service.py` (modified): a read-only `document_keys(session, document_ids)`, because `RetrievedChunk` carries the document ID and the labels are doc keys. `retrieve`, its signature and the ranking are unchanged.
- `apps/api/.importlinter`: `app.evaluation.retrieval_metrics` added to the pure-domain contract.
- `apps/api/tests/unit/evaluation/test_retrieval_metrics.py` (created).
- `eval/results/20261113T114752Z-retrieval-mock/run.json`, `eval/results/20261113T114756Z-retrieval-mock/run.json`, `eval/reports/20261113T114752Z-retrieval-mock.md`, `eval/reports/20261113T114756Z-retrieval-mock.md`: the two MOCK runs.
- `Makefile`: not changed. `eval` already passes `$(ARGS)`, and `PROVIDER` defaults to MOCK.

Trip frame (the queries carry preferences only): start 2027-03-01, 2 days, 2 adults, no children, no budget, contingency 10 %, template `itinerary_generate` v2 (gr-2). It is written into every run record.

## Commands and results

The database was a throwaway local PostgreSQL 16.2 with pgvector (pip `pgserver`, port 55432), stopped at the end. It was migrated with `make db-bootstrap`, seeded with `make seed` and `make seed SEED_DIRS=data/places/ahmedabad`, and indexed with `make rag-index` (MOCK embeddings).

| Command | Result |
| --- | --- |
| `make seed SEED_DIRS=data/places/ahmedabad` | `seed ahmedabad: places inserted 103, updated 0, unchanged 0, deactivated 0` (Sampleton: `places inserted 30`) |
| `make rag-index` | `rag-index: documents=151 chunks=227 embedded=189 inactive=0 warnings=0 errors=0` |
| `make test-unit ARGS='-k retrieval_metrics'` | `9 passed, 1031 deselected, 1 warning in 1.44s` |
| `make eval DATASET=retrieval/v1 ARGS='--suite retrieval'` (1) | `evaluation 20261113T114752Z-retrieval-mock: 12 queries, written to /home/hetlathiya/Group12/eval/results/20261113T114752Z-retrieval-mock` |
| `make eval DATASET=retrieval/v1 ARGS='--suite retrieval'` (2) | `evaluation 20261113T114756Z-retrieval-mock: 12 queries, written to /home/hetlathiya/Group12/eval/results/20261113T114756Z-retrieval-mock` |
| diff of the two `run.json` | identical apart from `run_id`, `started_at`, `ended_at` |
| `make lint` | exit 0 (`All matched files use Prettier code style!`) |
| `make typecheck` | `Success: no issues found in 118 source files` |
| `make imports` | `Contracts: 6 kept, 0 broken.` |
| `make test` | exit 0: unit `1040 passed, 1 warning`; contract `87 passed, 2 deselected, 1 warning`; api `425 passed, 1 warning`; authz `41 passed`; web `Tests  186 passed (186)` |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |

The `git_commit` in both run records is 1b8d753, the metrics-and-suite commit before rebase. A rebase changes commit IDs.

## Measured numbers (MOCK provider and MOCK embeddings)

These are numbers from MOCK hashed-token embeddings, not semantic quality. Live-embedding numbers come in the staging window.

| Scope | Queries | recall@6 | Place hit rate vector | Place hit rate lexical | Citation validity | Grounding rate |
| --- | --- | --- | --- | --- | --- | --- |
| overall | 12 | 0.7083 | 0.6667 | 0.7083 | 1.0 (68 citations) | 0.7571 |
| sampleton | 6 | 1.0 | 1.0 | 1.0 | 1.0 | 0.7429 |
| ahmedabad | 6 | 0.4167 | 0.3333 | 0.4167 | 1.0 | 0.7714 |

All 12 queries ran in `vector` mode. The grounding rate is below 1 because the MOCK adapter writes a note on every item but cites only the places whose passage was supplied (the top `RAG_TOP_K_PLACE`).

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-140 AC1 / TC-458: recall@6 and place hit rate in vector and lexical mode | verified | both runs; `run.json` `metrics.overall`, `by_destination`, `per_query`; unit tests for both metrics |
| FR-140 AC2 / TC-458: citation validity (1.0) and grounding rate for MOCK generations | verified | both runs: citation validity 1.0 over 68 saved citations, grounding rate 0.7571; unit tests |
| FR-140 AC3 / NFR-041: run metadata and two identical MOCK runs | verified | `run.json` has `dataset_version`, `dataset_sha256`, `provider`, `model_id`, `embedding_model_id`, `git_commit`; the two records are identical apart from `run_id` and the timestamps |
| Label review recorded in the manifest | verified | `manifest.json` `reviewers` |

## Blockers

None.

## Proposed decisions

- PD-IMP-318-1: the retrieval suite plans each query in a fixed trip frame (2027-03-01, 2 days, 2 adults, no budget), because the labelled lines carry preferences only. A later dataset version could carry trip fields.
- PD-IMP-318-2: a metric with an empty denominator is reported as `null` and left out of the means (for example citation validity with no saved citation), not as 0 or 1.

## Open issues

- Live-embedding (Gemini) numbers are not measured here. They need the staging window.
- E2E: run through `gh workflow run e2e.yml` on the branch (no Docker locally).
