# IMP-707 · architecture-api part

- Run id: RUN-083
- Owner: Manal Patel (part "Architecture and API documentation", 1 point, issue #155)
- Status: PR_OPEN (commit on the batch branch; the pull request is opened by the operator)
- Base commit: `f75aa94`
- Branch: `S7B/docs-core` (batch branch of RUN-083; one commit for this part)

## Card text used (TASK_REGISTER.md, IMP-707)

Implementation step for this part (quoted):

2. Export architecture and ER diagrams into docs/architecture.md, including the AWS deployment view and the RAG pipeline (corpus, chunking, embeddings, retrieval, grounding, citations; Amendment A1 §3 and §6); docs/api.md links contracts/openapi.v1.json and the published OpenAPI page (NFR-033); docs/test-plan.md summarises §13 with links to test reports.

Card step 5 applies to every part (drafting rule, summarised): draft from the repository and the specification only; run every documented command locally before writing it; mark commands that could not be run "not verified". The docs/test-plan.md half of step 2 is the test-plan part (Junaid).

Acceptance criteria of the card (quoted):

- Each required document exists in docs/ with owner and version (US-145 AC1)
- The architecture document matches the deployed system or lists the differences (US-145 AC2)
- A member outside the platform squad completed README setup (time recorded) and a clean deployment answered /health (US-146 AC2, CHK-18)
- A new member created a trip and an itinerary from the user guide without help (US-146 AC1)
- make openapi-check is green, so docs/api.md points to a current contract

## Changed files

- `docs/architecture.md` (created)
- `docs/api.md` (created)
- `docs/progress/parts/IMP-707-architecture-api.md` (created)

## What the documents contain

- `docs/architecture.md`: system context; AWS deployment view (resources, environments, deploy flow with the release task); backend layers, the six import contracts, modules and service ranks, AI provider layer; frontend; authentication sequence; generation job lifecycle and the twelve-step pipeline; the RAG pipeline (corpus, guide gate, chunking, embeddings, indexing, retrieval and hybrid ranking, grounding with gr-2 and io-2, citation check, stored citations, `SourceRef`, degradation, evaluation, constants); edit transaction; failure paths; ER diagram; 13 differences between the documented design and the built or deployed system. Ten Mermaid diagrams.
- `docs/api.md`: the contract and AI schemas, the check and regeneration commands, the published OpenAPI page (`/docs`, `/redoc`, `/openapi.json` outside production), conventions, the 36-operation catalogue generated from `contracts/openapi.v1.json` (method, path, access, request body, query parameters, success response), generation lifecycle, `SourceRef`, the error envelope and twelve codes, four differences between the specification and the contract.

## Commands run

All in this run, Linux container, proxy variables unset, `PYTHONPATH=/home/user/wt-S7B-docs-core/apps/api`.

| Command | Result line (quoted exactly) |
| --- | --- |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` (exit 0) |
| `make imports` | `Contracts: 6 kept, 0 broken.` (exit 0) |
| `make lint` | `All checks passed!` … `All matched files use Prettier code style!` (exit 0) |
| `make typecheck` | `Success: no issues found in 123 source files` (exit 0) |
| `cd apps/api && .venv/bin/python -m app.rag.index --help` | `usage: python -m app.rag.index [-h] [--destination SLUG] [--check] [--strict]` |
| `python3` read of `contracts/openapi.v1.json` (operations, schemas, security scheme) | 36 operations, 80 component schemas, OpenAPI `3.1.0`, scheme `HTTPBearer` |

## Not run

| Command | Reason |
| --- | --- |
| `make openapi` | Writes `contracts/` and the web types; no contract change is allowed under the freeze (IMD-201); `make openapi-check` shows the output equals the committed files |
| `make api` and opening `/docs`; staging `/docs` | Needs a database; staging is off between windows (IMD-137) and no staging call is allowed in this run |
| `make rag-index`, `make seed`, `make smoke`, `make eval ... --suite retrieval`, `docker compose up api web`, `sh scripts/release.sh`, every `aws` command | Need a database, Docker, AWS, a provider key or the network; marked "not verified" in `docs/architecture.md` §12 |
| Mermaid rendering of the ten diagrams | No Mermaid renderer in the container and no network; syntax checked by reading only |

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| Each required document exists in docs/ with owner and version (US-145 AC1), for `docs/architecture.md` and `docs/api.md` | verified | Header tables: owner Manal Patel, version 1.0 (draft for SG-7), 19 November 2026 |
| Step 2: architecture and ER diagrams, AWS deployment view and RAG pipeline in `docs/architecture.md` | verified | Sections 2 (deployment), 7 (RAG: corpus, chunking, embeddings, retrieval, grounding, citations) and 10 (ER diagram) |
| Step 2: `docs/api.md` links `contracts/openapi.v1.json` and the published OpenAPI page (NFR-033) | verified for the links; the page itself not verified | Header and §1 link the contract; §2 names `/docs`, `/redoc`, `/openapi.json` from `apps/api/app/main.py`; the running page was not opened |
| The architecture document matches the deployed system or lists the differences (US-145 AC2) | verified for the repository state; not verified against the running deployment | §11 lists 13 differences from repository sources; staging was not inspected (off between windows, IMD-137; no AWS call in this run) |
| make openapi-check is green, so docs/api.md points to a current contract | verified | `make openapi-check` exit 0 in this run (result line above) |
| A member outside the platform squad completed README setup (time recorded) and a clean deployment answered /health (US-146 AC2, CHK-18) | not verified | HUMAN step 6 of the card; not part of this part |
| A new member created a trip and an itinerary from the user guide without help (US-146 AC1) | not verified | User-guide part (Jeel), HUMAN |
| Step 5: commands run locally first, else "not verified" | verified | `docs/architecture.md` §12 and `docs/api.md` §9 |

## Blockers

- none for this part. Checking the architecture against the running staging deployment needs a staging window (IMD-137).

## Proposed decisions

- PD-IMP-707-2: update the specification §6.6.1 API-01 response to `{status, version, environment, provider}` and its health-check note from Render to the Express Mode health check, so §6 matches the contract (`docs/api.md` P-01, P-04).
- PD-IMP-707-3: update the specification §13.7 CI matrix to the built `ci.yml` (web build and `openapi-check` in `lint-types`, no separate `build` job) and `e2e.yml` (push to `main` and dispatch, no nightly, IMD-185) (`docs/architecture.md` A-10, A-11).

## Open issues

- When staging is next on, the deployed services, the RDS instance and the release-task log should be compared with `docs/architecture.md` §2 and §11 (A-06 to A-09) and the result recorded by the SG-7 gate.
