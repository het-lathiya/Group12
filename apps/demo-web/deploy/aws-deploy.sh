#!/usr/bin/env bash
# Deploy the demo frontend to AWS Amplify Hosting (manual zip deploy, no Git connection).
#   /api/*            -> proxied to the staging API (same origin for the browser, so CORS is untouched)
#   /trips/<id>/...   -> served from the prerendered /trips/_/... pages (the page reads the id from the URL)
# Re-running uploads a new build to the same app/branch.
# Tagged Project=group12-demo_test; aws-teardown.sh removes it.
set -euo pipefail

REGION=ap-south-1
NAME=group12-demo-test
BRANCH=demo
API_HOST=gr-8c92985228bc4ea8ada4840e8cf45d50.ecs.ap-south-1.on.aws
HERE="$(cd "$(dirname "$0")" && pwd)"
APP="$(cd "$HERE/.." && pwd)"
STATE="$HERE/.aws-demo-state"
export AWS_REGION=$REGION

echo "==> Building static site"
(cd "$APP" && rm -rf out && npm run build:static >/dev/null 2>&1)

RULES=$(cat <<JSON
[
  {"source": "/api/<*>", "target": "https://$API_HOST/api/<*>", "status": "200"},
  {"source": "/trips/new/<*>", "target": "/trips/new/<*>", "status": "200"},
  {"source": "/trips/_/<*>", "target": "/trips/_/<*>", "status": "200"},
  {"source": "/trips/<id>/<*>", "target": "/trips/_/<*>", "status": "200"},
  {"source": "/<*>", "target": "/404.html", "status": "404-200"}
]
JSON
)

if [ -f "$STATE" ]; then
  # shellcheck disable=SC1090
  source "$STATE"
  echo "==> Updating existing Amplify app $APP_ID"
  aws amplify update-app --app-id "$APP_ID" --custom-rules "$RULES" >/dev/null
else
  echo "==> Creating Amplify app"
  APP_ID=$(aws amplify create-app --name "$NAME" --platform WEB --custom-rules "$RULES" \
    --tags Project=group12-demo_test --query app.appId --output text)
  aws amplify create-branch --app-id "$APP_ID" --branch-name "$BRANCH" --stage PRODUCTION >/dev/null
  printf 'APP_ID=%s\nBRANCH=%s\n' "$APP_ID" "$BRANCH" > "$STATE"
fi

echo "==> Uploading build"
ZIP="$HERE/.site.zip"
rm -f "$ZIP"
(cd "$APP/out" && zip -qr "$ZIP" .)
read -r JOB_ID URL < <(aws amplify create-deployment --app-id "$APP_ID" --branch-name "$BRANCH" --query '[jobId,zipUploadUrl]' --output text)
curl -sf -X PUT -H "Content-Type: application/zip" --upload-file "$ZIP" "$URL" >/dev/null
aws amplify start-deployment --app-id "$APP_ID" --branch-name "$BRANCH" --job-id "$JOB_ID" >/dev/null
rm -f "$ZIP"

echo -n "==> Deploying (job $JOB_ID)"
while :; do
  S=$(aws amplify get-job --app-id "$APP_ID" --branch-name "$BRANCH" --job-id "$JOB_ID" --query job.summary.status --output text)
  case "$S" in SUCCEED) echo " done"; break ;; FAILED|CANCELLED) echo " $S"; exit 1 ;; *) echo -n "."; sleep 5 ;; esac
done

echo
echo "Demo URL: https://$BRANCH.$APP_ID.amplifyapp.com"
