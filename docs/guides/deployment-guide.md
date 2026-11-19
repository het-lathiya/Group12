# Deployment guide

| Field | Value |
| --- | --- |
| Document | Deployment guide for staging and production on AWS (IMP-707, deployment-guide part; US-146, NFR-022) |
| Owner | Kirtan |
| Version | 0.1, draft of 19 November 2026 |
| Based on | `main` at `f75aa94`; Amendment A1 §3, §4, §5.1 and §7.2; [aws-setup.md](aws-setup.md) and [deployment.md](deployment.md) |
| Status | Draft. The AWS and Supabase steps are Kirtan's and were not run while writing this guide. The trial on a clean account by a member outside the platform squad (card step 6) is open |

This guide brings together how the AI Travel Planner is deployed and operated: the AWS resources, the auth-only Supabase project, the environment values, the release task, deploys, smoke tests, rollback, cost guardrails and the operator account-deletion procedure. It builds on two existing guides and does not repeat their full command lists:

- [aws-setup.md](aws-setup.md): the one-time AWS set-up, step by step (IMP-217);
- [deployment.md](deployment.md): images, deploy workflows, staging windows and the rollback alarm (IMP-112, IMP-218, IMD-137, IMD-139).

Only Kirtan, the owner of the AWS account, runs AWS commands and holds AWS credentials (A1 §4.1). Nobody else runs the `infra/aws/` scripts.

## 0. How commands are marked

Every command in this guide carries one of these marks (card step 5):

| Mark | Meaning |
| --- | --- |
| **Run (RUN-083)** | Run in a Linux container while writing this guide, with the result line quoted |
| **Not verified — run by Kirtan** | Needs the AWS account, the hosted Supabase project or the GitHub repository settings. Not run while writing this guide |
| **Not verified** | A local command that needs Docker, a database or the network, which could not be used while writing this guide |

Commands copied from [aws-setup.md](aws-setup.md) and [deployment.md](deployment.md) keep the mark of this guide; where those guides record a result, the record is cited.

## 1. What runs where

| Part | Where it runs | Source |
| --- | --- | --- |
| Web app | Amazon ECS Express Mode service `group12-web-<env>` (Fargate, 0.25 vCPU, 512 MiB, exactly one task), container port 3000, health check `/` | `apps/web/Dockerfile`, `infra/aws/services/web.staging.json.tmpl` |
| API | Express Mode service `group12-api-<env>`, same size, container port 8000, health check `/health` | `apps/api/Dockerfile`, `infra/aws/services/api.staging.json.tmpl` |
| Load balancer | One internet-facing Application Load Balancer shared by the services, created by Express Mode; AWS-generated HTTPS URLs, no custom domain | A1 §3 |
| Database | Amazon RDS PostgreSQL 16 `group12-rds` (`db.t4g.micro`, 20 GB gp3, single-AZ, private, TLS required, deletion protection, 1 day of backups); databases `travel_staging` and, from IMP-801, `travel_production`; holds the auth stub | A1 §4.1, §5.1 |
| Images | Amazon ECR `group12-api` and `group12-web`, scan on push, newest 10 images kept | A1 §4.1 |
| Secrets | SSM Parameter Store `SecureString` parameters `/group12/<env>/DATABASE_URL`, `/group12/<env>/GEMINI_API_KEY`, `/group12/<env>/ORS_API_KEY`, passed to the API as ECS `secrets` references | A1 §4.1, IMD-102 |
| Logs | CloudWatch log groups `/ecs/group12-api-<env>` and `/ecs/group12-web-<env>`, 7 days | A1 §4.1 |
| Sign-in | One hosted Supabase project, Auth only, for both environments; the API verifies tokens through JWKS | IMD-101, IMD-123 |
| Network | Default VPC and its public subnets; tasks have a public IP; **no NAT gateway** | A1 §4.1 |

The region is `ap-south-1`. Production (services, database and the `PRODUCTION_*` variables) is created in IMP-801, which has not been done at this version: `infra/aws/services/` holds only the two staging templates.

**Recorded state.** The staging set-up has been done and deployed: [gates.md](../progress/gates.md) records a green **Deploy staging** run and the staging `/health` answer `{"status":"ok","version":"ec6973ad25d7…","environment":"staging","provider":"GEMINI"}` on 13 November 2026. That commit ID predates the history rewrite of 18 November 2026 (IMD-208, [commit-map.md](../progress/commit-map.md)). Staging is switched off between staging windows (IMD-137, section 7.3).

## 2. One-time AWS set-up (staging)

Follow [aws-setup.md](aws-setup.md) in order, from the repository root on an up-to-date `main`. If the AWS Free plan refuses anything, stop and ask for a team decision; never enable AWS Organizations, Control Tower or IAM Identity Center (A1 §4.1, IMD-104).

| Step | Command | aws-setup.md | Mark |
| --- | --- | --- | --- |
| Account checks and tools | `aws --version`, `python3 --version`, `envsubst --version`, `aws sts get-caller-identity --query Account --output text` | §1 | Not verified — run by Kirtan |
| Fill in the untracked `infra/aws/env.sh` | `cp infra/aws/env.sh.example infra/aws/env.sh`, then add `SUPABASE_JWKS_URL` | §2 | Not verified — run by Kirtan |
| Budget USD 50 with alerts at USD 25 and USD 50 | `infra/aws/01_budget.sh` | §3 | Not verified — run by Kirtan |
| RDS instance and security group | `infra/aws/02_rds.sh` (master password at a hidden prompt) | §4 | Not verified — run by Kirtan |
| ECR repositories, then SSM parameters | `infra/aws/03_ecr.sh`, `infra/aws/04_ssm.sh` (values at hidden prompts; `--overwrite` to replace) | §5 | Not verified — run by Kirtan |
| Roles and the GitHub OIDC deploy role | `infra/aws/05_iam.sh` | §6 | Not verified — run by Kirtan |
| First API image by hand | `docker build ... -f apps/api/Dockerfile ...`, `docker push ...` | §7 | Not verified — run by Kirtan |
| API service | `infra/aws/06_services.sh api` | §8 | Not verified — run by Kirtan |
| First web image by hand | `docker build ... apps/web`, `docker push ...` | §9 | Not verified — run by Kirtan |
| Web service and allowed origin | `infra/aws/06_services.sh web` | §10 | Not verified — run by Kirtan |
| Supabase URL settings | Dashboard (section 3 below) | §11 | Not verified — run by Kirtan |
| Repository variables (Actions variables, not secrets) | `gh variable set ...` | §12 | Not verified — run by Kirtan |
| Verify and record | `curl`, `make smoke`, `aws rds describe-db-instances`, `nc`, `aws ecs describe-task-definition`, `aws logs describe-log-groups` | §13 | Not verified — run by Kirtan |

Local checks of the same files, **Run (RUN-083)**:

| Command | Result |
| --- | --- |
| `for f in infra/aws/0*.sh; do bash -n "$f" \|\| echo "FAIL $f"; done` | no output, exit 0 (all six scripts parse) |
| `jq -e . infra/aws/services/api.staging.json.tmpl >/dev/null && echo api-ok` | `api-ok` |
| `jq -e . infra/aws/services/web.staging.json.tmpl > /dev/null && echo web-ok` | `web-ok` |

The AWS CLI and `envsubst` are not installed in the container used for this guide, so none of the scripts could be tried there.

## 3. The auth-only Supabase project

Supabase serves sign-in only (IMD-101). The database is RDS.

1. In the Supabase dashboard, Authentication, URL Configuration: set the Site URL to `STAGING_WEB_ORIGIN` and add `<STAGING_WEB_ORIGIN>/auth/callback` to the redirect URLs ([aws-setup.md](aws-setup.md) §11). For production, add the production web URL and its `/auth/callback` to the same project (A1 §5.1, OD-15). **Not verified — run by Kirtan.**
2. E-mail confirmation follows [accounts.md](../decisions/accounts.md) section 2 ("Email confirmation on staging"), so that the confirmation link reaches `/auth/callback`. **Not verified — run by Kirtan.**
3. Token mode: the project uses JWT signing keys, so the API reads `SUPABASE_JWKS_URL` (`<project URL>/auth/v1/.well-known/jwks.json`). **Do not create** an SSM parameter for `SUPABASE_JWT_SECRET`: it is not used (IMD-123).

The web image receives the project URL and anon key as build arguments (both public by design); the API holds no Supabase secret.

## 4. Environment values

### 4.1 Per environment (A1 §4.2)

| Aspect | Local | Test / CI | Staging | Production |
| --- | --- | --- | --- | --- |
| `APP_ENV` | `local` | `test` | `staging` | `production` |
| Database | Supabase CLI local Postgres (`127.0.0.1:54322`) or compose `db` | compose or service `db` (`pgvector/pgvector:pg16`) with the auth stub, blank per run | RDS `travel_staging` with the auth stub | RDS `travel_production` with the auth stub |
| `DB_AUTH_STUB` | `false` on the local stack, `true` on compose `db` | `true` | `true` | `true` |
| Auth | Local Supabase Auth (JWKS mode on newer CLI stacks, see [local-setup.md](local-setup.md) §4) | Minted test tokens; E2E uses the local stack | Hosted Supabase Auth, JWKS | Same project as staging |
| `AI_PROVIDER` | `MOCK` | `MOCK` only, no key in PR CI | `GEMINI`; `MOCK` only for the failure demo (IMD-33) | `GEMINI`; the API refuses `MOCK` at start-up |
| RAG index | `make rag-index` after `make seed`, MOCK embeddings | Built by test fixtures with MOCK embeddings | Built by the release task with Gemini embeddings | Same as staging |
| Secrets live in | Untracked `apps/api/.env`, `apps/web/.env.local` | GitHub Actions (none for PR jobs) | SSM Parameter Store | SSM Parameter Store |
| Deployed by | The member | The pipeline | `deploy-staging.yml` after CI on `main` | Kirtan, by hand from a tag, `deploy-production.yml` |

### 4.2 API service values (staging template)

`infra/aws/services/api.staging.json.tmpl` sets, at this version:

| Kind | Variables and values |
| --- | --- |
| Plain environment | `APP_ENV=staging`, `LOG_LEVEL=INFO`, `ALLOWED_ORIGINS=${STAGING_WEB_ORIGIN}`, `RATE_LIMIT_PER_MIN=60`, `FEATURES_DISABLED=${STAGING_FEATURES_DISABLED}`, `SUPABASE_URL=${STAGING_SUPABASE_URL}`, `SUPABASE_JWKS_URL=${SUPABASE_JWKS_URL}`, `DB_AUTH_STUB=true` |
| AI | `AI_PROVIDER=GEMINI`, `GEMINI_MODEL_ID=gemini-3.5-flash-lite`, `GEMINI_EMBEDDING_MODEL_ID=gemini-embedding-2`, `GEMINI_TIMEOUT_S=35`, `GEMINI_MAX_RETRIES=1`, `PROMPT_TEMPLATE_VERSION=v2`, `AI_MAX_INPUT_TOKENS` and `AI_MAX_OUTPUT_TOKENS` empty (treated as unset), `AI_DAILY_GENERATIONS_PER_USER=10`, `AI_DAILY_GENERATIONS_GLOBAL=200`, `AI_DAILY_ASSIST_CALLS_PER_USER=30` |
| Other | `ORS_TIMEOUT_S=8`, `SEED_DIRS=data/places/ahmedabad`, `PORT=8000` |
| Secrets (SSM ARNs only) | `DATABASE_URL`, `GEMINI_API_KEY`, `ORS_API_KEY` |
| Baked into the image | `BUILD_VERSION` = the commit SHA (IMD-103) |

`DATABASE_URL` has the form `postgresql+psycopg://<user>:<password>@<rds-endpoint>:5432/travel_<env>?sslmode=require`; `04_ssm.sh` builds it and percent-encodes the password. A change of a non-secret value is a reviewed pull request to the template, because every deploy sends the full rendered configuration (A1 §4.3). In staging and production the API refuses to start when a required `GEMINI_*` value, `GEMINI_EMBEDDING_MODEL_ID` included, is empty or a placeholder.

### 4.3 Web image values

The four `NEXT_PUBLIC_*` values are build arguments, because Next.js inlines them: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_API_BASE_URL` (`<API URL>/api/v1`) and `NEXT_PUBLIC_FEATURES_DISABLED`. Each environment therefore has its own web image. The runtime environment is only `PORT=3000`, `HOSTNAME=0.0.0.0`, `NODE_ENV=production`. The web image holds no secret.

### 4.4 Repository variables

The deploy workflows read Actions variables, none of them secret, and authenticate to AWS through OIDC, so no AWS key is stored (A1 §4.4). The names and values are in [aws-setup.md](aws-setup.md) §12 and [docs/secrets.md](../secrets.md). While a required variable is missing, a deploy workflow prints `AWS staging not configured (blocked by IMP-217)` or `AWS production not configured (blocked by IMP-801)` and ends green without deploying.

## 5. The release task (migrations, seed, RAG index)

Every deploy runs a one-off ECS task with the new API image before any service changes (A1 §4.5, IMD-103). The workflow registers a revision `group12-api-<env>-release` (the service's current task definition with the new image) and runs `sh scripts/release.sh`, which does, in order:

1. `python -m app.db.auth_stub --if-missing`: applies the auth stub only when schema `auth` is missing;
2. `alembic upgrade head`: the migrations; the container never migrates on start (IMD-38);
3. `python -m app.places.seed <dir>` for each directory in `SEED_DIRS` (staging: `data/places/ahmedabad`);
4. `python -m app.rag.index --strict`: exit 1 (guide-gate errors) fails the release; exit 3 (embedding provider unavailable) prints a warning and the release continues (IMD-112).

The workflow prints the task's CloudWatch log and fails on any non-zero exit; nothing is updated after a failure. The release task runs with the service's **current** environment, so a new template value (for example `SEED_DIRS`) reaches the release task one deploy after the deploy that sets it ([deployment.md](deployment.md) §6).

Checks of these commands, **Run (RUN-083)**, with `PYTHONPATH=apps/api` and the API virtual environment:

| Command | Result |
| --- | --- |
| `sh -n apps/api/scripts/release.sh` | no output, exit 0 |
| `python -m app.db.auth_stub --help` | exit 0; `usage: auth_stub.py [-h] --if-missing` |
| `python -m app.places.seed --help` | exit 0; `usage: python -m app.places.seed [-h] [--check] [--strict]` |
| `python -m app.rag.index --help` | exit 0; `usage: python -m app.rag.index [-h] [--destination SLUG] [--check] [--strict]` |

The same steps against a local database, **Not verified** (they need a database):

```sh
make db-bootstrap                              # auth stub if missing, then migrations (plain or RDS-like database)
make seed SEED_DIRS=data/places/ahmedabad      # SAMPLE fixture plus Ahmedabad
make rag-index ARGS='--strict'                 # all destinations; MOCK embeddings locally
```

## 6. Deploy

### 6.1 Staging

`deploy-staging.yml` runs after the **CI** workflow succeeds on a push to `main`, and by hand from `main`. Its steps: assume the OIDC role; build and push the API image tagged with the commit SHA; run the release task; update the API service with the rendered template and wait until `/health` reports the commit; build, push and update the web image the same way; load the web page and run `make smoke` with the CORS check ([deployment.md](deployment.md) §6).

Start it by hand (for example at the start of a staging window), **Not verified — run by Kirtan**:

```sh
gh workflow run deploy-staging.yml --ref main -f simulate_release_failure=false
```

### 6.2 Production

`deploy-production.yml` runs only by hand with a release tag `vMAJOR.MINOR.PATCH` that is on `main`; its deploy job waits for approval in the GitHub environment `production` (required reviewer Kirtan; IMD-185 requires that environment before the first production deploy). It needs the production services, database, templates and `PRODUCTION_*` variables of IMP-801. **Not verified — run by Kirtan** (no production deploy has been made at this version):

```sh
gh workflow run deploy-production.yml --ref main -f tag=v1.0.0
```

## 7. Smoke tests, rollback and staging windows

### 7.1 Smoke tests

After a deploy, **Not verified — run by Kirtan** (the deploy workflow also runs `make smoke`):

```sh
. infra/aws/env.sh
curl -sS "$STAGING_API_URL/health"
curl -sS -o /dev/null -w '%{http_code}\n' "$STAGING_WEB_ORIGIN/"
make smoke URL="$STAGING_API_URL" ARGS="--web-origin $STAGING_WEB_ORIGIN"
```

`/health` answers `{"status":"ok","version":"<commit>","environment":"staging","provider":"GEMINI"}` (the recorded staging answer is in section 1). `make smoke` also checks `/health/ready`, which reports the database.

The same smoke test against the production images on your own machine (A1 §4.6, TC-338), **Not verified** (needs Docker):

```sh
make db-up
docker compose run --build --rm --no-deps api sh scripts/release.sh
docker compose up --build -d api web
make smoke URL=http://localhost:8000 ARGS='--web-origin http://localhost:3000'
docker compose down
```

[gates.md](../progress/gates.md) (SG-1) records an earlier run of this local container smoke: `5 passed` with `--web-origin`.

### 7.2 Rollback

- **A failing release task** stops the deploy before any service changes; the running version keeps serving (NFR-035).
- **Forced failure (TC-438):** run **Deploy staging** with `simulate_release_failure` set to `true`; the release command becomes `false` and neither service changes. **Not verified — run by Kirtan:** `gh workflow run deploy-staging.yml --ref main -f simulate_release_failure=true`.
- **Rolling back a bad version:** deploy the previous tag's images, by running `deploy-production.yml` with the previous tag, or on staging by re-running the earlier commit's deploy. **Not verified — run by Kirtan.**
- **Migrations are forward only.** The `down` files exist for tests; a rollback never reverses a migration, so the older image must work with the newer schema.
- **Express Mode rollback alarm.** Each service has `default/<service>/RollbackAlarm`, which counts 4xx and 5xx responses at the time of observation (9 November 2026); IMD-139 decides it should count only 5xx and failed health checks, not yet applied ([deployment.md](deployment.md) §9).

### 7.3 Staging windows (IMD-137)

Staging is off between planned windows. Kirtan starts RDS and the services for a window, re-runs the deploy of the latest `main` and waits for it to end green before any staging check, and stops them afterwards, logging each start and stop in [deployment.md](deployment.md) §8. The exact start and scaling commands are still "to be confirmed by Kirtan" in that section. A stopped RDS instance starts again by itself after 7 days and is stopped again.

## 8. Cost guardrails (A1 §4.7, NFR-049)

- **Budget:** AWS Budgets, USD 50 per month, e-mail alerts at USD 25 and USD 50 (`01_budget.sh`; record for TC-435 in [aws-setup.md](aws-setup.md) §3). **Not verified — run by Kirtan.**
- **Size:** each service runs exactly one task (minimum and maximum one), 0.25 vCPU and 512 MiB.
- **Network:** no NAT gateway and no second load balancer; Express Mode shares one. Do not add either.
- **Logs:** 7 days of retention; ECR keeps the newest 10 images.
- **Staging windows:** staging is off outside windows (section 7.3).
- **Estimate:** the monthly cost table in [aws-setup.md](aws-setup.md) §14 is still "TO BE FILLED BY KIRTAN" from the AWS Pricing Calculator.
- **Production:** created only in Sprint 8 (IMP-801), and scaled down or deleted after the course demo, with the decision recorded.
- **Free plan:** if it refuses a needed service, stop and record a decision (IMD-104).
- **Pause or tear down:** `aws rds stop-db-instance`, `aws ecs delete-express-gateway-service`, the final snapshot and the deletions of [aws-setup.md](aws-setup.md) §15. **Not verified — run by Kirtan.**

## 9. Operator account deletion (NFR-022)

There is no delete-account screen. When a traveller asks for their account to be deleted, Kirtan does both halves (A1 §5.1, IMD-101):

1. **Supabase Auth.** In the Supabase dashboard, Authentication, Users, find the user, note the user ID (a UUID) and delete the user. **Not verified — run by Kirtan.**
2. **The database row.** Run a one-off ECS task with the API task definition and the command `python -m app.db.admin delete-user --user-id <uuid>`. It deletes the user's `auth.users` row in one transaction; the foreign keys cascade to the profile, trips and plans. The e-mail address is never stored in the database. The command refuses unless `DB_AUTH_STUB` is true (it is `true` in the API template), and prints only `delete-user: N row(s) deleted`.

A one-off task for step 2, following the release-task invocation of the deploy workflows (it needs the AWS CLI v2 and `jq`). **Not verified — run by Kirtan** (written for this guide; not tried against AWS):

```sh
. infra/aws/env.sh
user_id="<uuid from step 1>"
td="$(aws ecs describe-services --cluster "$ECS_CLUSTER" --services "$API_SERVICE" \
  --query "services[0].deployments[?status=='PRIMARY'].taskDefinition | [0]" --output text)"
container="$(aws ecs describe-task-definition --task-definition "$td" \
  --query 'taskDefinition.containerDefinitions[0].name' --output text)"
task_arn="$(aws ecs run-task --cluster "$ECS_CLUSTER" --task-definition "$td" --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$AWS_SUBNET_IDS],securityGroups=[$API_TASKS_SECURITY_GROUP],assignPublicIp=ENABLED}" \
  --overrides "$(jq -n --arg name "$container" --arg id "$user_id" \
    '{containerOverrides: [{name: $name, command: ["python", "-m", "app.db.admin", "delete-user", "--user-id", $id]}]}')" \
  --query 'tasks[0].taskArn' --output text)"
aws ecs wait tasks-stopped --cluster "$ECS_CLUSTER" --tasks "$task_arn"
aws logs get-log-events --log-group-name "$API_LOG_GROUP" --start-from-head \
  --log-stream-name "ecs/$container/${task_arn##*/}" --query 'events[].message' --output text
```

Expect `delete-user: 1 row(s) deleted` (0 rows when the user never used the app after signing up, so no row was mirrored). Record the date and the request, never the e-mail address.

Checks of the command, **Run (RUN-083)**:

| Command | Result |
| --- | --- |
| `python -m app.db.admin --help` | exit 0; `usage: admin.py [-h] {delete-user} ...` |
| `python -m app.db.admin delete-user --help` | exit 0; `usage: admin.py delete-user [-h] --user-id USER_ID` |

The command's database behaviour is covered by the IMP-219 tests on the compose database ([IMP-219 part record](../progress/parts/IMP-219-whole-task.md)); the one-off task on RDS has not been recorded.

## 10. Commands run while writing this guide

All in this repository at `f75aa94`, in a Linux container, with `PYTHONPATH=apps/api` and the proxy variables unset:

| Command | Result line |
| --- | --- |
| `make help` | exit 0 |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |
| `make lint` | `All checks passed!`; `All matched files use Prettier code style!` |
| `make typecheck` | `Success: no issues found in 123 source files` |
| `make imports` | `Contracts: 6 kept, 0 broken.` |
| `jq --version`, `docker --version`, `supabase --version` | `jq-1.7`, `Docker version 29.10.0, build fdd4b8e`, `2.122.0` (tool presence only; no container, stack or AWS command was run) |

## 11. Differences between documented and built behaviour

Found while writing this guide. None was checked against AWS.

1. **The card text and the hosting.** The IMP-707 card in specification §10.8 (step 4) still names Vercel, Render and Supabase; Amendment A1 and the amended card in TASK_REGISTER.md replace them with AWS (IMD-99), as this guide does.
2. **Production templates.** A1 §4.3 and `deploy-production.yml` expect production service templates; `infra/aws/services/` has only `api.staging.json.tmpl` and `web.staging.json.tmpl` (IMP-801 not done).
3. **`file:///dev/stdin` in the set-up scripts.** A1 §4.5 and the deploy workflows say AWS CLI v2 does not read `--cli-input-json file:///dev/stdin` and write a file instead (FIX-IMP-218). `infra/aws/02_rds.sh`, `04_ssm.sh` and `06_services.sh` still pipe into `--cli-input-json file:///dev/stdin`. Staging exists, so how these scripts behaved on Kirtan's machine is not recorded in the repository; Kirtan should confirm.
4. **Task definition query in aws-setup.md §13.** The TC-434 check reads `services[0].taskDefinition`, which Express Mode leaves empty ([deployment.md](deployment.md) §6, A1 §4.5). Section 9 above uses the `PRIMARY` deployment instead; the same change applies to the TC-434 check.
5. **Local auth in A1 §4.2.** A1 §4.2 names an HS256 secret for the local stack; newer Supabase CLI stacks need JWKS mode ([local-setup.md](local-setup.md) §4, IMD-123).
6. **Staging windows.** A1 §4.7 expects the staging services to run all the time with one task; IMD-137 switches staging off between windows, and the start, stop and scaling commands are not yet confirmed ([deployment.md](deployment.md) §8).
7. **Rollback alarm.** IMD-139 (5xx and failed health checks only) is decided but not applied; the observed alarm still counts 4xx.
8. **Cost estimate.** A1 §4.7 requires a cost estimate in aws-setup.md; its table is still to be filled.
