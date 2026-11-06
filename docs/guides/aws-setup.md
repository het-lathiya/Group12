# AWS staging set-up (IMP-217)

- **Card:** IMP-217 · AWS staging foundation (US-002, US-004, US-163; FR-123; NFR-005, NFR-013, NFR-015, NFR-035, NFR-049)
- **For:** Kirtan, the owner of the AWS account. Nobody else runs these steps or holds these credentials.
- **Design:** [Amendment A1 §4](../spec/AMENDMENT_A1_AWS_RAG.md); decisions IMD-99 to IMD-104.
- **Scripts:** [infra/aws/](../../infra/aws/README.md).

Run every command from the repository root on an up-to-date `main`, in your own terminal or AWS CloudShell. Docker is needed for steps 7 and 9, and CloudShell may not have enough disk for the web build, so use your own terminal for those.

**If the Free plan refuses anything, stop.** Do not lower a setting or work around the refusal. Copy the error, without any value, and ask for a team decision: upgrade to the Paid plan (credits still apply) or change the design (IMD-104). Which services the Free plan blocks is not known in advance (A1 §12); RDS backup retention and ECS Express Mode are the first places to watch.

## 1. Account checks

Do these in the AWS console before anything else, and record each answer.

| Check | Expected |
| --- | --- |
| Account plan (Billing and Cost Management) | Free plan, with the credits shown |
| MFA on the root user (IAM, Security recommendations) | On |
| AWS Organizations | **Not enabled** |
| Control Tower, IAM Identity Center | **Not enabled** |
| Your CLI user | Not the root user, with permission to create the resources below |

Never enable AWS Organizations, Control Tower or IAM Identity Center: that converts the account to the Paid plan.

Then confirm the tools. `envsubst` comes with the `gettext` package.

```sh
aws --version          # AWS CLI v2, with the Express Mode commands (checked with 2.39.5)
python3 --version
envsubst --version
aws sts get-caller-identity --query Account --output text
```

## 2. Fill in env.sh

```sh
cp infra/aws/env.sh.example infra/aws/env.sh
```

Replace every `<placeholder>`. The file is untracked and holds no secret. Leave the blank values at the end alone: you set the two image tags in steps 7 and 9, and `06_services.sh` records the rest.

Then add the JWKS URL, which the API template needs. `06_services.sh` stops with `needs SUPABASE_JWKS_URL` without it.

```sh
echo 'export SUPABASE_JWKS_URL="$STAGING_SUPABASE_URL/auth/v1/.well-known/jwks.json"' >> infra/aws/env.sh
```

## 3. Budget

```sh
infra/aws/01_budget.sh
```

**Record for TC-435 (NFR-049):**

```sh
. infra/aws/env.sh
aws budgets describe-notifications-for-budget --account-id "$AWS_ACCOUNT_ID" --budget-name "$BUDGET_NAME" \
  --query 'Notifications[].[Threshold,ThresholdType,NotificationType]' --output table
```

It must show 25 and 50 as `ABSOLUTE_VALUE`. Add a screenshot of the budget page with the e-mail address hidden.

## 4. Database

Choose the master password first and keep it in the team password manager. RDS refuses `/`, `@`, `"` and spaces in it.

```sh
infra/aws/02_rds.sh
```

The script asks for the password twice at a hidden prompt, then waits until the instance is available, which takes several minutes. The instance has no inbound rule yet; step 8 adds it.

## 5. Registry and parameters

```sh
infra/aws/03_ecr.sh
infra/aws/04_ssm.sh
```

`04_ssm.sh` asks at hidden prompts for the RDS master password, `GEMINI_API_KEY` and `ORS_API_KEY`. It builds `DATABASE_URL` itself, in the form `postgresql+psycopg://<user>:<password>@<rds-endpoint>:5432/travel_staging?sslmode=require`, with the password percent-encoded. Get the Gemini key from Nidhi and the OpenRouteService key from Junaid through the password manager. An empty value stops the script, and all three parameters must exist before step 8: a task cannot start with a missing parameter.

To replace values later, run `infra/aws/04_ssm.sh --overwrite`, then redeploy, because tasks read parameters when they start.

**Token mode.** The hosted project uses JWT Signing Keys, so the API verifies tokens through `SUPABASE_JWKS_URL` (JWKS mode, IMP-218). **Do not create `/group12/staging/SUPABASE_JWT_SECRET`:** the legacy HS256 secret is being revoked and is not used anywhere. `04_ssm.sh` asks for it only if the template references it, and the template does not.

## 6. Roles

```sh
infra/aws/05_iam.sh
```

Run it after `04_ssm.sh`: the first SecureString creates the `aws/ssm` key that the execution role is allowed to use.

The deploy role's actions, each checked against the AWS CLI reference and the Service Authorization Reference on 6 November 2026:

| Purpose | Actions | Resource |
| --- | --- | --- |
| Registry login | `ecr:GetAuthorizationToken` | `*` (the action has no resource level) |
| Push and pull | `ecr:BatchCheckLayerAvailability`, `ecr:BatchGetImage`, `ecr:CompleteLayerUpload`, `ecr:GetDownloadUrlForLayer`, `ecr:InitiateLayerUpload`, `ecr:PutImage`, `ecr:UploadLayerPart` | The two repositories |
| Services | `ecs:DescribeExpressGatewayService`, `ecs:UpdateExpressGatewayService`, `ecs:DescribeServices` | `service/default/group12-*` |
| Express Mode gateway | `ecs:CreateGateway`, `ecs:AssociateGatewayWithCluster`, `ecs:TagResource` | `gateway/*` and `service/default/group12-*` |
| Task definitions | `ecs:DescribeTaskDefinition`, `ecs:RegisterTaskDefinition` | `*` |
| Release task | `ecs:RunTask` | `task-definition/group12-api-*-release:*` |
| Release task status | `ecs:DescribeTasks` | `task/default/*` |
| Passing the ECS roles | `iam:PassRole`, to `ecs-tasks.amazonaws.com` and `ecs.amazonaws.com` only | The two ECS roles |
| Log output | `logs:GetLogEvents` | `/ecs/group12-*` log groups |

These are the permissions of A1 §4.4, plus the Express Mode gateway row: AWS lists those actions as dependent actions of `UpdateExpressGatewayService` (PD-IMP-217-1, IMP-218). If a deploy stops with an access error on any other action, report it for a decision; do not widen the role by hand.

**Record for TC-436:**

```sh
aws iam get-role --role-name group12-github-deploy --query Role.AssumeRolePolicyDocument
```

The output must show `aud` equal to `sts.amazonaws.com` and exactly these three subjects: `repo:het-lathiya/Group12:ref:refs/heads/main`, `repo:het-lathiya/Group12:ref:refs/tags/v*` and `repo:het-lathiya/Group12:environment:production`.

## 7. First API image, by hand

The deploy workflow automates this after the set-up. The first image is built by hand from the repository root, and `/health` then reports that tag as its version.

```sh
. infra/aws/env.sh
registry="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
tag="$(git rev-parse --short origin/main)"
aws ecr get-login-password | docker login --username AWS --password-stdin "$registry"
docker build --platform linux/amd64 -f apps/api/Dockerfile --build-arg BUILD_VERSION="$tag" \
  -t "$registry/$ECR_API_REPO:$tag" .
docker push "$registry/$ECR_API_REPO:$tag"
echo "$tag"
```

Set `API_IMAGE_TAG` in `infra/aws/env.sh` to that tag.

## 8. API service

```sh
infra/aws/06_services.sh api
```

The script creates the log group with 7-day retention and the service, waits until it is stable, records `API_TASKS_SECURITY_GROUP`, `AWS_SUBNET_IDS`, `STAGING_API_SERVICE_ARN` and `STAGING_API_URL` in `env.sh`, and allows the group on `group12-rds` TCP 5432.

- If it stops with an assume-role error right after step 6, wait a minute and run it again: IAM changes take a moment to spread.
- If the wait times out, run it again. The first service also creates the cluster, the load balancer and the certificate.
- `ALLOWED_ORIGINS` is empty until step 10, and the API then allows only its local default.
- The template sends some empty environment values (for example `SEED_DIRS`). The API treats them as unset. If AWS refuses an empty value, stop and report it: the fix is a pull request to the template.

Check the API (TC-288). `/health/ready` reports the database as down or behind until the first release task of IMP-218 migrates it; that is expected.

```sh
. infra/aws/env.sh
curl -sS -o /dev/null -w '%{http_code}\n' "$STAGING_API_URL/health"
```

## 9. First web image, by hand

The web image needs the API URL at build time. `apps/web/.dockerignore` keeps env files out of the build context.

```sh
. infra/aws/env.sh
registry="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
tag="$(git rev-parse --short origin/main)"
docker build --platform linux/amd64 \
  --build-arg NEXT_PUBLIC_SUPABASE_URL="$STAGING_SUPABASE_URL" \
  --build-arg NEXT_PUBLIC_SUPABASE_ANON_KEY="$STAGING_SUPABASE_ANON_KEY" \
  --build-arg NEXT_PUBLIC_API_BASE_URL="$STAGING_API_URL/api/v1" \
  --build-arg NEXT_PUBLIC_FEATURES_DISABLED="$STAGING_FEATURES_DISABLED" \
  --build-arg BUILD_VERSION="$tag" \
  -t "$registry/$ECR_WEB_REPO:$tag" apps/web
docker push "$registry/$ECR_WEB_REPO:$tag"
echo "$tag"
```

Set `WEB_IMAGE_TAG` in `infra/aws/env.sh` to that tag.

## 10. Web service and allowed origin

```sh
infra/aws/06_services.sh web
```

The script creates the web service, records `STAGING_WEB_SERVICE_ARN` and `STAGING_WEB_ORIGIN`, then updates the API service with its full rendered configuration so that `ALLOWED_ORIGINS` is the web URL.

## 11. Supabase Auth

In the auth-only Supabase project, under Authentication, URL Configuration:

- Site URL: the value of `STAGING_WEB_ORIGIN`.
- Redirect URLs: add `<STAGING_WEB_ORIGIN>/auth/callback`.

## 12. Repository variables

Set these as **Actions variables, not secrets**, in `het-lathiya/Group12`. None of them is a secret, and all the values are in `env.sh` or printed by the scripts. Setting them needs admin rights on the repository; ask het-lathiya if you do not have them.

| Variable | Value |
| --- | --- |
| `AWS_REGION` | `ap-south-1` |
| `AWS_ACCOUNT_ID` | `AWS_ACCOUNT_ID` of `env.sh` |
| `AWS_DEPLOY_ROLE_ARN` | Last line printed by `05_iam.sh` |
| `ECR_API_REPO`, `ECR_WEB_REPO` | `group12-api`, `group12-web` |
| `ECS_EXECUTION_ROLE_ARN`, `ECS_INFRASTRUCTURE_ROLE_ARN` | From `env.sh` |
| `AWS_SUBNET_IDS`, `API_TASKS_SECURITY_GROUP` | From `env.sh`, recorded by `06_services.sh api` |
| `STAGING_API_SERVICE_ARN`, `STAGING_API_URL` | From `env.sh` |
| `STAGING_WEB_SERVICE_ARN`, `STAGING_WEB_ORIGIN` | From `env.sh` |
| `STAGING_SUPABASE_URL`, `STAGING_SUPABASE_ANON_KEY` | From `env.sh` |
| `STAGING_FEATURES_DISABLED` | From `env.sh`; may be empty |

The seven `PRODUCTION_*` equivalents are set in IMP-801. For example:

```sh
. infra/aws/env.sh
for name in AWS_REGION AWS_ACCOUNT_ID ECR_API_REPO ECR_WEB_REPO ECS_EXECUTION_ROLE_ARN ECS_INFRASTRUCTURE_ROLE_ARN \
  AWS_SUBNET_IDS API_TASKS_SECURITY_GROUP STAGING_API_SERVICE_ARN STAGING_API_URL STAGING_WEB_SERVICE_ARN \
  STAGING_WEB_ORIGIN STAGING_SUPABASE_URL STAGING_SUPABASE_ANON_KEY; do
  gh variable set "$name" --repo "$GITHUB_REPO" --body "${!name}"
done
gh variable set AWS_DEPLOY_ROLE_ARN --repo "$GITHUB_REPO" --body "arn:aws:iam::$AWS_ACCOUNT_ID:role/group12-github-deploy"
gh variable set STAGING_FEATURES_DISABLED --repo "$GITHUB_REPO" --body "$STAGING_FEATURES_DISABLED"
```

## 13. Verify and record

Record the output in a comment on the IMP-217 pull request or send it to the operator, for IMP-299. Hide account-specific values you would not paste in public, and **never paste a secret value**.

**TC-288, US-002:**

```sh
. infra/aws/env.sh
curl -sS "$STAGING_API_URL/health"
curl -sS -o /dev/null -w '%{http_code}\n' "$STAGING_WEB_ORIGIN/"
make smoke URL="$STAGING_API_URL" ARGS="--web-origin $STAGING_WEB_ORIGIN"
```

`make smoke` also checks `/health/ready`, so it passes fully only after the first release task (IMP-218).

**TC-433, RDS is private.** Run this from outside the VPC. `nc` must time out, and the first command must print `False`.

```sh
aws rds describe-db-instances --db-instance-identifier "$RDS_INSTANCE_ID" \
  --query 'DBInstances[0].[PubliclyAccessible,DeletionProtection,BackupRetentionPeriod,EngineVersion,DBInstanceClass]' --output text
endpoint="$(aws rds describe-db-instances --db-instance-identifier "$RDS_INSTANCE_ID" --query 'DBInstances[0].Endpoint.Address' --output text)"
nc -vz -w 5 "$endpoint" 5432
```

That the API connects with `sslmode=require` is shown by `GET /health/ready` reporting `database: ok` after the first release task.

**TC-434, TC-354, secrets only as references.** This prints variable names and ARNs, never a value.

```sh
td="$(aws ecs describe-services --cluster "$ECS_CLUSTER" --services "$API_SERVICE" --query 'services[0].taskDefinition' --output text)"
aws ecs describe-task-definition --task-definition "$td" \
  --query 'taskDefinition.containerDefinitions[0].{plain:environment[].name,secrets:secrets}'
```

`DATABASE_URL`, `GEMINI_API_KEY` and `ORS_API_KEY` must appear under `secrets` only, and `SUPABASE_JWT_SECRET` must not appear at all.

**NFR-005, first-request time after a deploy.** Express Mode keeps one task running, so there is no sleep (A1 §9.2). Fill in the table in section 7 of [deployment.md](deployment.md).

```sh
curl -s -o /dev/null -w '%{time_total}\n' "$STAGING_API_URL/health"
```

**Log retention:**

```sh
aws logs describe-log-groups --log-group-name-prefix /ecs/group12- --query 'logGroups[].[logGroupName,retentionInDays]' --output text
```

## 14. Cost estimate

**Estimate, to be filled in by Kirtan** from the [AWS Pricing Calculator](https://calculator.aws/) for ap-south-1 at set-up, with the date. These are the billable resources of A1 §4.7. Credits may cover them, and the budget alerts still count the usage.

| Resource | Size | Estimated USD per month |
| --- | --- | --- |
| Fargate, API task | 0.25 vCPU, 512 MiB, one task all month | TO BE FILLED BY KIRTAN |
| Fargate, web task | 0.25 vCPU, 512 MiB, one task all month | TO BE FILLED BY KIRTAN |
| Application Load Balancer | One, shared by both services | TO BE FILLED BY KIRTAN |
| RDS instance | `db.t4g.micro`, single-AZ | TO BE FILLED BY KIRTAN |
| RDS storage and backup | 20 GB gp3, 1 day of backups | TO BE FILLED BY KIRTAN |
| Public IPv4 addresses | One per task and per load balancer node | TO BE FILLED BY KIRTAN |
| ECR storage | Up to 10 images per repository | TO BE FILLED BY KIRTAN |
| CloudWatch Logs | 7 days of retention | TO BE FILLED BY KIRTAN |
| SSM Parameter Store | Four standard parameters | TO BE FILLED BY KIRTAN |
| **Total** | Date of the estimate: TO BE FILLED BY KIRTAN | TO BE FILLED BY KIRTAN |

There is no NAT gateway and no second load balancer. Do not add either.

## 15. Stop or tear down

Spending continues until these are done. Record any teardown decision (IMD-104).

**Pause the database.** RDS starts a stopped instance again after 7 days.

```sh
aws rds stop-db-instance --db-instance-identifier "$RDS_INSTANCE_ID"
```

**Delete the services.** Express Mode then removes the load balancer once no service uses it. Scaling to zero is not reliable here, because the services have a minimum of one task.

```sh
. infra/aws/env.sh
aws ecs delete-express-gateway-service --service-arn "$STAGING_WEB_SERVICE_ARN"
aws ecs delete-express-gateway-service --service-arn "$STAGING_API_SERVICE_ARN"
```

**Snapshot and delete the database.** Remove the inbound rule from `group12-rds` afterwards if the group stays.

```sh
aws rds modify-db-instance --db-instance-identifier "$RDS_INSTANCE_ID" --no-deletion-protection --apply-immediately
aws rds delete-db-instance --db-instance-identifier "$RDS_INSTANCE_ID" \
  --final-db-snapshot-identifier "group12-rds-final-$(date +%Y%m%d)"
```

**Remove the rest**, once nothing needs them:

```sh
aws ssm delete-parameters --names /group12/staging/DATABASE_URL /group12/staging/GEMINI_API_KEY \
  /group12/staging/ORS_API_KEY
aws ecr delete-repository --repository-name "$ECR_API_REPO" --force
aws ecr delete-repository --repository-name "$ECR_WEB_REPO" --force
aws logs delete-log-group --log-group-name "$API_LOG_GROUP"
aws logs delete-log-group --log-group-name "$WEB_LOG_GROUP"
```

The IAM roles and the budget cost nothing and can stay. Snapshots are billed until you delete them.
