# AWS set-up scripts (IMP-217)

Idempotent AWS CLI v2 scripts for the staging foundation of Amendment A1 §4. **Only the owner of the AWS account (Kirtan) runs them,** from his own terminal or AWS CloudShell. Follow [docs/guides/aws-setup.md](../../docs/guides/aws-setup.md), which gives the order, the manual steps between the scripts, and the output to record.

| File | Creates |
| --- | --- |
| `env.sh.example` | Template of the untracked `env.sh`: account ID, names and non-secret values |
| `01_budget.sh` | Monthly budget of USD 50 with alerts at USD 25 and USD 50 |
| `02_rds.sh` | Security group `group12-rds` and the private RDS PostgreSQL 16 instance `group12-rds` with database `travel_staging` |
| `03_ecr.sh` | Repositories `group12-api` and `group12-web`, scan on push, newest 10 images kept |
| `04_ssm.sh` | The four SecureString parameters `/group12/staging/<NAME>`; `--overwrite` replaces them |
| `05_iam.sh` | Roles `group12-ecs-execution`, `group12-ecs-infrastructure` and `group12-github-deploy`, and the GitHub OIDC provider |
| `06_services.sh api` | Service `group12-api-staging`; records its security group, subnets and URL in `env.sh`; allows the group on `group12-rds` |
| `06_services.sh web` | Service `group12-web-staging`; records its URL; updates the API's `ALLOWED_ORIGINS` |
| `services/*.json.tmpl` | The full service configuration, used by the scripts and by the deploy workflows of IMP-218 |

## Rules

- `env.sh` is untracked and holds names only. A script stops if it is missing, if it still holds a `<placeholder>`, or if the credentials belong to another account.
- Secret values are typed at a hidden prompt and reach the AWS CLI on standard input. They are never an argument, a file or output, and no script prints one.
- Every script checks before it creates, so it can be run again. Scripts print names, ARNs and URLs only.
- A change of a non-secret service setting is a reviewed pull request that edits a template (A1 §4.3). Templates hold SSM parameter ARNs, never a secret value, and the image is always `${IMAGE}`.
- Template placeholders are `IMAGE` and repository variables of A1 §4.4 only, so the deploy workflows can render them without new variables.
