# IMP-313 · whole-task part

- Run id: RUN-048 (grouped, IMD-121, with IMP-306)
- Owner: Manal (manalPatel2557)
- Status: PR_OPEN
- Base commit: 654b4f7
- Branch: feat/IMP-306-313-wave3
- Reviewer: Nidhi (Nidhi9864)
- Traces to: US-166; FR-136; NFR-040; IMD-15, IMD-110, IMD-111; TC-447, TC-448, TC-449
- Card steps built: 1 to 11

## Changed files

- `apps/api/app/rag/` (created): `constants.py` (A1 §6.13), `documents.py`, `guides.py` and `chunker.py` (pure), `repository.py`, `service.py` (`index`), `index.py` (CLI).
- `apps/api/app/places/service.py`, `repository.py`: `ensure_data_source`, `DataSourceConflictError`, `data_source_terms` and `active_places_with_source_date`.
- `apps/api/app/ai/providers/base.py`, `mock.py`, `gemini.py`, `finetuned.py`, `tests/fixtures/ai.py`: `embedding_model_id` (PD-IMP-313-1).
- `data/fixtures/sampleton/guides/`: the three synthetic SAMPLE guides.
- `docs/guides/rag-corpus.md` (created), for curators.
- `Makefile`: `rag-index`. `apps/api/scripts/release.sh`: the index step is unconditional. `apps/api/.importlinter`: the pure modules, and a service-order contract for A1 §8.2.
- Tests: `tests/unit/rag/test_chunker.py`, `test_guides.py`, `test_documents.py`, `tests/api/test_rag_index.py` (created).

## Evidence: `make rag-index`

`make db-up`, `make db-bootstrap`, `make seed`, then `make rag-index ARGS='--destination sampleton'` twice with `AI_PROVIDER=MOCK`, then `make db-down`:

```text
rag-index: documents=33 chunks=38 embedded=38 inactive=0 warnings=0 errors=0
rag-index: documents=33 chunks=38 embedded=0 inactive=0 warnings=0 errors=0
```

`make rag-index ARGS='--destination ahmedabad --check'` was not run: no guides yet (IMP-314).

## Commands and results

| Command | Result line |
| --- | --- |
| `make test-unit ARGS='-k chunker'` | `9 passed, 676 deselected, 1 warning in 1.35s` |
| `make test-unit ARGS='-k guides'` | `51 passed, 634 deselected, 1 warning in 1.38s` |
| `make test-unit ARGS='-k documents'` | `7 passed, 678 deselected, 1 warning in 1.38s` |
| `make test-api ARGS='-k rag_index'` | `18 passed, 280 deselected, 1 warning in 9.84s` |
| `make rag-index ARGS='--destination sampleton --check --strict'` | `rag-index: documents=33 chunks=38 embedded=0 inactive=0 warnings=0 errors=0` |
| `make imports` | `Contracts: 6 kept, 0 broken.` |
| `make check` (all three parts of RUN-048 in the tree, `TEST_DATABASE_URL` on `pgvector/pgvector:pg16`) | exit 0: unit `685 passed, 1 warning`; contract `87 passed, 2 deselected, 1 warning`; api `298 passed, 1 warning`; authz `29 passed`; web `Tests  88 passed (88)` |

Not run: `make live-smoke`, and any Gemini embedding call (MOCK only, by instruction). `scripts/release.sh` was not run end to end; it needs the deployed image.

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| Every active place and gate-passing guide of SAMPLE is chunked and embedded, and each chunk resolves to its document and source (FR-136 AC1, TC-449) | verified | `test_tc_449_every_place_and_guide_...` |
| A guide with missing provenance, out-of-range length or a price, hour or travel statement fails the strict gate and is not indexed (FR-136 AC2, TC-448) | verified | `test_guides.py`, `test_tc_448_a_strict_gate_error_exits_1_and_writes_nothing` |
| Re-running embeds only new or changed chunks; removed documents are deactivated, never deleted (FR-136 AC3, TC-449) | verified | `test_tc_449_a_second_run_...`, `test_tc_449_a_changed_paragraph_...`, `test_tc_449_a_deleted_guide_...` |
| Chunker limits, headings and overlap hold (TC-447) | verified | `test_chunker.py` |
| A `ProviderError` stops with exit 3 and keeps saved batches | verified | `test_a_provider_error_exits_3_...`, MOCK only |
| Indexing with Gemini embeddings | not verified | No key in this run; the first staging release shows it |

## Blockers

None.

## Proposed decisions

- **PD-IMP-313-1: `embedding_model_id` on `ModelProvider`.** A1 §6.6 step 4 re-embeds chunks of another model, so the index must know the active model before any call, and §6.5 gives no way to ask. A read-only `embedding_model_id` is added to the interface and the three adapters. It is not on `ModelMetadata`, so readiness and OpenAPI are unchanged. §6.5 should list it.
- **PD-IMP-313-2: a gate error without `--strict`.** §6.6 sets exit 1 only with `--strict`. Without it, the failing guide is skipped and the rest are indexed with exit 0. A guide indexed earlier that now fails is no longer in the corpus, so it goes inactive.
- **PD-IMP-313-3: finding the data folder.** The wheel installs `app` away from `data/`, so `Path(__file__)` cannot find it. `service.data_root` looks in the working directory and its parents, which covers `/srv/api` in the image and `apps/api` under `make`. No environment variable is added.
- **PD-IMP-313-4: service-order contract.** Card step 10 names only the pure modules. A contract for the A1 §8.2 service order is added too, so the rule is enforced.

## Open issues

- A full run loads active destinations only, so documents of a destination that later goes inactive stay active until someone deactivates them. Generation cannot reach them, because trips need an active destination.
- `curated_by` is required by the gate but has no column, so it stays in the file.
- A heading is not sent to `embed_texts`; only the chunk content and the document title are. IMP-315 may want to revisit this when retrieval is calibrated.
