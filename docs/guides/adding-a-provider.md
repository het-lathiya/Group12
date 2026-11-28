# Adding a model provider

How a new adapter, for example the Stage 2 `FINETUNED_MODEL`, joins the application and the provider contract suite (specification §8.3 and §8.19, FR-040, NFR-043). Stage 2 work still needs a recorded decision first (CLAUDE.md §8).

## 1. Write the adapter

- Put it in `apps/api/app/ai/providers/<name>.py` and subclass `ModelProvider` from `app/ai/providers/base.py`. Implement every operation with the same parameters: `generate_itinerary`, `modify_itinerary`, `embed_texts`, `health_check` and `get_model_metadata`.
- Return `ProviderResult` and `EmbeddingResult` from `app/schemas/ai.py`. Report usage as the vendor gives it, or `None`. Never estimate it.
- Turn every vendor failure into one of the shared errors in `app/ai/errors.py` (timeout, rate limited, quota, unavailable, invalid output, auth or configuration, bad request). Never pass on vendor message text or chain the vendor exception.
- A vendor SDK is imported only in that adapter file.

## 2. Register it

- Construct it only in `app/ai/factory.py`, the one module allowed to import a concrete adapter. Everything else uses `app.ai.providers.base`, `app.ai.errors` and `app.ai.factory`.
- In `apps/api/.importlinter`, add the adapter to `protected_modules` of the `vendor-adapters` contract (written `app.*.providers.<name>`). If it brings a vendor SDK, add a `forbidden` contract like `vendor-sdk` that allows that SDK only in the adapter.
- `AI_PROVIDER` values and settings are contracts. Changing them needs the specification registers updated in the same pull request.

## 3. Join the contract suite: one fixture id

The shared suite is `apps/api/tests/contract/test_provider_contract.py`. Its `adapter` fixture runs every shared test once per entry of `ADAPTERS` in `apps/api/tests/contract/conftest.py`. Adding an adapter means adding one entry:

IMD-223 registers `groq_recorded` alongside `gemini_recorded`, `mock` and the test double.
Groq uses `httpx.MockTransport` and synthetic chat-completion recordings. Its prompt compatibility
tests cover v1 through v4 without changing the published prompt or io-1/io-2 schemas.

```python
ADAPTERS: dict[str, Adapter] = {
    ...
    "finetuned_recorded": Adapter(
        build=finetuned_replay,
        failing=lambda error: finetuned_replay(FINETUNED_FAILURES[type(error)]()),
    ),
}
```

- `build` returns a working provider. `failing(error)` returns one whose `generate_itinerary` raises that shared error, the way the vendor really fails (an HTTP status and body, or a transport exception), not by raising the error directly.
- Drive an HTTP vendor from recorded answers with respx over a fake transport, as `gemini_replay` does. Put the recordings in `apps/api/tests/fixtures/provider_recordings/<name>/` as `{"http_status", "headers", "body"}` files and list them in that folder's README. They hold no key, no prompt body and no personal data. Every place ID comes from the SAMPLE request.
- The suite then checks the adapter, with no other change: the operations and their signatures (TC-001), a schema-valid io-1 `ProviderResult` with usage and latency (TC-158), each failure as the shared type (TC-005), the same interface-only caller running unchanged (TC-157, TC-008), health and metadata shapes (TC-006, TC-007), and no network call (TC-162).
- A test that calls the real vendor is marked `live` and skips without its key. Only `make live-smoke` runs it. `make test-contract` runs with `-m "not live"`, and the socket guard in `tests/conftest.py` blocks provider hosts (add the new vendor's host to `PROVIDER_HOSTS`).

## 4. Check

```bash
make test-contract   # the new id appears in every shared test
make imports         # Contracts: N kept, 0 broken.
make check
```
