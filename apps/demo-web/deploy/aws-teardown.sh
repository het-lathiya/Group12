#!/usr/bin/env bash
# Turn the demo off so it costs nothing: deletes the Amplify app created by aws-deploy.sh.
# The code stays on the Git branch; run aws-deploy.sh again to bring the demo back (new URL).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
STATE="$HERE/.aws-demo-state"
export AWS_REGION=ap-south-1
[ -f "$STATE" ] || { echo "No demo deployment recorded ($STATE missing)."; exit 0; }
# shellcheck disable=SC1090
source "$STATE"
aws amplify delete-app --app-id "$APP_ID" >/dev/null
rm -f "$STATE"
echo "Deleted Amplify app $APP_ID. The demo URL no longer works."
