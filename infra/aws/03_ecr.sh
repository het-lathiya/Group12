#!/usr/bin/env bash
# ECR repositories with scan on push, keeping the newest 10 images (A1 §4.1).
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

lifecycle='{"rules": [{"rulePriority": 1, "description": "Keep the newest 10 images", "selection": {"tagStatus": "any", "countType": "imageCountMoreThan", "countNumber": 10}, "action": {"type": "expire"}}]}'

for repo in "$ECR_API_REPO" "$ECR_WEB_REPO"; do
  if aws ecr describe-repositories --repository-names "$repo" \
    --query 'repositories[0].repositoryArn' --output text 2>/dev/null; then
    echo "repository $repo exists"
  else
    aws ecr create-repository --repository-name "$repo" \
      --image-scanning-configuration scanOnPush=true \
      --query 'repository.repositoryArn' --output text
  fi
  aws ecr put-lifecycle-policy --repository-name "$repo" --lifecycle-policy-text "$lifecycle" \
    --query repositoryName --output text
done
