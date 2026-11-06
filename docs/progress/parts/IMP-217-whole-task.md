# IMP-217 · whole-task part

- Run id: RUN-041
- Owner: Kirtan (kirtan-S111)
- Status: PR_OPEN. The scripts, templates and guides are complete and checked offline; **no AWS resource exists because of this run**, and every live criterion is not verified.
- Base commit: 94849c6
- Branch: feat/IMP-217-whole-task
- Reviewer: Junaid (Junaid-Kureshi)
- Traces to: US-002, US-004, US-163; FR-123; NFR-005, NFR-013, NFR-015, NFR-035, NFR-049; TC-288, TC-354, TC-433 to TC-436; IMD-99 to IMD-104 (Amendment A1 §4)
- Card steps built: 1 to 6 as scripts and templates, 7 and 8 as guide steps, 9 and 10. Running them is Kirtan's, after merge.
- IMP-113: the operator confirmed on 6 November 2026 that Kirtan's AWS account exists. This is an operator fact, not verified here; `docs/decisions/accounts.md` is unchanged.

## Changed files

- `infra/aws/README.md` (created): what each file does and the rules.
- `infra/aws/env.sh.example` (created): names and placeholders for the untracked `env.sh`.
- `infra/aws/01_budget.sh` (created): USD 50 monthly budget, alerts at USD 25 and USD 50.
- `infra/aws/02_rds.sh` (created): security group `group12-rds` with no inbound rule, and RDS instance `group12-rds` with the settings of A1 §4.1. The master password is typed at a hidden prompt and reaches the CLI on standard input.
- `infra/aws/03_ecr.sh` (created): `group12-api` and `group12-web`, scan on push, newest 10 kept.
- `infra/aws/04_ssm.sh` (created): the four SecureString parameters, read with `read -s` and passed on standard input. It builds `DATABASE_URL` from the RDS endpoint with the password percent-encoded. `--overwrite` replaces values.
- `infra/aws/05_iam.sh` (created): the two ECS roles, the OIDC provider and `group12-github-deploy`, with the three subjects and the permissions of A1 §4.4.
- `infra/aws/06_services.sh` (created): phases `api` and `web`, because the web image is built with the API URL.
- `infra/aws/services/api.staging.json.tmpl`, `infra/aws/services/web.staging.json.tmpl` (created): full service configuration.
- `docs/guides/aws-setup.md` (created): account checks, run order, first images by hand, repository variables, what to record, cost table to fill in, teardown.
- `docs/secrets.md` (modified): stores moved to SSM and the template, RDS master password row, repository variables section.
- `docs/guides/deployment.md` (modified): Render and Vercel sections are pointers to the AWS guide. The workflow section still describes IMP-112, and says so, because IMP-218 replaces the workflows.
- `.gitignore` (modified): `infra/aws/env.sh`.
- `docs/progress/parts/IMP-217-whole-task.md` (created): this record.

Not changed: application code, migrations, `contracts/`, environment variable names, Make targets, workflows, `docs/decisions/accounts.md`.

## Design notes

- **Template placeholders** are `IMAGE` and repository variables of A1 §4.4 only (`AWS_REGION`, `AWS_ACCOUNT_ID`, `ECS_EXECUTION_ROLE_ARN`, `ECS_INFRASTRUCTURE_ROLE_ARN`, `STAGING_WEB_ORIGIN`, `STAGING_SUPABASE_URL`, `STAGING_FEATURES_DISABLED`), so IMP-218 can render them without a new variable.
- **Update shape.** The templates are in the create shape. An update drops `serviceName`, `cluster` and `infrastructureRoleArn` and adds `serviceArn`; `06_services.sh` does this, and IMP-218 must do the same.
- **Log groups** are pinned to `/ecs/group12-api-staging` and `/ecs/group12-web-staging` in the templates and created by the script. The Express Mode default name ends in a generated suffix, so the deploy role's `logs:GetLogEvents` could not be scoped and retention could not be set before the first task.
- **`RDS_MASTER_USER`** is `group12_owner`. A1 does not name it.
- **No shared script library:** the card's Files list has none, so the short preamble is repeated in each script.
- **The temporary web Dockerfile** of guide section 9 lives outside the repository and is built from `git archive`, so an untracked `.env.local` cannot reach the image. `apps/web` has no `output: standalone`, so it runs `next start`.

## Commands run

AWS CLI installed for the current user without sudo (`~/.local/aws-cli`): `aws-cli/2.39.5 Python/3.14.8 Linux/6.18.54.1-microsoft-standard-WSL2 exe/x86_64.ubuntu.24`. `shellcheck` was missing on the machine; version 0.11.0 ran from a temporary Python virtual environment outside the repository. `jq` is missing; `python3` did the JSON checks.

| Command | Result line |
| --- | --- |
| `bash -n infra/aws/*.sh` | `bash -n: ok (6 scripts)` |
| `shellcheck -x *.sh` (in `infra/aws`) | no errors, no warnings; `2 SC2016 (info)` |
| `envsubst` of both templates with `env.sh.example` values, then `python3 -m json.tool` | `api: valid JSON; unrendered placeholders: 0` / `web: valid JSON; unrendered placeholders: 0` |
| Rendered keys against `aws ecs create-express-gateway-service --generate-cli-skeleton` and the update skeleton | `api keys not in create skeleton: []`, `api keys not in update skeleton: []`, the same for web; no secret name in plain environment |
| Keys of the two standard-input payloads against the `rds create-db-instance` and `ssm put-parameter` skeletons | `rds keys unknown: []` / `ssm keys unknown: []` |
| Secret scan of scripts, templates and `env.sh.example` (AWS and Google key forms, JWTs, connection strings with a password, private keys, assigned passwords, 12-digit account IDs, `echo` of a secret variable, `set -x`) | no match (`grep` exit 1) |
| Offline run of all six scripts, twice, with a stand-in `aws` on `PATH` that logs its arguments and contacts nothing | see below |
| Temporary web Dockerfile, built with placeholder values | `build exit=0`; run with 512 MiB: `web / -> 200 in 0.089877s`, memory `45.22MiB / 512MiB`; the image was removed afterwards |
| `make lint` | `All checks passed!` / `All matched files use Prettier code style!` (exit 0) |
| `make check`, first run, during the web image build | `1 failed, 230 passed, 1 warning in 66.82s (0:01:06)` in `make test-api`: `test_the_job_timeout_fails_with_internal_and_says_timed_out` (see open issues). Exit 2 |
| `make test-api ARGS='-k test_the_job_timeout_fails -q'`, five times | `1 passed, 230 deselected, 1 warning` each time |
| `make check`, second run, nothing else running | `All checks passed!`; ESLint `✖ 1 problem (0 errors, 1 warning)` (the existing warning in `apps/web/lib/api/client.ts`); `Success: no issues found in 85 source files`; `Contracts: 4 kept, 0 broken.`; `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date`; unit `385 passed, 1 warning in 8.94s`; contract `35 passed, 1 warning in 0.85s`; api `231 passed, 1 warning in 61.99s (0:01:01)`; authz `28 passed in 14.97s`; web `Tests  80 passed (80)` (exit 0) |

SC2016 is kept twice in `06_services.sh`: both strings are meant literally (the `${}` characters given to `tr`, and the backticks of a JMESPath number in `--query`).

### Offline script run

No real AWS command ran. The stand-in showed:

- a script stops with exit 1 when `env.sh` is missing or holds a placeholder, and `04_ssm.sh` stops when there is no terminal;
- with a test password holding `/`, `@`, `%` and a space and a test key value, neither appears in any logged argument (`argv secret hits: 0`) or in script output;
- `DATABASE_URL` has the form `postgresql+psycopg://group12_owner:<password-encoded>@<endpoint>:5432/travel_staging?sslmode=require`;
- the second pass created nothing: `create-db-instance` 1, `put-parameter` 4, `create-express-gateway-service` 2, `update-express-gateway-service` 1, `authorize-security-group-ingress` 1, `create-budget` 1, `create-repository` 2, `create-role` 3 for both passes together;
- every policy and budget JSON argument parses, and the deploy role's trust holds exactly the three subjects with `aud` `sts.amazonaws.com`;
- the run found and fixed one defect: `AWS_SUBNET_IDS` ended in a comma.

This checks the scripts' own logic only. It says nothing about how AWS answers.

## Command check

Every `aws` command in the scripts and the guide, with its options, against the offline help of the installed CLI. Result: `TOTAL 43 commands, 0 with a problem`.

| Command | Options checked | CLI version |
| --- | --- | --- |
| `aws budgets create-budget` | `--account-id` `--budget` `--notifications-with-subscribers` | 2.39.5 |
| `aws budgets describe-budgets` | `--account-id` `--output` `--query` | 2.39.5 |
| `aws budgets describe-notifications-for-budget` | `--account-id` `--budget-name` `--output` `--query` | 2.39.5 |
| `aws ec2 authorize-security-group-ingress` | `--group-id` `--output` `--port` `--protocol` `--query` `--source-group` | 2.39.5 |
| `aws ec2 create-security-group` | `--description` `--group-name` `--output` `--query` `--vpc-id` | 2.39.5 |
| `aws ec2 describe-security-groups` | `--filters` `--group-ids` `--output` `--query` | 2.39.5 |
| `aws ec2 describe-vpcs` | `--filters` `--output` `--query` | 2.39.5 |
| `aws ecr create-repository` | `--image-scanning-configuration` `--output` `--query` `--repository-name` | 2.39.5 |
| `aws ecr delete-repository` | `--force` `--repository-name` | 2.39.5 |
| `aws ecr describe-images` | `--image-ids` `--output` `--query` `--repository-name` | 2.39.5 |
| `aws ecr describe-repositories` | `--output` `--query` `--repository-names` | 2.39.5 |
| `aws ecr get-login-password` | none | 2.39.5 |
| `aws ecr put-lifecycle-policy` | `--lifecycle-policy-text` `--output` `--query` `--repository-name` | 2.39.5 |
| `aws ecs create-express-gateway-service` | `--cli-input-json` `--output` `--query` | 2.39.5 |
| `aws ecs delete-express-gateway-service` | `--service-arn` | 2.39.5 |
| `aws ecs describe-express-gateway-service` | `--query` `--service-arn` | 2.39.5 |
| `aws ecs describe-services` | `--cluster` `--output` `--query` `--services` | 2.39.5 |
| `aws ecs describe-task-definition` | `--query` `--task-definition` | 2.39.5 |
| `aws ecs update-express-gateway-service` | `--cli-input-json` `--output` `--query` | 2.39.5 |
| `aws ecs wait services-stable` | `--cluster` `--services` | 2.39.5 |
| `aws iam attach-role-policy` | `--policy-arn` `--role-name` | 2.39.5 |
| `aws iam create-open-id-connect-provider` | `--client-id-list` `--output` `--query` `--url` | 2.39.5 |
| `aws iam create-role` | `--assume-role-policy-document` `--output` `--query` `--role-name` | 2.39.5 |
| `aws iam get-open-id-connect-provider` | `--open-id-connect-provider-arn` `--output` `--query` | 2.39.5 |
| `aws iam get-role` | `--output` `--query` `--role-name` | 2.39.5 |
| `aws iam put-role-policy` | `--policy-document` `--policy-name` `--role-name` | 2.39.5 |
| `aws iam update-assume-role-policy` | `--policy-document` `--role-name` | 2.39.5 |
| `aws kms describe-key` | `--key-id` `--output` `--query` | 2.39.5 |
| `aws logs create-log-group` | `--log-group-name` | 2.39.5 |
| `aws logs delete-log-group` | `--log-group-name` | 2.39.5 |
| `aws logs describe-log-groups` | `--log-group-name-prefix` `--output` `--query` | 2.39.5 |
| `aws logs put-retention-policy` | `--log-group-name` `--retention-in-days` | 2.39.5 |
| `aws rds create-db-instance` | `--cli-input-json` `--output` `--query` | 2.39.5 |
| `aws rds delete-db-instance` | `--db-instance-identifier` `--final-db-snapshot-identifier` | 2.39.5 |
| `aws rds describe-db-engine-versions` | `--engine` `--output` `--query` | 2.39.5 |
| `aws rds describe-db-instances` | `--db-instance-identifier` `--output` `--query` | 2.39.5 |
| `aws rds modify-db-instance` | `--apply-immediately` `--db-instance-identifier` `--no-deletion-protection` | 2.39.5 |
| `aws rds stop-db-instance` | `--db-instance-identifier` | 2.39.5 |
| `aws rds wait db-instance-available` | `--db-instance-identifier` | 2.39.5 |
| `aws ssm delete-parameters` | `--names` | 2.39.5 |
| `aws ssm describe-parameters` | `--output` `--parameter-filters` `--query` | 2.39.5 |
| `aws ssm put-parameter` | `--cli-input-json` `--output` `--query` | 2.39.5 |
| `aws sts get-caller-identity` | `--output` `--query` | 2.39.5 |

The IAM managed policy names, the trust principals (`ecs-tasks.amazonaws.com`, `ecs.amazonaws.com`) and the action names were read from the Amazon ECS developer guide and the Service Authorization Reference on 6 November 2026. The CLI cannot check them offline.

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| Staging API answers `GET /health` with 200 over HTTPS; the web URL serves the landing page (US-002 AC1, TC-288) | not verified | needs the live account; guide section 13 |
| RDS is not publicly accessible; the API connects with `sslmode=require` (TC-433) | not verified | needs the live account. `PubliclyAccessible` false and the URL suffix are shown offline only |
| Task definitions carry the secrets only as SSM references; no secret in the repository, an image or plain environment (TC-434, TC-354) | not verified | live half needs the account. Repository half holds: templates hold ARNs only, the secret scan found nothing |
| Budget alerts at USD 25 and USD 50 exist (NFR-049, TC-435) | not verified | needs the live account; guide section 3 |
| The deploy role's trust admits only main, `v*` tags and the `production` environment (TC-436) | not verified | needs the live account. The policy the script sends holds exactly the three subjects |
| First-request time recorded (NFR-005) | not verified | needs the live account; `deployment.md` section 7 |
| Every live criterion is verified from Kirtan's recorded output; until it exists it is reported as "not verified" | verified | this table |
| `bash -n infra/aws/*.sh` (card test) | verified | `bash -n: ok (6 scripts)` |
| `make smoke URL=<staging API URL>` (card test) | not verified | no staging URL yet |

## Blockers

Live steps pending, all Kirtan's after merge: run the guide, set the repository variables, record the output of section 13, fill in the cost table. The operator passes the results on (IMP-299).

- `GEMINI_API_KEY` and `ORS_API_KEY` must exist before `04_ssm.sh` finishes: `docs/decisions/accounts.md` does not yet record them (Nidhi, Junaid).
- IMP-218 is needed before `/health/ready` and `make smoke` can pass: the first image holds no migrations, and the database stays unmigrated until the first release task.

## Proposed decisions

- PD-IMP-217-1 (deploy role permissions): the Service Authorization Reference lists `ecs:AssociateGatewayWithCluster` and `ecs:CreateGateway` as dependent actions of `UpdateExpressGatewayService`, and `ecs:TagResource` of `RunTask` and `RegisterTaskDefinition` when tags are used. A1 §4.4 names none of them, so `05_iam.sh` grants exactly §4.4. Proposal: check on the first IMP-218 deploy, and add them to §4.4 only if AWS refuses the call.
- PD-IMP-217-2 (OD-06): the template is in HS256 mode (`SUPABASE_JWKS_URL` empty, `SUPABASE_JWT_SECRET` referenced), matching the four parameters of the run prompt, because OD-06 is undecided. The API prefers JWKS whenever that URL is set. If the hosted project uses asymmetric keys, a pull request changes the template (guide section 5), with no new repository variable.
- PD-IMP-217-3 (`RDS_INSTANCE_ID`): A1 §4.1 names only the security group `group12-rds`. The run prompt's `group12-rds` is used for the instance too.
- PD-IMP-217-4 (phases of `06_services.sh`): the card lists one script, but a hand-built image falls between the API and web services, so it takes `api` or `web`.

## Open issues

- **Timing-sensitive API test, outside this card.** `tests/api/test_generations.py::test_the_job_timeout_fails_with_internal_and_says_timed_out` failed once under CPU load with `sqlalchemy.exc.PendingRollbackError` from `app/generation/jobs.py` `_fail_internal`: the 0.05 s timeout cancelled a database call in flight, and the failure path reused the session. This branch changes no application or test code, so it was not touched. Whether the same can happen outside the test's shared savepoint connection is not checked. It needs an owner, because it can turn CI red at random and a job that fails this way may not record its failure.
- **Empty environment values** (`SUPABASE_JWKS_URL`, `GEMINI_MODEL_ID`, `AI_MAX_INPUT_TOKENS`, `AI_MAX_OUTPUT_TOKENS`, `SEED_DIRS`, and `ALLOWED_ORIGINS` and `FEATURES_DISABLED` while blank) are sent as `""`. The API treats them as unset, and the CLI reference states no minimum length, but whether Express Mode accepts them is not verified.
- `GEMINI_MODEL_ID` stays empty until IMP-316 switches staging to GEMINI (`AI_PROVIDER=MOCK` needs no model). `SEED_DIRS` stays empty until IMP-218 fixes the image paths.
- `ecs:CreateCluster` and the service-linked roles are created on the first service, under Kirtan's own credentials. The Free plan's limits on RDS and Express Mode are unknown (A1 §12); the guide stops on any refusal (IMD-104).
- `StorageEncrypted` is left at the API default because A1 §4.1 does not set it. Decide before production (IMP-801).
- `apps/api/Dockerfile` and the deploy workflows still mention Render; IMP-218 owns both.
- `docs/decisions/accounts.md` still lists Render and Vercel; it belongs to IMP-113.
