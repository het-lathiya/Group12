# IMP-312 · whole-task part

- Run id: RUN-047 (grouped, IMD-121, with IMP-305 and IMP-302)
- Owner: Nidhi (Nidhi9864)
- Status: PARTIAL run; this part is complete and pushed, no pull request yet
- Base commit: 7974da0
- Branch: feat/IMP-312-305-302-wave2
- Reviewer: Manya (manyarana)
- Traces to: US-164; FR-136, FR-137; NFR-031, NFR-043; TC-002, TC-443, TC-444, TC-445, TC-446
- Card steps built: 1 to 6

## Changed files

- `apps/api/app/schemas/ai.py`: `EmbeddingResult`, `EmbeddingPurpose` and the limits 768, 32 and 2,000.
- `apps/api/app/ai/providers/base.py`: `embed_texts` on the protocol; `check_embed_input` and `l2_normalised`, shared by the adapters.
- `apps/api/app/ai/providers/gemini.py`: `embed_texts`, `_call_embed_vendor` (the only embedding vendor call), the §8.4 retries and `_models_api_code`.
- `apps/api/app/ai/providers/mock.py`: `hashed_embedding` (`mock-embed-v1`, A1 §6.5) and the `embed_error` argument.
- `apps/api/app/ai/providers/finetuned.py`: the stub refuses.
- `apps/api/app/ai/factory.py`: the Gemini cache key also holds the embedding model and `GEMINI_MAX_RETRIES`, which the adapter now reads.
- `apps/api/app/core/config.py`, `.env.example`: `GEMINI_EMBEDDING_MODEL_ID` and its start-up check.
- Tests: `tests/unit/ai/test_mock_embeddings.py`, `tests/unit/ai/test_gemini_embeddings.py` (created); `tests/contract/test_provider_contract.py`, `tests/unit/core/test_config.py`, `tests/fixtures/ai.py` (modified). `tests/api/test_health.py` and `tests/authz/test_route_inventory.py` set the new variable on their production settings.

`infra/aws/services/api.staging.json.tmpl` already sets `GEMINI_EMBEDDING_MODEL_ID`, so it is unchanged.

## Commands and results

| Command | Result line |
| --- | --- |
| `make test-unit ARGS='-k embeddings'` | `32 passed, 538 deselected, 1 warning in 2.68s` |
| `make test-contract ARGS='-k embed'` | `16 passed, 66 deselected, 1 warning in 1.35s` |
| `make test-unit ARGS='-k embedding_model'` | `10 passed, 560 deselected, 1 warning in 1.48s` |
| `make imports` | `Contracts: 5 kept, 0 broken.` |
| `make typecheck` | `Success: no issues found in 91 source files` |
| `make check` (with this commit's tree, `TEST_DATABASE_URL` on `pgvector/pgvector:pg16`) | exit 0: unit `570 passed, 1 warning`; contract `80 passed, 2 deselected, 1 warning`; api `251 passed, 1 warning`; authz `28 passed`; web `Tests  80 passed (80)` |

Not run: `make live-smoke` (no key in this run, by instruction). `test_tc_444_gemini_embed_live` is marked `live` and skips without a key.

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| MOCK embeddings are deterministic, 768-dimensional, unit length, no network (TC-443) | verified | `test_tc_443_*` in `test_mock_embeddings.py`, including the A1 hash for one token |
| Gemini requests carry the model, 768 dimensions and the prefix or task type; vectors are normalised (TC-444) | verified with a fake transport, through the real SDK | `test_tc_444_*` in the contract suite and `test_gemini_embeddings.py` |
| `google.genai` is imported only in `gemini.py` (TC-002) | verified | `make imports` |
| Embedding errors map to the taxonomy and never open the generation breaker (TC-445) | verified, within the limit in the open issues | `test_tc_445_*` |
| Start-up refuses a missing or unsupported model for GEMINI in staging and production (TC-446) | verified | `test_tc_446_*` |
| One live embedding call | not verified | No key; run by the key holder with `make live-smoke` |

## Blockers

None.

## Proposed decisions

- **PD-IMP-312-1: retries live in the adapter for embeddings.** The card applies the §8.4 retries to `embed_texts`, but IMP-401 owns the generation retry loop, which does not exist yet. `_embed_with_retries` is private to embeddings; IMP-401 can share it or replace it.
- **PD-IMP-312-2: telling daily quota from rate limit.** The models API answers 429 `RESOURCE_EXHAUSTED` for both. `_models_api_code` treats a `quotaId` containing `PerDay` as quota and anything else as rate. This comes from the documented error shape and is unverified without a key, so a live run should confirm it. A wrong reading only retries once or falls back to lexical ranking (IMD-112).

## Open issues

- The breaker (`app/ai/breaker.py`) does not exist until IMP-401. Today TC-445 shows that an embedding failure leaves `health_check` and `_last_state` alone; IMP-401 must keep embeddings out of the breaker.
- The Gemini API reports no embedding token counts, so `EmbeddingResult.usage` is all null there. The usage fields of the response should be checked on the first live run.
