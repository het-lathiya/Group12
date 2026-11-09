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
