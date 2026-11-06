#!/usr/bin/env bash
# Monthly cost budget of USD 50 with e-mail alerts at USD 25 and USD 50 (A1 §4.1, NFR-049, TC-435).
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

existing="$(aws budgets describe-budgets --account-id "$AWS_ACCOUNT_ID" \
  --query "Budgets[?BudgetName=='$BUDGET_NAME'].BudgetName" --output text)"
if [ -n "$existing" ]; then
  echo "budget $BUDGET_NAME exists"
  exit 0
fi

alert() {
  cat <<JSON
{
  "Notification": {
    "NotificationType": "ACTUAL",
    "ComparisonOperator": "GREATER_THAN",
    "Threshold": $1,
    "ThresholdType": "ABSOLUTE_VALUE"
  },
  "Subscribers": [{"SubscriptionType": "EMAIL", "Address": "$BUDGET_ALERT_EMAIL"}]
}
JSON
}

aws budgets create-budget --account-id "$AWS_ACCOUNT_ID" \
  --budget "{\"BudgetName\": \"$BUDGET_NAME\", \"BudgetType\": \"COST\", \"TimeUnit\": \"MONTHLY\", \"BudgetLimit\": {\"Amount\": \"50\", \"Unit\": \"USD\"}}" \
  --notifications-with-subscribers "[$(alert 25), $(alert 50)]"
echo "budget $BUDGET_NAME created with alerts at USD 25 and USD 50"
