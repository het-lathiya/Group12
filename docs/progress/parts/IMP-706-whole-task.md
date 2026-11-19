# IMP-706 · whole-task part

- Run id: RUN-083
- Owner: Manya (Manya Rana), 3 points; issue #153
- Status: PARTIAL (all five documents drafted and marked Proposed; the blueprint content they name still has to be confirmed by Manya)
- Base commit: f75aa949fe306361d2f515ede632504518d19b63 (on top of the IMP-705 commit of the same batch branch, its prerequisite)
- Branch: S7B/eval (batch branch; card branch name `feat/IMP-706-<short>`)
- Traces to: US-132; CHK-23; FR-121, FR-122 (Stage 2); NFR-023 (TC-361)
- Card steps built: 1 to 5. Documents only.

## Changed files

- `docs/stage2/README.md` (created)
- `docs/stage2/migration-gate-criteria.md` (created)
- `docs/stage2/data-governance-policy.md` (created)
- `docs/stage2/dataset-schema.md` (created)
- `docs/stage2/data-card-template.md` (created)
- `docs/progress/parts/IMP-706-whole-task.md` (created)

No other file is changed. There is no training code, export script, fine-tuned adapter, training data or result claim.

## Sources used

`docs/spec/IMPLEMENTATION_SPEC.md` (§1.3, §2.6, §4.1, §4.5, §8.4, §8.11, §8.12, §8.16, FR-118, NFR-004, NFR-023, NFR-046), `docs/spec/AMENDMENT_A1_AWS_RAG.md` (§6.3, §6.14), `docs/spec/DECISION_REGISTER.md` (PD-03, PD-06, PD-08, PD-09, PD-13, PD-14, OD-10, OD-13, OD-17, IMD-31, IMD-92, IMD-125, IMD-176, IMD-181, IMD-185, IMD-195, IMD-200), `contracts/ai/gr-1.schema.json`, `contracts/ai/io-1.schema.json` (and gr-2 / io-2 for the open point), `eval/reports/baseline-1.md`, `eval/reports/final-baseline.md` (IMP-705, this batch). The blueprint (§18.8, §22, §33.4) is not in the repository. Every place that depends on it says "to be confirmed against blueprint §NN by Manya".

## Commands run

Run from the part worktree with `PYTHONPATH` set to its `apps/api` and the proxy variables unset. The database was `travel_eval` (compose PostgreSQL 16 with pgvector).

| Command | Result line (quoted exactly) |
| --- | --- |
| `make check` (first run; the IMP-705 seed and index were still in `travel_eval`, and `DB_AUTH_STUB=true` was set) | `make lint`: `All checks passed!`, `234 files already formatted`, `All matched files use Prettier code style!`; `make typecheck`: `Success: no issues found in 123 source files`, `✓ Types generated successfully`; `make imports`: `Contracts: 6 kept, 0 broken.`; `make openapi-check`: `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date`; `make test-unit`: `1210 passed, 1 warning in 20.22s`; `make test-contract`: `91 passed, 2 deselected, 1 warning in 19.95s`; `make test-api`: `21 failed, 569 passed, 1 warning in 191.50s (0:03:11)` (stopped there) |
| `python -m app.db.reset` then `make db-bootstrap` (`travel_eval` only, back to migrated and empty) | `db-reset: schema public dropped and recreated`; alembic ran up to `0007` |
| `make test-api test-authz test-web` (`DB_AUTH_STUB=true` still set) | `1 failed, 589 passed, 1 warning in 275.30s (0:04:35)` (`test_me.py::test_a_valid_token_for_a_deleted_account_is_401`: with `DB_AUTH_STUB` true the API mirrors the auth user by design, `app/auth/deps.py`) |
| `make test-api test-authz test-web` (`DB_AUTH_STUB` unset) | `590 passed, 1 warning in 271.88s (0:04:31)`; `87 passed, 14 skipped, 1 warning in 56.93s`; `Test Files  43 passed (43)` / `Tests  288 passed (288)` |
| `grep -rniE "training\|fine.?tun\|jsonl"` over `apps/api/app` and `apps/web/lib/api/schema.d.ts` | only the FINETUNED_MODEL stub, the factory refusal, config and the evaluation dataset readers; no export path |

The 21 failures of the first `make test-api` came from the database state this batch had created: tests expecting an empty RAG index or no seeded destinations, plus the `DB_AUTH_STUB` case. After the reset and with `DB_AUTH_STUB` unset, every suite passed. The changes of this part are documents only.

## Not run

| Command | Reason |
| --- | --- |
| A test tagged TC-361 | no test in the repository carries TC-361 (the card says it lives with the IMP-702 security checks). Evidence is the code search above and the full suites passing |
| `make e2e` | the part touches no journey |

## Acceptance criteria

| Criterion | Status (verified / not verified) | How |
| --- | --- | --- |
| All five files exist under docs/stage2/, each marked Proposed with owner and date (US-132 AC1, CHK-23) | verified | Each file starts with "Status: Proposed", "Owner: Manya (Manya Rana)", "Date: 19 November 2026" |
| README.md states that fine-tuning is not part of the eight-week commitment (US-132 AC2) | verified | `docs/stage2/README.md`, section "Position" |
| The PR changes no file outside docs/stage2/ and make check stays green | verified for this part's commit; `make check` green except as noted | This commit changes only `docs/stage2/` and this part record (the record is required by CLAUDE.md §11). Every `make check` step passed: lint, typecheck, imports, openapi-check, unit and contract in the first run; api, authz and web in the last run on a clean database |
| TC-361 still passes: no code path exports user data to training files | not verified by a test (no TC-361 test exists) | The code search found no export path, and this part adds no code |
| Migration-gate criteria E1 to E7 from blueprint §22 and §33.4 | not verified | The blueprint is not in the repository. E1 to E7 are listed as "to be confirmed against blueprint §22 and §33.4 by Manya", and repository-derived candidate criteria (C1 to C5, G1 to G12) are drafted with every threshold Proposed |

## Blockers

- The blueprint (§18.8, §22, §33.4) is not in the repository, so E1 to E7, the consent-process content, the storage and retention rules, and the approval owner cannot be copied. Manya confirms them against the blueprint.

## Proposed decisions

- **PD-IMP-706-1: schema versions of Stage 2 examples.** The card names gr-1 / io-1, while the active prompt v2 (IMD-200) uses gr-2 / io-2. Decide which pair a Stage 2 training example uses (`docs/stage2/dataset-schema.md`, "Open point").
- **PD-IMP-706-2: TC-361 evidence.** No test carries TC-361. Either add a test tag to an existing security check or record TC-361 as verified by code review in the SG-7 gate.

## Open issues

- The comparison values in migration-gate-criteria.md use baseline-1 for Gemini, because the final Gemini run of IMP-705 is not measured (no key in the run environment).
