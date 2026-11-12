#!/usr/bin/env bash
# ECS execution and infrastructure roles, GitHub OIDC provider and deploy role (A1 §4.1, §4.4; IMD-102).
# Run after 04_ssm.sh: the first SecureString creates the aws/ssm key that the execution role decrypts
# with. Policies and trust are written on every run, so a second run restores them.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$here/env.sh" ] || { echo "infra/aws/env.sh is missing: copy env.sh.example and fill it in" >&2; exit 1; }
if grep -vE '^[[:space:]]*(#|$)' "$here/env.sh" | grep -q '<'; then
  echo "infra/aws/env.sh still holds a <placeholder>" >&2
  exit 1
fi
# shellcheck source=env.sh.example
. "$here/env.sh"
if [ "$(aws sts get-caller-identity --query Account --output text)" != "$AWS_ACCOUNT_ID" ]; then
  echo "these credentials are not for account AWS_ACCOUNT_ID of env.sh" >&2
  exit 1
fi

region="$AWS_REGION"
account="$AWS_ACCOUNT_ID"
oidc_host=token.actions.githubusercontent.com
oidc_arn="arn:aws:iam::$account:oidc-provider/$oidc_host"
# GitHub also presents the immutable subject form owner@<owner id>/repo@<repository id> (IMD-138).
# The two IDs are public GitHub identifiers of het-lathiya and Group12, not secrets.
github_repo_ids="${GITHUB_REPO%%/*}@185104529/${GITHUB_REPO#*/}@1436091116"

ensure_role() { # role name, trust policy JSON
  if aws iam get-role --role-name "$1" --query Role.Arn --output text 2>/dev/null; then
    aws iam update-assume-role-policy --role-name "$1" --policy-document "$2"
  else
    aws iam create-role --role-name "$1" --assume-role-policy-document "$2" --query Role.Arn --output text
  fi
}

service_trust() { # service principal
  printf '{"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": {"Service": "%s"}, "Action": "sts:AssumeRole"}]}' "$1"
}

# Task execution role: ECR pull and logs from the managed policy, /group12/* parameters from the inline one.
ensure_role group12-ecs-execution "$(service_trust ecs-tasks.amazonaws.com)"
aws iam attach-role-policy --role-name group12-ecs-execution \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
ssm_key_arn="$(aws kms describe-key --key-id alias/aws/ssm --query KeyMetadata.Arn --output text)"
aws iam put-role-policy --role-name group12-ecs-execution --policy-name group12-read-parameters \
  --policy-document "$(cat <<JSON
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": "ssm:GetParameters", "Resource": "arn:aws:ssm:$region:$account:parameter/group12/*"},
    {"Effect": "Allow", "Action": "kms:Decrypt", "Resource": "$ssm_key_arn"}
  ]
}
JSON
)"

# Express Mode infrastructure role.
ensure_role group12-ecs-infrastructure "$(service_trust ecs.amazonaws.com)"
aws iam attach-role-policy --role-name group12-ecs-infrastructure \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSInfrastructureRoleforExpressGatewayServices

# GitHub OIDC provider.
if aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$oidc_arn" \
  --query Url --output text 2>/dev/null; then
  echo "OIDC provider $oidc_host exists"
else
  aws iam create-open-id-connect-provider --url "https://$oidc_host" --client-id-list sts.amazonaws.com \
    --query OpenIDConnectProviderArn --output text
fi

# Deploy role: exactly the six subjects of A1 §4.4 and IMD-138 (TC-436). Its policy adds to A1 §4.4 the dependent
# actions of UpdateExpressGatewayService (PD-IMP-217-1, IMP-218).
ensure_role group12-github-deploy "$(cat <<JSON
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Federated": "$oidc_arn"},
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {"$oidc_host:aud": "sts.amazonaws.com"},
      "StringLike": {"$oidc_host:sub": [
        "repo:$GITHUB_REPO:ref:refs/heads/main",
        "repo:$GITHUB_REPO:ref:refs/tags/v*",
        "repo:$GITHUB_REPO:environment:production",
        "repo:$github_repo_ids:ref:refs/heads/main",
        "repo:$github_repo_ids:ref:refs/tags/v*",
        "repo:$github_repo_ids:environment:production"
      ]}
    }
  }]
}
JSON
)"

aws iam put-role-policy --role-name group12-github-deploy --policy-name group12-deploy \
  --policy-document "$(cat <<JSON
{
  "Version": "2012-10-17",
  "Statement": [
    {"Sid": "EcrLogin", "Effect": "Allow", "Action": "ecr:GetAuthorizationToken", "Resource": "*"},
    {"Sid": "EcrPushPull", "Effect": "Allow",
     "Action": ["ecr:BatchCheckLayerAvailability", "ecr:BatchGetImage", "ecr:CompleteLayerUpload",
                "ecr:GetDownloadUrlForLayer", "ecr:InitiateLayerUpload", "ecr:PutImage", "ecr:UploadLayerPart"],
     "Resource": ["arn:aws:ecr:$region:$account:repository/$ECR_API_REPO",
                  "arn:aws:ecr:$region:$account:repository/$ECR_WEB_REPO"]},
    {"Sid": "EcsServices", "Effect": "Allow",
     "Action": ["ecs:DescribeExpressGatewayService", "ecs:UpdateExpressGatewayService", "ecs:DescribeServices"],
     "Resource": "arn:aws:ecs:$region:$account:service/$ECS_CLUSTER/group12-*"},
    {"Sid": "EcsExpressGateway", "Effect": "Allow",
     "Action": ["ecs:CreateGateway", "ecs:AssociateGatewayWithCluster", "ecs:TagResource"],
     "Resource": ["arn:aws:ecs:$region:$account:gateway/*",
                  "arn:aws:ecs:$region:$account:service/$ECS_CLUSTER/group12-*"]},
    {"Sid": "EcsTaskDefinitions", "Effect": "Allow",
     "Action": ["ecs:DescribeTaskDefinition", "ecs:RegisterTaskDefinition"], "Resource": "*"},
    {"Sid": "EcsReleaseTask", "Effect": "Allow", "Action": "ecs:RunTask",
     "Resource": "arn:aws:ecs:$region:$account:task-definition/group12-api-*-release:*"},
    {"Sid": "EcsReleaseTaskStatus", "Effect": "Allow", "Action": "ecs:DescribeTasks",
     "Resource": "arn:aws:ecs:$region:$account:task/$ECS_CLUSTER/*"},
    {"Sid": "PassEcsRoles", "Effect": "Allow", "Action": "iam:PassRole",
     "Resource": ["$ECS_EXECUTION_ROLE_ARN", "$ECS_INFRASTRUCTURE_ROLE_ARN"],
     "Condition": {"StringEquals": {"iam:PassedToService": ["ecs-tasks.amazonaws.com", "ecs.amazonaws.com"]}}},
    {"Sid": "ReadTaskLogs", "Effect": "Allow", "Action": "logs:GetLogEvents",
     "Resource": "arn:aws:logs:$region:$account:log-group:/ecs/group12-*:log-stream:*"}
  ]
}
JSON
)"

echo "AWS_DEPLOY_ROLE_ARN: arn:aws:iam::$account:role/group12-github-deploy"
