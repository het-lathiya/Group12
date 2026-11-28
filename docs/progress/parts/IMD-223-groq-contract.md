# IMD-223 · Groq contract tests and prompt compatibility

- Run: RUN-108 · Owner: Manya Rana · Points: 0
- Status: implemented for the combined `feat/groq-provider` pull request
- Base commit: `8e7dd4fb6471cf3e7108e2d3e7410b448e4c78ca`
- Traces: IMP-512, IMD-223, FR-040–FR-046, NFR-043; TC-001, TC-005–TC-008, TC-156–TC-158, TC-162

## Changes

- `apps/api/tests/contract/conftest.py`: `groq_recorded` joins the same parameterized adapter suite
  as `gemini_recorded`, MOCK and the double. Success and seven shared errors pass through the real
  Groq adapter over recorded HTTP answers or a transport timeout, with fake time and no sockets.
- `apps/api/tests/contract/test_provider_contract.py`: GROQ is a recognized name, and the generation
  import-isolation check includes the Groq adapter.
- `apps/api/tests/fixtures/provider_recordings/groq/`: seven synthetic format recordings and README.
  These are not live account captures; they hold no key, prompt body or personal data.
- `apps/api/tests/contract/test_groq_prompt_compatibility.py`: v1–v4 use exactly the registry's
  existing system/user content and original output model. Strict conversion requires every property,
  closes objects and removes defaults without altering the canonical schema; numeric, length,
  count and HH:MM constraints remain. Nullable optional summary stays nullable. Best-effort and
  JSON object response modes are covered too.
- `docs/guides/adding-a-provider.md`: describes the new registry entry and compatibility coverage.
- `eval/results/run-108-mock/run.json`: actual MOCK evaluation manifest from this working tree,
  based on the base commit above; trips/v1 and prompt v1, 15/15 schema-valid, usable, valid place IDs
  and no duplicates, no provider failures. No published prompt or AI schema changed.

## Commands and evidence

| Command | Result line |
| --- | --- |
| Combined targeted pytest command in Nidhi's part record, including `tests/contract -m 'not live'` | `1062 passed, 2 deselected, 1 warning in 84.26s (0:01:24)` |
| `make eval PROVIDER=MOCK DATASET=trips/v1 ARGS='--repeats 1 --out /tmp/group12-r108-mock-eval'` | `evaluation 20261128T162029Z-mock: 15 attempts, written to /tmp/group12-r108-mock-eval` |
| `make imports` | `Contracts: 8 kept, 0 broken.` |
| `make openapi-check` | `openapi-check: contracts/, apps/web/lib/api/schema.d.ts and apps/web/lib/api/any-city-schema.d.ts are up to date` |

## Live probe

**not verified: no key**. Reading settings checked only whether `GROQ_API_KEY` was non-empty;
the result was `GROQ_API_KEY: absent`. No live call was made. HTTP status: not observed;
valid io-1: not verified; latency: not measured. No extra account or key was used.

Acceptance: shared result/error contract, unchanged prompts/io-1/io-2, and the MOCK evaluation are
verified by the tests above. Live compatibility remains unverified. Full checks/E2E deferred to CI
under operator fast mode. Blockers: none. Proposed decisions: none.
