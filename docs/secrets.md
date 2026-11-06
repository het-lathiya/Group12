# Secrets register

Which secret values exist, who owns each, where it is stored and when it is rotated. **This file never holds a value**, not even a local one. Variable names come from `.env.example` (specification §4.5); a new secret variable gets a row here in the same pull request that adds it. The hosted accounts (GitHub, AWS, Supabase, Google AI Studio, OpenRouteService, email sender) and their owners are recorded in [docs/decisions/accounts.md](decisions/accounts.md) (IMP-113). The "Owner member" column confirms who holds each value; it names a member, never a value.

## Where values live

| Environment | Store |
| --- | --- |
| Local (each member) | Untracked `apps/api/.env` and `apps/web/.env.local`, copied from `.env.example` and `apps/web/.env.local.example`; local Supabase keys come from `supabase status -o env` |
| Pull-request CI | No secret except the built-in `GITHUB_TOKEN`; `AI_PROVIDER=MOCK` and fixed local values in `.github/workflows/ci.yml` |
| Staging and production | AWS SSM Parameter Store SecureString parameters `/group12/<env>/<NAME>`, which reach the API container as ECS `secrets` references (IMD-102, [docs/guides/aws-setup.md](guides/aws-setup.md)). Non-secret settings live in `infra/aws/services/*.json.tmpl`. The web image holds only `NEXT_PUBLIC_*` values. GitHub Actions authenticates through the OIDC role `group12-github-deploy`, so no AWS key is stored anywhere |
| Team copy | The team password manager, one entry per hosted value, shared only with the owner and the integration lead |
| AWS set-up names | Untracked `infra/aws/env.sh`, which holds names and no secret |

## Register

"Local stack" values are created by `supabase start` on each member's machine, only work against that machine's stack and never leave it.

| Variable | Secret? | Owner role | Owner member | Where stored | Rotation rule |
| --- | --- | --- | --- | --- | --- |
| `DATABASE_URL` | Yes in staging and production (holds the database password); local default is not secret | Database Engineer (Malhar), with the DevOps Engineer and Integration Lead (Kirtan) for the hosted values | TO BE FILLED BY KIRTAN | Local: `apps/api/.env`. Staging, production: SSM `/group12/<env>/DATABASE_URL`, password manager | Change the RDS master password, then run `infra/aws/04_ssm.sh --overwrite` and redeploy, when exposed or when a member with access leaves |
| `TEST_DATABASE_URL` | No (fixed local and CI value `travel_test`) | Database Engineer (Malhar) | TO BE FILLED BY KIRTAN | `.env.example` default, `ci.yml` | None; never point it at a hosted database |
| `SUPABASE_URL` | No: A1 §4.3 makes it plain environment, and the same URL is public in the web app | Backend Engineer, Auth (Het), with the Integration Lead for hosted values | TO BE FILLED BY KIRTAN | Local: `apps/api/.env` (local stack). Staging, production: service template, from the repository variable `<ENV>_SUPABASE_URL` | None while the project exists; it changes only when the project is replaced, and then every store is updated |
| `SUPABASE_JWT_SECRET` | Yes | Backend Engineer, Auth (Het), with the Integration Lead for hosted values | TO BE FILLED BY KIRTAN | Local: `apps/api/.env` (local stack). Staging, production (HS256 mode only): SSM `/group12/<env>/SUPABASE_JWT_SECRET`, password manager | Hosted: rotate in the Supabase dashboard when exposed (this signs out every user); local: `make stack-down` and a fresh stack |
| `SUPABASE_JWKS_URL` | No (public URL) | Backend Engineer, Auth (Het) | TO BE FILLED BY KIRTAN | Service template in `infra/aws/services/` | None (OD-06 decides whether it is used) |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes (bypasses row-level security) | Frontend and QA Engineer, E2E (Krrish) | TO BE FILLED BY KIRTAN | Local only: `apps/api/.env` for `make e2e` | Never set outside the local stack; if a hosted service-role key is ever exposed, rotate it in the Supabase dashboard at once |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | No (public by design; row-level security protects data) | Frontend Engineer, Web App Lead (Manasvi), with the Integration Lead for hosted values | TO BE FILLED BY KIRTAN | Local: `apps/web/.env.local`. Staging, production: repository variable `<ENV>_SUPABASE_ANON_KEY`, a build argument of the web image | Rotate together with the JWT secret, then rebuild the web image |
| `GEMINI_API_KEY` | Yes (billed; spending control in production) | AI Engineer, Provider Layer (Nidhi) | TO BE FILLED BY KIRTAN | Staging, production: SSM `/group12/<env>/GEMINI_API_KEY`, password manager. Local: only for `make live-smoke`, a personal key in `apps/api/.env` | Revoke and replace at once when exposed; replace when a member with access leaves; never in pull-request CI |
| `ORS_API_KEY` | Yes | Backend and QA Engineer, Routing (Junaid) | TO BE FILLED BY KIRTAN | Staging, production: SSM `/group12/<env>/ORS_API_KEY`, password manager. Local: optional, `apps/api/.env` | Revoke and replace when exposed or when a member with access leaves |
| RDS master password (not an environment variable) | Yes | DevOps Engineer and Integration Lead (Kirtan) | TO BE FILLED BY KIRTAN | Inside `DATABASE_URL` in SSM, password manager. Set by the owner, not managed by RDS | Change it on the instance and update `DATABASE_URL` when exposed or when a member with access leaves |
| `FINETUNED_API_KEY` | Yes when used | AI Engineer, Provider Layer (Nidhi) | TO BE FILLED BY KIRTAN | Empty in Stage 1 | Defined by the Stage 2 decision that enables the adapter |

`GEMINI_MODEL_ID` is not secret: Nidhi records the chosen identifier in [docs/decisions/accounts.md](decisions/accounts.md) section 3, and it is set in `infra/aws/services/api.staging.json.tmpl` by the pull request that switches staging to Gemini (IMP-316).

Non-secret settings (`APP_ENV`, `ALLOWED_ORIGINS`, caps, timeouts, `WIKI_USER_AGENT`, `FEATURES_DISABLED` and the other `NEXT_PUBLIC_*` names) are listed only in `.env.example`.

## Repository variables (AWS deploys)

These are GitHub Actions **variables, not secrets**: none of them is a secret, so they may be read in logs (A1 §4.4). Owner for all of them: DevOps Engineer and Integration Lead (Kirtan). Where each value comes from is in [docs/guides/aws-setup.md](guides/aws-setup.md) section 12. The AWS account holds no access key for CI.

| Variable | Meaning |
| --- | --- |
| `AWS_REGION`, `AWS_ACCOUNT_ID` | Region (`ap-south-1`) and account |
| `AWS_DEPLOY_ROLE_ARN` | The OIDC role `group12-github-deploy` |
| `ECR_API_REPO`, `ECR_WEB_REPO` | The two ECR repositories |
| `ECS_EXECUTION_ROLE_ARN`, `ECS_INFRASTRUCTURE_ROLE_ARN` | The two ECS roles |
| `AWS_SUBNET_IDS`, `API_TASKS_SECURITY_GROUP` | Network of the release task, recorded from the API service |
| `STAGING_API_SERVICE_ARN`, `STAGING_WEB_SERVICE_ARN` | The staging services |
| `STAGING_API_URL`, `STAGING_WEB_ORIGIN` | The staging URLs |
| `STAGING_SUPABASE_URL`, `STAGING_SUPABASE_ANON_KEY` | Public values of the auth-only Supabase project |
| `STAGING_FEATURES_DISABLED` | Switched-off features; may be empty |
| The seven `PRODUCTION_*` equivalents | Set in IMP-801 |

## Rules for every secret

- Never commit, print, log or paste a value: not in code, tests, fixtures, issues, pull requests, progress records or chat. Redact keys in any pasted command output.
- CI fails when a real env file is tracked (the `guards` job; only the two templates are allowed) and when gitleaks finds a secret pattern.
- Do not set `GOOGLE_API_KEY`: the Gemini SDK would prefer it to `GEMINI_API_KEY`.
- **When a value is exposed**: tell the owner and the integration lead at once, rotate it first, then remove it from where it leaked. Removing a commit does not un-expose a value that was pushed.
