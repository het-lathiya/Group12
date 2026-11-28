# RUN-109B N3 — pause re-embedding after quota exhaustion

Owner: Nidhi Chauhan. 0 points. Base: `0346ee8` (N4 regression commit precedes this part).
Related: IMP-312, IMP-313, IMP-726; A1 §6.6, §6.11, IMD-112; RUN-107 N3.
Status: verified locally.

The embedding loop previously stopped on quota errors or exhausted 429 retries, but the
minute-based re-embed round had no memory of that failure. It therefore retried and warned
every minute even when the daily quota could not recover.

`app/rag/service.py` now remembers a pause per embedding provider/model. A daily quota error,
or repeated 429s whose retry budget is exhausted, pauses document embedding until the next
**UTC** midnight unless the provider supplies a positive Retry-After. Retry-After can move
the resume time before or after midnight. The same state covers an import's embedding phase,
subsequent re-embed rounds, and another provider instance using the same embedding model.
An isolated 429 that exceeds the budget without Retry-After keeps the existing next-round retry;
ordinary budget exhaustion and provider outages do not cause a daily pause.

The transition logs one warning naming the failure, queued count and resume time. Paused
re-embed rounds make no provider or repository calls. `app/places/live_jobs.py` suppresses
its per-round informational line while paused. At the deadline, the pause expires and the
remaining chunks are embedded normally; completed batches are retained. The minute scheduler
keeps running its other housekeeping.

`app/ai/errors.py` carries optional Retry-After metadata on quota errors. The Gemini adapter
retains that header for quota failures and reads seconds or an HTTP date; malformed, negative
and non-finite values fall back to the UTC reset. These are internal Python fields: io-1,
io-2, OpenAPI, migrations and environment settings are unchanged.

The pause is in process memory, matching the existing single-process import scheduler
(IMD-12). Restarting the process loses the pause; persistence across restarts is not claimed.
Query embeddings and the generation circuit breaker are unchanged.

Verification:

- `tests/unit/rag/test_embed_pacing.py` uses a fake UTC clock, monotonic clock and sleep, with
  an in-memory store and scripted provider. Existing D3 cases plus new N3 cases give
  `13 passed in 0.33s`. Tests cover partial progress, minute polls without calls or logs,
  exact reset boundaries, a UTC date/year rollover, a non-UTC clock, another provider instance,
  repeated 429s beyond budget, Retry-After before/after midnight, resumption and ordinary outages.
- Adapter tests prove quota Retry-After retention, HTTP-date parsing with a fake UTC clock,
  and invalid-header handling. Shared pytest setup isolates the new process-level pause state.
  Its reset uses a private patch context: the initial CI run exposed that borrowing the shared
  monkeypatch fixture changes the socket-guard teardown order. No socket guard is disabled.
- `make test-unit` (after that fixture correction): `2005 passed, 1 warning in 32.97s`.
- `pytest tests/unit/rag tests/unit/ai tests/unit/generation tests/unit/validation tests/contract -m 'not live' -q`:
  `984 passed, 2 deselected, 1 warning in 39.15s`.
- `pytest tests/api/test_live_guides_index.py tests/api/test_rag_index.py tests/api/test_itinerary.py tests/api/test_live_generation.py -q`:
  `64 passed in 143.51s (0:02:23)`.
- `ruff check .`: `All checks passed!`; `ruff format --check .`: `283 files already formatted`.
- `mypy app`: `Success: no issues found in 140 source files`.
- `make imports`: `Contracts: 8 kept, 0 broken.`
- `make openapi-check`: `openapi-check: contracts/, apps/web/lib/api/schema.d.ts and apps/web/lib/api/any-city-schema.d.ts are up to date`.

No real provider calls. The only production change outside rag/ai is the re-embed round's
logging guard. RUN-109A's OSM provider and import timestamps were untouched.
