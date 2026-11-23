# Deployment: staging and production

- **Cards:** IMP-112 (image, smoke tests), IMP-217 (AWS foundation), IMP-218 (web image, AWS deploy workflows, release task) (US-002; FR-123; NFR-005, NFR-015, NFR-035)
- **Owner:** Kirtan (DevOps Engineer and Integration Lead)
- **Status:**
  - The local container path works.
  - Hosting is AWS (IMD-99). Vercel and Render are not used. The set-up is in [aws-setup.md](aws-setup.md); it is run by Kirtan, and its results are not recorded yet.
  - The deploy workflows follow A1 §4.5 and end green while their repository variables are missing. The first real deploy and the forced-failure run are recorded at IMP-299.

| Part | Where it runs | How it is deployed |
| --- | --- | --- |
| Web app (`apps/web/Dockerfile`) | Amazon ECS Express Mode service `group12-web-<env>` | Image pushed to ECR by the deploy workflow |
| API (`apps/api/Dockerfile`) | Amazon ECS Express Mode service `group12-api-<env>` | Image pushed to ECR by the deploy workflow |
| Database | Amazon RDS PostgreSQL 16, private, `travel_<env>` | Migrations from the release task (A1 §4.5, IMP-218), never on container start (IMD-38) |
| Auth | Hosted Supabase project, sign-in only (IMD-101) | Settings in the Supabase dashboard |

## 1. The images

`apps/api/Dockerfile` builds the production API image, with the repository root as build context:

- **Base and install:** `python:3.12-slim` with a normal (non-editable) wheel install of `apps/api`, so the prompt templates ship as package data (IMP-111).
- **Contents:** no dev extras or tests. For the release task it holds the migrations, `scripts/release.sh`, `data/places/` and `data/guides/` (when present); `data/fixtures/` stays out.
- **User:** a non-root user (`app`, uid 10001).
- **Command:** `uvicorn app.main:app` on `${PORT:-8000}`. The service template sets `PORT`.
- **Version:** `/health` reports `BUILD_VERSION`, the build argument baked into the image (the commit SHA, IMD-103), or `dev` locally.
- **No migrations on start:** the container never runs migrations (IMD-38).
- **Bad configuration:** the API refuses to start on a bad configuration and names the variable, never its value (FR-124).

`apps/web/Dockerfile` builds the production web image, with `apps/web` as build context. It is a standalone Next.js build on `node:22-slim`, run as the non-root user `node` on `PORT` 3000 with `HOSTNAME=0.0.0.0`. The four `NEXT_PUBLIC_*` values are build arguments, because Next.js inlines them, so each environment gets its own image. Neither image holds a secret or an `.env` file (TC-355, TC-434).

### Local container smoke (A1 §4.6, TC-338)

From the repository root. `docker compose up` needs no env file: the `api` service runs with `AI_PROVIDER=MOCK` against the compose `db`, and the web build arguments default to public local values.

```sh
make db-up
docker compose run --build --rm --no-deps api sh scripts/release.sh   # the release task: stub and migrations
docker compose up --build -d api web                                  # API on 8000, web on 3000
make smoke URL=http://localhost:8000 ARGS='--web-origin http://localhost:3000'
docker compose down
```

## 2. Deploy configuration

Deploys on AWS use the repository variables of A1 §4.4 and an OIDC role, so no AWS key and no deploy secret is stored. The names are in [docs/secrets.md](../secrets.md); the values are set in [aws-setup.md](aws-setup.md) section 12. The service secrets live in SSM Parameter Store.

## 3. API service

Replaced by the AWS set-up: see [aws-setup.md](aws-setup.md) sections 7 and 8. Render is not used (IMD-99).

## 4. Web service

Replaced by the AWS set-up: see [aws-setup.md](aws-setup.md) sections 9 and 10. Vercel is not used (IMD-99), so there are no pull-request previews. The staging API allows only the exact staging web origin (NFR-015).

## 5. Database and Auth

The database is RDS, set up in [aws-setup.md](aws-setup.md) section 4. It holds the auth stub, applied by `python -m app.db.auth_stub --if-missing` (IMP-219). Supabase serves sign-in only: its URL settings are in section 11 of the same guide, and e-mail confirmation follows IMP-113 section 2, so that the confirmation link reaches `/auth/callback` (IMP-109).

## 6. Deploy workflows

Both follow A1 §4.5. While a repository variable they need is missing, they print `AWS staging not configured (blocked by IMP-217)` or `AWS production not configured (blocked by IMP-801)`, skip the deploy job and end green.

- **`deploy-staging.yml`** runs after the **CI** workflow succeeds on a push to `main`, or by hand from `main`. It never runs on pull requests.
- **`deploy-production.yml`** runs by hand with a release tag `vMAJOR.MINOR.PATCH` (Kirtan). The tag must be on `main`, and the deploy job waits for approval in the GitHub environment `production`. It needs the production templates of IMP-801.

The steps, in order:

1. Assume the deploy role through OIDC.
2. Build the API image and push it, tagged with the commit SHA.
3. Run the release task:
   - register the revision `group12-api-<env>-release`: the service's current task definition with the new image;
   - run it with `sh scripts/release.sh`: auth stub, migrations, seed of `SEED_DIRS`, RAG index;
   - wait, print its CloudWatch log into the job log, and fail on any non-zero exit.
4. Update the API service with the full configuration rendered from its template, wait for the new image, then wait until `/health` reports the commit.
5. Build the web image with the environment's `NEXT_PUBLIC_*` values, push it and update the web service the same way.
6. Load the web page and run `make smoke` with the CORS check.

A failing release task stops the run before any service changes. An embedding outage (index exit 3) only warns (IMD-112).

The release task runs with the service's **current** environment, because its revision is copied from the running service. A new template value such as `SEED_DIRS` therefore reaches the release task on the deploy after the one that sets it.

**Express Mode note.** An Express Mode service leaves `taskDefinition` and `networkConfiguration` empty in `describe-services`. Its task definition is only under `deployments`, on the entry with status `PRIMARY`, and the workflow stops with an error when that entry is missing. The task definition families are `default-group12-<service>-<env>`, for example `default-group12-api-staging`. The release task's network comes from `AWS_SUBNET_IDS` and `API_TASKS_SECURITY_GROUP`.

**Forced failure (TC-438).** Run **Deploy staging** from `main` with `simulate_release_failure` set. The release command becomes `false`, the run fails at the release step, and neither service changes. Record the run link for IMP-299.

**Rollback.** Redeploy the previous tag's images: run `deploy-production.yml` with that tag, or on staging rerun the earlier commit's deploy. Production migrations are forward only: the `down` files exist for tests, so a rollback never reverses a migration, and the older image must work with the newer schema.

## 7. First-request time (NFR-005), not measured yet

Express Mode keeps one task running, so there is no sleep (A1 §9.2). After a deploy, Kirtan records the time of the first request with `curl -s -o /dev/null -w '%{time_total}\n' <staging API URL>/health`.

| Measurement | Date (YYYY-MM-DD) | Time since the deploy (minutes) | First `/health` response time (s) |
| --- | --- | --- | --- |
| 1 | | | |
| 2 | | | |
| 3 | | | |

**Wake-up routine before a demo or a test session:** to be written with the measurements.

## 8. Staging windows (IMD-137)

Staging is off between planned staging windows, to keep the AWS bill down. Kirtan turns it on for a window and off again afterwards, and logs every start and stop in the table below.

- Merges to `main` are allowed at any time. The automatic **Deploy staging** run that fails while staging is off is expected.
- Staging must be on, with a green **Deploy staging** run of the latest `main`, before any staging check, the IMP-414 staging run and each gate.
- A stopped RDS instance starts again by itself after 7 days. Stop it again when that happens and log it.
- The load balancer is billed while the services exist, even with no task running.

**Start order**

1. Start the RDS instance `group12-rds`: to be confirmed by Kirtan in the next staging window (the command, and how long it takes).
2. Wait until it reports `available`:
   `aws rds describe-db-instances --db-instance-identifier group12-rds --query 'DBInstances[0].DBInstanceStatus' --output text`
3. Scale the API service, then the web service, back up: to be confirmed by Kirtan in the next staging window (Express Mode scaling is set through `update-express-gateway-service --scaling-target`; whether `minTaskCount` may be 0 is not confirmed).
4. Re-run the deploy of the latest `main`:
   `gh workflow run deploy-staging.yml --ref main -f simulate_release_failure=false`
   and wait for it to end green before any check.

**Stop order** (after the window)

1. Scale the web service, then the API service, down: to be confirmed by Kirtan in the next staging window.
2. Stop the RDS instance `group12-rds`: to be confirmed by Kirtan in the next staging window.
3. Check what is left running (read-only):
   - `aws ecs describe-services --cluster default --services group12-api-staging group12-web-staging --query 'services[].{name:serviceName,running:runningCount,desired:desiredCount}' --output table`
   - `aws rds describe-db-instances --db-instance-identifier group12-rds --query 'DBInstances[0].DBInstanceStatus' --output text`

**Stop and start log**

| Date (YYYY-MM-DD) | Time (IST) | Action (start, stop, auto-restart stopped) | By | Deploy run link (after a start) | Note |
| --- | --- | --- | --- | --- | --- |
| | | | | | |

## 9. Rollback alarm (IMD-139)

**Current alarm (as observed on 9 November 2026).** Each Express Mode service has the alarm `default/<service>/RollbackAlarm`. It fires when the share of 4xx and 5xx responses is above 1 % in 2 of 3 minutes, and a firing alarm rolls the deployment back. Because 4xx responses count, ordinary client errors (for example 401 without a token, 404, 422) can roll a healthy deployment back.

**Target (IMD-139).** For the web and API services, count only 5xx responses and failed health checks, not 4xx. The health-check rollback stays on. No change is made yet: Kirtan applies it once the place where Express Mode keeps this configuration is confirmed.

**Inspect the alarms (read-only):**

`aws cloudwatch describe-alarms --alarm-name-prefix default/group12- --query 'MetricAlarms[].{name:AlarmName,state:StateValue,threshold:Threshold,operator:ComparisonOperator,periods:EvaluationPeriods,datapoints:DatapointsToAlarm}' --output table`

Run it with `--query 'MetricAlarms[].Metrics'` instead to see the metrics the alarm adds up. Where the alarm is configured, and how to change it, is to be confirmed by Kirtan in the next staging window.

## 10. Any-city mode addendum (Amendment A2 §7.2; IMP-733)

Any-city mode is OFF by default, and its routes answer 404 then. Turning it on for staging or production is a configuration change, set by Kirtan as the AWS account owner. This addendum documents it; no `infra/` template or workflow is changed by it.

**Switch.**

- The token `!any_city_mode` goes into the repository variable `STAGING_FEATURES_DISABLED`, comma-separated with any cut-list names already there.
- That one variable reaches both sides:
  - the API, as `FEATURES_DISABLED` (`infra/aws/services/api.staging.json.tmpl`);
  - the web build argument `NEXT_PUBLIC_FEATURES_DISABLED` (`deploy-staging.yml`).
  Both must carry the token, so a redeploy rebuilds the web image.
- An explicit `any_city_mode` in the list wins and keeps the mode OFF (A2 §3.1).

**Variables (plain task-definition environment; none is a secret, IMD-102).**

| Name | Default | Staging value with the switch ON |
| --- | --- | --- |
| `LIVE_DATA_PROVIDER` | `FAKE` | `LIVE` (start-up refuses `FAKE` in staging and production with the switch ON) |
| `WIKI_USER_AGENT` | empty | "<to be set by Kirtan: app name + team contact>", for example `AITravelPlanner/1.0 (contact: <team address>)`; required with `LIVE`, never a placeholder |
| `NOMINATIM_BASE_URL` | `https://nominatim.openstreetmap.org` | default (`https://` only) |
| `OVERPASS_BASE_URL` | `https://overpass-api.de/api/interpreter` | default (`https://` only) |
| `NOMINATIM_TIMEOUT_S` | 10 | default |
| `OVERPASS_TIMEOUT_S` | 90 | default |
| `MEDIAWIKI_TIMEOUT_S` | 10 | default |
| `LIVE_MIN_USABLE_PLACES` | 40 | default |
| `LIVE_DATA_TTL_DAYS` | 30 | default |
| `LIVE_DAILY_IMPORTS_PER_USER` | 5 | default |
| `LIVE_DAILY_IMPORTS_GLOBAL` | 50 | default (IMD-217) |

No new `NEXT_PUBLIC_*` name is added. The names and defaults are in `.env.example`.

**One API task while ON.** The outbound spacing and the circuit breakers of the live-data services are per process (A2 §7.3), and imports are serial in one process. Keep the API service at one running task while the switch is ON (IMD-12).

**Pre-import.** Before a demo, import the demo cities with the CLI in a one-off task (`python -m app.places.live_import --query "<city>"`). The runbook is [any-city-staging.md](any-city-staging.md).

**Rollback.** Remove `!any_city_mode` from `STAGING_FEATURES_DISABLED` and deploy. The routes answer 404, the city search disappears, curated trips are unchanged, and no data is deleted. `LIVE_DATA_PROVIDER` can stay `LIVE`: it has no effect with the switch OFF.

**Production.** The same names apply to the production service (IMP-801). Production is not created yet.
