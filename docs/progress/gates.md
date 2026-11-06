# Gate results

One section per sprint gate (specification §14.1). The gate card of each sprint records the result (pass, pass with listed gaps, or fail), the exit code of each check, open defects and carry-over tasks under its heading.

## SG-1 end of week 1: runnable skeleton and contracts in place (IMP-199)

Status: **pass with listed gaps**

- Run: RUN-017 (IMP-199, Kirtan), 2 November 2026. Part record: [IMP-199-whole-task.md](parts/IMP-199-whole-task.md).
- Commit verified on a clean clone: `4764c5f` (`main` at preflight). `main` then moved to `887e25e` when PR #200 (IMP-113, documentation only) merged at 08:51 UTC; CI and deploy-staging on `887e25e` are recorded below.
- Clean clone: `git clone https://github.com/het-lathiya/Group12.git` into a temporary directory outside the working copy; no `.env` file read or written; the clone was deleted at the end.

### Criteria

| # | Criterion (card IMP-199) | Result | Evidence |
| --- | --- | --- | --- |
| 1 | All commands of step 1 exit 0 on a clean clone | pass | Table "Step 1 on a clean clone" below: six commands, each exit 0 |
| 2 | Local sign-up, sign-in and sign-out work against the Supabase local stack | pass | In the clean clone, local stack keys passed as environment variables only (as RUN-008): `make e2e ARGS='auth'` `  20 passed (32.3s)` (TC-051, TC-052, TC-053 sign-up; TC-054, TC-056 sign-in, reload, sign-out); `make e2e ARGS='smoke'` `  12 passed (11.1s)` (signed-in dashboard and signed-out redirect); `make api` then `curl http://localhost:8000/health`: `{"status":"ok","version":"dev","environment":"local","provider":"MOCK"}` HTTP 200 |
| 3 | CI on main is green (lint, types, imports, unit, guards, audit, api) | pass | [CI run 41416050824](https://github.com/het-lathiya/Group12/actions/runs/41416050824) on `887e25e` (push): lint-types, unit, guards, audit, api success; attribution skipped (it runs on pull requests only). [CI run 41415156650](https://github.com/het-lathiya/Group12/actions/runs/41415156650) on `4764c5f`: the same |
| 4 | Staging `/health` returns 200, or the deployment is recorded as blocked by accounts with an owner | pass (blocked, recorded) | **Deployment blocked by IMP-113, owner Kirtan, 2026-11-02.** IMP-113 merged as templates only (PR #200); no hosted account exists yet. [deploy-staging run 41416325367](https://github.com/het-lathiya/Group12/actions/runs/41416325367) on `887e25e`: success, log line `staging not configured (blocked by IMP-113)` (also [run 41415419222](https://github.com/het-lathiya/Group12/actions/runs/41415419222) on `4764c5f`). Local container smoke (RUN-016 path) in the clean clone: `docker compose ... --profile api up -d --build --wait api` ` Container sg1-clone-api-1 Healthy `; `make smoke URL=http://localhost:8000` `========================= 4 passed, 1 skipped in 0.08s =========================`; with `ARGS='--web-origin http://localhost:3000'` `============================== 5 passed in 0.04s ===============================` |
| 5 | SG-1 entry in docs/progress/gates.md states the result and the evidence links | pass | This entry |

### Step 1 on a clean clone (`4764c5f`)

| Command | Exit | Last line |
| --- | --- | --- |
| `make setup` | 0 | `setup: Playwright browsers skipped (make setup ARGS=--with-browsers installs Chromium)` |
| `make stack-up` | 0 | `  Never paste these values into a tracked file, an issue or a pull request (docs/secrets.md).` |
| `make db-up` | 0 | ` Container sg1-clone-db-1 Healthy ` |
| `make db-migrate DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:54322/postgres` | 0 | `INFO  [alembic.runtime.migration] Will assume transactional DDL.` (`alembic current`: `0006 (head)`) |
| `APP_ENV=local DATABASE_URL=<same> make seed` | 0 | `seed sampleton: opening hours replaced for 27 places, unchanged for 3` |
| `make check TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/travel_test` | 0 | `   Duration  6.86s (environment 60%, setup 16%, transform 9%, tests 8%, import 7%)` |

`make check` parts: ruff `All checks passed!`; Prettier `All matched files use Prettier code style!`; mypy `Success: no issues found in 47 source files`; import-linter `Contracts: 3 kept, 0 broken.`; `openapi-check: not yet implemented (IMP-214)`; unit `201 passed, 1 warning in 4.98s`; contract `11 passed in 0.07s`; api `64 passed, 1 warning in 3.57s` (includes the schema-drift test); authz `9 passed in 0.44s`; web `Tests  48 passed (48)`.

Note on `make db-migrate`: the Supabase CLI keeps its database volume across `make stack-down`, so the local stack was already at `0006` from earlier runs and the upgrade had nothing to do. Migration from a blank schema was shown in the same clone on the compose db (`public` dropped, then `make db-migrate`: six `Running upgrade` lines ending `Running upgrade 0005 -> 0006`) and runs on every `api` job in CI (TC-337).

### Contracts on main (step 3)

| Contract | Path | Present |
| --- | --- | --- |
| AI schema gr-1 | `contracts/ai/gr-1.schema.json` | yes |
| AI schema io-1 | `contracts/ai/io-1.schema.json` | yes |
| Error envelope | `apps/api/app/schemas/common.py` (`ErrorCode`, `ErrorDetail`, `ErrorBody`, `ErrorEnvelope`) | yes |
| Migrations 0001-0006, one Alembic head | `apps/api/migrations/sql/0001_helpers.sql` to `0006_updated_at_triggers.sql`; `apps/api/migrations/versions/0001_helpers.py` to `0006_updated_at_triggers.py`; `alembic heads`: `0006 (head)` | yes |
| Environment template | `.env.example` | yes |
| Project instructions | `CLAUDE.md` | yes |

### Working-agreement audit (IMD-68)

Every pull request merged from the start of the project to 2 November 2026 (`gh pr list --state merged`), 14 in all. All were merged by the operator account `het-lathiya`. "Checks green" means all six required checks succeeded on the merged head commit.

| PR | Title | reviewDecision | Approving reviewer | Reviewer owns a part of the card / is the operator | Checks green on merged head | Meets the agreement |
| --- | --- | --- | --- | --- | --- | --- |
| #1 | IMP-101 · repo-tree-makefile part | none | none (Junaid-Kureshi requested) | n/a | n/a (no checks: CI was added by PR #3) | **no**: no approval, no checks |
| #2 | IMP-101 · api-pyproject-guard part | APPROVED | kirtan-S111 | yes, owns repo-tree-makefile of IMP-101 / no | n/a (no checks: CI was added by PR #3) | **no**: no checks; reviewer owns a part of the card |
| #3 | IMP-102 · whole task | none | none (Junaid-Kureshi requested) | n/a | yes (6/6) | **no**: no approval |
| #190 | IMP-103 · whole task | none | none (kirtan-S111 requested) | n/a | yes (6/6) | **no**: no approval |
| #191 | IMP-105 · whole task | none | none (jeelfefar2141 requested) | n/a | yes (6/6) | **no**: no approval |
| #192 | IMP-104 · whole task | none | none (Assassin-byte requested) | n/a | yes (6/6) | **no**: no approval |
| #193 | IMP-106 · sql-migrations and orm-drift-fixture parts | none | none (kirtan-S111 requested) | n/a | yes (6/6) | **no**: no approval |
| #194 | IMP-109 · whole task | none | none (Manasvi1704 requested) | n/a | yes (6/6) | **no**: no approval |
| #195 | IMP-110 · whole task | none | none (kirtan-S111 requested) | n/a | yes (6/6) | **no**: no approval |
| #196 | IMP-108 · whole task | none | none (manalPatel2557 requested) | n/a | yes (6/6) | **no**: no approval |
| #197 | IMP-107 · whole task | none | none (Malhar1112-v requested) | n/a | yes (6/6) | **no**: no approval |
| #198 | IMP-111 · whole task | none | none (Nidhi9864 requested) | n/a | yes (6/6, after a cancelled first run) | **no**: no approval |
| #200 | IMP-113 · accounts-secrets-register, ors-email-sender and gemini-key-terms parts | none | none | n/a | yes (6/6) | **no**: no approval; merged during this gate run while expected to stay a draft |
| #202 | IMP-112 · whole task | none | none (Junaid-Kureshi requested) | n/a | yes (6/6) | **no**: no approval |

Summary: 14 merged; 1 with an approval (#2, from a reviewer who owns another part of the card); 12 with all six checks green on the merged head and 2 that predate CI; **no merged pull request meets the working agreement in full**, because 13 have no approving review. Nothing was changed on these pull requests. Every merged pull request has its part records on `main`.

### Gaps and open defects

- No severity 1 or 2 defect found in the gate's scope.
- Staging not deployed: blocked by IMP-113 (accounts), owner Kirtan, 2026-11-02 (the gate's acceptable known defect).
- Working agreement not met by any merged pull request (audit above); TC-343's "cannot be merged" half stays not verified (IMD-79).
- TC-335 setup walkthrough: about 100 minutes against a 60-minute target (NFR-032 not met; measured by Nidhi on 1 November 2026).
- No screenshot of a local sign-in was taken in this run (the SG-1 evidence column lists one); sign-in is shown by the Playwright auth run above, and the IMP-109 record holds its sign-up screenshot.

### Carry-over

| Item | Owner | Reference |
| --- | --- | --- |
| IMP-113 outcomes: accounts, secrets register, OpenRouteService key, email sender, Gemini key and terms (templates merged, results "TO BE FILLED") | Kirtan, Junaid, Nidhi | PR #200 (merged as templates) |
| IMP-114 stakeholder interviews round 1 | Junaid, Krrish | draft PR #201 |
| IMP-115 seed-data plan and the two demo destinations | Malhar | draft PR #199 |
| IMP-112 hosted half: staging deployment, staging `/health` 200, hosted RLS check | Kirtan | `docs/guides/deployment.md`; after IMP-113 |
| TC-335 over target (100 minutes against 60): shorten `docs/guides/local-setup.md` or the image download step | Malhar (guide owner) | NFR-032 |
| PD-H follow-up: `make setup` upgrades `pip` in the venv so the pip audit can become blocking | Kirtan | IMD-76 |
| AuthGuard loads `['me']` (API-03) once | web, later card (IMP-601, Het) | IMP-108 and IMP-109 records |
| `apps/web/lib/api/client.ts` generated client | Kirtan (IMP-214) | IMD-98 |
| Start-up check that `PROMPT_TEMPLATE_VERSION` exists in the registry | Nidhi (IMP-208) | IMP-111 record |
| `repair.txt` for `itinerary_generate/v1` adds its line to `tests/fixtures/prompt_hashes.json` | Nidhi (IMP-502) | IMP-111 record |
| Working agreement: approvals before merge from now on | Kirtan (integration lead), all reviewers | IMD-68 |

## SG-2 end of week 2: walking skeleton (blueprint Gate 1, IMP-299)

Status: **pass with listed gaps**

- Run: RUN-044 (IMP-299, Kirtan), 6 November 2026. Index: [sprint-2.md](sprint-2.md).
- Commit verified: `0b361fc` (`main` at preflight), in the working copy on branch `chore/IMP-299-sg2-gate` before any file changed. No `.env` file was read.
- Scope of this result: the walking skeleton is shown locally and in CI. **Nothing is shown on AWS staging yet**, which is what the card and Amendment A1 §10.4 ask for. The result is the operator's, with the staging criteria carried as an open item due before SG-3.
- Sprint 2 cards: all 20 are merged and none is blocked ([sprint-2.md](sprint-2.md)).

### Criteria

| # | Criterion (specification §9.1 as amended by A1 §10.4) | Result | Evidence |
| --- | --- | --- | --- |
| 1 | A signed-in user creates a trip, generates with MOCK and sees the saved plan | pass (local and CI; on staging see row 4) | `make e2e ARGS='journey'` `  4 passed (26.5s)` in this run; [E2E run 42233148950](https://github.com/het-lathiya/Group12/actions/runs/42233148950) on `0b361fc`: success; [IMP-216 record](parts/IMP-216-whole-task.md) |
| 2 | A generation record exists | pass | IMP-210 tests in `make test-api`, `231 passed, 1 warning in 57.74s` in this run; the journey reads API-23 with provider `MOCK` and outcome `model`; [IMP-210 record](parts/IMP-210-whole-task.md) |
| 3 | Destination 1 loaded with its quality report | pass locally; staging load not verifiable until the AWS set-up | [quality_report.md](../../data/places/ahmedabad/quality_report.md): 103 usable against a minimum of 100. In this run: `seed ahmedabad: gate loaded 103, rejected 0, flagged 0` (`--check --strict`). Local load: [IMP-206 record](parts/IMP-206-lead-curation.md) |
| 4 | AWS staging: both Express services healthy, release task run, migration 0007 applied, `make smoke` against the staging API | not verifiable (open item, owner Kirtan, due before SG-3) | No AWS resource exists yet. [Deploy staging run 42233551590](https://github.com/het-lathiya/Group12/actions/runs/42233551590) on `0b361fc` is green only because it skips: notice `AWS staging not configured (blocked by IMP-217)`. No staging URL exists, so `make smoke` was not run. Migration 0007 is applied locally only (`alembic current`: `0007 (head)`) |
| 5 | Contract v1 declared, including `sources[]` and the `GenerationOut` retrieval fields | pass | [IMP-214 record](parts/IMP-214-whole-task.md); `make openapi-check` `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` and `make test-contract` `35 passed, 1 warning in 0.94s` in this run |
| 6 | Tag `contract-v1` | open item (operator) | `git tag --list 'contract-v1'` printed nothing and the remote has no such tag. To set it: `git tag contract-v1 1baa1f09b0b46d93f252602bf6f9a2364a6f543f` (the last commit of the IMP-214 merge, PR #227) and push the tag. Card step 4 also asks for the cross-squad contract review first; no record of one was found |
| 7 | `make check` | pass | Table below, exit 0; [CI run 42233148962](https://github.com/het-lathiya/Group12/actions/runs/42233148962) on `0b361fc`: success |
| 8 | `make test-authz` | pass | Part of `make check`: `28 passed in 12.72s` |
| 9 | `make e2e ARGS='journey'` | pass | `  4 passed (26.5s)` on the local stack, set up as in `e2e.yml`; [E2E run 42233148950](https://github.com/het-lathiya/Group12/actions/runs/42233148950) |
| 10 | Acceptable known defects | within the gate | Unbuilt endpoints answer 501 `NOT_IMPLEMENTED` (IMP-214) |

### Checks of this run (`0b361fc`)

| Command | Exit | Last line |
| --- | --- | --- |
| `make db-up` | 0 | ` Container group12-db-1 Healthy ` |
| `make check TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/travel_test` | 0 | `   Duration  6.30s (environment 61%, tests 16%, setup 14%, import 7%, transform 2%)` |
| `make db-down` | 0 | ` Network group12_default Removed ` |
| `make stack-up` | 0 | output discarded, because it holds the stack's keys |
| `make db-migrate` | 0 | `INFO  [alembic.runtime.migration] Will assume transactional DDL.` (`alembic current`: `0007 (head)`) |
| `make seed` | 0 | `seed sampleton: places inserted 0, updated 0, unchanged 30, deactivated 0` |
| `make e2e ARGS='journey'` | 0 | `  4 passed (26.5s)` |
| `make stack-down` | 0 | output discarded |
| `git tag --list 'contract-v1'` | 0 | prints nothing |

`make check` parts: ruff `All checks passed!`; ESLint `✖ 1 problem (0 errors, 1 warning)` (`window.location.assign` in `apps/web/lib/api/client.ts`); Prettier `All matched files use Prettier code style!`; mypy `Success: no issues found in 85 source files`; import-linter `Contracts: 4 kept, 0 broken.`; openapi-check up to date; unit `385 passed, 1 warning in 9.66s`; contract `35 passed, 1 warning in 0.94s`; api `231 passed, 1 warning in 57.74s`; authz `28 passed in 12.72s`; web `Tests  80 passed (80)`.

The API for the journey was started by hand as in `e2e.yml` (`APP_ENV=test`, `AI_PROVIDER=MOCK`, `DB_AUTH_STUB=false`, `SUPABASE_JWKS_URL`), with the stack's values held in the process environment only. The local stack keeps its database volume across `make stack-down`, so its migration step may have had nothing to do; migration from an empty database runs on every CI `api` job.

### Working-agreement audit (IMD-68)

Every pull request merged after the SG-1 audit, from `gh pr view <n> --json reviews,statusCheckRollup`: 30 in all, including the Sprint 1 cards and decisions that merged in this period. All were merged by the operator account `het-lathiya`. "Checks green" means all six required checks succeeded on the merged head commit.

| PR | Title | reviewDecision | Approving reviewer | Checks green on merged head | Meets the agreement |
| --- | --- | --- | --- | --- | --- |
| #199 | IMP-115 · whole task | none | none (Junaid-Kureshi requested) | yes (6/6) | **no**: no approval |
| #203 | IMP-199 · whole task | none | none (Junaid-Kureshi requested) | yes (6/6) | **no**: no approval |
| #204 | IMP-203 · whole task | none | none (kirtan-S111 requested) | yes (6/6) | **no**: no approval |
| #205 | IMP-205 · import-quality-gate and places-api-search parts | none | none (kirtan-S111 requested) | yes (6/6) | **no**: no approval |
| #206 | IMP-205 · places-api-search part (service layer) | none | none (kirtan-S111 requested) | yes (6/6) | **no**: no approval |
| #207 | IMP-204 · whole task | none | none (kirtan-S111 requested) | yes (6/6) | **no**: no approval |
| #208 | IMP-207 · whole task | none | none (Nidhi9864 requested) | yes (6/6) | **no**: no approval |
| #209 | IMP-202 · whole task | none | none (Malhar1112-v requested) | yes (6/6) | **no**: no approval |
| #210 | IMP-208 · whole task | none | none (manyarana requested) | yes (6/6) | **no**: no approval |
| #211 | IMP-209 · whole task | none | none (kirtan-S111 requested) | yes (6/6) | **no**: no approval |
| #226 | IMD-99 · Amendment A1: AWS hosting and RAG pipeline | none | none (Nidhi9864 requested) | yes (6/6) | **no**: no approval |
| #227 | IMP-214 · whole task | none | none (kirtan-S111, Junaid-Kureshi requested) | yes (6/6) | **no**: no approval |
| #228 | IMP-311 · whole task | none | none (kirtan-S111 requested) | yes (6/6) | **no**: no approval |
| #229 | IMP-219 · whole task | none | none (manalPatel2557 requested) | yes (6/6) | **no**: no approval |
| #231 | IMP-201 · whole task | none | none (Junaid-Kureshi requested) | yes (6/6) | **no**: no approval |
| #232 | IMP-210 · whole task | none | none (manalPatel2557 requested) | yes (6/6) | **no**: no approval |
| #233 | IMP-215 · whole task | none | none (kirtan-S111 requested) | yes (6/6) | **no**: no approval |
| #234 | IMD-117 · screen drafts as design references | none | none (kirtan-S111 requested) | yes (6/6) | **no**: no approval |
| #235 | IMP-212 · whole task | none | none (Assassin-byte requested) | yes (6/6) | **no**: no approval |
| #236 | IMP-211 · whole task | none | none (manalPatel2557 requested) | yes (6/6) | **no**: no approval |
| #237 | IMD-118 · UI design guide and theme tokens | none | none (Assassin-byte requested) | yes (6/6) | **no**: no approval |
| #238 | IMD-119 · in-progress conflict names the active generation | none | none (manalPatel2557 requested) | yes (6/6) | **no**: no approval |
| #239 | IMP-213 · whole task | none | none (Manasvi1704 requested) | yes (6/6) | **no**: no approval |
| #240 | IMD-120 · desk-checked seed data and plan for destination 1 | none | none (Junaid-Kureshi requested) | yes (6/6) | **no**: no approval |
| #241 | IMP-213 · fix flaky timeout test | none | none (Manasvi1704 requested) | yes (6/6) | **no**: no approval |
| #242 | IMP-206 · lead-curation and hours-prices parts | none | none (kirtan-S111 requested) | yes (6/6) | **no**: no approval |
| #243 | IMP-217 · whole task | none | none (Junaid-Kureshi requested) | yes (6/6) | **no**: no approval |
| #244 | IMP-210 · fix job-timeout race | none | none (manalPatel2557 requested) | yes (6/6) | **no**: no approval |
| #245 | IMP-218 · deploy-workflows and web-image parts | none | none (kirtan-S111 requested) | yes (6/6) | **no**: no approval |
| #246 | IMP-216 · whole task | none | none (Junaid-Kureshi requested) | yes (6/6) | **no**: no approval |

Summary: 30 merged; **0 with an approval**; 30 with all six checks green on the merged head. **No merged pull request meets the working agreement in full.** Exceptions: all 30 lack an approving review, and #227 also requested its own part owner (kirtan-S111) as a reviewer. The SG-1 carry-over "approvals before merge from now on" was not met. Nothing was changed on these pull requests.

### Gaps and open defects

- Staging criteria not shown (row 4); tag `contract-v1` not set (row 6).
- Working agreement not met by any merged pull request (audit above).
- The defects under Open items carry no severity in the part records. None stops the journey, which passes.
- Evidence the card lists and this run does not have: staging screenshots, the screenshot of the saved plan, the cross-squad contract review and the point-scale recalibration of card step 5.

### Open items

| Item | Owner | Due |
| --- | --- | --- |
| AWS set-up, first deploy (TC-437), forced failure (TC-438), staging smoke and CORS, IMP-216 staging walk-through, IMP-206 staging load, NFR-005 first-request time, TC-433 to TC-436 | Kirtan | before SG-3 |
| Tag `contract-v1` (row 6) | operator | before SG-3 |
| IMP-113 outcome: accounts, Gemini terms and model IDs, ORS key and email sender | Kirtan, Nidhi, Junaid | before SG-3 |
| IMD-120: confirm the plan answers and fill the "not stated" fields | Malhar | before SG-3 |
| IMD-120: review the plan and the 20 percent sample (US-026 AC3), recorded in `docs/progress/parts/IMP-206-review.md`, since `quality_report.md` is written by the seed | Junaid | before SG-3 |
| IMD-120: check the 60 unverified rows | Jeel, Malhar | before SG-3 |
| IMP-114 interviews (draft #201), by operator decision of 6 November 2026 | Junaid, Krrish | after Sprint 3, before SG-4 |
| F-1: `Money.currency` lacks the three-letter pattern (`app/schemas/common.py`) | Kirtan | next change to that file |
| F-3: `BudgetStatus` shows an excess when not exceeded | Manal | IMP-308 |
| F-2: `AmountRange` min greater than max | team (proposed decision) | next decision run |
| `IllegalTransitionError` when a job timeout fires after the plan commit | Het | IMP-305, Het's part |
| `user_hash` empty in access logs (one line in `app/auth/deps.py`) | Kirtan | next change to that file |
| No committed ES256 token test | Het | IMP-108 area |
| Control radius scale and cards at 16.8 px instead of 12 px; a foreign trip shows the empty itinerary state | Manasvi | IMP-309 |
| No axe tooling for NFR-025 | Krrish | IMP-513, IMP-703 |
| Local guide lacks `SUPABASE_JWKS_URL` and the env values needed without `.env` files, and should name `make db-bootstrap` for a plain database | Kirtan | next DevOps card |
| `docs/guides/README.md` lacks `ui-design.md` and `screen-drafts.md` | next docs change | next docs change |
| Manasvi's commits show no GitHub account until 202301108@dau.ac.in is verified on her account (no repository change) | Manasvi | no date set |
| PR #230 stays open outside the plan (operator decision); PR #201 stays a draft | operator | none |

## SG-3 end of week 3: Gemini vertical slice (blueprint Gate 2, IMP-399)

Status: not run

## SG-4 end of week 4: core reliability (blueprint Gate 3, IMP-499)

Status: not run

## SG-5 end of week 5: trip management (IMP-599)

Status: not run

## SG-6 end of week 6: MVP feature freeze (IMP-699)

Status: not run

## SG-7 end of week 7: release candidate and extension freeze (IMP-799)

Status: not run

## SG-8 week 8: release and demo (IMP-899)

Status: not run
