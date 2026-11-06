# Deployment: staging and production

- **Cards:** IMP-112 (image, smoke tests, workflows), IMP-217 (AWS foundation), IMP-218 (AWS deploy workflows) (US-002; FR-123; NFR-005, NFR-015, NFR-035)
- **Owner:** Kirtan (DevOps Engineer and Integration Lead)
- **Status:**
  - The local container path works.
  - Hosting is AWS (IMD-99). Vercel and Render are not used. The set-up is in [aws-setup.md](aws-setup.md); it is run by Kirtan, and its results are not recorded yet.
  - The deploy workflows still hold the IMP-112 Render steps, skip while their secrets are missing, and are replaced by IMP-218.

| Part | Where it runs | How it is deployed |
| --- | --- | --- |
| Web app (`apps/web`) | Amazon ECS Express Mode service `group12-web-<env>` | Image pushed to ECR; by hand until IMP-218 |
| API (`apps/api/Dockerfile`) | Amazon ECS Express Mode service `group12-api-<env>` | Image pushed to ECR; by hand until IMP-218 |
| Database | Amazon RDS PostgreSQL 16, private, `travel_<env>` | Migrations from the release task (A1 §4.5, IMP-218), never on container start (IMD-38) |
| Auth | Hosted Supabase project, sign-in only (IMD-101) | Settings in the Supabase dashboard |

## 1. The API image

`apps/api/Dockerfile` builds the production image:

- **Base and install:** `python:3.12-slim` with a normal (non-editable) wheel install of `apps/api`, so the prompt templates ship as package data (IMP-111).
- **Contents:** no dev extras, tests or migrations.
- **User:** a non-root user (`app`, uid 10001).
- **Command:** `uvicorn app.main:app` on `${PORT:-8000}`. The service template sets `PORT`.
- **Version:** `/health` reports `BUILD_VERSION`, or `dev` when it is not set. IMP-218 bakes the commit SHA into the image at build time (IMD-103).
- **No migrations on start:** the container never runs migrations (IMD-38).
- **Bad configuration:** the API refuses to start on a bad configuration and names the variable, never its value (FR-124).

### Local container run (the card's path while the accounts are missing)

From the repository root:

```sh
make db-up
psql "postgresql://postgres:postgres@localhost:5432/travel_test" -v ON_ERROR_STOP=1 \
  -f apps/api/migrations/sql/test_auth_stub.sql      # plain PostgreSQL only, never Supabase
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/travel_test make db-migrate
```

The `api` service of `docker-compose.yml` sits behind the `api` profile, and its `apps/api/.env` file is optional (IMP-105). To pass non-secret local values without an env file, use a compose override file outside the repository:

```yaml
services:
  api:
    environment:
      APP_ENV: local
      AI_PROVIDER: MOCK
      DATABASE_URL: postgresql+psycopg://postgres:postgres@db:5432/travel_test
      ALLOWED_ORIGINS: http://localhost:3000
    depends_on:
      db:
        condition: service_healthy
```

Then run:

```sh
docker compose -f docker-compose.yml -f <override file> --profile api up -d --build api
make smoke URL=http://localhost:8000 ARGS='--web-origin http://localhost:3000'
docker compose --profile api down   # stops api and db
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

**These still describe the IMP-112 Render steps.** While their secrets are missing they end green without deploying. IMP-218 replaces them with the AWS flow of A1 §4.5.

### `deploy-staging.yml`

- **Trigger:** runs after the **CI** workflow completes successfully on a push to `main`. It never runs on pull requests.
- **Configuration check:** the job first checks the four staging secrets.
  - If one is missing, it prints `staging not configured (blocked by IMP-113)` with the missing names and ends successfully.
  - Otherwise it checks out the commit CI tested and then runs four steps in order:
    1. `make db-migrate` with `DATABASE_URL` from `STAGING_DATABASE_URL`;
    2. a POST to the Render deploy hook with `ref=<commit>`;
    3. a poll of `GET /health` every 15 s, for up to 20 minutes, until `version` equals the commit (this also covers a cold start);
    4. `make smoke URL=<staging API URL> ARGS='--web-origin <staging web origin>'`.

### `deploy-production.yml`

- **Trigger:** "Run workflow" by hand, with a release tag `vMAJOR.MINOR.PATCH` (Kirtan, §4.5).
- **Checks and steps:** the same configuration check with the `PRODUCTION_*` secrets. When configured:
  1. checks that the tag is on `main`;
  2. runs the same four steps against production.

## 7. First-request time (NFR-005), not measured yet

Express Mode keeps one task running, so there is no sleep (A1 §9.2). After a deploy, Kirtan records the time of the first request with `curl -s -o /dev/null -w '%{time_total}\n' <staging API URL>/health`.

| Measurement | Date (YYYY-MM-DD) | Time since the deploy (minutes) | First `/health` response time (s) |
| --- | --- | --- | --- |
| 1 | | | |
| 2 | | | |
| 3 | | | |

**Wake-up routine before a demo or a test session:** to be written with the measurements.
