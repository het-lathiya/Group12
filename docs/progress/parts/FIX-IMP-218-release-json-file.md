# FIX-IMP-218 · release-json-file part

- Run id: RUN-065b (fix of RUN-065)
- Owner: Junaid
- Status: **implemented; offline checks pass. The live behaviour is not verified until the post-merge Deploy staging run**
- Base commit: `59f174e` (origin/main)
- Head commit: the single commit of this pull request (`fix(deploy): IMP-218 pass task definitions to the AWS CLI as files`). The ID changes on Rebase and merge.
- Traces to: IMP-218; TC-437, TC-438; A1 §4.3, §4.4, §4.5

## Failure

- Failed run: `42659831566`, Deploy staging on `main` at `59f174e`, step "Run the release task".
- The RUN-065 lookup worked: `service task definition: arn:aws:ecs:ap-south-1:609865800257:task-definition/default-group12-api-staging:2`.
- Then: `aws: [ERROR]: An error occurred (ParamValidation): Error parsing parameter 'cli-input-json': Invalid JSON received.` (exit 252).
- Cause: the step piped the jq output into `aws ecs register-task-definition --cli-input-json file:///dev/stdin`. AWS CLI v2 does not read `file:///dev/stdin` as JSON. The same error shows offline with a valid input (see below), so the JSON was not the problem.

## Every stdin-fed `--cli-input-json` (before this change)

There is no `--cli-input-yaml`. The helper is written inline by each workflow (`$RUNNER_TEMP/deploy-helpers.sh`, step "Write the deploy helpers"), so it has no separate file in the repository.

| # | File | Place | Call |
| --- | --- | --- | --- |
| 1 | `.github/workflows/deploy-staging.yml` | helper `update_service` (used by "Update the API service" and "Update the web service") | `aws ecs update-express-gateway-service --cli-input-json file:///dev/stdin` |
| 2 | `.github/workflows/deploy-staging.yml` | step "Run the release task" | `aws ecs register-task-definition --cli-input-json file:///dev/stdin` |
| 3 | `.github/workflows/deploy-production.yml` | helper `update_service` | the same as 1 |
| 4 | `.github/workflows/deploy-production.yml` | step "Run the release task" | the same as 2 |

`infra/aws/02_rds.sh`, `04_ssm.sh` and `06_services.sh` also contain `/dev/stdin`. They are out of scope (account-owner scripts, A1 §4) and were not changed.

## Changed files

- `.github/workflows/deploy-staging.yml` and `.github/workflows/deploy-production.yml`. The change is the same in both files; the two blocks were checked identical with `diff` before the change.
  - **`update_service`:** the rendered template goes to `$RUNNER_TEMP/update-<service name>.json`. Then `jq -e .` checks it (on failure: `::error::<file> is not valid JSON` and the function returns 1). Only `jq -c 'keys'` is printed. Then `aws ecs update-express-gateway-service --cli-input-json "file://<file>"`.
  - **Run the release task:** the allow-list output goes to `$RUNNER_TEMP/release-task-definition.json`. Then `jq -e .` checks it (on failure: `::error::<file> is not valid JSON` and `exit 1`). Only `jq -c 'keys'` is printed. Then `aws ecs register-task-definition --cli-input-json "file://<file>"`.
- `docs/progress/parts/FIX-IMP-218-release-json-file.md`: this record.

Unchanged on purpose: the jq allow-list, the `del(...) + {serviceArn}` filter, the family `group12-api-<env>-release`, the image replacement, the PRIMARY-deployment lookup and its guard, and `simulate_release_failure` (TC-438). No step prints a value from the task definition or the rendered service configuration, only top-level keys. The `$RUNNER_TEMP` files are deleted with the runner.

## Offline proof (no AWS request possible)

AWS CLI `aws-cli/2.39.5 Python/3.14.8`. Every call ran with `env -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN -u AWS_PROFILE AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null AWS_EC2_METADATA_DISABLED=true aws ... --region ap-south-1`. The fixtures were outside the repository and used account `000000000000`.

- The register-task-definition fixture is a `describe-task-definition`-shaped object:
  - `containerDefinitions` with name, image, port mapping, `environment`, `secrets` as SSM parameter ARNs and an `awslogs` `logConfiguration`;
  - the extra fields `taskDefinitionArn`, `revision`, `status`, `requiresAttributes`, `compatibilities`, `registeredAt`, `registeredBy`, and a null `pidMode`.
  - It was run through the workflow's exact allow-list filter.
- The update-express-gateway-service input was rendered from the real `infra/aws/services/{api,web}.staging.json.tmpl` with dummy values. In b) it was built by the helper extracted verbatim from each workflow and run under `bash -e -o pipefail`, as the step runs.

| Call | a) old form (`file:///dev/stdin`) | b) new form (`file://<file>`) |
| --- | --- | --- |
| register-task-definition | exit 252: `aws: [ERROR]: An error occurred (ParamValidation): Error parsing parameter 'cli-input-json': Invalid JSON received.` | keys `["containerDefinitions","cpu","enableFaultInjection","executionRoleArn","family","memory","networkMode","placementConstraints","requiresCompatibilities","runtimePlatform","taskRoleArn","volumes"]`; exit 253: `aws: [ERROR]: An error occurred (NoCredentials): Unable to locate credentials. You can configure credentials by running "aws login".` |
| update-express-gateway-service (api) | exit 252: `aws: [ERROR]: An error occurred (ParamValidation): Error parsing parameter 'cli-input-json': Invalid JSON received.` | staging and production helpers: keys `["cpu","cpuArchitecture","executionRoleArn","healthCheckPath","memory","primaryContainer","scalingTarget","serviceArn"]`; exit 253: `aws: [ERROR]: An error occurred (NoCredentials): Unable to locate credentials. ...` |
| update-express-gateway-service (web) | the same input path as api | staging and production helpers: the same keys; exit 253 `NoCredentials` |

The old form reproduces the CI failure. The new form gets past parameter parsing and stops only at the credentials error. Under `bash -e` the failed call ends the step before the rollout poll.

## Checks

| Command | Result |
| --- | --- |
| `actionlint .github/workflows/deploy-staging.yml .github/workflows/deploy-production.yml` | no output, exit 0 |
| `shellcheck -s bash` on "Write the deploy helpers" (whole step and the helper body) and "Run the release task", each workflow, extracted to temp files | exit 0 for all six; the only note is SC1091 (info) on `. "$RUNNER_TEMP/deploy-helpers.sh"` |
| `make lint` | `All checks passed!` (ruff), `✖ 1 problem (0 errors, 1 warning)` (ESLint, an existing web warning this part does not touch), `All matched files use Prettier code style!`; exit 0 |

## Acceptance

| Criterion | Status | How |
| --- | --- | --- |
| No `--cli-input-json` reads `file:///dev/stdin` in either deploy workflow | verified | `grep` finds `/dev/stdin` only in the explanatory comments |
| Each input is written under `$RUNNER_TEMP`, checked with `jq -e`, and only its keys are printed | verified | diff, and the offline b) output above |
| The new form passes AWS CLI parameter parsing | verified (offline) | the b) column |
| TC-437 / TC-438 deploy and release behaviour | not verified | live behaviour not verified until the post-merge Deploy staging run |

## Blockers, proposed decisions, open issues

- Blockers: none.
- Proposed decisions: none.
- Open issue: the `infra/aws/` scripts also use `/dev/stdin` with the AWS CLI. They are for the account owner to check; they were not changed here.
