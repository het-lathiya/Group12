#!/usr/bin/env bash
# Express Mode services (A1 §4.1, §4.3; card IMP-217 step 6). Two phases, because the web image is
# built with the API URL:
#   06_services.sh api   needs API_IMAGE_TAG: creates the API service, records its security group,
#                        subnets and URL in env.sh, and allows that group on the RDS group.
#   06_services.sh web   needs WEB_IMAGE_TAG: creates the web service, records its URL, and updates
#                        the API service so that ALLOWED_ORIGINS is the web URL.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$here/env.sh" ] || { echo "infra/aws/env.sh is missing: copy env.sh.example and fill it in" >&2; exit 1; }
if grep -vE '^[[:space:]]*(#|$)' "$here/env.sh" | grep -q '<'; then
  echo "infra/aws/env.sh still holds a <placeholder>" >&2
  exit 1
fi
# shellcheck source=env.sh.example
. "$here/env.sh"
export STAGING_GEMINI_FALLBACK_MODEL_ID="${STAGING_GEMINI_FALLBACK_MODEL_ID:-}" # optional (IMD-222): an older env.sh lacks it
if [ "$(aws sts get-caller-identity --query Account --output text)" != "$AWS_ACCOUNT_ID" ]; then
  echo "these credentials are not for account AWS_ACCOUNT_ID of env.sh" >&2
  exit 1
fi

command -v envsubst >/dev/null || { echo "envsubst is missing (package gettext)" >&2; exit 1; }

registry="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
api_template="$here/services/api.staging.json.tmpl"
web_template="$here/services/web.staging.json.tmpl"

set_env() { # name, value: records a non-secret value in env.sh and in this shell
  grep -q "^export $1=" "$here/env.sh" || { echo "env.sh has no line for $1" >&2; exit 1; }
  sed -i "s|^export $1=.*|export $1=$2|" "$here/env.sh"
  export "$1=$2"
  echo "$1=$2"
}

render() { # template: stops on a placeholder without a variable, because envsubst would blank it
  local name
  for name in $(grep -oE '\$\{[A-Z0-9_]+\}' "$1" | tr -d '${}' | sort -u); do
    [ -n "${!name+set}" ] || { echo "$1 needs $name" >&2; exit 1; }
  done
  envsubst < "$1"
}

require_image() { # repository, tag
  [ -n "$2" ] || { echo "set the image tag of $1 in env.sh after pushing the image" >&2; exit 1; }
  aws ecr describe-images --repository-name "$1" --image-ids "imageTag=$2" \
    --query 'imageDetails[0].imageTags[0]' --output text >/dev/null
}

ensure_log_group() { # the template names this group, so its retention is set before the first task
  if [ -z "$(aws logs describe-log-groups --log-group-name-prefix "$1" \
    --query "logGroups[?logGroupName=='$1'].logGroupName" --output text)" ]; then
    aws logs create-log-group --log-group-name "$1"
  fi
  aws logs put-retention-policy --log-group-name "$1" --retention-in-days 7
  echo "log group $1: retention 7 days"
}

service_arn() { # the cluster does not exist before the first service, so an error means no service
  aws ecs describe-services --cluster "$ECS_CLUSTER" --services "$1" \
    --query "services[?status=='ACTIVE'].serviceArn | [0]" --output text 2>/dev/null || true
}

ensure_service() { # service name, template; prints the ARN
  local arn
  arn="$(service_arn "$1")"
  if [ -z "$arn" ] || [ "$arn" = "None" ]; then
    arn="$(render "$2" | aws ecs create-express-gateway-service --cli-input-json file:///dev/stdin \
      --query service.serviceArn --output text)"
  fi
  echo "$arn"
}

service_url() { # service ARN
  local endpoint
  endpoint="$(aws ecs describe-express-gateway-service --service-arn "$1" \
    --query "service.activeConfigurations[0].ingressPaths[?accessType=='PUBLIC'].endpoint | [0]" --output text)"
  [ -n "$endpoint" ] && [ "$endpoint" != "None" ] || { echo "$1 has no public URL yet" >&2; exit 1; }
  endpoint="${endpoint#https://}"
  echo "https://${endpoint%/}"
}

api_phase() {
  require_image "$ECR_API_REPO" "$API_IMAGE_TAG"
  ensure_log_group "$API_LOG_GROUP"
  export IMAGE="$registry/$ECR_API_REPO:$API_IMAGE_TAG"
  local arn
  arn="$(ensure_service "$API_SERVICE" "$api_template")"
  set_env STAGING_API_SERVICE_ARN "$arn"
  echo "waiting for $API_SERVICE to become stable"
  aws ecs wait services-stable --cluster "$ECS_CLUSTER" --services "$API_SERVICE"

  local network groups subnets rds_group
  # Express Mode leaves services[0].networkConfiguration (and taskDefinition) null; the PRIMARY
  # deployment holds them, as in the deploy workflows' fix (FIX-IMP-218, A1 §4.5).
  network="services[0].deployments[?status=='PRIMARY'].networkConfiguration.awsvpcConfiguration | [0]"
  groups="$(aws ecs describe-services --cluster "$ECS_CLUSTER" --services "$API_SERVICE" \
    --query "$network.securityGroups" --output text)"
  subnets="$(aws ecs describe-services --cluster "$ECS_CLUSTER" --services "$API_SERVICE" \
    --query "$network.subnets" --output text)"
  case "$subnets" in
    "" | None) echo "no PRIMARY deployment network configuration on $API_SERVICE" >&2; exit 1 ;;
  esac
  case "$groups" in
    sg-*[[:space:]]* | "" | None) echo "expected one security group on $API_SERVICE, found: $groups" >&2; exit 1 ;;
  esac
  set_env API_TASKS_SECURITY_GROUP "$groups"
  set_env AWS_SUBNET_IDS "${subnets//$'\t'/,}"

  rds_group="$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$RDS_SECURITY_GROUP" \
    --query 'SecurityGroups[0].GroupId' --output text)"
  if aws ec2 describe-security-groups --group-ids "$rds_group" \
    --query 'SecurityGroups[0].IpPermissions[?FromPort==`5432`].UserIdGroupPairs[].GroupId' --output text \
    | grep -qw "$groups"; then
    echo "$RDS_SECURITY_GROUP already allows $groups on TCP 5432"
  else
    aws ec2 authorize-security-group-ingress --group-id "$rds_group" --protocol tcp --port 5432 \
      --source-group "$groups" --query 'SecurityGroupRules[0].SecurityGroupRuleId' --output text
    echo "$RDS_SECURITY_GROUP allows $groups on TCP 5432"
  fi

  set_env STAGING_API_URL "$(service_url "$arn")"
}

web_phase() {
  [ -n "$STAGING_API_SERVICE_ARN" ] || { echo "run 06_services.sh api first" >&2; exit 1; }
  require_image "$ECR_WEB_REPO" "$WEB_IMAGE_TAG"
  require_image "$ECR_API_REPO" "$API_IMAGE_TAG"
  ensure_log_group "$WEB_LOG_GROUP"
  export IMAGE="$registry/$ECR_WEB_REPO:$WEB_IMAGE_TAG"
  local arn origin
  arn="$(ensure_service "$WEB_SERVICE" "$web_template")"
  set_env STAGING_WEB_SERVICE_ARN "$arn"
  echo "waiting for $WEB_SERVICE to become stable"
  aws ecs wait services-stable --cluster "$ECS_CLUSTER" --services "$WEB_SERVICE"
  origin="$(service_url "$arn")"

  if [ "$origin" = "$STAGING_WEB_ORIGIN" ]; then
    echo "ALLOWED_ORIGINS of $API_SERVICE is already $origin"
    return
  fi
  # An update sends the full rendered configuration (A1 §4.3); the create-only keys are dropped.
  export STAGING_WEB_ORIGIN="$origin"
  export IMAGE="$registry/$ECR_API_REPO:$API_IMAGE_TAG"
  render "$api_template" | python3 -c '
import json, sys
config = json.load(sys.stdin)
for key in ("serviceName", "cluster", "infrastructureRoleArn"):
    del config[key]
config["serviceArn"] = sys.argv[1]
json.dump(config, sys.stdout)
' "$STAGING_API_SERVICE_ARN" | aws ecs update-express-gateway-service --cli-input-json file:///dev/stdin \
    --query service.serviceArn --output text
  echo "waiting for $API_SERVICE to become stable"
  aws ecs wait services-stable --cluster "$ECS_CLUSTER" --services "$API_SERVICE"
  set_env STAGING_WEB_ORIGIN "$origin"
}

case "${1:-}" in
  api) api_phase ;;
  web) web_phase ;;
  *) echo "usage: 06_services.sh api|web" >&2; exit 2 ;;
esac
