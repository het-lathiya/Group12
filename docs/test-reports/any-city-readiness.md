# Any-city readiness audit and local real-provider check (IMP-733, CHK-26)

- Run: RUN-095 (Sprint 7, any-city follow-up), part rc-switch-readiness; owner Nidhi
- Base commit: `07b4395` (on `main`); all file and line citations are at that commit, except A2 §3.2 and `docs/acceptance/any-city.md`, which this part changes (IMD-220)
- Decision: IMD-220 (production target ON, under conditions)
- Method: the code, tests and records were read; the suites of this run are in the part record. **No live call was made**: nothing reached Nominatim, Overpass, MediaWiki or Gemini. Anything that could not be confirmed is marked "not verified".
- CI evidence on `main` at `07b4395`: CI run [45652072603](https://github.com/het-lathiya/Group12/actions/runs/45652072603) and E2E run [45652072705](https://github.com/het-lathiya/Group12/actions/runs/45652072705), both success.

| Run and job | Switch | Result line |
| --- | --- | --- |
| CI `unit` | OFF | unit `1851 passed, 1 warning in 23.47s`; contract `99 passed, 2 deselected, 1 warning in 22.48s`; web `50 passed (50)` files, `364 passed (364)` tests |
| CI `api` | OFF | api `680 passed, 1 warning in 230.33s (0:03:50)`; authz `91 passed, 14 skipped, 1 warning in 43.98s` |
| CI `any-city` (not a required check, `.github/workflows/ci.yml:261`) | ON, FAKE | `make test-api ARGS='-m any_city'`: `67 passed, 613 deselected, 1 warning in 19.85s`; `make test-unit ARGS='-m any_city'`: `1851 deselected`, "no tests collected (exit 5 treated as success)"; MOCK `trips/live-v1`: `evaluation 20261125T161719Z-mock: 24 attempts` |
| E2E `live` (`.github/workflows/e2e.yml:271`, `:341`) | ON, FAKE, MOCK | `4 passed (15.6s)` (`live-city.spec.ts` at 360 and 1280 px) |
| E2E `e2e` | OFF | success; `4 passed (42.6s)` for the journey |

## 1. Acceptance (a) to (e) of A2 §2

"CI" below means the CI row above; a test passes there as part of its suite's result line.

| Criterion | Tests on `main` | Last recorded result | Only staging can show |
| --- | --- | --- | --- |
| (a) itinerary or "not enough data", never a 5xx or blank screen | TC-467 `apps/api/tests/unit/livedata/test_normalise.py:507`, `:535`; TC-473 `apps/api/tests/api/test_live_destinations.py:259` to `:372`; TC-475 `apps/api/tests/api/test_live_import_jobs.py:391` to `:487`; TC-483 `apps/web/tests/unit/trips/CitySearch.test.tsx:230`, `ImportProgress.test.tsx:122`; TC-486 `apps/web/e2e/live-city.spec.ts:68`, `:158` | CI and E2E `live`: passed | ACC-21 with real data. A geocoder outage answers 503 by design (`app/places/live_service.py:130-132`, A2 §5), which the web shows as a message (`CitySearch.tsx:175-178`) |
| (b) stored places only; tier, badges, attribution, "Price unknown" | TC-479 `apps/api/tests/api/test_live_generation.py:195`, `:211`; TC-484 `apps/web/tests/unit/labels/TierBadge.test.tsx:167` to `:388`, `LiveAttribution.test.tsx:70`; TC-485 `apps/web/tests/unit/costs/CostBreakdown.live.test.tsx:151`, `:209`; TC-486 (footer asserted on itinerary and costs, `live-city.spec.ts:133`, `:152`; explore in `TierBadge.test.tsx:388`) | CI and E2E `live`: passed | ACC-20. The summary page and the trip form's places and review steps carry no attribution (gap G6) |
| (c) provider failure → rule-based plan | TC-480 `test_live_generation.py:227` (timeout), `:247` (quota, IMD-44) | CI: passed | ACC-22 on staging (gap G4) |
| (d) OFF = `c23d78b`; ON keeps the existing tests | TC-460 `apps/api/tests/unit/core/test_any_city_switch.py:56` to `:68`; TC-461 `apps/api/tests/contract/test_any_city_contract.py:52` to `:99`; TC-490 record [any-city-switch.md](any-city-switch.md) | OFF: CI on `07b4395` passed. ON: RUN-092 record on that branch: unit 1851, contract 96, api 678 passed; authz 84 passed with the two tests of IMD-219 also deselected. **Not verified:** an ON run of the unit, contract, authz and full api suites at `07b4395`, and any ON run of the web suite (the record has no web row) or of the existing curated E2E journeys (the `live` job runs `live-city` only) | ACC-23 on Ahmedabad |
| (e) offline tests use fakes only | TC-471 `apps/api/tests/unit/livedata/test_fakes.py:195` to `:218`; socket guard `apps/api/tests/conftest.py:31`, `test_throttle.py:496`, `:503` | CI: passed | nothing |

## 2. "Cut if late" items (A2 §1.3)

| Item | State | Proof |
| --- | --- | --- |
| Refresh of an expired live destination | Built for `completed`; **not for an expired `insufficient_data`** city through API-77 | `app/places/live_service.py:251-258` requeues `failed`, or `completed` and expired; the CLI also re-runs an expired `insufficient_data` row (`app/places/live_import.py:117-132`). A2 §6.1 says "failed, or past `expires_at`" (gap G15) |
| Wikipedia as second guide source | Built | `app/livedata/providers/wiki.py:24-34` (both sources) |
| Lexical guide passages without embeddings | Cut | `IMP-726-whole-task.md` "Cut if late"; `app/rag/service.py:464-465` falls back with no guides |
| Prompt template v4 and its activation | Template built, hashed, **not activated** | `app/ai/prompts/templates/itinerary_generate/v4/`; `app/core/config.py:74` is `v2`; `eval/reports/live-v1-gemini-2026-11-25.md`; IMD-220 (e) |
| Nearby-city lookup through Overpass | Built, capital as fallback | `app/places/live_jobs.py:215-231`; `app/livedata/providers/base.py:178-186` |
| Multi-zone countries (no longer "cut if late", IMD-216) | Built | `app/livedata/countries.py:813-824`; TC-464 (`IMP-724-countries.md`) |
| Curated-versus-live evaluation report | Built (MOCK comparison) | `eval/reports/live-v1-2026-11-23.md` "Comparison with trips/v1" |

## 3. Real-provider readiness

**Usage-policy dates (IMP-723 step 8)** — `docs/progress/parts/IMP-723-throttle-isolation.md`, "Usage policy check":

| Service | Recorded | State |
| --- | --- | --- |
| Nominatim | The wiki summary was read 23 Nov 2026; the policy page could not be read | **not verified — Junaid to confirm** |
| Overpass API | Read 23 Nov 2026; "regular use" is about 100 queries and 10 MB a day | recorded; caps unchanged (IMD-217) |
| MediaWiki API | Read 23 Nov 2026 | recorded |
| OSM copyright | Page read 23 Nov 2026; the exact credit wording could not be read | exact wording **not verified — Junaid to confirm** |

**Facts recorded on 25 November 2026 (RUN-096).** Status of each: "checked by the planner on 25 Nov 2026 against the source; confirmation by Junaid (IMP-723 step 8) pending". They are also in A2 §16.

| Service | Source | Fact |
| --- | --- | --- |
| Nominatim | https://operations.osmfoundation.org/policies/nominatim/ | End-user-triggered use with a moderate number of users is acceptable; periodic app requests count as bulk geocoding and are strongly discouraged; a valid Referer or User-Agent identifying the application is required (stock library agents are not accepted); absolute maximum 1 request per second. Matches A2 §7.3 |
| Overpass API | https://dev.overpass-api.de/overpass-doc/en/preface/commons.html, https://wiki.openstreetmap.org/wiki/Overpass_API | Rate limit per IP; denials answered with HTTP 429; default run time 180 s and memory 512 MiB unless declared; 10,000 queries and under 1 GB per day for one-off use, divided by 100 for regular use. The daily cap (50 new imports, at most 2 queries each) gives at most 100 queries per day; the 15-minute breaker on 429 matches the request to back off. Not covered by that cap: re-queued failed imports (G20), CLI imports, and the data volume |
| Wikimedia | https://www.mediawiki.org/wiki/Wikimedia_APIs/Access_policy, https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy, https://www.mediawiki.org/wiki/Manual:Maxlag_parameter | A User-Agent with contact information is required on every request, preferred form `<client>/<version> (<contact>) <library>/<version>`; library-default agents are rate limited down to 1 request per second per IP or blocked; a maxlag refusal returns HTTP 200 with error code `maxlag`, which `wiki.py:98-100` maps to a failure (tests: `IMP-725-live-import-hardening.md`, addendum) |
| OpenStreetMap ODbL attribution | — | not re-checked in this run |

`security-any-city.md` ("Policy pages: Junaid to confirm by reading") still lists all three services as open, while the IMP-723 record dates two of them. A2 §7.3 asks for the reading before the first call outside tests, so it comes before section 6.

**Settings per host**

| Host | User-Agent | Spacing | Breaker | Timeout |
| --- | --- | --- | --- | --- |
| Nominatim | `WIKI_USER_AGENT` on each request (`app/livedata/providers/osm.py:65-68`) | ≥ 1.0 s (`throttle.py:43`) | yes (`throttle.py:181-183`, `:191`) | 10 s (`config.py:97`) |
| Overpass | same | ≥ 2.0 s (`throttle.py:44`) | yes (`throttle.py:186-188`, `:195`) | `[timeout:90]`, HTTP 95 s (`config.py:98`, `osm.py:36`, `:236`) |
| MediaWiki | same (`wiki.py:80-82`) | ≥ 0.2 s between **fetches**, not between the requests of one fetch (`throttle.py:161-162` wraps the whole fetch; `wiki.py:177-181`; gap G16) | none (`throttle.py:159`) | 10 s (`config.py:99`) |

- Breaker: 5 consecutive transient failures → 60 s open; a 429 → 15 minutes open (`app/ai/breaker.py` constants; `throttle.py:91-97`; `test_throttle.py:254`, `:280`).
- Throttle and breaker are per process (`throttle.py:165-188`). A CLI run is its own process, so nothing spaces one CLI run from the next, or from the API.
- The start-up check of the User-Agent runs in `create_app` only (`app/main.py:50`, `app/core/config.py:200-207`). The import CLI calls `get_settings()` only (`live_import.py:218`), so an empty or placeholder User-Agent would be sent (gap G11).

**Overpass failures**

| Case | Recorded state | What the user sees (`ImportProgress.tsx:11-14`, `:91-95`) |
| --- | --- | --- |
| HTTP 429, or breaker open | `failed` / `rate_limited` (`osm.py:75-76`, `live_jobs.py:134-135`, `throttle.py:105-107`) | "We could not reach the map data service. Try again in a few minutes. The service is busy." and "Try again". With the 15-minute breaker, an earlier retry fails at once |
| No answer (HTTP timeout, or the 300 s job limit) | `failed` / `timeout` (`osm.py:71-72`, `live_jobs.py:132-133`) | "We could not reach the map data service. Try again in a few minutes." and "Try again" |
| Other HTTP error, malformed body | `failed` / `provider_unavailable` (`osm.py:77`, `:245-246`) | same as timeout |
| HTTP 200 with a server-side error note | **No code reads it**: `osm.py:240-248` reads `elements` only, and no test or fixture has a `remark` field. That the service answers this way is **not verified** here | possibly a false "not enough data", kept for `LIVE_DATA_TTL_DAYS` (gap G8) |
| Failure of the nearby-city lookup | import not failed; the capital is used (`live_jobs.py:223-231`) | the capital's name in the message |

Tests: TC-475 `test_live_import_jobs.py:391`, TC-469 `test_clients.py:234`. Nominatim errors give 503 "City search is not available right now. Try again in a few minutes." (`live_service.py:66`, `:130-132`, `:188-191`). A MediaWiki error stores places without guides (IMD-218, `app/rag/service.py:260-266`).

**Only the fakes or SAMPLE recordings have exercised** (no record in the repository shows a real call):

- every real response shape, size and duration: the client fixtures are SAMPLE (`apps/api/tests/unit/livedata/test_clients.py:1-4`);
- which `addresstype` Nominatim gives the demo cities: only city, town, village and municipality are kept (`osm.py:38-43`);
- element counts, response size, import time (NFR-051 not measured) and memory of a large city;
- the gate on real data, and which small town fails it;
- dedupe, categories and names on real tags (local-language names are stored as they are, `normalise.py:289`);
- MediaWiki title matching, redirects and geosearch on real titles;
- Gemini embeddings of a live corpus (up to 400 chunks, `live_guides.py:29`).

## 4. Deployment readiness

- **A2 §7.2 values for staging.** They are documented in `docs/guides/deployment.md:158-172`, with defaults in `app/core/config.py:91-103`. They are **not** in `infra/aws/services/api.staging.json.tmpl:21-44`. Each deploy sends the full rendered template (`deploy-staging.yml:158-159`), so a value added by hand in AWS would be replaced. With the switch ON and no `LIVE_DATA_PROVIDER`, the default `FAKE` stops start-up (`config.py:200-205`; TC-462 `test_any_city_switch.py:124`). Gap G1.
- **Switch variable.** `STAGING_FEATURES_DISABLED` feeds the API (`api.staging.json.tmpl:26`) and the web build argument (`deploy-staging.yml:296`). Its present value: not verified (a repository variable).
- **`WIKI_USER_AGENT` contact.** Still open, owner Kirtan (`deployment.md:163`; `IMP-733-environment.md` open issues). Gap G2.
- **Production task template.** None: `infra/aws/services/` holds only the two staging templates (A2 §15.1), and `deploy-production.yml:201-202` needs `api.production.json.tmpl` and `web.production.json.tmpl`. Production is not created yet (`deployment.md:182`). Gap G5.
- **ACC-22.** The staging template fixes `AI_PROVIDER` to `GEMINI` (`api.staging.json.tmpl:30`) and has no `MOCK_PROVIDER_SCENARIO`; no guide holds the steps to switch staging to the MOCK timeout and back. Gap G4. A release task run while the service environment is MOCK would re-embed the curated corpus with MOCK vectors, because the task uses the service's current environment (`deploy-staging.yml:198`), indexes every run (`apps/api/scripts/release.sh:22`) and re-embeds chunks of another model (`app/rag/repository.py:155`).
- **One task.** `minTaskCount` and `maxTaskCount` are 1 (`api.staging.json.tmpl:10-13`), as A2 §7.3 needs. The task has 256 CPU units and 512 MB (`:7-8`); the import parses and normalises in that process (`live_jobs.py:158-159`). Gap G12.
- **Pre-import command.** The runbook gives the CLI lines "in the same way as the release task" but no `run-task` command (`any-city-staging.md:18-25`). The only written one-off pattern is for another command, marked "Not verified — run by Kirtan" (`deployment-guide.md:231-245`). Gap G13.

## 5. Known limits of the live tier

- **No opening hours.** Live places never have hours; every stop gets an "unknown hours" warning, grouped into one line (A2 §6.3, §6.6; `normalise.py:90`).
- **No prices.** Live places never have a price. Costs show "Known costs only", and a budget status covers known costs only (A2 §6.6).
- **Step-free is mostly unknown.** Only `wheelchair=yes` counts, and step-free trips leave out every place with an unknown value, so the list may be short (`normalise.py:195-201`; `app/generation/retrieval.py:119`).
- **Ranking.** With no prices, the budget priority has no effect on live places (`IMP-727-whole-task.md` "Ranking note").
- **Not checked by the team.** Places and texts come from OpenStreetMap, Wikivoyage and Wikipedia contributors (`CitySearch.tsx:16-17`). At most 300 places per city, the richest first (`normalise.py:21`, `:343-360`), inside a box of about 28 km around the centre (`countries.py:56`).
- **Gemini overload.** While Gemini answers 503, plans end as the labelled rule-based plan (IMD-33; `eval/reports/live-v1-gemini-2026-11-25.md` sections 3, 4 and 6: 1 usable attempt of 24).
- **No guide citations without embeddings.** If embedding fails during the import, plans cite no guide passage, and nothing embeds that city again before it expires (section 7, G9).
- **Shared public services.** Nominatim, Overpass and MediaWiki are public instances with no guarantee. A busy Overpass fails an import, and the "regular use" budget is far below the app's caps (`IMP-723-throttle-isolation.md`).
- **Old prompt wording.** v2 calls passages "curated sources", which is inexact for live guides (A2 §1.3).

## 6. Operator local real-provider check

**For the operator only, on 26 November 2026, before the cutoff of 27 November 23:59 IST. Nothing here was run in RUN-095.** It is a rehearsal: it does not count as ACC-20, ACC-21 or TC-491, which need staging.

**Before the first call:** Junaid's Nominatim reading is recorded (G3); the team contact for the User-Agent is agreed (G2); the small town is chosen (G14). Run everything in separate terminals from the repository root, and run no `make test` or `make e2e` there: the exports would change the test settings, and `make e2e` would drive the real providers.

### 6.1 Stack, migrations and seed

```sh
make stack-up
make db-migrate     # head 0008
make seed           # Sampleton; add SEED_DIRS=data/places/ahmedabad for the curated city
```

### 6.2 Environment (names; values in the operator's shell only)

Names needed: `APP_ENV`, `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_JWKS_URL` (or `SUPABASE_JWT_SECRET`), `DB_AUTH_STUB`, `AI_PROVIDER`, `LIVE_DATA_PROVIDER`, `FEATURES_DISABLED`, `WIKI_USER_AGENT`; web: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_FEATURES_DISABLED`. The operator's untracked env files already hold the base ones (`docs/guides/local-setup.md` section 3). An exported value wins over the API's `.env` file. Leave `ORS_API_KEY` unset or as it is; without it, travel uses the distance estimate. Never set `GOOGLE_API_KEY`.

In the terminals of the CLI and of `make api` (single quotes: zsh expands an unquoted `!`):

```sh
export AI_PROVIDER=MOCK
export LIVE_DATA_PROVIDER=LIVE
export FEATURES_DISABLED='!any_city_mode'
read -r WIKI_USER_AGENT && export WIKI_USER_AGENT     # type the agreed value; it is not echoed into a file
case "$WIKI_USER_AGENT" in ''|'<'*) echo 'STOP: WIKI_USER_AGENT is empty or a placeholder';; *) echo 'User-Agent is set';; esac
```

The last line matters: the CLI itself does not check it (G11).

### 6.3 Import the four cities, one at a time

```sh
cd apps/api
time .venv/bin/python -m app.places.live_import --query 'Jaipur, Rajasthan, India'
time .venv/bin/python -m app.places.live_import --query 'Udaipur, Rajasthan, India'
time .venv/bin/python -m app.places.live_import --query 'Mumbai, Maharashtra, India'
time .venv/bin/python -m app.places.live_import --query '<small town, state, country>'
```

Wait at least 10 s between commands, since spacing does not carry over between processes (section 3). Stop and record if any run prints `rate_limited`; do not retry within 15 minutes.

Each run prints (`live_import.py:177-191`): `destination_id`, `slug`, `import_ran`, `import_status`, `failure_reason`, `places_found`, `places_usable`, `nearby_city`, `is_active`, `imported_at`, `expires_at`. Exit codes: 0 completed or not enough data; 1 failed or not importable; 2 bad arguments; 3 another run holds it (`live_import.py:46-49`, `:194-200`).

| City | Expected state | Expected counts |
| --- | --- | --- |
| Jaipur, Udaipur, Mumbai | `completed`, `is_active: True`, `failure_reason: -`, exit 0 (not verified: no real import has run) | `places_usable` 40 to 300, of which 6 to 105 food and at least 12 non-food (`normalise.py:21-27`, `:392-406`); `places_found` not known in advance |
| Small town | `insufficient_data`, `is_active: False`, `nearby_city` a name other than the town, exit 0 (not verified) | `places_usable` below 40, or fewer than 6 food or 12 non-food |

Check that the slug's end is the intended OSM reference. `--query` takes the first settlement, and the output has no region or country. Record the date, the OSM reference, the state, the two counts and the `time` line. If a run is interrupted, its row stays `running` until the API with the switch ON reaps it after 360 s (`live_jobs.py:256-275`).

What does not exist:

- a `make` target for the import: does not exist;
- a `--force`, `--dry-run` or delete option of the CLI: does not exist (a completed or not-enough-data city that has not expired is only printed);
- a printed duration, OSM reference or guide count: does not exist (use `time`, the slug and the web footer);
- a command that embeds a live city again: does not exist (G9).

### 6.4 API and web with the switch ON

```sh
# terminal 1, with the exports of 6.2
make api
# terminal 2
export NEXT_PUBLIC_FEATURES_DISABLED='!any_city_mode'
make web
```

Open `http://localhost:3000`. Do not edit API files meanwhile: `make api` reloads, which would stop a running import.

- **ACC-20 rehearsal (MOCK).** Sign in; in Create a trip, search "Jaipur", choose the result; expect "Ready: N places from OpenStreetMap" at once. Create the trip and generate. Expect "Live data", OpenStreetMap badges, "Price unknown", "Hours unknown" and the "Data sources" footer on explore, itinerary and costs. Also open the summary page and note that it has no footer (G6).
- **ACC-21 rehearsal.** Search the small town, choose it; expect "We could not find enough places for {name} yet. Try {nearby_city}, a larger city nearby." and no 5xx.
- **GEMINI, once, only if the operator chooses.** Stop `make api`, set `AI_PROVIDER=GEMINI` with `GEMINI_API_KEY`, `GEMINI_MODEL_ID` and `GEMINI_EMBEDDING_MODEL_ID` in the shell, start it again and generate once. Cities imported with MOCK hold MOCK vectors, so retrieval falls back to lexical ranking and cites no guide (`app/rag/service.py:453-465`, `app/rag/repository.py:182`). To see guide citations, run the imports of 6.3 with the GEMINI settings from the start. Failures are recorded as they are and not re-run (IMD-200).

Afterwards: stop both servers and unset the exports. Live rows stay in the local database and do nothing with the switch OFF; `make db-reset` removes them with all other local data.

### 6.5 Expected calls

| Service | Four imports of 6.3 | Web walk of 6.4 | Spacing |
| --- | --- | --- | --- |
| Nominatim | 8 (one search and one lookup per city) | 2 searches; 3 if the nearby-city button is pressed; 0 lookups for cities that exist (`live_service.py:184-186`) | ≥ 1.0 s in one process |
| Overpass | 5 (one per city, plus one nearby-city query for the small town) | 0 | ≥ 2.0 s in one process |
| MediaWiki | 6 to 18 (2 to 6 per completed city; 0 for the small town, `live_jobs.py:163-186`) | 0 | serial; no spacing inside one fetch (G16) |
| Gemini | 0 with MOCK. With GEMINI: at most 13 embedding batches per completed city, 26 attempts (`RAG_EMBED_BATCH` 32, `live_guides.py:29`, one retry) | 0 with MOCK. With GEMINI, one generation: at most 2 generation calls, 1 repair call and 2 query-embedding attempts | not spaced by the live-data throttle |

A failed import run again makes 1 search (with `--query`) and no lookup, and then the Overpass and MediaWiki calls again (`live_import.py:126-132`). The browser also loads map tiles.

## 7. Gap list

Severity 1 blocks an IMD-220 production-ON condition; 2 is a visible defect; 3 is polish. "Before cutoff" means a merge by 27 November 2026 23:59 IST.

| # | Sev | Gap and evidence | Proposed owner (A2 §12) | Before cutoff |
| --- | --- | --- | --- | --- |
| G1 | 1 | `LIVE_DATA_PROVIDER` and `WIKI_USER_AGENT` are not in the staging template, so staging with the switch ON refuses to start (section 4). With the switch OFF the values have no effect (`deployment.md:180`), so they can land early | Kirtan (IMP-733) | yes |
| G2 | 1 | `WIKI_USER_AGENT` has no agreed team contact (`deployment.md:163`). It must follow the Wikimedia preferred form with a real contact (Kirtan) | Kirtan (IMP-733) | yes |
| G3 | 1 | The Nominatim policy and the exact OSM credit text are not read; A2 §7.3 requires it before the first real call, so it blocks section 6 and TC-491. Facts recorded by the planner (section 3); Junaid's confirmation pending | Junaid (IMP-723, IMP-731) | yes (reading and a record) |
| G4 | 1 | ACC-22 cannot be run on staging from the template, and no procedure is written (section 4) | Kirtan (IMP-733) | yes (procedure) |
| G5 | 1 | No production template, so the production A2 §7.2 values cannot be reviewed (A2 §15.1) | Kirtan (IMP-733, IMP-801) | not needed; before IMP-801 |
| G6 | 1 | Live place names without attribution on the summary page (`apps/web/app/(app)/trips/[tripId]/summary/page.tsx:53`, `PrintLayout.tsx:92`) and in the trip form (`PlacesStep.tsx:155`, `ReviewStep.tsx:171`); `LiveAttribution` is used on explore, itinerary and costs only. A2 §9.2 lists those three, A2 §10 says every screen: the team decides which reading IMD-220 (c) means | Krrish (IMP-729) | yes |
| G7 | 1 | No real import has run (TC-491, NFR-051 not measured) | operator (section 6), Kirtan (staging) | local check yes; TC-491 on 28 November |
| G8 | 2 | An Overpass HTTP 200 answer with an error note would count as data: a false "not enough data" (or a partial city) kept 30 days, with no forced re-import (section 3) | Manal (IMP-723, IMP-725) | yes |
| G9 | 2 | Chunks left without embeddings are never embedded later: the release index is curated-only (`release.sh:18-22`), and `embed_destinations` is called by the import only (`live_jobs.py:236`). The Gemini overload of 24 and 25 November makes this likely during a pre-import | Nidhi (IMP-726) | yes |
| G10 | 2 | The guide page is taken by title alone when one exists (`wiki.py:146-148`), with no coordinate check, so a city can get the page of another place of the same name | Manal (IMP-723) | yes |
| G11 | 2 | The import CLI skips the start-up checks, so an empty or placeholder User-Agent is sent (section 3) | Manal (IMP-725) | yes |
| G12 | 2 | Memory and CPU of a large import in the 512 MB API task are not measured; parsing and normalising block the API process | Kirtan (measure), Manal (fix if needed) | measure locally yes |
| G13 | 2 | The runbook has no exact one-off task command for the pre-import (section 4) | Kirtan, Nidhi (IMP-733) | yes |
| G14 | 2 | The small town for ACC-21 is not named (IMD-220 (d), PD-AC-2) | operator for the team | yes |
| G15 | 3 | An expired `insufficient_data` city is not queued again by API-77 (section 2) | Het (IMP-725) | yes |
| G16 | 3 | MediaWiki's 0.2 s spacing does not apply inside one fetch (up to 6 requests), and an error on the Wikipedia half loses the Wikivoyage sections already read (`wiki.py:174-184`) | Junaid (IMP-723), Manal | yes |
| G17 | 3 | One search result with a missing field (for example no country code) turns the whole search into 503 (`osm.py:160-169`); not observed | Manal (IMP-723) | yes |
| G18 | 3 | The nearby city uses the local `name` (`osm.py:257`) while the settlement uses its English name (`live_service.py:210`), so "never the settlement itself" (`normalise.py:409-418`) can miss a local-script match; the suggested city is not checked to be larger | Jeel (IMP-724), Manal | not needed |
| G19 | 3 | Queued imports older than 10 minutes are reaped (`live_jobs.py:59`) while one import may take 300 s and only one runs at a time, so a fourth queued city can time out waiting | Manal (IMP-725) | not needed |
| G20 | 3 | A failed city can be queued again without any daily cap (`live_service.py:251-258`) | Het (IMP-725) | not needed |
| G21 | 3 | The switch-ON record is from RUN-092; it has no web row and no curated E2E run ON, and the CI unit step for `any_city` collects no test | Krrish (IMP-730) | yes (a new ON run) |
| G22 | 3 | Stale wording: `any-city-staging.md:12` and `final-report.md:369` say PD-AC-2 is proposed; `security-any-city.md` lists two policies as unread that IMP-723 dates | Nidhi, Junaid | yes |
