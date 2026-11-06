# IMP-218 · deploy-workflows part

- Run id: RUN-042
- Owner: Junaid (card lead)
- Status: **implemented; everything that runs without AWS is verified. TC-437, TC-438, the staging smoke and CORS on staging are verified after merge**
- Base commit: `2c66e14`
- Traces to: US-002, US-163; FR-123; NFR-013, NFR-015, NFR-035, NFR-048; TC-288, TC-351, TC-434, TC-437, TC-438

## Changed files

- `apps/api/Dockerfile` (modified):
  - The repository root is now the build context.
  - The image adds `alembic.ini`, `migrations/`, `scripts/` and `data/` under `/srv/api`, and `BUILD_VERSION` is a build argument.
  - `data/` belongs to the user `app`, because `app.places.seed` writes `quality_report.md` into each destination directory.
  - A link from `site-packages/migrations` to `/srv/api/migrations` makes `AUTH_STUB_SQL` resolve without changing application code.
  - It still never migrates on start (IMD-38).
- `apps/api/scripts/release.sh` (created): auth stub, migrations, seed of `SEED_DIRS`, and the RAG index when `app.rag.index` exists. Index exit 3 only warns; exit 1 and 2 fail.
- `.github/workflows/deploy-staging.yml` and `deploy-production.yml` (rewritten): the flow of A1 §4.5. `deploy-staging.yml` also has the `workflow_dispatch` input `simulate_release_failure`.
  - A `check-configuration` job prints the notice of A1 §4.4 and the deploy job is skipped, so a production run asks for approval only when it can deploy.
  - Service templates are checked before the release task, because migrations are forward only.
  - After an update, the job waits until the only active configuration holds the new image, then runs `services-stable`, which alone can return before a rollout starts.
- `.github/workflows/ci.yml` (modified): a "Web production build" step in the existing `lint-types` job. No other CI change.
- `apps/api/tests/smoke/test_deployed.py` (modified): `/health` must report `BUILD_VERSION` when that variable is set. The deploy workflows set the commit SHA. It is read from the environment because `conftest.py` is not on the card's Files list.
- `docker-compose.yml` (modified): the `api` service builds from the repository root, has fixed local values and waits for `db`. The `profiles` lines are removed (PD-IMP-218-3).
- `docs/guides/deployment.md` (modified): the images, the local container smoke, the deploy flow, forced failure and rollback.

## Narrowed changes

- **PD-IMP-217-1.** `infra/aws/05_iam.sh` adds `ecs:CreateGateway`, `ecs:AssociateGatewayWithCluster` and `ecs:TagResource` to the deploy role, because AWS lists them as dependent actions of `UpdateExpressGatewayService`.
  - They are limited to `gateway/*` and `service/<cluster>/group12-*`. The AWS service reference (`servicereference.us-east-1.amazonaws.com/v1/ecs/ecs.json`) gives `gateway` as the resource of the first two.
  - `docs/guides/aws-setup.md` section 6 matches.
- **PD-IMP-217-2.** The hosted project signs with an ES256 key, so staging uses JWKS mode.
  - `api.staging.json.tmpl` sets `SUPABASE_JWKS_URL` from the `${SUPABASE_JWKS_URL}` placeholder and no longer references `SUPABASE_JWT_SECRET`.
  - The workflows fill the placeholder from `STAGING_SUPABASE_URL` plus `/auth/v1/.well-known/jwks.json`.
  - `04_ssm.sh` asks for `SUPABASE_JWT_SECRET` only if the template references it.
  - `docs/secrets.md` and `docs/guides/aws-setup.md` are updated: Kirtan must not create that parameter.
  - `06_services.sh` renders the same template and stops without the placeholder's variable. `env.sh.example` is outside this run's file list, so `aws-setup.md` section 2 adds one line to `env.sh` by hand (see Open issues).
- **Web build check.** The `ci.yml` step above. It would have caught the build break found in RUN-036b.

`aws-setup.md` sections 7 and 9 also change, because the API image now builds from the repository root and the web image has a real Dockerfile.

## Preflight

| Check | Result |
| --- | --- |
| Algorithms in JWKS mode (`app/auth/tokens.py`) | `ES256`, `RS256`, `EdDSA` |
| Hosted JWKS (public) | one key: `kty` EC, `crv` P-256, `alg` ES256, no private part |
| A real ES256 token through `TokenVerifier`, with a local JWKS | valid token verified; wrong key, expired token and forged HS256 token each refused with `Unauthenticated` |
| Tools | `Docker version 29.9.2`, `aws-cli/2.39.5`; actionlint 1.7.12, shellcheck 0.11.0 and jq 1.8.2 installed for the current user |

## Commands run

| Command | Result line |
| --- | --- |
| `docker build -f apps/api/Dockerfile --build-arg BUILD_VERSION=imp218test -t group12-api:imp218 .` | exit 0; image size `368MB` |
| `docker compose run --rm --no-deps -e SEED_DIRS=data/places/ahmedabad api sh scripts/release.sh` (blank database) | `Running upgrade 0006 -> 0007`; `seed ahmedabad: places inserted 103, updated 0, unchanged 0, deactivated 0`; `release: done`; exit 0 |
| The same command again | `places inserted 0, updated 0, unchanged 103`; exit 0 |
| `docker compose run --rm --no-deps api false` (the forced-failure command) | `false exit=1` |
| `release.sh` with stub `python` and `alembic` | index 0: exit 0; index 3: warning, exit 0; index 1: exit 1; index 2: exit 2; no module: skipped, exit 0; alembic 7: exit 7; stub step 5: exit 5 |
| `docker compose up -d api web`, `make smoke URL=http://localhost:8000` | `4 passed, 1 skipped in 0.13s` |
| `make smoke URL=http://localhost:8000 ARGS='--web-origin http://localhost:3000'` | `5 passed in 0.06s` |
| `BUILD_VERSION=wrong make smoke URL=http://localhost:8000` (mutation) | `1 failed, 3 passed, 1 skipped in 0.10s` |
| `docker compose logs api`, counting `Running upgrade` | `0` (no migration on start, IMD-38) |
| `docker compose down` | ` Network group12_default Removed `; no container left |
| Image scan, `.env` files and key-like values | API `count: 0`, `matches: 0`; web `count: 0`, `matches: 0` |
| `actionlint -no-color .github/workflows/*.yml` (shellcheck on `PATH`) | `actionlint exit=0` |
| `bash -n` and `shellcheck` on `release.sh`, `04_ssm.sh`, `05_iam.sh`, and shellcheck on the deploy helpers | `rc=0` for each |
| `envsubst` plus `jq -e` on both staging templates | `rc=0`; no `${` left |
| The API image with the rendered staging environment (`APP_ENV=staging`, JWKS mode, empty values kept), `make smoke` | `5 passed in 0.10s`; `/health/ready` `ready`, migration `0007`; a protected route without a token `401` |
| Rendered JSON keys against `aws ecs update-express-gateway-service --generate-cli-skeleton` and `register-task-definition --generate-cli-skeleton` | no unknown key |
| Every `aws` command and option in the workflows against `aws <service> <command> help` | all exist |
| Web production build, the commands of the new `ci.yml` step | `✓ Generating static pages using 12 workers (11/11)`; exit 0 |
| `make lint` | `All matched files use Prettier code style!` |
| `make typecheck` | `Success: no issues found in 85 source files` |
| `make imports` | `Contracts: 4 kept, 0 broken.` |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |
| `make test` | unit `385 passed, 1 warning in 7.33s`; contract `35 passed, 1 warning in 0.65s`; api `231 passed, 1 warning in 55.25s`; authz `28 passed in 10.56s`; web `Tests  80 passed (80)` |

**Workflow dry run.** A scratch harness ran every `run:` step of the real YAML against stub `aws`, `docker`, `curl` and `make` programs, with no credentials and no call to AWS. It proves the logic and the order, not AWS's behaviour.

| Scenario | Result |
| --- | --- |
| Staging, all succeed | all steps pass; 2 services updated; call order as A1 §4.5 |
| `simulate_release_failure=true` | fails at the release step with override `["false"]`; 0 services updated |
| Release exit 1 | fails at the release step; 0 services updated |
| Container never started (exit code `None`) | fails at the release step; 0 services updated |
| Task not started | fails at the release step; 0 services updated |
| Rollout never finishes | fails after 15 minutes at the API update; web untouched |
| Production, no templates | fails at the template check, before any build or release |
| Production, temporary templates (removed afterwards) | all steps pass; family `group12-api-production-release` |
| Production, tag not on `main` | fails; 0 services updated |
| Variables: none set, one missing, all set (both workflows) | exit 0 with `configured=false`, `false`, `true`; the notice text of A1 §4.4 |

## Acceptance

| Criterion | Status | How |
| --- | --- | --- |
| After a merge to main, both images are built with the SHA, the release task exits 0, both services update and `make smoke` passes (US-002 AC1, TC-437, TC-288) | not verified | Needs AWS and Kirtan's set-up; verified from the first run after merge (IMP-299). Order and logic shown by the dry run |
| A failing release task stops the workflow before any service update (TC-438) | not verified | Needs AWS; recorded run after merge (IMP-299). Logic shown by the dry run |
| CORS admits the staging web origin and refuses another (US-002 AC2, NFR-015, TC-351) | not verified on staging | Verified locally: `5 passed`, and with the rendered staging environment |
| Neither image contains a secret or an `.env` file (TC-434 repository half) | verified | Image scans; the template holds SSM ARNs only |
| `docker compose up api web` and `make smoke` pass locally (NFR-035, TC-338) | verified | Commands above |
| The release script steps, exit codes and idempotence (A1 §4.5) | verified | Real run on a blank database, twice; stub runs for the index exit codes, because `app.rag.index` does not exist yet |
| Workflows end green with the notice while variables are missing (A1 §4.4) | verified locally | Dry run; confirmed by the first run on `main` after merge |
| actionlint and shellcheck clean; rendered templates valid JSON; every `aws` command and option exists | verified | Commands above |

## Blockers

None for this pull request. The first real deploy needs Kirtan's set-up and the repository variables.

## Proposed decisions

- **PD-IMP-218-3 (`profiles` removed from `docker-compose.yml`):** with profiles, `docker compose down` and `make db-down` leave `api` and `web` running and fail on the network. Without them `make db-up` still starts only `db`, because it names the service. A bare `docker compose up` now starts all three. This changes a choice of IMP-105 and IMP-112.
- **PD-IMP-218-4 (compose `api` environment):** the card names only the build context, but TC-338 needs `docker compose up api web` to run without an env file, so the service sets `APP_ENV`, `AI_PROVIDER`, `DATABASE_URL`, `ALLOWED_ORIGINS` and `DB_AUTH_STUB`. A1 §4.6 says "against the local stack"; the compose `db` is used, because that is the one a container can reach.
- **PD-IMP-218-5 (specification text):** A1 §4.3 and §4.4 still list the HS256 secret and the shorter action list. The decision run should record OD-06 as JWKS and add the three actions, as `docs/spec/` is outside this run.

## Open issues

- **`env.sh.example` lacks `SUPABASE_JWKS_URL`.** Kirtan adds the line by hand (`aws-setup.md` section 2). If it is missed, `06_services.sh` stops with `needs SUPABASE_JWKS_URL` before creating anything. A later change should add it to the example.
- **`apps/api/.dockerignore` is now unused,** because the build context is the repository root, and its comment is out of date. Deleting it was outside this run's file list.
- **Assumptions only the first AWS run can check:**
  - `activeConfigurations` shrinks to the new image once a rollout ends. If it does not, the update step times out after 15 minutes, with the service already updated.
  - The release task log stream is `<prefix>/<container>/<task id>`. If it is not, the job warns and the exit code still decides.
  - Whether the three added actions are enough, and whether their resources are wide enough for `ecs:TagResource`.
- **The release task runs with the service's current environment,** as A1 §4.5 specifies. A new template value such as `SEED_DIRS` reaches it one deploy later (`deployment.md` section 6).
- **No committed test covers ES256.** It was shown by a one-off script in this run. Suggested for the IMP-108 owner.
- `apps/api/tests/smoke/README.md` still shows `docker compose --profile api up api`. It still works; the text is out of date.
