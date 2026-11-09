# FIX-IMP-218 · express-task-definition part

- Run id: RUN-065
- Owner: Junaid
- Status: **implemented; offline checks pass. The live behaviour is not verified until the post-merge Deploy staging run**
- Base commit: `16839a0` (origin/main)
- Head commit: the single commit of this pull request (`fix(deploy): IMP-218 read the Express Mode task definition from the primary deployment`). The ID changes on Rebase and merge.
- Traces to: IMP-218; TC-437, TC-438; A1 §4.3, §4.4, §4.5

## Failure

- Failed run: `42656014540`, step "Run the release task", Deploy staging.
- Error: `ClientException ... DescribeTaskDefinition ... Unable to describe task definition`.
- Cause: the step read `services[0].taskDefinition` from `describe-services`. An ECS Express Mode service leaves that field null, so `--output text` printed `None`, and the workflow passed that value to `describe-task-definition`.

## Facts from the account owner (Kirtan, recorded output of 9 Nov 2026)

- `aws ecs describe-services --cluster default --services group12-api-staging` returns:
  - `failures []` and status `ACTIVE`;
  - `services[0].taskDefinition = null`;
  - `deployments = [{status: "PRIMARY", taskDefinition: "arn:aws:ecs:ap-south-1:609865800257:task-definition/default-group12-api-staging:2"}]`.
- The Express Mode task definition families are `default-group12-api-staging` and `default-group12-web-staging`. `describe-task-definition` on `default-group12-api-staging:2` works (ACTIVE).
- Cluster: `arn:aws:ecs:ap-south-1:609865800257:cluster/default`.
- `describe-services` for an Express Mode service also has no `networkConfiguration`.

## Changed files

- `.github/workflows/deploy-staging.yml` and `.github/workflows/deploy-production.yml`, step "Run the release task". The same 11-line block was changed in both files, checked with `cmp`:
  - **Lookup.** The task definition now comes from `services[0].deployments[?status=='PRIMARY'].taskDefinition | [0]`.
  - **Guard.** If the lookup result is not an ARN (empty, `None`, or any other text), the step prints `::error::no PRIMARY deployment task definition for <service> in <cluster> (got '<value>')` and exits 1. This happens before `describe-task-definition`, `register-task-definition` or `run-task`.
  - **Release revision.** The jq delete-list is replaced by an allow-list of the fields that `register-task-definition` accepts. Null-valued keys are dropped. Then `.family` is set to `group12-api-<env>-release` and the image of `containerDefinitions[0]` is replaced, as before.
- `docs/guides/deployment.md`: a short Express Mode note. The task definition is only under the `PRIMARY` deployment, and the families are `default-group12-<service>-<env>`.
- `docs/progress/parts/FIX-IMP-218-express-task-definition.md`: this record.

Unchanged on purpose:
- The release task's network still comes from `AWS_SUBNET_IDS` and `API_TASKS_SECURITY_GROUP`.
- `simulate_release_failure` (TC-438) and its behaviour are as they were. The diff touches no line containing it.
- `infra/aws/**`, app code and other workflows are not touched.

## Allow-list source

The AWS CLI reference for `register-task-definition` (https://docs.aws.amazon.com/cli/latest/reference/ecs/register-task-definition.html, read 9 Nov 2026) lists 18 top-level request parameters:

- `family`, `taskRoleArn`, `executionRoleArn`, `networkMode`, `containerDefinitions`, `volumes`;
- `placementConstraints`, `requiresCompatibilities`, `cpu`, `memory`, `tags`, `pidMode`;
- `ipcMode`, `proxyConfiguration`, `inferenceAccelerators`, `ephemeralStorage`, `runtimePlatform`, `enableFaultInjection`.

The allow-list is the run prompt's 16 fields plus `enableFaultInjection`:
- `enableFaultInjection` is accepted by the API and returned by `describe-task-definition`, so the release revision keeps the service's setting.
- `tags` is left out because it is never part of the `taskDefinition` object that `describe-task-definition` returns.

## Later steps checked for fields Express Mode leaves empty

| Read | Source | Result |
| --- | --- | --- |
| Container name, log group, stream prefix | The task definition (`containerDefinitions[0]`), which works per Kirtan's facts | Unchanged. A missing log configuration only gives the existing warning; the task's exit code still decides. |
| Release task exit code and stopped reason | `describe-tasks` (task level, not service level) | Unchanged |
| `update_service` (API and web) | `update-express-gateway-service`, then `describe-express-gateway-service` `service.activeConfigurations[].primaryContainer.image` | These are Express Mode APIs, so unchanged |
| `aws ecs wait services-stable` | `describe-services` deployments and running/desired counts | Unchanged. It does not read `taskDefinition` or `networkConfiguration`, and Kirtan's output shows `deployments` filled in. |

## Offline checks (no AWS)

The fixtures were built from Kirtan's facts in a temp directory outside the repository:
- `services.json`: `taskDefinition: null` and a PRIMARY deployment with the `:2` ARN;
- `services-empty.json`: `deployments: []`;
- `services-active-only.json`: only an ACTIVE deployment;
- `taskdef.json`: has `taskDefinitionArn`, `revision`, `status`, `requiresAttributes`, `compatibilities`, `registeredAt`, `registeredBy`, an unknown `unknownExpressField`, and `pidMode: null`.

The query was run with the `jmespath` library (1.1.0), which the AWS CLI uses, applying the CLI's text output rule (null prints `None`). The jq program was taken verbatim from `deploy-staging.yml`.

| Command | Result |
| --- | --- |
| `actionlint .github/workflows/deploy-staging.yml .github/workflows/deploy-production.yml` (1.7.12, with shellcheck on PATH) | `actionlint exit 0` |
| `shellcheck -s bash release-staging.sh` (0.11.0, the extracted "Run the release task" block) | only `SC1091 (info): Not following: ./deploy-helpers.sh`, because the helper is written at run time |
| `shellcheck -s bash -e SC1091 release-staging.sh` / `release-production.sh` | `exit 0` / `exit 0` |
| Lookup on `services.json` | `arn:aws:ecs:ap-south-1:609865800257:task-definition/default-group12-api-staging:2 -> guard passes` |
| Lookup on `services-empty.json` | `'None' -> guard: ::error:: exit 1` |
| Lookup on `services-active-only.json` | `'None' -> guard: ::error:: exit 1` |
| Old query `services[0].taskDefinition` on `services.json` | `'None'` (reproduces the failure) |
| jq allow-list on `taskdef.json`, keys | `["containerDefinitions","cpu","enableFaultInjection","executionRoleArn","family","memory","networkMode","placementConstraints","requiresCompatibilities","runtimePlatform","taskRoleArn","volumes"]` |
| `jq -e` assertions: only accepted keys, family `group12-api-staging-release`, new image, no null values, `pidMode` dropped, `enableFaultInjection` kept | `allow-list assertions: PASS` |
| Downstream reads on `taskdef.json` | `container=Main log_group=/aws/ecs/default/group12-api-staging log_prefix=ecs` |
| `cmp` of the changed block, staging against production | `changed block identical in both workflows (11 lines)` |
| `make lint` | `All checks passed!` (ruff); ESLint `✖ 1 problem (0 errors, 1 warning)`, an existing warning in web code outside this part; `All matched files use Prettier code style!` |

## Acceptance

| Criterion | Status | How |
| --- | --- | --- |
| The task definition is read from the PRIMARY deployment in both workflows | verified | Fixture lookup returns the `:2` ARN; `cmp` shows the same block in both files |
| An empty or `None` lookup stops the run with `::error::` before any later AWS call | verified | The empty and ACTIVE-only fixtures give `None`, and the guard exits 1. The guard comes before `describe-task-definition` in the step. |
| The release revision keeps only accepted fields, with the new family and image | verified | `jq -e` assertions pass |
| TC-438 `simulate_release_failure` unchanged | verified | The diff has no line containing `simulate` |
| Live release task and deploy on staging (TC-437, TC-438) | **not verified until the post-merge Deploy staging run** | The OIDC trust admits only `main`, so the fix cannot run on this branch |

## Blockers

None.

## Proposed decisions

None.

## Open issues

- After merge, Kirtan checks that Deploy staging passes "Run the release task" with `service task definition: ...default-group12-api-staging:2` (or a later revision) in its log. Then he can rerun TC-438 with `simulate_release_failure`.
