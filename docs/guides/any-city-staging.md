# Any-city mode on staging: pre-import runbook (IMP-733)

For the staging window of 28 November 2026 (Amendment A2 §14), run by Kirtan, only if the release ships with `any_city_mode` ON. The environment and the switch are in [deployment.md](deployment.md) (any-city addendum). This page covers the live cities.

## Before you start

- The switch is ON in the API (`STAGING_FEATURES_DISABLED` holds `!any_city_mode`) and in the web build.
- `LIVE_DATA_PROVIDER=LIVE` and `WIKI_USER_AGENT` is set (start-up refuses FAKE, or an empty or placeholder User-Agent, in staging with the switch ON; TC-462).
- **One API task** runs. The outbound spacing is per process (A2 §7.3).
- The usage policies of Nominatim, Overpass and MediaWiki have been read, with the date recorded ([security-any-city.md](../test-reports/security-any-city.md), "Junaid to confirm by reading").

## Demo cities (PD-AC-2, still proposed)

Proposed list: **Jaipur, Udaipur, Mumbai and one small town** (the small town shows the not-enough-data path, ACC-21). The team confirms the list. Import them before the demo, so no live import runs in front of an audience.

## Pre-import

Run the import CLI once per city in a one-off ECS task with the API image, in the same way as the release task (A1 §4.5; Kirtan only, never from a laptop with AWS credentials in the repository):

```sh
python -m app.places.live_import --query "Jaipur"
python -m app.places.live_import --query "Udaipur"
python -m app.places.live_import --query "Mumbai"
python -m app.places.live_import --query "<small town>"
```

- `--query` takes the first settlement Nominatim returns; `--osm-ref R1234567` picks an exact one.
- The CLI runs the same import as the app, synchronously. It prints the counts and the final state, and it is idempotent per OSM reference: a completed, unexpired city is only printed.
- Imports are serial. Wait for each to finish before the next.
- Record for each city (TC-491): the OSM reference, the final state, places found and usable, the import time and the date.

## After the import

- Open each city in the web app: the "Live data" badge, the OpenStreetMap badges and the attribution footer (with a per-page Wikivoyage entry where a guide was found).
- Run ACC-20 to ACC-23 and record them in [any-city.md](../acceptance/any-city.md).

## Rollback

Remove `!any_city_mode` from `STAGING_FEATURES_DISABLED` and from the web build argument, then deploy. The any-city routes then answer 404, the city search disappears and curated trips are unchanged. No data is deleted.
