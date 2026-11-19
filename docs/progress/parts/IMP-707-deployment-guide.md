# IMP-707 · deployment-guide part

- Run id: RUN-083 (docs-guides batch)
- Owner: Kirtan
- Status: PARTIAL (guide and README links drafted; the AWS and Supabase steps and the clean-account trial of card step 6 are open)
- Base commit: f75aa94
- Branch: S7B/docs-guides (batch branch of RUN-083; the card names `feat/IMP-707-<part>`, and the lead integrates the batch)
- Issue: #158

## Changed files

- docs/guides/deployment-guide.md (created)
- README.md (modified: a "Documentation" section and a "How we merge" note were added at the end; nothing else changed)
- docs/progress/parts/IMP-707-deployment-guide.md (created)

## What was done

Card step 4 (as amended by A1): the deployment guide covers the AWS resources (ECS Express Mode, RDS, SSM, ECR, CloudWatch), the auth-only Supabase project, the environment values per A1 §4.2 and §7.2 and the staging template, the release task (auth stub, migrations, seed, RAG index), staging and production deploys, smoke tests, rollback and staging windows, cost guardrails, and the operator account-deletion procedure for NFR-022 (Supabase Auth user, then `python -m app.db.admin delete-user` as a one-off ECS task). It builds on docs/guides/aws-setup.md and docs/guides/deployment.md and links their steps instead of copying them.

Card step 5: every command carries a mark. Commands run in this run are marked "Run (RUN-083)" with their result line. AWS, Supabase-project and GitHub-settings steps are marked "Not verified — run by Kirtan". Local commands that need Docker or a database are marked "Not verified".

README.md: the "Documentation" section links the ten documents of this batch (docs/srs.md, docs/architecture.md, docs/api.md, docs/test-plan.md, docs/guides/user-guide.md, docs/guides/deployment-guide.md, docs/stage2/README.md, eval/reports/final-baseline.md, docs/test-reports/cost-latency-report.md, docs/test-reports/accessibility-sprint7.md). Only the two guides exist on this branch; the other eight are written in other parts of the batch and exist after integration. The "How we merge" note follows the lead's wording (operator Nidhi, IMD-209, IMD-211; IMD-208 and docs/progress/commit-map.md).

## Commands run

All run in this worktree at base f75aa94, with `PYTHONPATH=/home/user/wt-S7B-docs-guides/apps/api` and the proxy variables unset. Python modules were run with `apps/api/.venv/bin/python`.

| Command | Result line (quoted exactly) |
| --- | --- |
| `make help` | exit 0 (first line `Targets (specification §4.7):`) |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |
| `make lint` | `All checks passed!`; `234 files already formatted`; `All matched files use Prettier code style!` |
| `make typecheck` | `Success: no issues found in 123 source files`; `✓ Types generated successfully` |
| `make imports` | `Contracts: 6 kept, 0 broken.` |
| `sh -n apps/api/scripts/release.sh` | no output, exit 0 |
| `for f in infra/aws/0*.sh; do bash -n "$f" \|\| echo "FAIL $f"; done` | no output, exit 0 |
| `jq -e . infra/aws/services/api.staging.json.tmpl >/dev/null && echo api-ok` | `api-ok` |
| `jq -e . infra/aws/services/web.staging.json.tmpl > /dev/null && echo web-ok` | `web-ok` |
| `python -m app.db.admin --help` | `usage: admin.py [-h] {delete-user} ...` (exit 0) |
| `python -m app.db.admin delete-user --help` | `usage: admin.py delete-user [-h] --user-id USER_ID` (exit 0) |
| `python -m app.db.auth_stub --help` | `usage: auth_stub.py [-h] --if-missing` (exit 0) |
| `python -m app.places.seed --help` | `usage: python -m app.places.seed [-h] [--check] [--strict]` (exit 0) |
| `python -m app.rag.index --help` | `usage: python -m app.rag.index [-h] [--destination SLUG] [--check] [--strict]` (exit 0) |
| `jq --version`; `docker --version`; `supabase --version` | `jq-1.7`; `Docker version 29.10.0, build fdd4b8e`; `2.122.0` |
| `aws --version`; `envsubst --version` | `aws: command not found`; `envsubst: command not found` |

## Not run

| Command | Reason |
| --- | --- |
| All `infra/aws/*.sh` scripts, every `aws ...` command, `docker build`/`docker push` to ECR, the Supabase dashboard steps, `gh variable set`, `gh workflow run deploy-staging.yml ...`, `gh workflow run deploy-production.yml ...` | AWS, the hosted Supabase project and the GitHub settings belong to Kirtan; this run holds no credentials and may not use gh. Marked "Not verified — run by Kirtan" |
| The NFR-022 one-off task (`aws ecs run-task ... delete-user`) and `aws logs get-log-events` | Same reason; the command block in guide section 9 was written for the guide from the workflow's run-task call and is marked not tried against AWS |
| `make smoke URL=<staging API URL> ...`, `curl <staging>/health` | Needs the staging URLs and the network; staging is off outside windows |
| Local container smoke (`make db-up`, `docker compose run ... release.sh`, `docker compose up ...`, `make smoke URL=http://localhost:8000 ...`) | Docker and the test database are not allowed in this run |
| `make db-bootstrap`, `make seed SEED_DIRS=data/places/ahmedabad`, `make rag-index ARGS='--strict'` | Need a database |
| `make setup && make check` (TC-335) | `make check` includes the test suites, which need the test database |

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| Each required document exists in docs/ with owner and version (US-145 AC1), for the deployment guide | verified | docs/guides/deployment-guide.md header table: Owner Kirtan, Version 0.1 |
| A member outside the platform squad completed README setup (time recorded) and a clean deployment answered /health (US-146 AC2, CHK-18) | not verified | Card step 6 is a team trial on a clean account; not done. Outcome goes into docs/progress/sprint-7.md |
| make openapi-check is green | verified | Result line above |
| Card step 5: commands run before being documented, others marked "not verified" | verified | Every command in the guide carries a mark (guide section 0); the run ones are listed above |
| Card step 5: differences between documented and built behaviour listed | verified (from the repository) | Guide section 11 lists eight differences; none was checked against AWS |
| README.md links the batch documents and states the merge method | verified for the text; links not verified | Eight of the ten link targets do not exist on this branch; they must exist after integration |

## Differences between documented and built behaviour (guide section 11)

1. The IMP-707 card in specification §10.8 still names Vercel, Render and Supabase; A1 and TASK_REGISTER.md use AWS.
2. Production templates are expected by A1 §4.3 and `deploy-production.yml` but only the staging templates exist (IMP-801).
3. A1 §4.5 and the workflows say AWS CLI v2 does not read `--cli-input-json file:///dev/stdin`; `infra/aws/02_rds.sh`, `04_ssm.sh` and `06_services.sh` still pipe into it. Staging exists, so their real behaviour on Kirtan's machine is not recorded; to be confirmed by Kirtan.
4. aws-setup.md §13 (TC-434) reads `services[0].taskDefinition`, which Express Mode leaves empty; the `PRIMARY` deployment query is needed.
5. A1 §4.2 names an HS256 secret for local auth; newer CLI stacks use JWKS mode (local-setup.md §4, IMD-123).
6. A1 §4.7 assumes always-on staging with one task; IMD-137 switches staging off between windows, and the start, stop and scaling commands are still unconfirmed.
7. IMD-139 (rollback alarm counts only 5xx and failed health checks) is decided, not applied.
8. The cost estimate required by A1 §4.7 is still unfilled in aws-setup.md §14.

## Blockers

- The AWS, Supabase and GitHub-settings steps, the NFR-022 one-off task on RDS and the clean-account trial (card step 6) need Kirtan and a staging window.

## Proposed decisions

- none. Differences 3 and 4 are candidates for a small fix to `infra/aws/` and aws-setup.md after Kirtan confirms them; this record only reports them.

## Open issues

- **"How we merge" sources.** At base f75aa94, DECISION_REGISTER.md has IMD-208 and IMD-209 but no IMD-211, and IMD-209 names the operator as het-lathiya ("from his machine"). The README note names Nidhi and cites IMD-211 as the lead instructed for this batch; it is correct only once IMD-211 is in the register. The proposed IMD-212 broker guide on `origin/chore/IMD-212-pr-broker` names the operator Nidhi9864.
- When IMP-801 creates production, sections 1, 4.2 and 6.2 of the guide need the production names and templates.
