# Pre-demo checklist

**DRAFT — template (IMP-803 step 1); completed on demo day.** Each step is ticked only by the person who did it, with the time. Nobody fills a row for someone else, and no row is filled before demo day.

| Item | Value |
| --- | --- |
| Card | IMP-803 (US-149; NFR-005, NFR-009; CHK-16, CHK-24, CHK-25) |
| Demo date and place | |
| Release (tag and commit) | |

## Deployment, database and fallback (Malhar)

| # | Step | How to check | Done by | Time |
| --- | --- | --- | --- | --- |
| M1 | Backend awake at least 10 minutes before the demo (NFR-005) | `curl` the production `/health`; it answers with the release version | | |
| M2 | RDS instance available, not stopped | Kirtan: the read-only `aws rds describe-db-instances` of [deployment.md](../guides/deployment.md) §8 prints `available` | | |
| M3 | RDS manual snapshot taken (NFR-009, A1 §5.1) | Kirtan takes it; write its name here: ____ | | |
| M4 | CHK-24: production runs on AWS from the tagged images; budget alerts active; task definitions hold no secret values | Kirtan; record of the check: ____ | | |
| M5 | CHK-25: RAG index built, with guides at least for destination 1; retrieval evaluation report committed | index line of the production release task: ____; report under `eval/reports/` | | |
| M6 | `make smoke URL=<production API URL>` passes | paste the summary line: ____ | | |
| M7 | Local stack with `AI_PROVIDER=MOCK` runs on the presenter machine | [README.md](README.md); `/health` says provider MOCK | | |
| M8 | Any-city switch state as decided at IMP-801 (IMD-220) | state: ____; with ON, the demo cities answer in the city search | | |

## Keys, accounts, itineraries and demo path (Jeel)

| # | Step | How to check | Done by | Time |
| --- | --- | --- | --- | --- |
| J1 | Gemini key, `GEMINI_MODEL_ID` and remaining quota checked | Kirtan or Het check the key; no key is written here. A 503 "high demand" answer is possible: the plan is then rule-based and labelled | | |
| J2 | Demo accounts sign in on production | each account signs in and out; no password is written here | | |
| J3 | Saved sample itinerary ready: curated Ahmedabad | open it on the demo account | | |
| J4 | Saved sample itinerary ready: one live demo city, only if production is ON | open it; "Live data" badge and "Data sources" footer visible; write "not applicable" if OFF | | |
| J5 | Network at the venue | the production web page loads on the demo machine | | |
| J6 | Demo path run once, start to end | [demo-script.md](demo-script.md), path: ____ | | |
