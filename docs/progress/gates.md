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
| 6 | Tag `contract-v1` | open item (operator) | `git tag --list 'contract-v1'` printed nothing and the remote has no such tag. To set it: `git tag contract-v1 1baa1f09b0b46d93f252602bf6f9a2364a6f543f` (the last commit of the IMP-214 merge, PR #227) and push the tag. Card step 4 also asks for the cross-squad contract review first; no record of one was found. tag after contract review by Kirtan (CODEOWNER contracts/) and Manasvi (consumer), recorded as review comments on PR #247; operator tags 1baa1f0 |
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

From SG-2 onward the pre-merge gate requires reviewDecision APPROVED (operator decision of 6 November 2026)

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
| Manasvi's commits show no GitHub account until her college address is verified on her account (no repository change) | Manasvi | no date set |
| proposed decision, team to decide before SG-3: PD-IMP-203-4, `budget.currency` must equal the destination currency (§9.3.2), which contradicts the API-07 worked example in §6.7 ([record](parts/IMP-203-whole-task.md)) | team | before SG-3 |
| proposed decision, team to decide before SG-3: PD-IMP-204-5, `PreferencesOut.must_visit_places` is in contract v1 but not in §6.5 ([record](parts/IMP-204-whole-task.md)) | team | before SG-3 |
| proposed decision, team to decide before SG-3: PD-IMP-204-7, duplicate `interests` or `must_visit_place_ids` answer 422, a rule §6 does not state ([record](parts/IMP-204-whole-task.md)) | team | before SG-3 |
| proposed decision, team to decide before SG-3: PD-IMP-205-3, the `min_usable_places` key in `destination.json` is not in the §5.6 file format ([record](parts/IMP-205-import-quality-gate.md)) | team | before SG-3 |
| proposed decision, team to decide before SG-3: PD-IMP-205-7, API-16 answers an empty page for an inactive or unknown destination, while §6.2 says inactive destinations are invisible (404) ([record](parts/IMP-205-places-api-search.md)) | team | before SG-3 |
| proposed decision, team to decide before SG-3: PD-IMP-205-8, the API-16 `category` filter refuses `stay` with 422, a rule API-16 does not state ([record](parts/IMP-205-places-api-search.md)) | team | before SG-3 |
| PR #230 stays open outside the plan (operator decision); PR #201 stays a draft | operator | none |

## SG-3 end of week 3: Gemini vertical slice (blueprint Gate 2, IMP-399)

Status: **pass with listed gaps**

- Run: RUN-055 (IMP-399, Nidhi), 7 November 2026. Index: [sprint-3.md](sprint-3.md).
- Commit verified: `5eaf19f` (`main` at preflight), with only the IMP-215 test-helper fix of this run on top, on branch `chore/IMP-399-sg3-gate`. No `.env` file was read and no Gemini call was made in this run; the Gemini evidence is the operator's, from the operator's local stack (WSL, Supabase CLI v2.122, `AI_PROVIDER=GEMINI`).
- Scope of this result: the Gemini and RAG slice is shown on the local stack. **Nothing is shown on AWS staging**, because staging is not ready. The card and Amendment A1 §10.4 ask for staging, so "pass with listed gaps" is the operator's decision of 7 November 2026; the staging criteria move to SG-4 (Kirtan).
- Sprint 3 cards: all 16 are merged and none is blocked; IMP-302 and IMP-310 did not slip ([sprint-3.md](sprint-3.md)).
- Team decisions D1 to D13 of 7 November 2026 are recorded as IMD-124 to IMD-136.

![Itinerary page of the local Gemini run with "Sources (1)" open](gates/sg3-local-gemini-itinerary.png)

### Criteria

| # | Criterion (card IMP-399 as amended by A1 §10.4) | Result | Evidence |
| --- | --- | --- | --- |
| 1 | A Gemini-generated plan is visible after validation and recalculation, and its record names provider, model and prompt version (TC-370) | pass on the operator's local stack; not verifiable on staging | `ai_generations` latest row, created 2026-11-07 16:42 UTC: `completed \| model \| GEMINI \| gemini-3.5-flash-lite \| v2 \| vector \| gemini-embedding-2 \| retrieval_ms 927 \| latency_ms 5835`. The page shows AI-written themes and notes, Curated and Unavailable cost labels, "Estimated travel time (distance based)" and recalculated times (09:00 start, 15-minute buffer); screenshot above. One generation only |
| 2 | `make check` green on `main` at the gate commit | pass | Table below, exit 0, on `5eaf19f` plus the IMP-215 test-helper commit; [CI run 42393259997](https://github.com/het-lathiya/Group12/actions/runs/42393259997) on `5eaf19f`: success |
| 3 | `make smoke` against staging | not verifiable | No staging URL exists. [Deploy staging run 42393440346](https://github.com/het-lathiya/Group12/actions/runs/42393440346) on `5eaf19f` is green only because `deploy-staging` is skipped |
| 4 | `retrieval_mode = vector` and at least one cited passage shown on the itinerary page (ACC-19) | pass locally; not verifiable on staging | Row 1 record has `vector`; "Sources (1)" lists show title, kind, source name, licence and retrieval date (screenshot) |
| 5 | Retrieval time p95 over 10 staging generations (NFR-050, TC-459) | not verifiable | No staging. One local value only: `retrieval_ms 927`. This is not a p95 and no NFR-050 claim is made |
| 6 | The release task log shows the destination-1 chunks embedded on staging | not verifiable; local strict index recorded | Local `make rag-index ARGS='--destination ahmedabad --strict'` with `gemini-embedding-2`: run 1 embedded 96, then exit 3 (embedding provider unavailable, per-minute limit); run 2 embedded 93 (`documents=118 chunks=189`, `warnings=0 errors=0`). All 189 chunks are embedded after two runs. **Finding:** one release task will not finish the index under the per-minute limit (open item). Seed: `ahmedabad` gate loaded 103, rejected 0; 29 sources |
| 7 | Live Gemini (TC-029) and live embeddings | pass | `make live-smoke` by the key holder on `fix/IMP-301-wire-schema` at `589ded8`: 2 passed (TC-029 and the live embedding test). Before the fix: 1 passed, 1 failed with HTTP 400 "too many states for serving". Cause: the schema's numeric, length and count limits; fix in [IMP-301 wire-schema](parts/IMP-301-wire-schema.md), rule IMD-136 (D13) |
| 8 | API-33 totals equal the engine output, not model values | pass by tests | `test_tc_140_stored_totals_equal_the_calculation_when_the_model_writes_its_own` and `tests/api/test_costs.py` ([IMP-308 budget-costs](parts/IMP-308-budget-costs.md), [IMP-308 schedule](parts/IMP-308-schedule.md)), part of `make check` here. Not checked by hand on the Gemini plan |
| 9 | IMP-302 and IMP-310 merged, not slipped | pass | #250 and #248 ([sprint-3.md](sprint-3.md)) |
| 10 | The gate decision is recorded; warnings may remain and no quality claim is made | pass | This entry. No quality claim is made |

### Checks of this run (`5eaf19f` plus the IMP-215 helper fix)

| Command | Exit | Last line |
| --- | --- | --- |
| `make db-up` | 0 | ` Container group12-db-1 Healthy ` |
| `make check TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/travel_test` | 0 | `   Duration  7.92s (environment 49%, tests 23%, import 15%, setup 10%, transform 3%)` |
| `make db-down` | 0 | ` Network group12_default Removed ` |
| `make stack-up` | 0 | output discarded, because it holds the stack's keys |
| `make db-migrate` | 0 | `INFO  [alembic.runtime.migration] Will assume transactional DDL.` |
| `make seed` | 0 | `seed sampleton: opening hours replaced for 0 places, unchanged for 30` |
| `make e2e ARGS='journey'` | 0 | `  4 passed (8.0s)` |
| `make stack-down` | 0 | output discarded |

`make check` parts: ruff `All checks passed!`; ESLint `✖ 1 problem (0 errors, 1 warning)`; Prettier `All matched files use Prettier code style!`; mypy `Success: no issues found in 105 source files`; import-linter `Contracts: 6 kept, 0 broken.`; openapi-check up to date; unit `844 passed, 1 warning in 20.18s`; contract `87 passed, 2 deselected, 1 warning in 4.59s`; api `334 passed, 1 warning in 125.36s (0:02:05)`; authz `31 passed in 21.42s`; web `Tests  119 passed (119)`.

The API for the journey was started by hand as in `e2e.yml` (`APP_ENV=test`, `AI_PROVIDER=MOCK`, `DB_AUTH_STUB=false`, `SUPABASE_JWKS_URL`), with the stack's values held in the process environment only. The journey uses MOCK, so it shows the flow and not Gemini.

Latest runs on `main` at `5eaf19f`: [CI 42393259997](https://github.com/het-lathiya/Group12/actions/runs/42393259997) success; [E2E 42393260038](https://github.com/het-lathiya/Group12/actions/runs/42393260038) success; [Deploy staging 42393440346](https://github.com/het-lathiya/Group12/actions/runs/42393440346) success with the deploy job skipped.

### Authorization flake found in RUN-054 (IMP-215 follow-up)

`tests/authz/test_ownership.py[API-07 POST /api/v1/trips]` got a 401 once in 8 runs. Cause found: on WSL `systemd-timesyncd` steps the wall clock back by up to about 0.35 s every 30 s or so, the test helper set `iat` to the current second, and PyJWT rejects `iat` in the future with no leeway. Fixed in the test helper, with no change to product code; `make test-authz` then passed 20 of 20 in a loop on the same machine. Details: [IMP-215 authz-tokens](parts/IMP-215-authz-tokens.md).

### Working-agreement audit (IMD-68)

Pull requests #248 to #257, from `gh pr view <n> --json reviews,statusCheckRollup`. All were merged by the operator account `het-lathiya`. "Checks green" means all six required checks succeeded on the merged head commit.

| PR | Title | reviewDecision | Approving reviewer | Checks green on merged head | Meets the agreement |
| --- | --- | --- | --- | --- | --- |
| #248 | IMP-304 · IMP-307 · IMP-310 · Sprint 3 wave 1: retrieval, routing, evaluation set | none | none (manalPatel2557 requested) | yes (6/6) | **no**: no approval |
| #249 | IMP-303 · IMP-301 · Sprint 3 wave 1: generation request and Gemini adapter | none | none (Nidhi9864, kirtan-S111 requested) | yes (6/6) | **no**: no approval; Nidhi9864 owns a part |
| #250 | IMP-312 · IMP-305 · IMP-302 · Sprint 3 wave 2: embeddings, generation pipeline, provider health | none | none (Nidhi9864, kirtan-S111, manyarana requested) | yes (6/6) | **no**: no approval; Nidhi9864 and kirtan-S111 own parts |
| #251 | IMP-306 · IMP-313 · Sprint 3 wave 3: output validation and RAG indexing | none | none (Nidhi9864, kirtan-S111 requested) | yes (6/6) | **no**: no approval |
| #252 | IMP-315 · IMP-308 · Sprint 3 wave 4: hybrid retrieval, schedule and costs | none | none (kirtan-S111 requested) | yes (6/6) | **no**: no approval |
| #253 | IMP-309 · IMP-314 · Sprint 3: day-wise itinerary view and Ahmedabad guides | none | none (kirtan-S111 requested) | yes (6/6) | **no**: no approval |
| #254 | IMP-316 · grounded generation with validated citations | none | none (Nidhi9864, kirtan-S111 requested) | yes (6/6) | **no**: no approval |
| #255 | IMP-317 · whole task | none | none (Assassin-byte requested) | yes (6/6) | **no**: no approval |
| #256 | IMP-301 · wire-schema fix | none | none (Nidhi9864, manyarana requested) | yes (6/6; a first run on the same head was cancelled by the second) | **no**: no approval; Nidhi9864 owns the part |
| #257 | SG-3 prep · staging Gemini settings and account facts | none | none (Junaid-Kureshi requested) | yes (6/6) | **no**: no approval |

Summary: 10 merged; **0 with an approval**; 10 with all six checks green on the merged head. **No merged pull request meets the working agreement in full.** Exceptions: all 10 lack an approving review, although the operator decision of 6 November 2026 made reviewDecision APPROVED a pre-merge requirement from SG-2 onward; #249, #250 and #256 also requested a part owner as a reviewer. Nothing was changed on these pull requests.

### Gaps and open defects

- Every staging criterion (rows 1, 3, 4, 5 and 6) is not shown. Row 5 has one local value and no p95.
- The Gemini evidence is one generation on one local stack, reported by the operator. No Gemini run happened in this gate run.
- Working agreement not met by any merged pull request (audit above).
- Evidence the card lists and this run does not have: a staging screenshot and a CI-side Gemini record, since live calls never run in CI.
- PD-IMP-307-2, PD-IMP-307-3 and PD-IMP-307-4 are not named in D1 to D13, so they stay undecided.
- IMD-134 accepts PD-IMP-306-3 (OUTSIDE_TRIP_DATES makes the answer unusable), while IMD-126 drops those items instead. Until the D3 code lands the built behaviour is PD-IMP-306-3; the team should confirm that IMD-126 replaces its OUTSIDE_TRIP_DATES half.
- Spec lines left as they are, because the decisions name only the lines changed in this run: §7.6 `SourceBadge` and the §9.2 label table still say "Curated, checked <date>" for prices (IMD-130); the §6.7 API-07 example keeps `Asia/Kolkata` for Sampleton, and the other §6.7 examples stay in INR (IMD-128); the IMP-301 card step 3 keeps its old text (IMD-136).

### Open items

| Item | Owner | Due |
| --- | --- | --- |
| AWS staging set-up, first deploy (TC-437), forced failure (TC-438), smoke and CORS, SSM `GEMINI_API_KEY`, ACC-19 on staging, NFR-050 p95 over 10 staging generations, staging index line, TC-433 to TC-436, IMP-216 staging walk-through, IMP-206 staging load | Kirtan | required for SG-4 |
| Staging index needs several deploys or one manual index run under the per-minute limit (row 6) | Kirtan | required for SG-4 |
| IMP-113 remaining facts: Gemini tier, ORS key and allowance, e-mail sender, AWS plan | Nidhi, Junaid, Kirtan | before SG-4 |
| IMD-120 data checks: Malhar plan, Junaid 20 percent sample, Jeel and Malhar 60 rows | Malhar, Junaid, Jeel | before SG-4 |
| Local guide must state JWKS mode for Supabase CLI v2.12x: local sign-in looped back to sign-in until the API used `SUPABASE_JWKS_URL=http://127.0.0.1:54321/auth/v1/.well-known/jwks.json`, because the stack signs with asymmetric keys although `supabase status` still prints a `JWT_SECRET` | Kirtan | next DevOps card |
| `pytest-cov` in CI for TC-334 | Kirtan | next DevOps card |
| axe in Playwright specs | Krrish | no date set |
| D3 fix (IMD-126): `OUTSIDE_TRIP_DATES` instead of whole-answer failure | Manya | with IMP-402 |
| D4 fix (IMD-127): API-16 answers 404 for an inactive destination | Malhar | no date set |
| D12 fix (IMD-135): year in retrieval dates | Manasvi | no date set |
| F-1: `Money.currency` pattern; `user_hash` in access logs | Kirtan | next change to those files |
| ES256 token test | Het | no date set |
| IMP-114 interviews (#201) | Junaid, Krrish | before SG-4 |

## SG-4 end of week 4: core reliability (blueprint Gate 3, IMP-499)

Status: **pass with listed gaps**

- Run: RUN-064 (decision-record, Nidhi; IMP-499 whole-task, Kirtan), 14 November 2026. Index: [sprint-4.md](sprint-4.md). Checkpoint: [cut-list-checkpoint.md](../decisions/cut-list-checkpoint.md).
- Gate commit: `ec6973a` (`main` at preflight, as expected), with only this run's two documentation commits on top, on branch `feat/IMP-499-sg4-gate`. No `.env` file was read, and no staging URL, AWS or Gemini call was made in this run. The staging evidence below is the operator's, quoted as given.
- Scope of this result: criteria 1 to 3 are shown on the local stack in CI and by API tests. On AWS staging, only the deploy, `/health`, the draft check and a configuration-error run are shown (operator). The card's staging steps (journey, timeout fallback demo, edit totals, `make smoke`) wait for the staging window of Wednesday 18 November 2026 (IMD-137). So the result is "pass with listed gaps", with every staging item an open item with an owner and a date.
- Sprint 4 cards: all 25 parts on 15 cards (IMP-401 to IMP-414 and IMP-318) are merged. None is blocked or cut. The Ahmedabad half of FR-036 AC3 (IMP-402) is open ([sprint-4.md](sprint-4.md)).
- Team decisions of 12–13 November 2026 are recorded as IMD-159 to IMD-166, and IMD-148 is confirmed (RUN-064 decision-record).
- Cut-list checkpoint: **C cannot be computed from the repository** (no per-story point values). No cut is applied, and `FEATURES_DISABLED` is unchanged. Proposed decision PD-IMP-499-1; supervisor to confirm.

### Staging evidence (operator, quoted as given)

- Deploy staging [43440282256](https://github.com/het-lathiya/Group12/actions/runs/43440282256) green on `ec6973a`. `/health` on 13 Nov 20:39 IST: `{"status":"ok","version":"ec6973ad25d7…","environment":"staging","provider":"GEMINI"}`.
- Draft check on staging, 13 Nov 2026: step-1-only trip "abc" (Ahmedabad) shown under Drafts with Continue draft; Continue draft resumed at step 2 with step 1 filled (operator).
- Timing run on staging, 13 Nov 20:39 IST: 10 of 10 AI generations ended status `failed` / failure_reason `config_error`, retrieval_mode `lexical_fallback`; no plan written. This shows the configuration-error path (IMD-44) on staging. **It is not a fallback-plan demonstration and gives no NFR-050 value.**

### Criteria

| # | Criterion (card IMP-499) | Result | Evidence |
| --- | --- | --- | --- |
| 1 | Sign-up to a saved, edited itinerary passes on staging (TC-369, IMP-414 evidence) | pass on the local stack in CI; not verifiable on staging | [E2E 43431854989](https://github.com/het-lathiya/Group12/actions/runs/43431854989) on `f741fd6`: `4 passed (36.7s)` at four widths with sign-up, generation (MOCK), removal with toast and focus, retime, reload and Open latest ([IMP-414 journey-staging](parts/IMP-414-journey-staging.md), [journey report](../test-reports/journey-sprint4.md)). The journey also passed on `main` at the gate commit: [E2E 43439545599](https://github.com/het-lathiya/Group12/actions/runs/43439545599) (push) and [E2E 43537426722](https://github.com/het-lathiya/Group12/actions/runs/43537426722) (nightly). TC-370 on staging, with MOCK and with Gemini: open item |
| 2 | A provider failure produces a labelled fallback plan (TC-148, IMP-403 evidence) | pass by API tests; not verifiable on staging | This run: `make test-api ARGS='-k generation_failures'` → `30 passed, 395 deselected, 1 warning in 8.99s` (TC-148 timeout, rate limit, unavailable and invalid JSON fall back; TC-308 outage leaves the trip unchanged; TC-307, TC-149, TC-150). Part record: [IMP-403 failure-outcomes](parts/IMP-403-failure-outcomes.md) (`30 passed, 374 deselected`). Labelled notice: [IMP-403 fallback-notice](parts/IMP-403-fallback-notice.md), wording per IMD-154 ([RUN-059 fallback-wording](parts/RUN-059-fallback-wording.md)). The staging `MOCK_PROVIDER_SCENARIO=timeout` demo (IMD-33) with a screenshot: open item. The staging config_error run shows IMD-44 only |
| 3 | Edits recalculate in one transaction (IMP-407 evidence) | pass by API tests; not verifiable on staging | [IMP-407 whole-task](parts/IMP-407-whole-task.md): TC-206 (every edit returns recalculated totals equal to API-24), TC-207 and TC-312 (a fault in validate, insert_warnings or insert_version rolls back and nothing is written), stale 409 and active-generation 409. Remove, retime and move routes: [IMP-408 remove-retime-ops](parts/IMP-408-remove-retime-ops.md) (TC-200, TC-204), [IMP-409 move-op](parts/IMP-409-move-op.md) (TC-199). All are part of `make test-api` (`425 passed`) in this run's `make check`. Edit totals on staging: open item. The itinerary page shows no totals until IMP-507 (note) |
| 4 | `make check` and the e2e job are green on `main` at the gate commit | pass | [CI 43439545525](https://github.com/het-lathiya/Group12/actions/runs/43439545525) success, [E2E 43439545599](https://github.com/het-lathiya/Group12/actions/runs/43439545599) and [43537426722](https://github.com/het-lathiya/Group12/actions/runs/43537426722) success, [Deploy staging 43440282256](https://github.com/het-lathiya/Group12/actions/runs/43440282256) success, all on `ec6973a`. Local `make check` in this run: exit 0 (table below) |
| 5 | The checkpoint decision with its arithmetic is recorded; any cut is applied by flag, not by deleting code | pass with a gap | [cut-list-checkpoint.md](../decisions/cut-list-checkpoint.md) records the rule, the search, why C cannot be computed (no per-story points; card points total 244, not the planned 203), the stories not complete, the bound (no cut unless they exceed 23 of 203 points), and PD-IMP-499-1. No cut, so no flag change and no code deleted. Gap: the decision waits for the supervisor's confirmation |

Card tests: `make e2e ARGS='journey'` in CI (row 1; not run locally, since this machine has no Docker); `make test-api ARGS='-k generation_failures'` (row 2, this run); `make smoke URL=<staging api url>` **not run** (no staging call in this run; open item).

### Checks of this run (`ec6973a` plus the decision-record commit)

The API suites ran against a throwaway local PostgreSQL 16.2 with pgvector (pip `pgserver`, port 55432), which was stopped afterwards.

| Command | Exit | Last line |
| --- | --- | --- |
| `make lint` | 0 | `All matched files use Prettier code style!` |
| `make test-api ARGS='-k generation_failures'` | 0 | `30 passed, 395 deselected, 1 warning in 8.99s` |
| `make check` | 0 | `      Tests  190 passed (190)` |

`make check` parts: ruff `All checks passed!`; ESLint `✖ 1 problem (0 errors, 1 warning)` (a warning from before this run); Prettier `All matched files use Prettier code style!`; mypy `Success: no issues found in 118 source files`; import-linter `Contracts: 6 kept, 0 broken.`; openapi-check `contracts/ and apps/web/lib/api/schema.d.ts are up to date`; unit `1040 passed, 1 warning in 16.79s`; contract `87 passed, 2 deselected, 1 warning in 13.46s`; api `425 passed, 1 warning in 112.14s (0:01:52)`; authz `41 passed in 17.82s`; web `Test Files  26 passed (26)`, `Tests  190 passed (190)`.

### Working-agreement audit (IMD-68)

Pull requests #259 to #273 merged in Sprint 4, from `gh pr view <n> --json reviewDecision,reviews,mergedBy,statusCheckRollup`. All were merged by the operator account `het-lathiya`.

| PR | Title | reviewDecision | Approving reviewer | Checks green on merged head | Meets the agreement |
| --- | --- | --- | --- | --- | --- |
| #259 | IMP-404 · IMP-413 · validator rules and evaluation harness | none | none | yes (6/6) | **no**: no approval |
| #260 | IMP-410 · IMP-411 · IMP-412 · drafts, budget inputs and screen states | none | none | yes (6/6) | **no**: no approval |
| #261 | IMP-401 · IMP-402 · IMP-406 · retries, fallback planner, samples and must-visit | none | none | yes (6/6) | **no**: no approval |
| #267 | IMP-403 · IMP-405 · IMP-407 · failure outcomes, warnings and edit core | none | none | yes (6/6) | **no**: no approval |
| #268 | IMP-408 · IMP-409 · remove, retime and move edits | none | none | yes (6/6) | **no**: no approval |
| #269 | RUN-059 · decision record IMD-137..155 and SG-3 fixes | none | none | yes (6/6) | **no**: no approval |
| #270 | IMP-402 · sample-itineraries part | none | none | yes (6/6) | **no**: no approval |
| #271 | IMP-318 · whole task | none | none | yes (6/6) | **no**: no approval |
| #272 | IMP-414 · journey test, fixtures and staging job | none | none | yes (6/6 on the last run; an earlier run of six was cancelled) | **no**: no approval |
| #273 | IMP-410 · dashboard New trip fix | none | none | yes (6/6) | **no**: no approval |

Summary: 10 merged; **0 with an approval**; 10 with all six checks green on the merged head. As at SG-3, no merged pull request meets the working agreement in full. Nothing was changed on these pull requests.

### Gaps and open defects

- Every staging step of the card (journey, timeout fallback demo, edit totals, `make smoke`) is not shown. On staging, Gemini generations end in `config_error` (operator's run of 13 November 2026), so no Gemini plan exists on staging yet.
- The card's evidence "journey recording" is not attached; the CI run above is the journey evidence.
- C is not computed (checkpoint record); PD-IMP-499-1 waits for the supervisor.
- Working agreement not met by any merged pull request (audit above).
- No severity 1 or 2 defect is open in the gate's scope. The one found in Sprint 4 (removal toast and focus, IMP-408) was fixed in RUN-063b and is covered by the journey.

### Open items

| Item | Owner | Due |
| --- | --- | --- |
| TC-370 journey on staging, with MOCK and with Gemini (fresh staging account, IMD-163, IMD-164) | Kirtan, Het | Wed 18 November 2026 |
| `MOCK_PROVIDER_SCENARIO=timeout` fallback on staging, with screenshot (IMD-33) | Kirtan | Wed 18 November 2026 |
| Edit an item on staging and confirm the totals change in one response | Kirtan | Wed 18 November 2026 |
| Gemini `config_error` on staging: compare the key in SSM with the working local key (`make live-smoke` passed locally on 13 November), then redeploy | Kirtan, Het | Wed 18 November 2026 |
| Staging RAG index line (including the per-minute limit finding of SG-3 row 6) | Kirtan | Wed 18 November 2026 |
| ACC-19 on staging | Het | Wed 18 November 2026 |
| NFR-050 p95 over 10 staging generations | Het | Wed 18 November 2026 |
| `make smoke` against staging, TC-433 to TC-435, Supabase redirect URLs, IMD-139 alarm output, staging stop/start log | Kirtan | Wed 18 November 2026 |
| Carried from SG-3: TC-438 forced failure, CORS on staging, IMP-216 staging walk-through, IMP-206 staging load | Kirtan | Wed 18 November 2026 |
| IMP-114 interviews (US-151), PR #201 | Junaid, Krrish | Thu 19 November 2026 |
| Ahmedabad saved samples (FR-036 AC3), waiting for two trip inputs | Jeel | no date set |
| TC-384 error-catalogue checklist | Krrish | no date set |
| Screenshots on the local stack of the #260, #261, #267 and #268 screens | Manasvi, Krrish | no date set |
| Idle-machine `make test-web` ×10 | operator | no date set |
| IMD-159 code fix: domain wording for a malformed `Money.currency` | Kirtan | no date set |
| `infra/aws/02_rds.sh`, `04_ssm.sh`, `06_services.sh`: replace `--cli-input-json file:///dev/stdin` with a file | Kirtan | before the next run of those scripts |
| Focus-fallback test (previous card, then day heading, after a removal) | Krrish | IMP-513 |
| Totals not shown on the itinerary page until IMP-507 | note only | IMP-507 |
| PD-IMP-499-1 confirmation (no cut at SG-4) | Supervisor, Kirtan | no date set |
| Carried from SG-3: IMP-113 remaining facts (Gemini tier, ORS key and allowance, e-mail sender, AWS plan); `docs/decisions/accounts.md` still says "outcome pending" | Nidhi, Junaid, Kirtan | no date set |
| Carried from SG-3: IMD-120 data checks (Malhar plan, Junaid 20 percent sample, Jeel and Malhar 60 rows); no record on `main` shows them done | Malhar, Junaid, Jeel | no date set |
| Carried from SG-3: TC-334 coverage, report-only step in CI since RUN-059; thresholds still proposed | Kirtan | no date set |

Closed since SG-3: AWS staging set-up and first deploy (Deploy staging green, `/health` above); TC-436 (IMD-138); local guide JWKS mode and `pytest-cov` in CI (RUN-059 devops-bundle); axe in Playwright (`apps/web/e2e/axe.ts`, used by the journey); D3 fix IMD-126 (RUN-057); D4 fix IMD-127 and the unknown-destination case IMD-166 (RUN-059 destination-404); D12 fix IMD-135 (`e3a4184`); F-1 `Money.currency` pattern and `user_hash` (RUN-059 devops-bundle); ES256 token test (RUN-059 token-leeway).

## SG-5 end of week 5: trip management (IMP-599)

Status: **pass with listed gaps** (IMD-186)

- Run: IMP-599 whole-task, owner Kirtan, 15 November 2026. Index: [sprint-5.md](sprint-5.md).
- Gate commit: the head of this PR (`chore/IMP-599-sg5-gate`); base `43a4240` (`main` after #279). The PR adds only this documentation commit. No `.env` file was read, and no staging URL, AWS, database or Gemini call was made in this run.
- Scope of this result: everything that can be shown in CI on the local stack with MOCK, by API tests and by the recorded Gemini baseline is shown below. Staging was off during this gate (IMD-137), so every staging criterion is **not verifiable** and is an open item for the staging window of Wednesday 18 November 2026 (IMD-186). No staging criterion is claimed as passed.
- Sprint 5 cards: all 22 parts on 14 cards (59 points) are merged (#275 to #279). IMP-515 (extension, 4 points) is cut (IMD-65, IMD-186); a switched-off extension counts as satisfied for the gate card (specification §11.2).
- Decisions used: IMD-65 (extensions cut), IMD-137 (staging off between windows), IMD-167 (no cut-list switch at SG-4), IMD-177 to IMD-184 (Sprint 5 fix decisions), IMD-185 (public repository; E2E on every push to main and by dispatch on each pull request) and IMD-186 (SG-5 passes with listed gaps), both recorded in `docs/spec/DECISION_REGISTER.md` in this pull request.

### Criteria

| # | Criterion (card IMP-599 acceptance and steps) | Result | Evidence |
| --- | --- | --- | --- |
| 1 | Step 1: every Sprint 5 task done or explicitly carried over in `sprint-5.md` with evidence links | PASS | [sprint-5.md](sprint-5.md): 22 parts merged, each row links its part record; IMP-515 listed as cut; carried-over items listed with owners and due dates |
| 2a | Acceptance 1 / step 2: `make check` green on the gate commit | PASS on `main` at the base; PR run pending | CI run on this PR (to be read on the PR before merge). `main` at the base: [CI 43601520229](https://github.com/het-lathiya/Group12/actions/runs/43601520229) (CI, push, 14 Nov 2026) on `43a4240`: `lint-types`, `unit`, `guards`, `audit`, `api` success (`attribution` skipped on push). This PR changes only `docs/progress/` |
| 2b | Acceptance 1 / step 2: `make e2e` green on the gate commit | PASS | Gate E2E dispatch on this PR's branch (E2E by dispatch on each pull request, IMD-185): run 43721801253 (workflow_dispatch on `3b038f2`, the gate commit before this cell was filled in; success). Journey: `4 passed (34.4s)`; map specs: `8 passed (19.4s)`; staging job skipped. Earlier E2E successes on the last Sprint 5 merges, all `workflow_dispatch`, success, steps "Run the journey" and "Run the map specs": [43600301340](https://github.com/het-lathiya/Group12/actions/runs/43600301340) (#279, head `663895a`), [43597245631](https://github.com/het-lathiya/Group12/actions/runs/43597245631) (#278, `a3338e0`), [43588206273](https://github.com/het-lathiya/Group12/actions/runs/43588206273) (#277, `4ecf7f9`) |
| 3 | Acceptance 2 / step 3: staging journey with GEMINI, end to end with all Sprint 5 functions (generate, add a place, replace an activity, lock an item, costs breakdown, map); outcome labels shown | NOT VERIFIABLE (staging off) | Open item, Kirtan and Het (Gemini key), due Wed 18 Nov 2026 (IMD-186). Existing evidence below the staging level: the MOCK E2E journey ([43600301340](https://github.com/het-lathiya/Group12/actions/runs/43600301340)) at four widths (360, 768, 1280, 1920) covers sign-up, trip creation, generation, remove, retime, reload, Open latest, skip link, keyboard move and the Costs page, and the map spec covers the map and its list fallback. **Add place, replace, lock, browse places and trip edit are not in the E2E journey**; they are covered by API tests in the CI `api` job (#275, #276) and by component tests ([sprint-5.md](sprint-5.md)). Gemini quality on dataset `trips` v1: usable outputs 44 / 45 ([baseline-1.md](../../eval/reports/baseline-1.md), run record `eval/results/20261114T104200Z-gemini/run.json`: provider GEMINI, model `gemini-3.5-flash-lite`, prompt v1, 15 cases × 3 repeats, git commit `15475eb`) |
| 4 | Step 3: `make smoke URL=<staging api>` (including the new cases of `apps/api/tests/smoke/test_deployed.py`) | NOT VERIFIABLE (staging off) | Not run. Open item, Kirtan, due Wed 18 Nov 2026 |
| 5 | Step 4: provider failure on staging (`AI_PROVIDER=MOCK`, `MOCK_PROVIDER_SCENARIO=timeout`, IMD-33): labelled fallback and repair outcome recorded | NOT VERIFIABLE (staging off) | Open item, Kirtan, due Wed 18 Nov 2026. API-level evidence in CI: repair and fallback tests of IMP-502 (TC-190, TC-191, TC-192, TC-011, TC-313; [record](parts/IMP-502-whole-task.md)) in #275, and the IMP-403 failure tests (SG-4 row 2), all in the `api` job of [CI 43601520229](https://github.com/het-lathiya/Group12/actions/runs/43601520229) |
| 6 | Step 5: a user at the cap gets 429 `AI_QUOTA_REACHED` without a provider call | NOT VERIFIABLE on staging | Open item, Kirtan, due Wed 18 Nov 2026. API-level evidence: TC-171, TC-172, TC-173, TC-310, TC-311, TC-353 in `apps/api/tests/api/test_generations.py` and TC-294 in `apps/api/tests/unit/core/test_rate_limit.py` (IMP-511, #276), run in the CI `api` and `unit` jobs; the part record itself marks the API cases not verified in its run ([record](parts/IMP-511-whole-task.md)) |
| 7 | Acceptance 3 / step 6: no open blocker-severity defect; known defects listed with severity and owner | PASS on the listed basis | Defect list below. No blocker-severity (severity 1) defect is known in the local and CI scope. The staging Gemini `config_error` is major but staging-only, and staging evidence is moved to 18 Nov 2026 by IMD-186 |
| 8 | Step 6: cut-list flags currently disabled recorded | recorded | See "Cut-list flags" below: **no flag is disabled in any configuration in the repository**; `ranking_explain` is not yet in the default list |
| 9 | Acceptance 5 / step 7: IMP-515 done with TC-399 to TC-401, or `ranking_explain` switched off with a recorded decision | PASS (cut) | IMP-515 cut by IMD-65 and IMD-186; API-63 and the "Why this place?" panel are not built (no route in `apps/api/app`). Gap: `ranking_explain` is off by decision, not yet by configuration (see below) |
| 10 | Acceptance 4: gate decision and evidence recorded in `gates.md` | PASS | This entry |
| 11 | §14.1 SG-5 tests: provider contract suite for MOCK and recorded GEMINI | PASS | IMP-512 ([record](parts/IMP-512-whole-task.md)): TC-156 to TC-158, TC-001 to TC-005, TC-008 at contract level for `mock` and `gemini_recorded`, no network; `make test-contract` is part of the `unit` job of [CI 43601520229](https://github.com/het-lathiya/Group12/actions/runs/43601520229). The recordings are still hand-written fixtures (open item) |
| 12 | §14.1 SG-5 evidence: baseline run record (dataset, provider, SHA) | PASS | `eval/results/20261114T104200Z-gemini/run.json`: dataset `trips` v1, provider GEMINI, `git_commit` `15475eb`; note [baseline-1.md](../../eval/reports/baseline-1.md) (44 / 45 usable) ([IMP-514 gemini-baseline](parts/IMP-514-gemini-baseline.md)) |

Card tests: `make e2e` by dispatch on this PR (row 2b); `make smoke URL=<staging api url>` **not run** (staging off). No command was run locally in this run: it changes only two documentation files, and the gate's evidence is CI.

### Known defects

Severity per IMD-41 (§14.1): 1 blocks a journey or exposes data; 2 breaks a requirement with no workaround; 3 has a workaround; 4 cosmetic.

| Defect | Severity | Owner | Source |
| --- | --- | --- | --- |
| Gemini generations on staging end `failed` / `config_error` (SG-4 operator run of 13 Nov 2026); local `make live-smoke` and the baseline run succeed | major, staging only (would be severity 2 if staging were in this gate's scope) | Kirtan, Het | SG-4 open items |
| Destructive Button hover about 4.40:1 over the page background (PD-RUN-071b-1); hover only, not scanned by axe | minor (severity 3) | Manasvi | IMD-183, deferred to Sprint 6 |
| The model writes "AI-written" into its own notes (492 of 557) and reuses places for meals (88 items) | minor (severity 3) | Manya (prompt v2), Nidhi | IMD-180, IMD-181; [baseline-1.md](../../eval/reports/baseline-1.md); Sprint 6 |
| TC-385 live-stack label review and screenshots not done | minor (severity 4, evidence gap) | Manasvi | [IMP-507 costs-page](parts/IMP-507-costs-page.md) |
| Provider spending limit is Awaiting validation | minor (risk, no defect observed) | Kirtan | [IMP-511](parts/IMP-511-whole-task.md) |
| CI: a pull-request edit should run only `attribution`; verified locally, not yet observed at runtime | minor (severity 4) | Kirtan | RUN-072, IMD-184 |

No blocker-severity defect is known. The Sprint 5 defects found in E2E (map worker in the production build, Button fade contrast, focus after a move, the 409 after an edit caused by the commit order) were fixed in RUN-071b, RUN-071c and RUN-072 and passed in [E2E 43600301340](https://github.com/het-lathiya/Group12/actions/runs/43600301340).

### Cut-list flags

- `FEATURES_DISABLED` default: `""` (`apps/api/app/core/config.py`, `features_disabled: str = ""`).
- `.env.example`: `FEATURES_DISABLED=` and `NEXT_PUBLIC_FEATURES_DISABLED=` (both empty).
- CI and E2E workflows: `NEXT_PUBLIC_FEATURES_DISABLED: ""`. Staging takes the repository variable `STAGING_FEATURES_DISABLED`, whose value is not in the repository and was not read (`infra/aws/env.sh.example` leaves it empty).
- So **no cut-list switch and no extension switch is disabled** in any configuration held in the repository. No MVP cut-list switch is applied (IMD-167; none added at SG-5).
- Switched off by decision, not by configuration: the nine extensions (IMD-65), among them `ranking_explain` (IMP-515, IMD-186) and IMP-612 `optimise_order`. Their routes and screens are not built. **`ranking_explain` is not yet in the default list**; adding it is a follow-up (open item). The configuration was not changed in this run.

### Gate decision

**Pass with listed gaps** (IMD-186). IMP-612 stays cut. The SG-5 restore decision point is closed. Sprint 6 starts. Every staging criterion is an open item due Wednesday 18 November 2026.

### Working-agreement audit (IMD-68)

From `gh pr view <n> --json reviewDecision,reviews,mergedBy,statusCheckRollup`. All were merged by the operator account `het-lathiya`.

| PR | reviewDecision | Approving reviewer | Check runs in the rollup | Meets the agreement |
| --- | --- | --- | --- | --- |
| #275 | none | none | 6 success | **no**: no approval |
| #276 | none | none | 8 success, 4 cancelled (superseded runs) | **no**: no approval |
| #277 | none | none | 11 success, 1 cancelled | **no**: no approval |
| #278 | none | none | 12 success | **no**: no approval |
| #279 | none | none | 6 success | **no**: no approval |

Summary: 5 merged, 0 with an approval. As at SG-3 and SG-4, no merged pull request meets the working agreement in full. Nothing was changed on these pull requests.

### Open items

| Item | Owner | Due | Source |
| --- | --- | --- | --- |
| Gate E2E dispatch on this PR: fill in the run id and the journey/map result line in row 2b | Kirtan | before merge of this PR | IMP-599 step 2 |
| Staging GEMINI journey with all Sprint 5 functions (generate, add, replace, lock, costs, map) and outcome labels; includes TC-370 with MOCK and Gemini (fresh staging account, IMD-163, IMD-164) | Kirtan, Het (Gemini key) | Wed 18 November 2026 | SG-5 rows 3; SG-4 |
| `make smoke` against staging with the new smoke cases, TC-433 to TC-435, Supabase redirect URLs, IMD-139 alarm output, staging stop/start log | Kirtan | Wed 18 November 2026 | SG-5 row 4; SG-4 |
| `MOCK_PROVIDER_SCENARIO=timeout` fallback on staging with the repair outcome recorded, with screenshot (IMD-33) | Kirtan | Wed 18 November 2026 | SG-5 row 5; SG-4 |
| Generation cap on staging: 429 `AI_QUOTA_REACHED` with no provider call | Kirtan | Wed 18 November 2026 | SG-5 row 6 |
| Gemini `config_error` on staging: compare the key in SSM with the working local key, then redeploy | Kirtan, Het | Wed 18 November 2026 | SG-4 |
| Edit an item on staging and confirm the totals change in one response | Kirtan | Wed 18 November 2026 | SG-4 |
| Staging RAG index line (including the per-minute limit finding of SG-3 row 6) | Kirtan | Wed 18 November 2026 | SG-4 |
| ACC-19 on staging | Het | Wed 18 November 2026 | SG-4 |
| NFR-050 p95 over 10 staging generations | Het | Wed 18 November 2026 | SG-4 |
| Carried from SG-3: TC-438 forced failure, CORS on staging, IMP-216 staging walk-through, IMP-206 staging load | Kirtan | Wed 18 November 2026 | SG-4 |
| IMP-114 interviews (US-151): anonymous notes with participant codes; PR #201 (open, draft) | Junaid, Krrish | Thu 19 November 2026 | SG-4 |
| Add `ranking_explain` to the `FEATURES_DISABLED` defaults (IMD-186); config not changed here | Kirtan | Sprint 6 | this gate |
| Destructive Button hover contrast about 4.40:1 (PD-RUN-071b-1) | Manasvi | Sprint 6 | IMD-183 |
| Prompt v2: application supplies the "AI-written" label; a place at most once in a generated plan, meal stops included | Manya, Nidhi | Sprint 6 | IMD-180, IMD-181 |
| TC-385 live-stack label review and screenshots | Manasvi | no date set | IMP-507 costs-page |
| Provider spending limit (Awaiting validation) | Kirtan | no date set | IMP-511 |
| Observe that a pull-request edit runs only `attribution` | Kirtan | next pull-request edit | RUN-072, IMD-184 |
| TC-382 manual screen-reader pass | Krrish | IMP-703 (Sprint 7) | IMP-513 |
| Screenshots on the local stack: Sprint 5 screens (place picker, alternatives dialog, lock toggle, trip edit, costs, map and list fallback) and the SG-4 screens (#260, #261, #267, #268, #273); 44 px targets at 375 px | Malhar, Krrish, Manasvi | no date set | Sprint 5 records; SG-4 |
| Ahmedabad saved samples (FR-036 AC3), waiting for two trip inputs | Jeel | no date set | SG-4 |
| TC-384 error-catalogue checklist | Krrish | no date set | SG-4 |
| Carried from SG-3: IMP-113 remaining facts (Gemini tier, ORS key and allowance, e-mail sender, AWS plan); `docs/decisions/accounts.md` still says "outcome pending" | Nidhi, Junaid, Kirtan | no date set | SG-4 |
| Production environment with required reviewers | Kirtan | Sprint 8 | IMD-185 |
| Fork pull-request approval setting | operator | no date set | IMD-185 |
| OpenFreeMap terms Unverified (`docs/decisions/map-tiles.md`) | Manasvi | no date set | IMP-508 |
| Gemini contract recordings are hand-written; replace with scrubbed live recordings | Junaid | no date set | IMP-512 |
| Idle-machine `make test-web` ×10 | operator | no date set | SG-4 |
| `infra/aws/02_rds.sh`, `04_ssm.sh`, `06_services.sh`: replace `--cli-input-json file:///dev/stdin` with a file (still present at `43a4240`) | Kirtan | before the next run of those scripts | SG-4 |
| Carried from SG-3: IMD-120 data checks (Malhar plan, Junaid 20 percent sample, Jeel and Malhar 60 rows); no record on `main` shows them done | Malhar, Junaid, Jeel | no date set | SG-4 |
| Carried from SG-3: TC-334 coverage, report-only step in CI; thresholds still proposed | Kirtan | no date set | SG-4 |

Closed since SG-4: IMD-159 code fix, plain-language `Money.currency` error (`5f53777`, #276); focus-fallback test after a removal (IMP-513, DayColumn cases, [record](parts/IMP-513-whole-task.md)); totals note (totals and breakdown now on the Costs page, IMP-507, TC-226 component path); PD-IMP-499-1 confirmation (IMD-167); repair call through the retry allowance (IMP-502, [record](parts/IMP-502-whole-task.md)).

Confirmed by: Kirtan (gate owner) — pending

## SG-6 end of week 6: MVP feature freeze (IMP-699)

Status: not run

## SG-7 end of week 7: release candidate and extension freeze (IMP-799)

Status: not run

## SG-8 week 8: release and demo (IMP-899)

Status: not run
