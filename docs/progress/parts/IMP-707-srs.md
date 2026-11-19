# IMP-707 · srs part

- Run id: RUN-083
- Owner: Malhar Mer (card lead; part "SRS and data model section", 2 points, issue #154)
- Status: PR_OPEN (commit on the batch branch; the pull request is opened by the operator)
- Base commit: `f75aa94`
- Branch: `S7B/docs-core` (batch branch of RUN-083; one commit for this part)

## Card text used (TASK_REGISTER.md, IMP-707)

Implementation step for this part:

1. Assemble docs/srs.md from this specification §2 and the blueprint; list every difference between documented and built behaviour (US-145 AC2).

Card step 5 applies to every part (drafting rule, summarised): draft from the repository and the specification only; run every documented command locally before writing it; mark commands that could not be run "not verified".

Acceptance criteria of the card:

- Each required document exists in docs/ with owner and version (US-145 AC1)
- The architecture document matches the deployed system or lists the differences (US-145 AC2)
- A member outside the platform squad completed README setup (time recorded) and a clean deployment answered /health (US-146 AC2, CHK-18)
- A new member created a trip and an itinerary from the user guide without help (US-146 AC1)
- make openapi-check is green, so docs/api.md points to a current contract

## Changed files

- `docs/srs.md` (created)
- `docs/progress/parts/IMP-707-srs.md` (created)

## What the document contains

- Scope, users, journey, constraints (specification §1, A1 §0 to §3).
- The 38 catalogue items plus C-13; the 88 MVP and MVP-S functional requirements (title, priority, release, module, sprint, tasks, tests, generated from §2.2); FR-136 to FR-140 (A1 §9.1); the cut extensions and the requirements outside the release.
- NFR-001 to NFR-050 with the evidence recorded so far; DR-01 to DR-36.
- Data model: migrations 0001 to 0007, the auth stub, a Mermaid ER diagram of the 17 tables and `auth.users`, writers (specification and code), RLS and the three locks, every column of every table (generated from the SQL and checked against it), indexes, enumerated values, transaction boundaries, seed and corpus data, lifecycle and the NFR-022 deletion procedure.
- 18 differences between documented and built behaviour (section 11), each with its source.

The blueprint is not in the repository, so the SRS is assembled from the specification §2 (which is generated from the blueprint registries) and Amendment A1.

## Commands run

All in this run, Linux container, proxy variables unset, `PYTHONPATH=/home/user/wt-S7B-docs-core/apps/api`.

| Command | Result line (quoted exactly) |
| --- | --- |
| `diff apps/api/migrations/sql/0007_rag_store.sql docs/spec/sql/0007_rag_store.sql` and `diff -q` for 0001 to 0006 | no output (identical) |
| `cd apps/api && .venv/bin/alembic heads` | `0007 (head)` |
| `cd apps/api && .venv/bin/alembic history` | `0006 -> 0007 (head), 0007 RAG store: pgvector, rag_documents and rag_chunks, item citations and retrieval record (A1 §5.3).` (last of seven lines; first `<base> -> 0001, 0001 helpers: the updated_at trigger functions (Appendix A.2).`) |
| `cd apps/api && .venv/bin/python -m app.rag.index --help` | `usage: python -m app.rag.index [-h] [--destination SLUG] [--check] [--strict]` |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` (exit 0) |
| `make imports` | `Contracts: 6 kept, 0 broken.` (exit 0) |
| `make lint` | `All checks passed!` … `All matched files use Prettier code style!` (exit 0) |
| `make typecheck` | `Success: no issues found in 123 source files` (exit 0) |
| `make test-unit` | `1210 passed, 1 warning in 20.91s` (exit 0) |
| `make test-contract` | `91 passed, 2 deselected, 1 warning in 20.26s` (exit 0) |
| `make test-web` | `Tests  288 passed (288)` (exit 0) |

Lead's counts of this run (base `f75aa94`, compose test database), quoted as given: `make test-api` → `590 passed, 1 warning in 276.11s (0:04:36)`; `make test-authz` → `87 passed, 14 skipped, 1 warning in 55.38s`.

## Not run

| Command | Reason |
| --- | --- |
| `make seed`, `make rag-index`, `make db-migrate`, `make db-reset`, `make test-api`, `make test-authz` (by this agent) | Need a database; the run rules forbid using the shared database, Docker or the Supabase stack. The lead ran `make test-api` and `make test-authz` (counts above) |
| `python -m app.db.auth_stub --if-missing`, `python -m app.db.admin delete-user --user-id <uuid>` | Need a database (and AWS for the operator procedure); marked "not verified" in the document |

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| Each required document exists in docs/ with owner and version (US-145 AC1), for `docs/srs.md` | verified | Header table of `docs/srs.md`: owner Malhar Mer, version 1.0 (draft for SG-7), 19 November 2026. The other documents of the card belong to other parts |
| Step 1: SRS assembled from §2; every difference between documented and built behaviour listed (US-145 AC2) | verified for the repository state; not verified against the deployed system | Section 11 lists 18 differences, each traced to a decision-register entry, gate record, deferred list or file at `f75aa94`. Staging was not reachable in this run (IMD-137), so behaviour on the deployed system is not compared |
| Data model matches migrations 0001 to 0007 in the repository | verified | Column tables generated from the SQL of `apps/api/migrations/sql/`, retention default and the four 0007 columns added by hand and checked against the SQL; 17 tables match the 17 `__tablename__` entries in `apps/api/app/db/models/`; `alembic heads` prints `0007 (head)` |
| Step 5: every documented command run locally first, else "not verified" | verified | Section 12 of `docs/srs.md` lists the commands run and those marked not verified |
| The architecture document matches the deployed system or lists the differences (US-145 AC2) | not verified (other part) | Part architecture-api (Manal) |
| A member outside the platform squad completed README setup (time recorded) and a clean deployment answered /health (US-146 AC2, CHK-18) | not verified | HUMAN step 6; needs a member and a clean AWS account |
| A new member created a trip and an itinerary from the user guide without help (US-146 AC1) | not verified | User-guide part (Jeel), HUMAN |
| make openapi-check is green, so docs/api.md points to a current contract | verified (command); docs/api.md is the architecture-api part | `make openapi-check` exit 0 in this run |

## Blockers

- none for this part. Card step 6 (onboarding and deployment-guide trial) and the user-guide and deployment-guide parts are outside this part.

## Proposed decisions

- PD-IMP-707-1: record in the specification §5.2 and §3.9 that `trip_places` is written by MOD-B03 (`app/trips/repository.py`) as IMD-190 decided for saved places, so the writer table matches the code (SRS D-04).

## Open issues

- The SRS states the repository state at `f75aa94`. Staging items (D-16), destination 2 (D-15), IMP-705 and IMP-706 (D-18) change after this run; the gate card SG-7 should update section 11.
