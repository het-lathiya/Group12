# Any-city mode on staging: pre-import runbook (IMP-733)

For the staging window of 28 November 2026 (Amendment A2 §14), run by Kirtan, only if the release ships with `any_city_mode` ON. The environment and the switch are in [deployment.md](deployment.md) (any-city addendum). This page covers the live cities.

## Before you start

- The switch is ON in the API (`STAGING_FEATURES_DISABLED` holds `!any_city_mode`) and in the web build.
- `LIVE_DATA_PROVIDER=LIVE` and `WIKI_USER_AGENT` is set (start-up refuses FAKE, or an empty or placeholder User-Agent, in staging with the switch ON; TC-462). `api.staging.json.tmpl` holds the A2 §7.2 values; its `WIKI_USER_AGENT` is a placeholder that start-up and the CLI refuse. Kirtan replaces it with the agreed team contact before the switch is turned ON.
- **One API task** runs. The outbound spacing is per process (A2 §7.3).
- The usage policies of Nominatim, Overpass and MediaWiki have been read, with the date recorded ([security-any-city.md](../test-reports/security-any-city.md), "Junaid to confirm by reading").

## Demo cities (PD-AC-2, adopted by IMD-220)

**Jaipur, Udaipur, Mumbai and one small town** (the small town shows the not-enough-data path, ACC-21; its name is still to be chosen). Import them before the demo, so no live import runs in front of an audience.

## Pre-import

Run the import CLI once per city in a one-off ECS task with the API image, in the same way as the release task (A1 §4.5; Kirtan only, never from a laptop with AWS credentials in the repository):

```sh
python -m app.places.live_import --query "Jaipur"
python -m app.places.live_import --query "Udaipur"
python -m app.places.live_import --query "Mumbai"
python -m app.places.live_import --query "<small town>"
```

**The one-off task.** It follows the release-task invocation of the deploy workflows, like the account-deletion task in [deployment-guide.md](deployment-guide.md) section 9 (it needs the AWS CLI v2 and `jq`). **Not verified — run by Kirtan** (written for this runbook; not tried against AWS). Run it after the deploy that turned the switch ON, so the service's task definition has the live values:

```sh
. infra/aws/env.sh
city="Jaipur, Rajasthan, India"        # one city per run; the small town last
td="$(aws ecs describe-services --cluster "$ECS_CLUSTER" --services "$API_SERVICE" \
  --query "services[0].deployments[?status=='PRIMARY'].taskDefinition | [0]" --output text)"
container="$(aws ecs describe-task-definition --task-definition "$td" \
  --query 'taskDefinition.containerDefinitions[0].name' --output text)"
task_arn="$(aws ecs run-task --cluster "$ECS_CLUSTER" --task-definition "$td" --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$AWS_SUBNET_IDS],securityGroups=[$API_TASKS_SECURITY_GROUP],assignPublicIp=ENABLED}" \
  --overrides "$(jq -n --arg name "$container" --arg city "$city" \
    '{containerOverrides: [{name: $name, command: ["python", "-m", "app.places.live_import", "--query", $city]}]}')" \
  --query 'tasks[0].taskArn' --output text)"
aws ecs wait tasks-stopped --cluster "$ECS_CLUSTER" --tasks "$task_arn"
aws ecs describe-tasks --cluster "$ECS_CLUSTER" --tasks "$task_arn" \
  --query "tasks[0].containers[?name=='$container'] | [0].exitCode" --output text
aws logs get-log-events --log-group-name "$API_LOG_GROUP" --start-from-head \
  --log-stream-name "ecs/$container/${task_arn##*/}" --query 'events[].message' --output text
```

Exit code 0 means completed or not enough data; 1 means the import failed or the configuration is refused; 3 means another run holds the city. The spacing to the public services is per process, so wait at least 10 s between tasks, and 15 minutes after `rate_limited`.

- `--query` takes the first settlement Nominatim returns; `--osm-ref R1234567` picks an exact one.
- The CLI runs the same import as the app, synchronously. It prints the counts and the final state, and it is idempotent per OSM reference: a completed, unexpired city is only printed.
- Add `--force` to import a city again before it expires (a wrong "not enough data", or new data). It never touches a running import.
- Running the CLI again on a completed city embeds the chunks an embedding outage left out and prints `embedded_on_re_run`.
- Do not run a release task while the service is on MOCK (ACC-22): it would re-embed the curated corpus with MOCK vectors.
- Imports are serial. Wait for each to finish before the next.
- Record for each city (TC-491): the OSM reference, the final state, places found and usable, the import time and the date.

## After the import

- Open each city in the web app: the "Live data" badge, the OpenStreetMap badges and the attribution footer (with a per-page Wikivoyage entry where a guide was found).
- Run ACC-20 to ACC-23 and record them in [any-city.md](../acceptance/any-city.md).

## Rollback

Remove `!any_city_mode` from `STAGING_FEATURES_DISABLED` and from the web build argument, then deploy. The any-city routes then answer 404, the city search disappears and curated trips are unchanged. No data is deleted.
