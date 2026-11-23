# AMENDMENT A2 — Any-city mode (specification v1.5 for any-city mode)

Updated 23 Nov 2026 by IMD-216.

| Item | Value |
| --- | --- |
| Status | Written in RUN-088 (Batch E0) on 22 November 2026 under IMD-210 and IMD-215; part owner Het. The cards of §12 are 0 points, outside the contribution plan |
| Applies to | `IMPLEMENTATION_SPEC.md` v1.3, `AMENDMENT_A1_AWS_RAG.md` (v1.4), `DECISION_REGISTER.md` (IMD-210, IMD-215), `CLAUDE.md` |
| Result | Specification v1.5 = v1.3 + Amendment A1 + this amendment, **for any-city mode only** |
| Precedence | **For any-city mode, this amendment wins over the specification and Amendment A1.** Everything this amendment does not mention stays in force unchanged. With the switch OFF (§3), v1.4 applies as it is |
| Source proposal | `docs/proposals/any-city-plan-option-c.md` (Option C plan of 18 November 2026). This amendment supersedes it where they differ; the plan's agentic tools, grounding and paid services are cut (§1.2) |
| New cards and IDs | Carried by this amendment (§12 to §14). `TASK_REGISTER.md` and `TRACEABILITY_MATRIX.md` are not edited by RUN-088 |
| Base | Code as of `c23d78b` (main, 22 November 2026); every file:line in §15 refers to that commit |

## 0. What changes and what does not

A signed-in traveller can type any city. The API resolves it to a settlement through Nominatim (OpenStreetMap geocoding) and creates a **live** destination. A background import job fetches places from the Overpass API (OpenStreetMap), normalises them to the existing `places` schema, removes duplicates and applies a minimum-places gate. It then stores them through the places module and indexes them, together with Wikivoyage and Wikipedia guide text, in the existing RAG store. The traveller then uses the normal trip, generation, itinerary and costs screens. Every live value is labelled as live, carries its source and attribution, and has no price or opening hours.

These rules stay exactly as before:

- The model only chooses place IDs from the shortlist, their order and times, and short notes. Prices, opening hours, travel times, totals and availability come from data and code (§8 of the specification, PR-02, §5.6). TC-357 and ACC-15 hold.
- The twelve-step pipeline: retrieve → plan → validate → at most one repair → rule-based fallback (IMD-33), the error taxonomy, the circuit breaker, the finding codes and the error envelope of §6.3. No new error code is added.
- `ModelProvider` is the only way to Gemini; embeddings go through `embed_texts` only; vector queries live only in `app/rag/repository.py`; RAG falls back to lexical ranking and never fails a generation (IMD-112). Exact cosine search applies (IMD-107; see §6.5 for the corpus cap).
- The budget currency equals the destination currency (IMD-128); money has two decimals (IMD-05).
- One writer per table. The places module stays the only writer of `destinations`, `data_sources`, `places` and `place_opening_hours`, and the RAG module of `rag_documents` and `rag_chunks`.
- No booking, payments or live prices (IMD-46). All nine extensions stay cut (IMD-65).
- The curated destination (Ahmedabad) and the SAMPLE fixture (Sampleton) behave exactly as before, whatever the switch.
- Tests never reach a provider. New providers are faked offline (§7.4) and the socket guard blocks their hosts (§11).

## 1. Scope

### 1.1 Kept (IMD-210)

| Item | Where |
| --- | --- |
| City search and resolve through Nominatim: cached, at most 1 request per second, identifying User-Agent, explicit search (no type-ahead) | §5.1, §6.1, §7 |
| Live destination plus asynchronous import job: Overpass places → normalise → dedupe → minimum-places gate → store | §4, §6.2 to §6.4 |
| Country → currency and time-zone table in code; IMD-128 holds | §6.1 |
| Data tier `curated` or `live`, always labelled | §4.1, §9 |
| Guide corpus from Wikivoyage and Wikipedia through the MediaWiki API, into the existing RAG pipeline with lexical fallback | §6.5 |
| Existing generation pipeline; unknown hours and prices shown as unknown, never supplied by the model | §6.6, §6.7 |
| OpenStreetMap ODbL and CC BY-SA attribution | §9.3, §10 |

### 1.2 Cut (future work, not built)

- A function-calling ("agentic") planner. The model keeps the gr-2 / io-2 contract.
- Firecrawl, or any scraping of web pages.
- Google Maps grounding, Google Search grounding, the Google Places API and the switch `live_grounding`.
- A paid Gemini key, or any spend beyond the existing free key.
- LLM-as-judge evaluation.
- Parsing the OpenStreetMap `opening_hours` tag. Live places have no hours rows in C-lite: their hours are unknown (§6.3).
- Prices from OpenStreetMap `fee` or `charge` tags, or from guide text. Live places have no price (§6.3).

### 1.3 "Cut if late"

These items are in scope, but are dropped without replacement if they do not fit their batch day. The amendment stays valid either way:

| Item | If cut |
| --- | --- |
| Refresh of an expired live destination (§6.4) | Expired cities stay as imported, showing their import date |
| Wikipedia as a second guide source (§6.5) | Wikivoyage only |
| Lexical guide passages when embeddings are missing (§6.5) | Live plans made without embeddings cite no guide passage (IMD-112 as today) |
| Prompt template `itinerary_generate/v4` and its activation (§6.7) | v2 stays active; the report states that its system text says "curated sources" |
| Nearby-city lookup through Overpass (§6.4) | The "not enough data" message names the country's capital from the country table |
| The curated-versus-live evaluation report (IMP-732) | The live dataset runs in CI; the comparison is described as not measured |

## 2. Acceptance of "works for any city" (= IMD-210 a to e)

- **(a)** Any query that resolves to a settlement yields either an itinerary or a "not enough data" message naming a larger nearby city. It never yields a 5xx or a blank screen. Tests: TC-467, TC-473, TC-483, TC-486; ACC-21.
- **(b)** Live plans use stored places only, and carry the tier label, source badges, attribution and "Price unknown". Tests: TC-479, TC-484, TC-485, TC-486; ACC-20.
- **(c)** A provider failure still yields the rule-based plan for a live city. Tests: TC-480; ACC-22.
- **(d)** With the switch OFF, the behaviour is that of `c23d78b` and every existing test passes unchanged. With the switch ON, the curated Ahmedabad destination still passes every existing test. The exception is the four inventory tests that by design list the OFF route set; §3.4 names them and their ON counterparts. Tests: TC-460, TC-461, TC-490; ACC-23.
- **(e)** Offline tests use fake providers only. Tests: TC-471, and the socket guard of §11.

## 3. The switch `any_city_mode`

### 3.1 Name and semantics

The switch is **`any_city_mode`**. It uses the existing variables `FEATURES_DISABLED` (API) and `NEXT_PUBLIC_FEATURES_DISABLED` (web) of IMD-11 and IMD-47, so no new environment variable and no fifth `NEXT_PUBLIC_*` name is added.

The existing mechanism is a disable list: a listed name is OFF, and an empty value means every feature is ON (`apps/api/app/core/flags.py:10-20`, `apps/web/lib/flags.ts:32-50`). Every environment ships an empty value today. A plain new name would therefore be ON everywhere, and changing the defaults would break the tests that pin them (`apps/api/tests/unit/core/test_config.py:50-55`, `apps/web/tests/unit/lib/flags.test.ts:13-16,28-32`). So `any_city_mode` is a **default-off switch**:

| Value of the variable | `any_city_mode` |
| --- | --- |
| empty, or any list without `!any_city_mode` (for example the nine cut-list names of the floor run) | **OFF** (default) |
| a list containing `!any_city_mode` and not `any_city_mode`, for example `!any_city_mode` or `versions,!any_city_mode` | **ON** |
| a list containing `any_city_mode` | OFF (an explicit OFF wins) |

Rules for the code (IMP-722, IMP-728):

- `app/core/flags.py` gains `DEFAULT_OFF: Final = frozenset({"any_city_mode"})`. `is_enabled(settings, name)` for a name in `DEFAULT_OFF` returns true only when the parsed set contains `"!" + name` and not `name`. For every other name it behaves exactly as today. `parse_features_disabled` and `Settings.features_disabled` stay unchanged: `!any_city_mode` is just another token to them.
- `apps/web/lib/flags.ts` gains `DEFAULT_OFF_FEATURES = ["any_city_mode"] as const`, kept **outside** `FEATURE_NAMES`. `flags.test.ts:28-32` iterates `FEATURE_NAMES`, and `playwright.config.ts:19` takes `FEATURE_NAMES.slice(0, 9)`, so both stay unchanged. `isEnabled` accepts `FeatureName | DefaultOffFeatureName`, with the same token rule.
- The API and the web read their own variable. Both must carry the token for the feature to be visible and usable. The web shows no any-city control unless its own value turns the switch ON.
- `.env.example` documents the token in the comment of both variables. Values stay empty, so the default is OFF.

### 3.2 Where it is set

| Environment | Value | Owner |
| --- | --- | --- |
| Local, CI, the existing E2E runs | empty (OFF) | unchanged |
| CI switch-ON jobs (IMP-730) | `!any_city_mode`, with `LIVE_DATA_PROVIDER=FAKE` | Krrish |
| Staging, 28 November window | `!any_city_mode` in `STAGING_FEATURES_DISABLED` and the web build argument, only if the batches are green by the cutoff (IMD-215) | Kirtan |
| Production | OFF unless the team decides otherwise after SG-7 | Kirtan |

### 3.3 Switch OFF equals `c23d78b`

With the switch OFF:

- The any-city router is **not mounted**: `create_app()` includes it only when `is_enabled(settings, "any_city_mode")`. Its paths answer 404 `NOT_FOUND` through the existing handler (`apps/api/app/core/errors.py:136`). `contracts/openapi.v1.json` and `apps/web/lib/api/schema.d.ts` stay byte-identical.
- The import reaper is not started, no live provider is built, and no outbound call is made.
- API-06 lists `data_tier = 'curated'` destinations only. No live rows exist while OFF, so the response is identical (TC-069 unchanged).
- Migration 0008 is applied in every environment, because one schema serves both states. It only adds nullable or defaulted columns to `destinations` (§4.1). The drift test compares columns from the models, so its code is unchanged (`apps/api/tests/api/test_schema_drift.py:39,88`: the table set does not change). `app/core/health.py:34` `MIGRATION_HEAD` becomes `"0008"` (code, not a test).
- `make imports` gains one contract (§8.2), so its summary line reads `Contracts: 7 kept, 0 broken.`

### 3.4 Switch ON

- **Contract.** `make openapi` also writes `contracts/openapi.any-city.v1.json` and `apps/web/lib/api/any-city-schema.d.ts`. These come from an app built with `features_disabled="!any_city_mode"` (`app/openapi_export.py`). `make openapi-check` checks all four files (IMP-722). The web calls API-76 to API-79 through a second `openapi-fetch` client typed by `any-city-schema.d.ts`.
- **Existing tests with the switch ON.** Every existing unit, API, contract, authz and web test passes with `FEATURES_DISABLED=!any_city_mode`, except four inventory tests that by design pin the OFF route set:
  - `tests/contract/test_openapi_contract.py::test_committed_contract_is_current`, `::test_every_mvp_endpoint_maps_to_exactly_one_operation` and `::test_no_path_outside_the_mvp_set`, which render or read the contract of the OFF app;
  - `tests/authz/test_ownership.py::test_tc_065_every_implemented_owned_route_is_in_the_matrix`, which walks the app through `unlisted_routes` (`tests/authz/route_matrix.py:212-219`).

  `test_route_inventory.py::test_tc_344_…` reads the committed OFF contract, so it is not affected.

  Their ON counterparts are `tests/contract/test_any_city_contract.py` (API-76 to API-79 exactly, `API-NN` summaries, no forbidden path word) and `tests/authz/test_any_city_routes.py` (TC-487). The switch-ON run deselects only these (IMP-730 records the exact command).
- **Test markers.** The pytest marker `live` already means "real provider, run only by `make live-smoke`" (`apps/api/pyproject.toml:95-96`), so it is not reused. New switch-ON backend tests use the marker **`any_city`**. They build the app with the switch ON through a settings override, and run in the normal suites with fake providers. The Playwright tag for switch-ON journeys is **`@live`** (no spec uses it today).
- **CI** (IMP-730). The existing jobs run with the switch OFF (the full suite). One added job runs `make test-api ARGS='-m any_city'`, `make test-unit ARGS='-m any_city'` and the E2E `@live` subset with `!any_city_mode` and `LIVE_DATA_PROVIDER=FAKE`. A one-time full switch-ON run of the existing suites (minus §3.4's deselected tests) is recorded for acceptance (d) (TC-490).

## 4. Data model: migration `0008_live_destinations`

### 4.1 Columns (all on `public.destinations`)

| Column | Type | Null, default | Rule |
| --- | --- | --- | --- |
| `data_tier` | text | not null, default `'curated'` | check in (`curated`, `live`) |
| `provider` | text | null | check in (`osm`); null for curated |
| `external_ref` | text | null | Nominatim OSM reference, `^[NWR][0-9]{1,12}$` (for example `R1234567`); null for curated |
| `imported_at` | timestamptz | null | time the last successful import finished |
| `expires_at` | timestamptz | null | `imported_at` + `LIVE_DATA_TTL_DAYS` |
| `import_status` | text | null | check in (`queued`, `running`, `completed`, `insufficient_data`, `failed`); null for curated |
| `import_failure_reason` | text | null | check in (`provider_unavailable`, `rate_limited`, `timeout`, `internal`); set only when `import_status = 'failed'` |
| `import_requested_by` | uuid | null | the user who started the current import; references the same user table as `trips.user_id`, `on delete set null` |
| `import_started_at` | timestamptz | null | set when the job takes the row (`running`) |
| `places_found` | integer | null | elements returned by Overpass, ≥ 0 |
| `places_usable` | integer | null | places that passed normalisation and dedupe, ≥ 0 |
| `nearby_city` | text | null | 1 to 120 characters; set only with `insufficient_data` |

Constraints:

- `ck_destinations_tier`: `(data_tier = 'curated' and provider is null and external_ref is null and import_status is null) or (data_tier = 'live' and provider is not null and external_ref is not null and import_status is not null and is_sample = false)`.
- `ck_destinations_failure`: `(import_status = 'failed') = (import_failure_reason is not null)` when `import_status` is not null.
- `ux_destinations_provider_ref`: unique `(provider, external_ref)` where `external_ref is not null`. This gives one row per OSM settlement, and duplicate resolves meet the same row.
- `ix_destinations_import_active`: on `(import_status)` where `import_status in ('queued', 'running')` (for the reaper).
- `ix_destinations_import_requester`: on `(import_requested_by, import_started_at)` where `import_requested_by is not null` (for the daily cap).

**Not changed:** no new table, no column on `places`, no change to `data_sources.source_type` (live guide sources use `other`) and no change to `ux_places_source_ref`. Live place uniqueness comes from the `external_ref` format of §6.3. Existing rows get `data_tier = 'curated'` from the default. RLS is already on for `destinations`, and browser roles keep their existing grants (0005); no policy changes.

### 4.2 Files and checks (IMP-721)

- `apps/api/migrations/sql/0008_live_destinations.sql`, `migrations/sql/down/0008_live_destinations.down.sql` (drops the indexes, constraints and columns), `migrations/versions/0008_live_destinations.py` (`revision = "0008"`, `down_revision = "0007"`).
- The ORM `Destination` model (`apps/api/app/db/models/places.py:31-56`) gains the columns in the same change.
- `app/core/health.py:34` becomes `"0008"`.
- The CI round trip (`upgrade head`, `downgrade base`, `upgrade head`) passes. `alembic heads` prints exactly one head, `0008 (head)`. The drift test passes with unchanged code (TC-463).

## 5. API (switch ON only; mounted under `/api/v1` with the bearer dependency)

The four routes live in `apps/api/app/places/live_router.py`. `create_app()` includes it only when the switch is ON (§3.3). Each operation's summary starts with its API ID. Request and response shapes are defined once in `app/places/live_schemas.py`. No new error code is added. `/destinations/search` is declared before `/destinations/{destination_id}`. No path contains a word forbidden by `test_openapi_contract.py:101-107`.

| ID | Method and path | Request | Response | Errors | Auth |
| --- | --- | --- | --- | --- | --- |
| API-76 | `GET /api/v1/destinations/search?q=` | `q`: 2 to 100 characters after trimming, control characters stripped | 200 `CitySearchOut` | 422 `VALIDATION_ERROR` (length), 429 `RATE_LIMITED` (`expensive_request` limiter), 503 `SERVICE_UNAVAILABLE` (geocoder down or breaker open) | bearer; reference data |
| API-77 | `POST /api/v1/destinations/resolve` | `ResolveCityIn {osm_ref}`: `^[NWR][0-9]{1,12}$`, taken from an API-76 result | 202 `LiveDestinationOut` when a new or refresh import is queued; 200 `LiveDestinationOut` when the destination already exists (any import state) | 404 `NOT_FOUND` (the geocoder knows no such object); 422 `VALIDATION_ERROR` (not a settlement; country or currency not supported, §6.1); 429 `RATE_LIMITED` (`LIVE_DAILY_IMPORTS_PER_USER` or `LIVE_DAILY_IMPORTS_GLOBAL` reached); 503 `SERVICE_UNAVAILABLE` | bearer; counted per user |
| API-78 | `GET /api/v1/destinations/{destination_id}/import` | path UUID | 200 `LiveDestinationOut` | 404 `NOT_FOUND` (unknown, or a curated destination) | bearer; reference data |
| API-79 | `GET /api/v1/destinations/{destination_id}` | path UUID | 200 `DestinationDetailOut` (curated or live) | 404 `NOT_FOUND` (unknown, or inactive and not live) | bearer; reference data |

Shapes:

- `CitySearchOut { results: CityCandidate[] }`, at most 8 results, settlements only (§6.1). `CityCandidate { osm_ref, name, display_name, region | null, country_code, lat, lon, kind: "city" | "town" | "village" | "municipality", destination_id | null, data_tier: "curated" | "live" | null }`. `destination_id` is set when the settlement already exists as a destination.
- `LiveDestinationOut { destination_id, slug, name, region | null, country_code, timezone, currency, data_tier: "live", import: ImportState }`. `ImportState { status, failure_reason | null, places_found | null, places_usable | null, nearby_city | null, started_at | null, imported_at | null, expires_at | null }`.
- `DestinationDetailOut` = every field of the API-06 item, plus `data_tier`, `imported_at | null` and `attribution: Attribution[]`, plus `import: ImportState | null`. `Attribution { source_name, licence, attribution_text, url }` comes from the `data_sources` rows the destination's active places and guide documents use.

Behaviour:

- **Destinations are reference data**, readable by every signed-in user, like API-06 and API-16 (authz `REFERENCE`). A live destination is shared by every user who resolves the same settlement. `import_requested_by` only counts the daily cap and is never returned.
- **API-06** returns `data_tier = 'curated'` only, unchanged in shape. Live destinations are reached through API-76, API-77 and API-79.
- **API-16 and API-17** work unchanged for an active live destination. A live destination stays `is_active = false` until its import is `completed`, so API-16 answers 404 before that, as today for an inactive destination.
- **Trip create (API-10).** It accepts a live destination only when it is active, and that only happens when the import is `completed`. The "supported destinations" list in the 422 message names curated destinations only (`apps/api/app/trips/domain.py:180-190`). IMD-128 is unchanged: the trip form takes the currency from `LiveDestinationOut.currency`.

## 6. Services and rules

### 6.1 Resolve (`app/places/live_service.py`, using `app/livedata/`)

- **Search (API-76).** The service calls `GeocodingProvider.search(q)` (Nominatim `/search`, `format=jsonv2`, `addressdetails=1`, `namedetails=1`, `limit=10`, `accept-language=en`). It keeps only results whose `addresstype` is `city`, `town`, `village` or `municipality`, at most 8. Results are cached in process for 24 hours (`SEARCH_CACHE_TTL_S = 86400`, code constant; at most 1,000 keys), keyed by the normalised query. Nominatim forbids type-ahead use, so the web calls API-76 only on an explicit search (button or Enter), never on each keystroke.
- **Resolve (API-77).** `osm_ref` is looked up again through `GeocodingProvider.lookup(osm_ref)` (Nominatim `/lookup`). The client never supplies coordinates, names or a country. Then:
  - The result must be a settlement, or 422 "Choose a city, town or village".
  - **Country table.** `app/livedata/countries.py` (pure, code) maps ISO 3166-1 alpha-2 → `{currency (ISO 4217), zones, capital}` for every ISO 3166-1 country (IMD-216). A single-zone country uses its zone. A multi-zone country lists `(zone, lat, lon)` representative points taken from the IANA tz database file `zone1970.tab` and committed as a static table, and the zone whose point is nearest the settlement's centre is chosen. Currency: any ISO 4217 code from the table; money keeps two decimals (IMD-05), so zero-decimal currencies show `.00` and three-decimal currencies are rounded to two (a recorded limitation; live places carry no prices). Only a country code missing from the table gives 422 "This country is not supported yet". Every zone in the table is checked with `zoneinfo` by a unit test (TC-464).
  - **Destination row.**
    - `slug`: `live-` + the ASCII transliteration of the name (NFKD, non-ASCII dropped, lower-case, runs of other characters → `-`), cut to 40 characters, + `-` + `external_ref` in lower case (for example `live-udaipur-r1234567`). If the transliteration is empty: `live-` + `external_ref`. The slug matches the existing slug check.
    - `name`: `namedetails["name:en"]`, else `name`.
    - `region`: the state.
    - `center`: the Nominatim point.
    - `bbox`: the Nominatim box, clipped to at most 0.25° of latitude and 0.25°/cos(lat) of longitude either side of the centre (about 28 km). A point-like box is widened to 0.05°.
    - `currency` and `timezone` from the country table. `data_tier = 'live'`, `provider = 'osm'`, `is_active = false`, `is_sample = false`.
  - **Existing row** (same `(provider, external_ref)`): 200 with its state. If it is `failed`, or past `expires_at` ("cut if late": refresh), the import is queued again with 202.
  - **Daily cap.** New imports by the same user started in the last 24 hours must be below `LIVE_DAILY_IMPORTS_PER_USER`, and all users together below `LIVE_DAILY_IMPORTS_GLOBAL`, counted from `destinations`. Otherwise 429 `RATE_LIMITED`. Resolving an existing destination does not count.

### 6.2 Import job (`app/places/live_jobs.py`)

- It copies the runner pattern of `app/generation/jobs.py` (submit → `asyncio.create_task`, strong references, `get_submit`-style dependency for tests), with its **own** semaphore (`IMPORT_MAX_CONCURRENT = 1`), timeout (`IMPORT_TIMEOUT_S = 300`) and staleness (`IMPORT_STALE_AFTER_S = 360`). These are code constants, as IMD-29.
- **Claim.** The job moves the row from `queued` to `running` with one `UPDATE … WHERE id = :id AND import_status = 'queued'`. If no row changes, another process holds it and the job ends. The unique `(provider, external_ref)` index stops duplicate destinations. The outbound limiter of §7.3 is per process; staging and production run one API task (IMD-12).
- **Reaper.** A lifespan task, started only with the switch ON, runs every 60 s. It sets `failed` / `timeout` on rows `running` for longer than `IMPORT_STALE_AFTER_S`, and on rows `queued` for longer than 10 minutes.
- **Steps.**
  1. Places: `PlacesProvider.fetch(bbox)`.
  2. Normalise, dedupe and cap (§6.3).
  3. Gate (§6.4).
  4. In one transaction through the places service: upsert the `OpenStreetMap` source, upsert places, deactivate places of this destination missing from the run (never delete), and set the counts.
  5. RAG: index the place documents and guides (§6.5) through `rag.service`. An embedding failure leaves the chunks without embeddings, gives `lexical_fallback` at generation and does not fail the import (IMD-112).
  6. Set `is_active = true`, `import_status = 'completed'`, `imported_at`, `expires_at`.
- **Errors.**
  - Provider timeout → `failed` / `timeout`.
  - HTTP 429, or the breaker open → `failed` / `rate_limited`.
  - Other provider errors or malformed bodies → `failed` / `provider_unavailable`.
  - Anything else → `failed` / `internal`, logged with the destination id only.
  - A failed import leaves earlier places of the destination as they were.
- **Import CLI** for the staging window (IMP-725): `python -m app.places.live_import --osm-ref R1234567` (also `--query "<city>"`, which takes the first settlement). It runs the same service synchronously and prints the counts and the final state. It is idempotent per `external_ref`.

### 6.3 Normalisation (`app/livedata/normalise.py`, pure)

- **Overpass query.** It is built only from the numeric bounding box and a fixed tag list; the user's text never reaches Overpass QL. `[out:json][timeout:<OVERPASS_TIMEOUT_S>][maxsize:67108864]`, then `nwr` elements with a `name` tag and one of these tags, then `out center tags;`.
  - `tourism` = `attraction`, `museum`, `gallery`, `viewpoint`, `zoo`, `aquarium`, `theme_park`.
  - `historic` = `monument`, `memorial`, `castle`, `fort`, `ruins`, `archaeological_site`, `palace`.
  - `leisure` = `park`, `garden`, `nature_reserve`.
  - `natural` = `beach`, `peak`.
  - `amenity` = `restaurant`, `cafe`, `fast_food`, `food_court`, `marketplace`, `theatre`, `arts_centre`, `place_of_worship`.
  - `shop` = `mall`, `department_store`.
- **Category, tags and default duration.** Accommodation (`stay`) is never produced.

  | OSM tags | `category` | `tags` (existing vocabulary only) | `typical_duration_min` |
  | --- | --- | --- | --- |
  | `tourism=museum` / `gallery` | museum | `history` / `art`, `indoor` | 90 |
  | `historic=*`, `tourism=attraction`, `tourism=viewpoint` | sight | `history`, `architecture`; `views` for viewpoints | 60 |
  | `leisure=park` / `garden` / `nature_reserve`, `natural=beach` / `peak` | nature | `outdoor`, `garden`, `walking`, `water`, `views` as applicable | 75 |
  | `amenity=restaurant` / `fast_food` / `food_court` / `cafe` | food | `lunch`, `dinner`; `cafe` and `tea` for cafés; `vegetarian` for `diet:vegetarian=yes` or `only` | 60 |
  | `amenity=marketplace`, `shop=mall` / `department_store` | shopping | `market`, `local` | 60 |
  | `amenity=theatre` / `arts_centre` | entertainment | `theatre`, `music`, `art`, `evening` | 120 |
  | `amenity=place_of_worship` | religious | `architecture`, `quiet` | 45 |
  | `tourism=zoo` / `aquarium` / `theme_park` | activity | `family`, `wildlife` | 120 |

  An element matching several rows takes the first row in table order. Unmapped elements are dropped and counted. The mapping only emits values of `Category` and `Tag` (`app/places/vocabulary.py`), so `Category(...)` and `Tag(...)` never fail (TC-465).
- **Fields.**
  - `external_ref` = `<destination external_ref>:<n|w|r><id>` (for example `R1234567:w987`). It is unique across destinations under the existing `(source_id, external_ref)` index.
  - `source` = the shared `data_sources` row `OpenStreetMap` (`source_type = 'osm_import'`, `licence = 'ODbL 1.0'`, the attribution text of §9.3, `url = https://www.openstreetmap.org/copyright`).
  - `verification_status = 'imported_osm'`; `price_min`, `price_max` and `price_currency` null; `price_label = 'unavailable'`; `hours_label = 'unavailable'` with no `place_opening_hours` rows; `hours_checked_on` null; `description` null (OSM free text is never stored).
  - `address` from `addr:*` tags, at most 150 characters; `website_url` only if `https://`; `booking_url` never set.
  - `step_free` true for `wheelchair=yes`, false for `wheelchair=no`, else null.
  - `indoor` true for museum, false for nature, else null; `child_friendly` null.
  - Coordinates from the element or its centre, which must be inside the clipped bbox.
- **Dedupe.** Two places of the same category whose names are equal after case folding, accent removal and whitespace collapse, within 75 m, are one place. The one with more of `wikidata`, `wikipedia`, `website` is kept, then the lower OSM id.
- **Cap.** At most `LIVE_MAX_PLACES = 300` places (code constant), ranked by richness: `wikidata` +3, `wikipedia` +2, `website` +1, `addr:*` +1, then OSM id. Food places take at most 35 % of the cap.

### 6.4 Minimum-places gate and "not enough data"

- The import is `insufficient_data` unless, after normalisation, there are at least `LIVE_MIN_USABLE_PLACES` usable places (default 40), including at least 6 `food` places and 12 non-food places. The 12 non-food places match the shortlist minimum of `app/generation/ranking.py:34-36`; the food places feed the lunch slots of `fallback_planner.py`.
- With `insufficient_data`, nothing is stored except the destination row, which stays inactive, with the counts and `nearby_city`. `nearby_city` is the most populous `place=city` node within 150 km from one extra Overpass query ("cut if late"), else the country's capital from the country table. It never names the settlement itself.
- The message the web shows: "We could not find enough places for {name} yet. Try {nearby_city}, a larger city nearby." The state is cached until `expires_at`.

### 6.5 Live guide corpus (`app/rag/live_guides.py`, called by the import job)

- `GuideSourceProvider.fetch(name, lat, lon)` asks Wikivoyage (and Wikipedia, "cut if late") through the MediaWiki API (`action=query`, `prop=extracts|info`, `explaintext=1`, `inprop=url`, `redirects=1`, a GeoData lookup when the title does not match, `maxlag=5`, serial requests). The result is plain-text sections with the page id, the revision id and the page URL.
- **Sections.** Each `==` section becomes its own guide document, `doc_key` = `guide:<destination slug>/<wikivoyage|wikipedia>-<pageid>-<section index>`. Sections named Sleep, Buy, Eat, Drink, Connect and Go next are skipped. A section is split at paragraph boundaries into documents of at most 6,000 characters (`rag/constants.py`).
- **Content rule.** Every paragraph that the existing guide content checks (`app/rag/guides.py:33-46`: currency amount, clock-time range, hours phrases) would flag is **dropped and counted**. A section shorter than 300 characters after dropping is skipped. A live import never fails on the strict gate. No price, hours or travel time from guide text can reach a passage.
- **Synthetic front matter.**
  - `title`: `<page title> — <section>`.
  - `source_name`: `Wikivoyage` or `Wikipedia`, two shared `data_sources` rows with `source_type = 'other'` and `licence = 'CC BY-SA 4.0'`.
  - `attribution_text`: §9.3.
  - `url`: the page URL.
  - `retrieved_on`: the import date.
  - `curated_by`: `not checked by the team (live import)`.

  The text is stored as fetched, apart from dropped paragraphs. Nobody rewrites it, and no tool writes guide prose. Amendment A1 §6.3's rule that members write real-destination guides applies to curated guides; for live guides it is replaced by this section.
- **Indexing.** The guide and place documents of the live destination are written through the same `_write` path as file guides, and embedded through `ModelProvider.embed_texts`. `index()` and the release task (`apps/api/scripts/release.sh:18-25`) index `data_tier = 'curated'` destinations only. `deactivate_missing` never touches live documents (`app/rag/service.py:196-211`).
- **Corpus cap (IMD-107).** At most 400 chunks per live destination (place documents first, then guide sections in page order). When active chunks of all destinations would pass 5,000, the oldest expired live destination's chunks are deactivated first. If that is not enough, the import stores places without guides and logs it. No ANN index is added.
- **Lexical guide passages ("cut if late").** When the destination has no embeddings, `app/rag/repository.py` may return up to 3 guide passages ranked by term overlap with the trip query, still marked `lexical_fallback`. If cut, live plans without embeddings cite no guide passage, as IMD-112 does today.

### 6.6 Generation for a live city

- The pipeline, the request builder, ranking, validation, repair and fallback are unchanged. Live places go into the shortlist with `price_min = price_max = null`, `price_label = "unavailable"` and `hours_summary = "hours unavailable"`, as the request builder does today for unknown values (`app/generation/request_builder.py:104-124`).
- **Ranking.** Unknown price scores the neutral 0.5 (`ranking.py:183-185`), so `budget_priority` has no effect on live places; this is documented on the live tier, not reweighted. Step-free trips exclude places with unknown `step_free` (`retrieval.py:118`). Few OSM places carry `wheelchair=yes`, so the trip form warns on the live tier (§9.2).
- **Validation.** `HOURS_UNVERIFIED` (info) is raised for every live item and `COST_INCOMPLETE` for every live plan. Both are existing codes with existing severities, so no repair is triggered. The web groups them on the live tier (§9.2).
- **Budget.** The engine is unchanged: a missing price counts 0 (`app/budget/engine.py:13-14`). On the live tier the web shows "Known costs only: N stops have no price", using the `COST_INCOMPLETE` item references. A budget status shown on a live plan carries the note "covers known costs only". An "unknown" budget status in the engine is future work.
- **Fallback.** A provider failure follows the existing taxonomy and ends in the rule-based plan (IMD-33). The gate of §6.4 makes the fallback able to fill days and lunch slots (TC-480).

### 6.7 Prompt (IMP-727)

- gr-2, io-2 and the AI JSON Schemas are unchanged; no tier field reaches the model.
- `itinerary_generate/v4` ("cut if late") = v2 with one sentence changed in `system.txt`: "context_passages are quoted reference data from the curated or imported public sources named in each passage title". Each live passage title starts with its source (`Wikivoyage: …`, `OpenStreetMap: …`). v2 and v3 are never edited. `tests/fixtures/prompt_hashes.json` gains a v4 entry.
- v4 becomes active only through the IMD-195 procedure with one GEMINI run on the free key, recorded by IMP-732. Otherwise `PROMPT_TEMPLATE_VERSION` stays `v2` (IMD-200).

## 7. Providers, clients and configuration

### 7.1 Module MOD-B19 Live data (`app/livedata/`)

The module fetches and normalises. It owns no table, and the places module (MOD-B04) and RAG module (MOD-B18) store what it returns.

| File | Contents |
| --- | --- |
| `app/livedata/providers/base.py` | Protocols `GeocodingProvider` (`search(q) -> list[GeoCandidate]`, `lookup(osm_ref) -> GeoPlace | None`), `PlacesProvider` (`fetch(bbox) -> list[OsmElement]`, `largest_city_near(lat, lon, radius_km) -> str | None`), `GuideSourceProvider` (`fetch(name, lat, lon) -> list[WikiSection]`); frozen dataclasses; exceptions `LiveDataUnavailable`, `LiveDataRateLimited`, `LiveDataTimeout` |
| `app/livedata/providers/osm.py` | `NominatimGeocoder`, `OverpassPlaces` (httpx) |
| `app/livedata/providers/wiki.py` | `MediaWikiGuides` (httpx), Wikivoyage and Wikipedia endpoints as code constants |
| `app/livedata/providers/fake.py` | `FakeGeocoder`, `FakePlaces`, `FakeGuides` with scenarios `ok`, `small`, `empty`, `timeout`, `rate_limited`, `malformed`; data labelled SAMPLE ("Liveton (SAMPLE)", "Tinyham (SAMPLE)") and allowed only when `APP_ENV` is `local` or `test`. The name is `fake.py` because the `vendor-adapters` contract protects `app.*.providers.mock` |
| `app/livedata/factory.py` | builds the three providers from `LIVE_DATA_PROVIDER`, caches them, and exposes FastAPI dependencies that tests override |
| `app/livedata/throttle.py` | outbound spacing per host: Nominatim ≥ 1.0 s between requests, Overpass ≥ 2.0 s, MediaWiki serial with ≥ 0.2 s |
| `app/livedata/normalise.py`, `app/livedata/countries.py` | pure (§6.1, §6.3) |

Real adapters follow the ORS client conventions (`app/routing/client.py`):

- one attempt, no retry;
- a timeout from settings;
- base URLs from settings (Nominatim, Overpass) or code constants (MediaWiki);
- every failure becomes a domain exception with a safe message;
- no response body or query text in logs;
- a `User-Agent: <WIKI_USER_AGENT>` header on every request.

Nominatim and Overpass each get a `CircuitBreaker` from `app/ai/breaker.py` (5 consecutive transient failures → 60 s open; a 429 → 15 minutes open). An open breaker gives 503 on API-76 and API-77, and `failed` / `rate_limited` for an import.

### 7.2 Environment variables (add to `Settings`, `.env.example` and the staging template; IMP-722, IMP-733)

| Name | Type, default | Rule |
| --- | --- | --- |
| `LIVE_DATA_PROVIDER` | `FAKE` or `LIVE`, default `FAKE` | `FAKE` is refused at start-up when `APP_ENV` is staging or production and the switch is ON |
| `WIKI_USER_AGENT` (existing, `core/config.py:86-88`) | str, default empty | Sent on every Nominatim, Overpass and MediaWiki request. Required (not empty, not a `<placeholder>`) at start-up when `LIVE_DATA_PROVIDER=LIVE`. Contains the app name and a team contact, for example `AITravelPlanner/1.0 (contact: <team address>)` |
| `NOMINATIM_BASE_URL` | str, default `https://nominatim.openstreetmap.org` | `https://` only |
| `OVERPASS_BASE_URL` | str, default `https://overpass-api.de/api/interpreter` | `https://` only |
| `NOMINATIM_TIMEOUT_S` | float > 0, default 10 | |
| `OVERPASS_TIMEOUT_S` | float > 0, default 90 | also written into the query's `[timeout:]` |
| `MEDIAWIKI_TIMEOUT_S` | float > 0, default 10 | |
| `LIVE_MIN_USABLE_PLACES` | int > 0, default 40 | §6.4 |
| `LIVE_DATA_TTL_DAYS` | int > 0, default 30 | §4.1 `expires_at` |
| `LIVE_DAILY_IMPORTS_PER_USER` | int > 0, default 5 | §6.1 |
| `LIVE_DAILY_IMPORTS_GLOBAL` | int > 0, default 50 | §6.1 |

None of these is a secret: no key is needed for Nominatim, Overpass or MediaWiki. The values reach staging as plain task-definition environment, which IMD-102 allows for non-secrets, set by the AWS account owner. No new `NEXT_PUBLIC_*` name is added.

### 7.3 Etiquette and limits

| Service | Rule followed |
| --- | --- |
| Nominatim (public instance) | At most 1 request per second per process; identifying User-Agent; search results cached 24 h and resolved settlements stored; no type-ahead; no bulk geocoding |
| Overpass API (public instance) | One places query per import (plus one nearby-city query when the gate fails); `[timeout:]` and `[maxsize:]` set; ≥ 2 s spacing; a 429 opens the breaker for 15 minutes |
| MediaWiki API | Serial requests, `maxlag=5`, identifying User-Agent, at most 2 pages per import |

These usage rules are stated from the source proposal and the team's knowledge, and are **Unverified** in this amendment. The IMP-723 owner reads each service's current usage policy before the first call outside tests, and records the date in the part record (§16).

### 7.4 Fakes in tests

Unit, API, contract, authz and E2E tests use `LIVE_DATA_PROVIDER=FAKE` or override the factory dependency. Client tests use `respx` with recorded JSON in `tests/fixtures/livedata/`. No test opens a socket to the new hosts (§11).

## 8. Code layout and import contracts

### 8.1 New and changed paths

| Path | Card |
| --- | --- |
| `apps/api/migrations/sql/0008_live_destinations.sql`, `sql/down/0008_live_destinations.down.sql`, `versions/0008_live_destinations.py`; `app/db/models/places.py`; `app/core/health.py` | IMP-721 |
| `app/core/flags.py`, `app/core/config.py`, `app/main.py` (conditional router and reaper), `app/openapi_export.py`, `Makefile` (`openapi`, `openapi-check`), `.env.example` | IMP-722 |
| `app/livedata/` (providers, factory, throttle), `.importlinter`, `tests/conftest.py` (`PROVIDER_HOSTS`), `tests/fixtures/livedata/` | IMP-723 |
| `app/livedata/normalise.py`, `app/livedata/countries.py` | IMP-724 |
| `app/places/live_router.py`, `live_schemas.py`, `live_service.py`, `live_jobs.py`, `live_import.py`, `repository.py`; `app/places/service.py` (API-06 curated filter); `app/trips/domain.py` (curated list in the message); `contracts/openapi.any-city.v1.json` | IMP-725 |
| `app/rag/live_guides.py`, `app/rag/service.py` (curated-only indexing), `app/rag/repository.py` (lexical guide passages, "cut if late"), `apps/api/scripts/release.sh` | IMP-726 |
| `app/ai/prompts/templates/itinerary_generate/v4/`, `tests/fixtures/prompt_hashes.json` | IMP-727 |
| `apps/web/lib/flags.ts`, `apps/web/lib/api/any-city-schema.d.ts`, `apps/web/lib/api/anyCityClient.ts`, `apps/web/lib/api/queries.ts`, `apps/web/components/trips/CitySearch.tsx`, `ImportProgress.tsx`, `TripDetailsStep.tsx`, `PlacesStep.tsx` | IMP-728 |
| `apps/web/components/labels/TierBadge.tsx`, `components/labels/SourceBadge.tsx`, `components/labels/LiveAttribution.tsx`, explore, itinerary and costs pages, `components/costs/CostBreakdown.tsx`, warnings panel | IMP-729 |
| `apps/web/e2e/live-city.spec.ts`, `.github/workflows/ci.yml` and `e2e.yml` (switch-ON job) | IMP-730 |

### 8.2 Import contracts (`apps/api/.importlinter`)

- **New contract `livedata-isolation`.** `httpx` may be imported in `app.livedata.providers.osm` and `app.livedata.providers.wiki` only, among `app.livedata`, `app.places` and `app.rag`. Existing httpx users stay as they are.
- `app.livedata.normalise` and `app.livedata.countries` join the `pure-domain` list.
- `app.livedata` may not import `app.generation`, `app.itinerary`, `app.budget`, `app.validation`, `app.trips` or `app.db`; it returns data, and the places and RAG services store it.
- `make imports` reports `Contracts: 7 kept, 0 broken.`

## 9. Web (switch ON only; `isEnabled("any_city_mode")`)

### 9.1 Trip form (IMP-728)

- The destination step keeps the existing `<select>` over API-06 (`TripDetailsStep.tsx:140-153`; the E2E pick "Sampleton (sample)" still works). Below it, a "Any city (live data)" search field with a Search button calls API-76 on submit only.
- Results are a list of buttons ("Udaipur, Rajasthan, India · city"). Choosing one calls API-77, then polls API-78 with the generation delays 2 / 3 / 4 / 5 s, stopping at `completed`, `insufficient_data` or `failed`.
- **States:**
  - "Building your city: finding places…" (`queued`, `running`);
  - "Ready: {places_usable} places from OpenStreetMap" (`completed`);
  - "We could not find enough places for {name} yet. Try {nearby_city}, a larger city nearby." with a button that searches `nearby_city` (`insufficient_data`);
  - "We could not reach the map data service. Try again in a few minutes." (`failed`; `rate_limited` adds "The service is busy.");
  - 422 and 503 messages from the error envelope.
- The currency is set from `LiveDestinationOut.currency` (IMD-128). The places step stays disabled until `completed`.
- Hint under the field: "Live data comes from OpenStreetMap and Wikivoyage. It is not checked by our team: opening hours and prices are unknown."

### 9.2 Labels, badges and attribution (IMP-729)

| Where | Live tier shows |
| --- | --- |
| Explore, itinerary and costs page header | `TierBadge` "Live data" (curated destinations: "Curated"; the SAMPLE label stays as today), with the hint text of §9.1 |
| Each place and item | `SourceBadge` "OpenStreetMap"; "Price unknown" and "Hours unknown" chips for `price_label` / `hours_label = 'unavailable'` on live places (curated places keep "Unavailable") |
| Item notes with citations | Existing `ItemSources` list; Wikivoyage and Wikipedia sources show their licence |
| Warnings panel | `HOURS_UNVERIFIED` grouped into one line, "Opening hours unknown for N stops" (severity stays info) |
| Costs page | "Known costs only: N stops have no price"; the budget status carries "covers known costs only" |
| Trip form, step-free required | "Few live places have step-free information; your list may be short" |
| Footer of explore, itinerary and costs (`LiveAttribution`) | the attribution texts of §9.3 from API-79 `attribution` |
| Landing page (`app/(public)/page.tsx:43-45`) | Unchanged while the switch is OFF; with it ON, "Plans are drafts built from curated or live open data" |

All new components meet `docs/guides/ui-design.md`: keyboard reachable, visible focus, labels in names, no colour-only meaning, 360 px without overflow, and axe with no serious or critical finding.

### 9.3 Attribution texts (exact)

- OpenStreetMap: "Place data © OpenStreetMap contributors, available under the Open Database Licence (ODbL)", linking to `https://www.openstreetmap.org/copyright`.
- Wikivoyage: "Guide text from Wikivoyage ({page title}), by its contributors, under CC BY-SA 4.0; excerpts, some sections left out", linking to the page URL and `https://creativecommons.org/licenses/by-sa/4.0/`.
- Wikipedia: the same, with "Wikipedia".
- Search results (API-76) show "Search by Nominatim · © OpenStreetMap contributors".

## 10. Licences

| Source | Licence | What we do |
| --- | --- | --- |
| OpenStreetMap data (Nominatim, Overpass) | ODbL 1.0 | Live places are a derivative database kept inside the app. Every screen showing them carries the §9.3 attribution. The database is not offered for download; if it ever is, it must be offered under ODbL |
| Wikivoyage, Wikipedia text | CC BY-SA 4.0 | Stored with page URL, licence and attribution. Changes (sections and paragraphs left out) are stated in the attribution. Passages are shown with their link |
| OpenFreeMap tiles | as today (§9.1 of the specification) | unchanged |

Firecrawl, Google Maps and Google Search are cut (§1.2), so no Google content is stored.

## 11. Security and privacy (adds to §13 of the specification and A1 §11)

- **Untrusted text.** OSM names, addresses and Wikivoyage or Wikipedia text are untrusted. They reach the model only as quoted passage or shortlist data. An instruction inside them changes neither the place set nor the costs (TC-481, TC-488, extending the TC-357 corpus). Names are stored as text, never rendered as HTML.
- **Query safety.** The search text goes only to Nominatim, URL-encoded, without the user's identity. Overpass queries are built from numbers and a fixed tag list (TC-469). Logs keep result counts and destination ids, never the query text.
- **Links.** `website_url` and source URLs are `https://` only, and open with `noopener noreferrer`.
- **Socket guard.** `PROVIDER_HOSTS` (`apps/api/tests/conftest.py:27-33`) adds `nominatim.openstreetmap.org`, `overpass-api.de`, `*.wikivoyage.org` and `*.wikipedia.org`, and the host of any configured mirror.
- **Abuse.** API-76 uses the existing `expensive_request` limiter. API-77 has the daily caps of §6.1. Imports are serialised (one at a time).
- **Authorization.** Every new route requires a bearer token. Destinations are reference data, and no route returns `import_requested_by`. The route checks are in TC-487.
- **Account deletion.** `import_requested_by` is set to null.

## 12. Cards (0 points each, outside the contribution plan; IDs IMP-721 to IMP-733 are unused in `TASK_REGISTER.md`)

Every card has the specification card shape:

- every commit is authored and committed by its part's owner;
- one branch per batch (IMD-215), with one part record per part (`docs/progress/parts/IMP-7NN-<part-slug>.md`);
- `make check` green, plus `make e2e` where a journey is touched;
- the switch OFF must keep every existing test unchanged, and §3.4 governs the switch-ON exceptions.

### Batch C1: backend and database (23 November: IMP-721 to IMP-724; 24 November: IMP-725)

#### IMP-721 Migration 0008: live destination columns

- **Owners and parts:** Malhar — migration SQL, down file and Alembic revision (lead); Jeel — ORM model, `MIGRATION_HEAD`, migration tests. 0 points.
- **Prerequisites:** IMD-210, IMD-215, this amendment §4.
- **Files:** §8.1 IMP-721 row; `apps/api/tests/api/test_live_destinations_schema.py` (create).
- **Steps:**
  1. Write the SQL of §4.1 with its constraints and indexes, and the down file.
  2. Add revision `0008`.
  3. Add the ORM columns.
  4. Set `MIGRATION_HEAD = "0008"`.
  5. Write tests: the CHECKs reject a live row without `external_ref`, a curated row with an import status, a live SAMPLE row, a failed row without reason, and a duplicate `(provider, external_ref)`; existing rows read `curated`.
- **Acceptance:**
  - The CI round trip passes, and `alembic heads` prints one head.
  - `test_schema_drift.py` passes unchanged.
  - Every existing test passes.
- **Tests:** TC-463 — `make db-up && make test-api ARGS='-k live_destinations_schema or drift'`.
- **Evidence:** the part record with the `alembic heads` line and the round-trip job link.

#### IMP-722 Switch `any_city_mode`, settings and the any-city contract

- **Owners and parts:** Het — whole card. 0 points.
- **Prerequisites:** IMP-721.
- **Files:** §8.1 IMP-722 row; `apps/api/tests/unit/core/test_any_city_switch.py`, `tests/contract/test_any_city_contract.py` (create).
- **Steps:**
  1. Add `DEFAULT_OFF` and the token rule (§3.1).
  2. Add the settings of §7.2 and the start-up checks.
  3. Make `create_app()` include the any-city router and the import reaper only when ON.
  4. Make the OpenAPI export write the any-city contract and web types; extend `openapi-check`.
  5. Document the token in `.env.example`.
- **Acceptance:**
  - OFF: `contracts/openapi.v1.json` and `schema.d.ts` unchanged; the any-city paths answer 404 `NOT_FOUND`.
  - ON: API-76 to API-79 present.
  - `test_config.py` and `flags.test.ts` unchanged and passing.
  - Start-up refuses `LIVE_DATA_PROVIDER=FAKE`, or an empty or placeholder `WIKI_USER_AGENT` with `LIVE`, in staging or production with the switch ON.
- **Tests:** TC-460, TC-461, TC-462 — `make test-unit ARGS='-k any_city_switch'`, `make test-contract ARGS='-k any_city'`, `make openapi-check`.
- **Evidence:** the part record; `make check` lines.

#### IMP-723 Live-data providers: Nominatim, Overpass and MediaWiki clients, fakes, throttle and isolation

- **Owners and parts:** Manal — protocols, real adapters, fakes and factory (lead); Junaid — throttle, socket-guard hosts, `livedata-isolation` contract, query-safety tests, and the usage-policy check of §7.3. 0 points.
- **Prerequisites:** IMP-722.
- **Files:** §8.1 IMP-723 row; `apps/api/tests/unit/livedata/test_clients.py`, `test_fakes.py`, `test_throttle.py` (create).
- **Steps:**
  1. Write the protocols and the exceptions.
  2. Write the httpx adapters on the ORS conventions, with the User-Agent header.
  3. Write the fakes with SAMPLE data and scenarios.
  4. Add the factory and the dependencies.
  5. Add the throttle and the breakers.
  6. Add the hosts to `PROVIDER_HOSTS`.
  7. Add the import contract.
  8. Record each service's usage policy and the date read.
- **Acceptance:**
  - Each client sends the User-Agent, makes one attempt and maps every failure to a domain exception without logging bodies.
  - The Overpass query contains no user text.
  - The throttle spaces calls.
  - The fakes cover every scenario.
  - `make imports` prints `Contracts: 7 kept, 0 broken.`
- **Tests:** TC-468, TC-469, TC-470, TC-471 — `make test-unit ARGS='-k livedata'`, `make imports`.
- **Evidence:** the part record with the policy dates.

#### IMP-724 Normaliser, country table and minimum-places gate

- **Owners and parts:** Jeel — normaliser, dedupe, cap and gate (lead); Malhar — country table, time-zone choice, bbox clipping and the capital fallback. 0 points.
- **Prerequisites:** IMP-723 (dataclasses).
- **Files:** `app/livedata/normalise.py`, `app/livedata/countries.py`; `apps/api/tests/unit/livedata/test_normalise.py`, `test_countries.py` (create).
- **Steps:**
  1. Write the mapping table of §6.3.
  2. Write the field rules.
  3. Write dedupe and cap.
  4. Write the gate of §6.4.
  5. Write the country table for every ISO 3166-1 country with a currency and at least one zone; zones and representative points from `zone1970.tab` (IMD-216).
  6. Add bbox clipping.
- **Acceptance:**
  - Only vocabulary values are produced, and `stay` never is.
  - Price and hours are always unknown.
  - Dedupe and cap are deterministic.
  - The gate gives `insufficient_data` with a nearby city or capital.
  - Every zone passes `zoneinfo`.
  - Every country has a currency and a zone; money stays two decimals (IMD-05).
- **Tests:** TC-464, TC-465, TC-466, TC-467 — `make test-unit ARGS='-k normalise or countries'`.
- **Evidence:** the part record.

#### IMP-725 Live import service, job runner, API-76 to API-79 and trip rule

- **Owners and parts:** Het — service, routes, schemas, API-06 filter and trip-create message (lead); Manal — job runner, claim, reaper, repository writes and the import CLI. 0 points.
- **Prerequisites:** IMP-721 to IMP-724.
- **Files:** §8.1 IMP-725 row; `apps/api/tests/api/test_live_destinations.py`, `test_live_import_jobs.py` (create).
- **Steps:**
  1. Write the resolve flow of §6.1, including the search cache and the daily caps.
  2. Write the import job of §6.2, storing through the places service and indexing through the RAG service.
  3. Add routes API-76 to API-79 with `API-NN` summaries.
  4. Add the API-06 curated filter.
  5. Add the trip-create message.
  6. Write the import CLI.
  7. Run `make openapi`.
- **Acceptance:**
  - Search, resolve, status and detail behave as §5.
  - An import with the fake `ok` scenario completes and activates the destination, and a trip and a MOCK generation succeed.
  - `small` gives `insufficient_data`; `timeout` and `rate_limited` give `failed` with the reason.
  - Stale imports are reaped.
  - A second resolve returns the same destination.
  - With the switch OFF nothing changes.
- **Tests:** TC-472 to TC-477, TC-479 — `make test-api ARGS='-m any_city'`.
- **Evidence:** the part record; the any-city contract diff.

### Batch C2: AI and frontend (25 November; the web parts may start on 24 November against the fakes and the any-city contract)

#### IMP-726 Live guide corpus from Wikivoyage and Wikipedia

- **Owners and parts:** Nidhi — whole card. 0 points.
- **Prerequisites:** IMP-723, IMP-725.
- **Files:** §8.1 IMP-726 row; `apps/api/tests/unit/rag/test_live_guides.py`, `tests/api/test_live_guides_index.py` (create).
- **Steps:**
  1. Fetch the sections through `GuideSourceProvider`.
  2. Apply the section split and the content-rule dropping.
  3. Build the synthetic front matter.
  4. Write and embed through the existing path.
  5. Make indexing and the release task curated-only.
  6. Add the corpus cap.
  7. Add lexical guide passages ("cut if late").
- **Acceptance:**
  - No price, clock-time or hours phrase reaches a stored chunk.
  - The `doc_key` format holds.
  - A release index run leaves live documents untouched.
  - An embedding failure leaves the import completed with `lexical_fallback` at generation.
- **Tests:** TC-478 — `make test-unit ARGS='-k live_guides'`, `make test-api ARGS='-k live_guides'`.
- **Evidence:** the part record.

#### IMP-727 Prompt v4 and live-plan generation checks

- **Owners and parts:** Manya — whole card. 0 points.
- **Prerequisites:** IMP-725, IMP-726.
- **Files:** §8.1 IMP-727 row; `apps/api/tests/unit/generation/test_live_requests.py`, `tests/api/test_live_generation.py` (create).
- **Steps:**
  1. Request-builder tests for live places (null prices, `unavailable` labels, hours unavailable).
  2. MOCK and rule-based generation for a live city.
  3. The provider-failure path (MOCK `timeout`, `quota`) for a live city.
  4. Template v4 and its hash ("cut if late").
  5. The ranking note of §6.6 in the part record.
- **Acceptance:**
  - Live plans contain stored place IDs only.
  - No item has a price or hours from the model.
  - `COST_INCOMPLETE` is present.
  - The provider failure yields the rule-based plan.
- **Tests:** TC-479, TC-480, TC-481 — `make test-unit ARGS='-k live_requests or registry'`, `make test-api ARGS='-k live_generation'`.
- **Evidence:** the part record.

#### IMP-728 Web: city search, import progress and the switch

- **Owners and parts:** Manasvi — whole card. 0 points.
- **Prerequisites:** IMP-722 (any-city contract and web types); IMP-725 for the live run.
- **Files:** §8.1 IMP-728 row; `apps/web/tests/unit/trips/CitySearch.test.tsx`, `ImportProgress.test.tsx`, `apps/web/tests/unit/lib/flags.default-off.test.ts` (create).
- **Steps:**
  1. Add the `DEFAULT_OFF_FEATURES` token rule.
  2. Add the any-city client and the query hooks (`useCitySearch`, `useResolveCity`, `useImportStatus`).
  3. Build the search field with submit-only search, the results list, resolve, progress, and the states and copy of §9.1.
  4. Set the currency.
  5. Lock the places step.
- **Acceptance:**
  - OFF: no control is rendered and no request is made.
  - ON: every state of §9.1 renders.
  - Search calls happen only on submit.
  - Keyboard and axe pass, and 360 px does not overflow.
- **Tests:** TC-482, TC-483 — `make test-web ARGS='CitySearch ImportProgress flags'`.
- **Evidence:** the part record with screenshots at 360 and 1280 px.

#### IMP-729 Web: tier label, source badges, unknown chips and attribution

- **Owners and parts:** Krrish — whole card. 0 points.
- **Prerequisites:** IMP-725 (API-79); IMP-728.
- **Files:** §8.1 IMP-729 row; `apps/web/tests/unit/labels/TierBadge.test.tsx`, `LiveAttribution.test.tsx`, `apps/web/tests/unit/costs/CostBreakdown.live.test.tsx` (create).
- **Steps:** build the §9.2 table and the exact texts of §9.3.
- **Acceptance:**
  - Live pages show the tier badge, source badges, "Price unknown" and "Hours unknown", the grouped hours warning, the known-costs note and the attribution footer.
  - Curated and SAMPLE pages are unchanged.
  - Axe and keyboard checks pass.
- **Tests:** TC-484, TC-485 — `make test-web ARGS='TierBadge LiveAttribution CostBreakdown'`.
- **Evidence:** the part record with screenshots.

### Batch C3: tests, evaluation and documents (26 to 27 November)

#### IMP-730 E2E `@live`, the CI switch-ON job and the ON/OFF record

- **Owners and parts:** Krrish — whole card. 0 points.
- **Prerequisites:** IMP-725, IMP-728, IMP-729.
- **Files:** `apps/web/e2e/live-city.spec.ts` (create); `.github/workflows/ci.yml`, `e2e.yml` (modify: one switch-ON job); `docs/test-reports/any-city-switch.md` (create).
- **Steps:**
  1. Spec E2E-10, tagged `@live`: search the fake "Liveton (SAMPLE)" → resolve → progress → trip → generate → itinerary with the "Live data" badge, OSM badges, "Price unknown" and the attribution.
  2. Spec: "Tinyham (SAMPLE)" → not-enough-data with the nearby city.
  3. Spec: the 360 px project.
  4. Add the CI job of §3.4.
  5. Run the full existing suites once with the switch ON (minus §3.4's deselected tests) and once OFF; record the result lines.
- **Acceptance:**
  - The `@live` specs pass three runs in a row.
  - OFF and ON results are recorded with their exact lines.
  - The existing E2E suite is unchanged.
- **Tests:** TC-486, TC-490 — `make e2e ARGS='--grep @live'`.
- **Evidence:** run links in the test report.

#### IMP-731 Security: any-city authorization, injection corpus and etiquette review

- **Owners and parts:** Junaid — whole card. 0 points.
- **Prerequisites:** IMP-725, IMP-726.
- **Files:** `apps/api/tests/authz/test_any_city_routes.py` (create); `apps/api/tests/fixtures/injection_corpus.json`, `tests/api/test_injection.py` (add cases); `docs/test-reports/security-any-city.md` (create).
- **Steps:**
  1. Authz with the switch ON: 401 without a token on API-76 to API-79; reference access for any user; `import_requested_by` never returned; daily cap per user.
  2. Hostile OSM names and wiki paragraphs in the injection corpus.
  3. A review of §7.3 and §11 against the code.
- **Acceptance:**
  - Every new route is covered.
  - An injected instruction changes neither the place set nor the costs.
  - The review is recorded.
- **Tests:** TC-487, TC-488 — `make test-authz ARGS='-k any_city'`, `make test-api ARGS='-k injection'`.
- **Evidence:** the security report addendum.

#### IMP-732 Evaluation `trips/live-v1`

- **Owners and parts:** Manya — whole card. 0 points.
- **Prerequisites:** IMP-727.
- **Files:** `eval/datasets/trips/live-v1/` (create: cases with unknown prices and hours and OSM-like SAMPLE names, `manifest.json`); `eval/reports/live-v1-*.md` (create); `.github/workflows/ci.yml` (add the MOCK live dataset run).
- **Steps:**
  1. Build the dataset (6 to 10 cases); `trips/v1` is never edited.
  2. Run MOCK and RULE_BASED.
  3. Report validity, the hallucinated-place rate (0 by construction, measured), the unknown-price share, citation coverage and latency.
  4. Compare with `trips/v1` ("cut if late").
  5. One GEMINI run for v4 only if quota allows (IMD-195, rule 16).
- **Acceptance:** the report is committed with its run metadata; every number comes from `eval/results/` or `eval/reports/`.
- **Tests:** TC-489 — `make eval PROVIDER=MOCK DATASET=trips/live-v1`.
- **Evidence:** the report.

#### IMP-733 Documents: acceptance record, guides, report addendum and environment

- **Owners and parts:** Nidhi — acceptance record (ACC-20 to ACC-23 sheet with "pending (Kirtan staging window)"), user-guide and final-report addenda (built and enabled, or built but disabled, IMD-215), the staging import runbook (lead); Kirtan — environment and SSM documentation only (deployment-guide addendum for §7.2 values, the switch token and the pre-import CLI). 0 points.
- **Prerequisites:** IMP-725 to IMP-732.
- **Files:** `docs/acceptance/any-city.md`, `docs/guides/any-city-staging.md` (create); `docs/guides/user-guide.md`, `docs/guides/deployment.md`, `docs/final-report.md` (add sections).
- **Steps:** write the files; record the switch state of the release candidate.
- **Acceptance:** the documents match the code at the cutoff; HUMAN and staging results stay "pending (owner)" until done.
- **Tests:** TC-491 (manual, staging window).
- **Evidence:** the part records.

## 13. Requirements, tests and acceptance (new IDs)

### 13.1 Catalogue item and requirements (adds to §2.1 to §2.3 of the specification and A1 §9)

| ID | Statement |
| --- | --- |
| C-14 | Any-city mode (switch `any_city_mode`, IMD-210) |
| FR-141 | City search: a signed-in user searches a city name and sees up to 8 settlements (API-76) |
| FR-142 | Live destination: choosing a settlement creates or reuses a live destination and imports its places in the background, with visible progress and a "not enough data" outcome naming a larger nearby city (API-77, API-78) |
| FR-143 | Tier and attribution: every live destination, place and item shows the live tier, its source and the licence attribution (API-79) |
| FR-144 | Unknown values: live places have no price and no opening hours; the app shows "Price unknown" and "Hours unknown" and never takes either from the model or from guide text |
| FR-145 | Live guide corpus: Wikivoyage (and Wikipedia) sections enter the RAG store with licence and attribution, without prices, hours or travel times |
| NFR-051 | Import time: a live import of a city with up to 300 places completes within 120 s at the 95th percentile on staging (proposed; replaced with the measured value) |
| NFR-052 | Provider etiquette: at most 1 Nominatim request per second per process, identifying User-Agent on every call, cached search results, no type-ahead |

### 13.2 Test cases (add to §13.3; TC-460 to TC-491)

| ID | What it proves | Card | Level |
| --- | --- | --- | --- |
| TC-460 | `any_city_mode` is OFF by default and with any list lacking `!any_city_mode`; ON with the token; an explicit `any_city_mode` wins; existing switch parsing unchanged | IMP-722, IMP-728 | Unit |
| TC-461 | OFF: any-city paths answer 404 `NOT_FOUND` and `openapi.v1.json` is unchanged; ON: API-76 to API-79 exactly, with `API-NN` summaries and no forbidden path word; the any-city contract is current | IMP-722 | Contract + API |
| TC-462 | Start-up refuses `LIVE_DATA_PROVIDER=FAKE`, or `LIVE` with an empty or placeholder `WIKI_USER_AGENT`, in staging and production with the switch ON | IMP-722 | Unit |
| TC-463 | Migration 0008 applies and survives the round trip; one Alembic head; the drift test passes unchanged; the CHECKs and the unique index reject the invalid rows of IMP-721 | IMP-721 | API |
| TC-464 | The country table gives currency and zone for every country; every zone loads in `zoneinfo`; multi-zone choice by nearest `zone1970.tab` point; a country code missing from the table is refused; money stays two decimals (IMD-05) | IMP-724 | Unit |
| TC-465 | OSM tags map to vocabulary categories, tags and durations; unmapped elements are dropped and counted; `stay` never appears; price and hours are always unknown; description is null; only `https` websites | IMP-724 | Unit |
| TC-466 | Dedupe merges same-name places within 75 m deterministically; the cap keeps 300 by richness with the food share | IMP-724 | Unit |
| TC-467 | The gate gives `insufficient_data` below the thresholds, with a nearby city or the capital, never the settlement itself | IMP-724, IMP-725 | Unit + API |
| TC-468 | The Nominatim client sends the User-Agent, makes one attempt, maps failures to domain exceptions without logging bodies; the throttle keeps ≥ 1 s between calls | IMP-723 | Unit (respx) |
| TC-469 | The Overpass query holds only numbers and the fixed tag list; city text never appears; 429 and timeout map to `rate_limited` and `timeout` | IMP-723 | Unit (respx) |
| TC-470 | The MediaWiki client sends the User-Agent and `maxlag`, requests serially, and returns no sections for a missing page | IMP-723 | Unit (respx) |
| TC-471 | The fakes cover `ok`, `small`, `empty`, `timeout`, `rate_limited`, `malformed`; the factory picks FAKE in local and test; the socket guard blocks the new hosts | IMP-723 | Unit |
| TC-472 | API-76 validates `q`, returns settlements only, serves a repeated query from the cache, answers 503 when the geocoder is down and 429 when the limiter trips | IMP-725 | API |
| TC-473 | API-77: a new settlement gives 202 `queued`; a repeat gives 200 with the same destination; the daily caps give 429; a non-settlement or unsupported country gives 422; an unknown reference gives 404 | IMP-725 | API |
| TC-474 | The import job goes `queued` → `running` → `completed`, stores labelled places, activates the destination; a repeat import is idempotent and deactivates missing places without deleting | IMP-725 | API |
| TC-475 | Provider timeout and rate limit give `failed` with the reason and an inactive destination; the reaper fails stale imports; the claim lets only one job run per destination | IMP-725 | API |
| TC-476 | API-78 and API-79 return the import state, the tier and the attribution for live and curated destinations; API-06 lists curated destinations only and keeps its shape (TC-069 unchanged) | IMP-725 | API |
| TC-477 | A trip can be created for a completed live destination with its currency (IMD-128); a destination still importing is refused with a message listing curated destinations only | IMP-725 | API |
| TC-478 | Live guides are split by section, flagged paragraphs are dropped and counted, front matter carries CC BY-SA attribution, `doc_key` follows §6.5; the release index skips live destinations | IMP-726 | Unit + API |
| TC-479 | A MOCK and a rule-based plan for a live city use stored place IDs only; items have no price and no hours from the model; `COST_INCOMPLETE` and `HOURS_UNVERIFIED` are raised | IMP-725, IMP-727 | API |
| TC-480 | A provider failure (MOCK `timeout`, `quota`) for a live city ends in the labelled rule-based plan | IMP-727 | API |
| TC-481 | Template v4 is hashed; live passages are quoted data with source-prefixed titles; v2 and v3 are unchanged | IMP-727 | Unit |
| TC-482 | The web switch is OFF by default; with it OFF no any-city control renders and no any-city request is made | IMP-728 | Component |
| TC-483 | City search calls API-76 only on submit; results, resolve, every import state and the not-enough-data message with its nearby-city action render; keyboard and axe pass | IMP-728 | Component |
| TC-484 | `TierBadge`, OSM `SourceBadge`, "Price unknown" and "Hours unknown" chips, the grouped hours warning and `LiveAttribution` render on live data only; axe and keyboard pass | IMP-729 | Component |
| TC-485 | The costs page shows "Known costs only: N stops have no price" and the budget note on live plans; curated plans are unchanged | IMP-729 | Component |
| TC-486 | E2E-10 `@live`: search → resolve → progress → trip → generate → itinerary with live labels and attribution; the not-enough-data path; 360 px | IMP-730 | E2E |
| TC-487 | With the switch ON, API-76 to API-79 require a token, give reference access to any user, never return `import_requested_by`, and count the daily cap per user | IMP-731 | Authz |
| TC-488 | Hostile OSM names and wiki paragraphs change neither the place set nor the costs | IMP-731 | API |
| TC-489 | `trips/live-v1` runs with MOCK and RULE_BASED and reports validity, hallucinated-place rate, unknown-price share, citation coverage and latency | IMP-732 | CLI |
| TC-490 | The full existing suites pass with the switch OFF unchanged, and with the switch ON except the inventory tests named in §3.4; both result lines recorded | IMP-730 | Suite record |
| TC-491 | On staging, the pre-imported demo cities are imported with the real providers and their counts and import times recorded | IMP-733 | Manual, recorded |

### 13.3 End-to-end scenario and acceptance (adds to §13.4 and A1 §9.3)

- **E2E-10.** Any-city journey with fake providers (TC-486).
- **ACC-20.** On staging with the switch ON, a signed-in user searches a pre-imported live city, creates a trip and gets an itinerary (Gemini, or rule-based when Gemini fails). It shows the "Live data" label, OpenStreetMap source badges, the attribution footer and "Price unknown".
- **ACC-21.** On staging, a small town returns "not enough data" naming a larger nearby city. No 5xx and no blank screen.
- **ACC-22.** On staging with `MOCK_PROVIDER_SCENARIO=timeout` (IMD-33), a live city still gets the labelled rule-based plan.
- **ACC-23.** On staging with the switch OFF, the primary journey on Ahmedabad is unchanged, the city search is absent, and API-76 to API-79 answer 404.
- **CHK-26.** The release records the switch state. If ON: the demo cities are pre-imported, ACC-20 to ACC-23 are recorded, and the attribution footer is visible on every live page.

## 14. Schedule, cutoff and fallback (IMD-215)

| Date (2026) | Work | Who |
| --- | --- | --- |
| Sun 22 Nov | E0: IMD-210, IMD-215, this amendment, impact survey (RUN-088) | Nidhi, Het |
| Mon 23 Nov | C1a: IMP-721, IMP-722, IMP-723, IMP-724 | Malhar, Jeel, Het, Manal, Junaid |
| Tue 24 Nov | C1b: IMP-725; C2 web parts start against the fakes and the any-city contract | Het, Manal; Manasvi, Krrish |
| Wed 25 Nov | C2: IMP-726, IMP-727, IMP-728, IMP-729 | Nidhi, Manya, Manasvi, Krrish |
| Thu 26 Nov to Fri 27 Nov | C3: IMP-730, IMP-731, IMP-732, IMP-733 | Krrish, Junaid, Manya, Nidhi, Kirtan |
| **Fri 27 Nov 23:59 IST** | **Cutoff.** Green with the switch OFF (full suite) and ON (`any_city` marker, `@live`, live dataset) → merged and available. Otherwise the release ships with the switch OFF, and the final report describes the work as built but disabled | operator |
| Sat 28 Nov | One staging window on the final candidate: SG-7 items, pre-imported live cities (PD-AC-2), ACC-20 to ACC-23 if ON | Kirtan |
| Sun 29 Nov | SG-7 close and `v1.0-rc1` if the criteria hold; afterwards only severity 1 and 2 fixes | Kirtan |

**Fallback rule.** A card not merged by the cutoff stays on its branch. Merged any-city code that is not green with the switch ON is left switched OFF, which is the default, so no revert is needed. "Cut if late" items (§1.3) are dropped first, before any card is.

## 15. Impact survey

A read-only survey of the code at `c23d78b`, made for this amendment. Each row is one assumption. "Required change" states the decision of this amendment where it differs from the obvious change. Owner and batch come from the cards of §12. Test files are listed only where a test pins behaviour. Literal counts of `ahmedabad|INR|Asia/Kolkata|sampleton` in tests and data are context only:

- api/tests/unit 58, api/tests/api 450, api/tests/authz 3, api/tests/fixtures 1;
- web/tests 62, web/e2e 25;
- eval 68;
- data/fixtures 17, data/places 159, data/guides 60;
- infra 1, Makefile 2.

App code has no destination literal except example texts ("such as INR") in `apps/api/app/auth/service.py:67` and `apps/web/components/profile/ProfileForm.tsx:41,166`, and the guide gate's currency-code pattern (`apps/api/app/rag/guides.py:33`).

| # | file:line | Assumption today | Required change | Owner | Batch |
| --- | --- | --- | --- | --- | --- |
| 1 | apps/api/app/places/seed.py:3-4; app/places/service.py:4-6 | The reference tables have one writer: the file-based seed (plus `ensure_data_source` for guides) | The live import must live in the places module (MOD-B04) and reuse `import_pipeline.prepare/load` with an in-memory `Prepared` built from Overpass rows; other modules call places service only | Het (IMP-725) | C1 |
| 2 | apps/api/app/places/import_pipeline.py:212-250 | Destination facts (timezone, currency, bbox, min_usable_places) come only from `destination.json` | A resolve step builds the destination row from Nominatim plus the country table; `min_usable_places` becomes a code constant or setting for live | Het (IMP-725) | C1 |
| 3 | (none) — grep finds no country table in apps/api/app | No country→currency/time-zone data exists | Add a pure module (e.g. `app/places/countries.py`) mapping ISO 3166 → ISO 4217 and IANA zone; add it to the import-linter pure-domain list | Malhar (IMP-724) | C1 |
| 4 | apps/api/migrations/sql/0002_reference_data.sql:13 + app/validation/rules.py:257 | One IANA time zone per destination, always valid | Multi-zone countries (US, CA, MX, BR, RU, AU, ID, KZ…) take the zone of the nearest `zone1970.tab` representative point (IMD-216); `ZoneInfo()` must never receive an invalid name | Malhar (IMP-724) | C1 |
| 5 | infra/aws/services/api.staging.json.tmpl:42; apps/api/scripts/release.sh:13-16 | Staging data arrives only by `SEED_DIRS` (Ahmedabad) at release | The "pre-imported live cities" of IMD-215 need an import CLI (e.g. `python -m app.places.live_import <query>`) that the release task or operator can run, idempotent per OSM id | Manal (IMP-725) | C1 |
| 6 | apps/api/app/places/import_pipeline.py:98,337-345 | `is_sample` is the only tier flag; SAMPLE is refused outside local/test | Add the `data_tier` (curated/live) column and set it on load; live import never sets `is_sample` | Het (IMP-725) | C1 |
| 7 | apps/api/migrations/sql/0002_reference_data.sql:6-26 | No `data_tier`, provider, external_ref, imported_at, expires_at or import status on destinations | Migration 0008 adds the columns of §4.1 to `destinations` (no new table), with the ORM in the same change | Malhar (IMP-721) | C1 |
| 8 | apps/api/migrations/sql/0002_reference_data.sql:8-9 | Slugs are hand-made ASCII kebab-case, unique | Live slugs need transliteration (e.g. "München", "東京") plus a collision suffix (OSM relation id); the slug also feeds `rag_documents.doc_key` | Het (IMP-725) | C1 |
| 9 | apps/api/migrations/sql/0002_reference_data.sql:15-20,25 | Centre and bbox are curated, small and valid (min<max) | Validate and **cap** the Nominatim bbox (admin areas can span hundreds of km); handle point-like boxes | Malhar (IMP-724) | C1 |
| 10 | apps/api/migrations/sql/0002_reference_data.sql:31-32 | `source_type` has `osm_import` but no MediaWiki type | No CHECK change: Wikivoyage and Wikipedia sources use `source_type = other` (§6.5) | Malhar (IMP-721) | C1 |
| 11 | apps/api/migrations/sql/0002_reference_data.sql:44,79-80 | `(source_id, external_ref)` is unique across **all** destinations | No index change: live `external_ref` = `<destination external_ref>:<n|w|r><id>` (§6.3) | Jeel (IMP-724) | C1 |
| 12 | apps/api/migrations/sql/0002_reference_data.sql:47-49; app/places/quality_gate.py:287-292 | Category and tags are the curated vocabulary; the gate rejects others | The OSM tag→category/tag mapping must emit vocabulary values only; unmapped elements are dropped and counted in the import report | Jeel (IMP-724) | C1 |
| 13 | apps/api/migrations/sql/0002_reference_data.sql:55; app/places/quality_gate.py:256,294-297 | `typical_duration_min` NOT NULL 15-480, typed by a curator | Category default durations of §6.3; the live tier hint says visit lengths are typical values | Jeel (IMP-724) | C1 |
| 14 | apps/api/migrations/sql/0002_reference_data.sql:51 | `description` is "curated, human-written" | Live places leave description NULL (or the OSM `description` tag verbatim); never Wikipedia text or model text | Jeel (IMP-724) | C1 |
| 15 | apps/api/migrations/sql/0002_reference_data.sql:61-63,84-100 | Hours rows are curated or estimated, with hours_label set | C-lite stores no hours for live places: no rows, `hours_label = unavailable`; `opening_hours` parsing is cut (§1.2) | Jeel (IMP-724) | C1 |
| 16 | apps/api/migrations/sql/0003_accounts_trips.sql:21,61; 0004_ai_and_plan.sql:72 | Destinations and places are never removed (FK ON DELETE RESTRICT) | Live refresh or expiry must deactivate (`is_active=false`, as `import_pipeline.py:578-582`), never delete | Manal (IMP-725) | C1 |
| 17 | apps/api/app/core/health.py:34 | `MIGRATION_HEAD = "0007"` | Bump to "0008" in the migration PR, or readiness reports `degraded` | Jeel (IMP-721) | C1 |
| 18 | apps/api/migrations/sql/0004_ai_and_plan.sql:6-47 | The only job table is trip-scoped `ai_generations` | Import state lives on `destinations` (§4.1); no new job table, so the drift test code is unchanged | Malhar (IMP-721) | C1 |
| 19 | apps/api/app/generation/jobs.py:28,34 | One module-level semaphore of 2 slots | Import jobs get their own semaphore so a slow Overpass import never blocks generations | Manal (IMP-725) | C1 |
| 20 | apps/api/app/generation/jobs.py:29-30 | 120 s pipeline timeout, 150 s staleness | Separate import timeout and staleness (Nominatim 1 req/s + Overpass + MediaWiki), set as constants | Manal (IMP-725) | C1 |
| 21 | apps/api/app/generation/jobs.py:88-114; app/main.py:57 | The reaper only fails stale `ai_generations` | Add an import-row round (restart leaves imports `running`) or a second reaper task in the lifespan | Manal (IMP-725) | C1 |
| 22 | apps/api/app/generation/jobs.py:1-2; app/core/rate_limit.py:1 | One API process (IMD-12) | Claim by conditional UPDATE plus `ux_destinations_provider_ref`; the limiter is per process, one API task (IMD-12) (§6.2) | Manal (IMP-725) | C1 |
| 23 | apps/api/app/routing/client.py:22,43-99 | Only ORS has an HTTP client | New `client` modules for Nominatim, Overpass and MediaWiki on the ORS pattern (URL constant, settings timeout, one attempt, domain exception, `lru_cache` singleton, no body in logs, identifying User-Agent header) | Manal (IMP-723) | C1 |
| 24 | apps/api/app/routing/service.py:41-78 | Cache-then-call-then-fallback exists only for routes | GeocodingService: geocode cache → Nominatim → typed "not found / ambiguous" result; the import service drives Overpass with the breaker | Manal (IMP-723) | C1 |
| 25 | apps/api/app/ai/factory.py:55-100 | The real/fake switch exists only for ModelProvider | Factory for live-data providers chosen by a setting (FAKE default in local/test, as `AI_PROVIDER=MOCK`), with a FastAPI dependency tests can override | Manal (IMP-723) | C1 |
| 26 | apps/api/.importlinter (vendor-adapters contract) | `app.*.providers.mock` (wildcard) is protected; only `app.ai.factory` may import it | A fake at `app/places/providers/mock.py` would match the wildcard and fail `make imports`: name it `fake.py` or use another package name | Junaid (IMP-723) | C1 |
| 27 | apps/api/.importlinter (routing-isolation, pure-domain) | httpx isolation covers only `app.routing` | Add a "live-data isolation" contract (httpx only in the new client modules) and list the normaliser/dedupe/country modules under pure-domain | Junaid (IMP-723) | C1 |
| 28 | apps/api/app/ai/breaker.py:29-65 | The breaker is used only for generation | Reuse `CircuitBreaker` for Overpass/Nominatim (an open breaker makes import fail fast with a clear status) | Manal (IMP-723) | C1 |
| 29 | apps/api/app/core/flags.py:10-20 | A disable list only; empty = all ON | Default-off token `!any_city_mode` in the existing variables (§3.1) | Het (IMP-722) | C1 |
| 30 | apps/api/app/core/config.py:52; tests/unit/core/test_config.py:55 | The `features_disabled` default is "" and a test pins it | Settings default unchanged; the rule lives in `flags.py` (§3.1) | Het (IMP-722) | C1 |
| 31 | apps/api/app/core/config.py:86-88,124-173 | `WIKI_USER_AGENT` exists but is unchecked; no Nominatim/Overpass settings | Settings of §7.2; start-up refuses FAKE, or LIVE with an empty or placeholder `WIKI_USER_AGENT`, in staging or production with the switch ON (TC-462) | Het (IMP-722) | C1 |
| 32 | apps/api/app/places/router.py:29-35 | Only API-06 list; no read-one, search, resolve or import-status route | API-76 to API-79 in `places/live_router.py`, mounted only when the switch is ON (§3.3, §5) | Het (IMP-725) | C1 |
| 33 | apps/api/app/places/service.py:26-28; app/places/repository.py:22-28 | API-06 lists every active destination (a few curated ones) | API-06 lists `data_tier = curated` only, shape unchanged (§5) | Het (IMP-725) | C1 |
| 34 | apps/api/app/trips/domain.py:180-190; app/trips/service.py:124-135 | Trip create checks the id against all active destinations and lists them all in the error | A live destination is active only after a completed import; the 422 message lists curated destinations only (§5) | Het (IMP-725) | C1 |
| 35 | apps/api/app/trips/domain.py:126-143 | IMD-128 budget currency = destination currency, from curated JSON | Holds unchanged; the resolve response must return the currency from the country table before the trip form submits | Het (IMP-725) | C1 |
| 36 | apps/api/app/places/service.py:67-69 | API-16 answers 404 for an inactive destination | Keep a live destination inactive until import plus gate succeed; the web shows progress or "not enough data" instead of the 404 | Het (IMP-725) | C1 |
| 37 | apps/api/tests/contract/test_openapi_contract.py:101-107 | Paths with `context`, `today`, `weather`, `compare`… are forbidden | Name new paths without those words (e.g. `/destinations/search`, `/destinations/resolve`, `/destinations/{id}/import`) | Het (IMP-725) | C1 |
| 38 | apps/api/app/core/rate_limit.py:14-53 | Only a per-user, per-minute inbound limiter | Add an outbound limiter (≤1 req/s to Nominatim, polite Overpass spacing) and a per-user daily cap on new imports | Junaid (IMP-723) | C1 |
| 39 | (new) Overpass query builder | No user text reaches an external query language today | Build Overpass QL only from the numeric bbox and a fixed tag list, never from the user's city text; the geocode query is URL-encoded | Junaid (IMP-723) | C1 |
| 40 | apps/api/migrations/sql/0005_mvp_security.sql:24-44,73-76; 0007_rag_store.sql:62-65 | Every table has RLS on and browser roles revoked | No new table, so no new RLS statement; `destinations` keeps its RLS and grants (§4.1) | Malhar (IMP-721) | C1 |
| 41 | apps/api/app/places/schemas.py:45-75 | The Destination response has `is_sample`, no tier, attribution or import state | API-06 shape unchanged (TC-069); tier and attribution come from the new API-79 (§5) | Het (IMP-725) | C1 |
| 42 | apps/api/app/trips/schemas.py:50-55 | `TripDestination` carries `is_sample` only | `TripDestination` unchanged; the web reads the tier from API-79 (§5, §9.2) | Het (IMP-725) | C1 |
| 43 | apps/api/app/places/schemas.py:128-129 | `Category(row.category)` / `Tag(tag)` never fail (curated data) | Unknown values would raise → 500; the normaliser and gate guarantee vocabulary values (add a unit test) | Jeel (IMP-724) | C1 |
| 44 | apps/api/app/places/vocabulary.py:41-80 | The tag vocabulary comes from the SAMPLE fixture plus pricing tags | The OSM mapping is limited to these tags; adding tags changes the OpenAPI enum (regenerate the contract and web types) | Jeel (IMP-724) | C1 |
| 45 | apps/api/app/places/schemas.py:153-159 | `PlaceSource.source_type` Literal mirrors the 0002 CHECK | Keep in step with finding 10 if a new source type is added | Malhar (IMP-721) | C1 |
| 46 | apps/api/app/validation/rules.py:245-305 | `HOURS_UNVERIFIED` (info) per item is rare with curated hours | For live plans every item gets one, so consider one aggregated message per day or tier-level copy in the UI (severity stays info, so no repair) | Krrish (IMP-729) | C2 |
| 47 | apps/api/app/validation/rules.py:334-381 | `COST_INCOMPLETE` is occasional | For live plans it is always raised; the message must read "prices unknown" for live data, and the item references stay | Krrish (IMP-729) | C2 |
| 48 | apps/api/app/budget/engine.py:13-14,214-219 | B6: a missing price counts 0; status from the priced total | Engine unchanged; the web shows "Known costs only" and "covers known costs only" on the live tier (§6.6, §9.2) | Krrish (IMP-729) | C2 |
| 49 | apps/api/app/budget/engine.py:128-133; app/schemas/common.py:22-24 | Minor unit = 1/100; Money has two decimals (IMD-05) | The country table gives every country its ISO 4217 currency; money stays two decimals (IMD-05), so zero-decimal currencies show `.00` and three-decimal ones are rounded to two (IMD-216) | Malhar (IMP-724) | C1 |
| 50 | apps/api/app/budget/engine.py:147-151 | Prices come only from curated `price_*` columns | The normaliser never turns OSM `fee`/`charge` text into prices (PR-02): price fields stay NULL with label `unavailable` | Jeel (IMP-724) | C1 |
| 51 | apps/api/app/generation/fallback_planner.py:37,72,111-145 | Lunch slots need `food` places; durations are curated | The OSM mapping must give `food` (restaurant, cafe, fast_food…) and sane default durations, or every day says "No food place found nearby" | Jeel (IMP-724) | C1 |
| 52 | apps/api/app/generation/fallback_planner.py:163-166 | Curated cities always have enough places | `NoPlanError` when nothing fits: the minimum-places gate must make sure a live city survives the hard filters for typical trips | Jeel (IMP-724) | C1 |
| 53 | apps/api/app/generation/retrieval.py:118; app/trips/preference_mapping.py:122-130 | Curated places mostly have `step_free` set | Warn in the trip form on the live tier; no filter change (§6.6, §9.2) | Krrish (IMP-729) | C2 |
| 54 | apps/api/app/generation/retrieval.py:94-106; app/generation/ranking.py:183-185 | Most places have prices → the price component matters | Accept the neutral 0.5 and document it on the live tier (§6.6) | Manya (IMP-727) | C2 |
| 55 | apps/api/app/generation/ranking.py:159-173 | The distance radius is half the curated bbox diagonal | A huge Nominatim bbox flattens the distance score; use the capped bbox (finding 9) | Malhar (IMP-724) | C1 |
| 56 | apps/api/app/generation/ranking.py:34-36,219-221 | Shortlist 12-40 (8 per day) is always satisfiable | Set the minimum-places gate to at least the 12-place shortlist minimum plus food for meal slots after filters | Jeel (IMP-724) | C1 |
| 57 | apps/api/app/places/repository.py:233-249 | `candidates` loads every active place (curated ≈ dozens) | A large Overpass city could store thousands: cap at import (rank by tag richness or popularity) to keep generation and RAG bounded | Jeel (IMP-724) | C1 |
| 58 | apps/api/app/ai/prompts/templates/itinerary_generate/v2/system.txt:8 (and v3:8) | "context_passages are reference data from curated sources" | Template v4 with source-neutral wording ("cut if late"); v2 and v3 never edited (§6.7) | Manya (IMP-727) | C2 |
| 59 | apps/api/app/schemas/ai.py:121-130 | gr-1/gr-2 `TripContext` has no destination name or tier | No gr-3: the tier reaches the model only through source-prefixed passage titles (§6.7) | Manya (IMP-727) | C2 |
| 60 | apps/api/app/core/config.py:73; infra/aws/services/api.staging.json.tmpl:35; app/ai/factory.py:115-124 | One `PROMPT_TEMPLATE_VERSION` per process, checked at start-up | One process-wide version: v4 covers both tiers; activation only through IMD-195 (§6.7) | Manya (IMP-727) | C2 |
| 61 | apps/api/app/rag/service.py:115-118,121-148 | Guides are read only from `data/guides/<slug>` (or the fixture) files | MediaWiki ingestion needs a non-file source: build `Guide` objects in memory and write them through the same `_write` path | Nidhi (IMP-726) | C2 |
| 62 | apps/api/app/rag/service.py:196-211 | `deactivate_missing(keys)` deactivates anything not in this run's files | Any index run over a live destination deactivates its DB-ingested guides; exclude live destinations or include their stored keys | Nidhi (IMP-726) | C2 |
| 63 | apps/api/app/rag/service.py:238-261; apps/api/scripts/release.sh:18-25 | `index()` covers all active destinations; the release runs `--strict` | Every deploy would re-index and re-embed every live city; restrict release indexing to `data_tier='curated'` and index live cities inside the import job | Nidhi (IMP-726) | C2 |
| 64 | apps/api/app/rag/guides.py:33-46 | Guide text is team-written, so price/clock/hours patterns are rare | Wikivoyage "Eat/Sleep/Get around" sections hit `currency_amount`, `clock_time_range` and hours phrases: drop those sections or paragraphs before chunking; never strict-fail a live import | Nidhi (IMP-726) | C2 |
| 65 | apps/api/app/rag/guides.py:16-27,110-131 | Front matter written by a member (title, source_name, source_type, url, licence, attribution for CC BY, retrieved_on, curated_by) | Synthesise the fields for MediaWiki pages: `licence="CC BY-SA 4.0"`, attribution naming the contributors and page URL, `retrieved_on`, and `curated_by` marked "not checked by the team" | Nidhi (IMP-726) | C2 |
| 66 | apps/api/app/rag/guides.py:200-212 | One licence and attribution text per source name | Keep one generic attribution per wiki source (`Wikivoyage`, `Wikipedia`) and put the page URL per document | Nidhi (IMP-726) | C2 |
| 67 | apps/api/app/rag/constants.py:16-17 | Guides are 300-6,000 characters | Wikivoyage articles exceed 6,000: split per section into several documents, with `doc_key` `guide:<slug>/<wiki>-<pageid>-<section>` (unique, `0007_rag_store.sql:17-18`) | Nidhi (IMP-726) | C2 |
| 68 | apps/api/app/rag/service.py:301-323 | Lexical fallback returns **no** guide passages | Lexical guide passages in `rag/repository.py` are "cut if late" (§6.5) | Nidhi (IMP-726) | C2 |
| 69 | apps/api/migrations/sql/0007_rag_store.sql:51; rag/constants.py:5 | Exact cosine search, the corpus kept under 5,000 chunks (IMD-107) | At most 400 chunks per live destination and expiry-first deactivation above 5,000 active chunks; no ANN index (§6.5) | Nidhi (IMP-726) | C2 |
| 70 | apps/web/lib/flags.ts:7-28,44-50 | Typed disable list; empty enables all | Add `DEFAULT_OFF_FEATURES=["any_city_mode"]` outside `FEATURE_NAMES` (keeps `flags.test.ts:28-32` and `playwright.config.ts:19` unchanged) with the `!any_city_mode` token | Manasvi (IMP-728) | C2 |
| 71 | apps/web/components/trips/TripDetailsStep.tsx:66,140-153 | Destination is a `<select>` over API-06 | Keep the select; add the switch-ON search field below it (§9.1) | Manasvi (IMP-728) | C2 |
| 72 | apps/web/components/trips/TripDetailsStep.tsx:79-86,120-121,294-303 | Currency auto-set from the destination; only a SAMPLE hint | Use the resolve response currency; add a tier hint ("Live data: not checked by our team") | Manasvi (IMP-728) | C2 |
| 73 | apps/web/components/trips/PlacesStep.tsx:38 | The must-visit picker searches API-16 right away | Block or disable the step until the import completes (API-16 is 404 while inactive) | Manasvi (IMP-728) | C2 |
| 74 | apps/web/lib/api/queries.ts:75-80,142,148-172 | `useDestinations` only; polling exists for generations | `useCitySearch`, `useResolveCity`, `useImportStatus` through the any-city client (§9.1) | Manasvi (IMP-728) | C2 |
| 75 | apps/web/app/(app)/trips/[tripId]/explore/page.tsx:34-36,40-46,93-97 | Notice only for SAMPLE or `estimate` labels | Live places (labels `unavailable`, `imported_osm`) get no notice: add a tier banner plus ODbL attribution from `data_tier` | Krrish (IMP-729) | C2 |
| 76 | apps/web/components/labels/SourceBadge.tsx:7-18; components/places/PlaceCard.tsx:31-45,113 | Labels are Curated / Estimate / Unavailable | Add a tier badge (Curated / Live) and "Price unknown" / "Hours unknown" wording for live (A2 copy) | Krrish (IMP-729) | C2 |
| 77 | apps/web/app/(public)/page.tsx:43-45 | Landing copy: "Plans are drafts built from curated sample data" | Tier-neutral copy (or switch-dependent) when any-city is ON | Krrish (IMP-729) | C2 |
| 78 | apps/web/components/map/MapPanel.tsx:30,94-97 | Attribution covers the OSM *tiles* only | ODbL attribution for live *place data* must also show on explore and itinerary (not only inside the map) | Krrish (IMP-729) | C2 |
| 79 | apps/web/app/(app)/trips/[tripId]/costs/page.tsx:44-73; components/costs/CostBreakdown.tsx:100-103 | Planning total plus "Some costs are unavailable" | With every price unknown, show an explicit "Prices unknown for live places" state and per-item chips rather than a near-zero estimate | Krrish (IMP-729) | C2 |
| 80 | apps/api/tests/conftest.py:27-33 | The socket guard blocks only Gemini and ORS | Add the four hosts of §11 to `PROVIDER_HOSTS` | Junaid (IMP-723) | C1 |
| 81 | apps/api/tests/api/test_schema_drift.py:39,88 | Fixed table set (MVP + RAG) | No new table: the drift test passes with unchanged code (§3.3) | Jeel (IMP-721) | C1 |
| 82 | apps/api/tests/contract/test_openapi_contract.py:89,93,98-100 | Exactly 36 MVP endpoints, no other path | The any-city router is mounted only when the switch is ON; ON counterparts in `test_any_city_contract.py` (§3.4) | Het (IMP-722) | C1 |
| 83 | apps/api/tests/authz/route_matrix.py:97-179,212-219 | Every implemented /api/v1 route is in MATRIX or REFERENCE | New `tests/authz/test_any_city_routes.py` with the switch ON; `route_matrix.py` unchanged (§3.4, TC-487) | Junaid (IMP-731) | C3 |
| 84 | apps/api/tests/api/test_places.py:154-171 | TC-069 pins the exact API-06 field set | API-06 unchanged, so TC-069 is unchanged (§5) | Het (IMP-725) | C1 |
| 85 | .github/workflows/e2e.yml:47-57,165-169 | The E2E stack has MOCK AI only; the floor run lists nine names | One switch-ON job with `!any_city_mode` and `LIVE_DATA_PROVIDER=FAKE`; existing runs unchanged (§3.4) | Krrish (IMP-730) | C3 |
| 86 | apps/web/playwright.config.ts:43-70 | Projects by width plus provider-failure plus floor | Add an `@live` grep or project run against a stack with the switch ON and fake providers | Krrish (IMP-730) | C3 |
| 87 | .env.example:11,25,56-59 | The switch comment lists EXT names; `WIKI_USER_AGENT` placeholder | Document the token, `LIVE_DATA_PROVIDER` and the settings of §7.2 (placeholders only) | Kirtan (IMP-733) | C3 |
| 88 | infra/aws/services/api.staging.json.tmpl:22-43; .github/workflows/deploy-staging.yml:150-156 | Plain env list without live-data values; `check_template` needs every `${VAR}` | Add constant values (timeouts, User-Agent text) or new `${VARS}` with workflow env; the owner applies infra changes, never automation | Kirtan (IMP-733) | C3 |
| 89 | eval/datasets/trips/v1/cases.jsonl (case trips-v1-001); manifest.json | Every eval shortlist is priced SAMPLE data | New dataset version (e.g. `trips/live-v1`) with unknown prices and hours and OSM-like names; never edit v1 (hash-pinned) | Manya (IMP-732) | C3 |
| 90 | eval/datasets/retrieval/v1/queries.jsonl; app/evaluation/run.py:348-360,554 | Retrieval labels are file guides of `ahmedabad`/`sampleton` | Live-guide evaluation needs DB-ingested guide keys (or a fake live city with frozen MediaWiki fixtures) | Manya (IMP-732) | C3 |
| 91 | .github/workflows/ci.yml:102 | CI evaluates `trips/v1` with MOCK only | Add the live dataset run (MOCK plus fake providers) | Manya (IMP-732) | C3 |
| 92 | apps/api/tests/fixtures/injection_corpus.json; tests/api/test_injection.py:44 | The injection corpus covers user notes and curated text | Add hostile OSM names and wiki text (passages are data, never instructions) | Junaid (IMP-731) | C3 |
| 93 | apps/api/app/generation/request_builder.py:104-124 | Shortlist places mostly priced, with hours | Add unit tests: a live place gives `price_min/max=None`, `price_label="unavailable"`, `hours_summary="hours unavailable"` | Manya (IMP-727) | C2 |

Findings by area: data model 11, RAG 9, tests/CI 8, API 6, destination/seed 6, providers 6, settings/switch 6, jobs 5, ranking/filters 5, schemas 5, security 4, web trip form 4, budget 3, eval 3, prompt 3, web search/explore 3, fallback planner 2, validation 2, web costs 1, web map 1; total 93. By batch: C1 56, C2 28, C3 9.

### 15.1 Gaps found (recorded under the stop conditions of RUN-088; the amendment is written with each gap resolved as stated)

- **Switch mechanism.** It is a disable list where empty means ON. OFF by default does not fit it as it stands. Resolved by the default-off token of §3.1, which needs no new variable and changes no existing test.
- **Job runner.** It is generation-specific: `ai_generations` and `generation/jobs.py`, in process (IMD-12), with no generic job table. Resolved by import state on `destinations` and a separate runner and reaper on the same pattern (§6.2).
- **IMD-210 (d) and always-mounted routes.** Switched routes today are always mounted, so new routes would change the contract and authz inventory tests. Resolved by mounting the any-city router only when ON and a separate any-city contract (§3.3, §3.4).
- **Lexical fallback has no guide passages.** Live plans in MOCK, CI and E2E cite no guide passage unless the "cut if late" lexical guide retrieval is built (§6.5).
- **No MediaWiki client exists.** CLAUDE.md §4 rule 2 names `app/context/client.py` (cut, IMD-65). The client is `app/livedata/providers/wiki.py` (§7.1), and this amendment wins for any-city mode.
- **No geocode cache and no outbound limiter exist.** Both are new and per process (§6.1, §7.1).
- **Data-model collisions** (slug charset; `(source_id, external_ref)` unique across destinations) are resolved by the slug and `external_ref` formats of §6.1 and §6.3, without an index change.
- **No production task template** in `infra/aws/services/` (only `*.staging.json.tmpl`). Production values for §7.2 cannot be reviewed in the repository (open question for Kirtan).
- **C1 is larger than one batch day.** It is split into C1a (23 November) and C1b (24 November). The items that cannot fit are marked "cut if late" (§1.3).

## 16. External facts and when they were checked

| Fact | Status |
| --- | --- |
| Nominatim public usage policy: at most 1 request per second, identifying User-Agent or Referer, caching expected, no client-side type-ahead search, no bulk geocoding | Unverified (team knowledge, 22 November 2026); IMP-723 reads the policy before the first call outside tests |
| Overpass API public instance: shared and throttled (HTTP 429 when busy); `[timeout:]` and `[maxsize:]` limit a query | Unverified; IMP-723 checks |
| MediaWiki API etiquette: descriptive User-Agent, serial requests, `maxlag` for background jobs; Wikivoyage and Wikipedia text under CC BY-SA 4.0 with attribution | Verified 26 October 2026 in the specification's §9.1 (MediaWiki row); re-checked by IMP-723 |
| OpenStreetMap data under ODbL 1.0, attribution "© OpenStreetMap contributors" with a link to the copyright page | Unverified; IMP-723 checks |
