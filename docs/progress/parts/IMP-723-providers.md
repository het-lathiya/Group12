# IMP-723 · providers part (protocols, real adapters, fakes and factory)

- Card: IMP-723 Live-data providers (Amendment A2 §7.1, §7.4, §12; 0 points)
- Part: protocols, real adapters, fakes and factory (lead)
- Run id: RUN-089 (Batch C1a, Sprint 7, inserted under IMD-215)
- Owner: Manal (Manal Patel)
- Status: PR_OPEN candidate on `feat/S7-C1a-any-city-foundation`
- Base commit: 08587c0 (on `main`)
- Traces to: IMD-210, IMD-216 (PD-A2-3); A2 §6.1, §6.3, §6.5, §7.1, §7.4, §11; TC-468, TC-469, TC-470, TC-471

## Changed files

- `apps/api/app/livedata/__init__.py`, `providers/__init__.py` (create): module MOD-B19 Live data.
- `apps/api/app/livedata/providers/base.py` (create, no I/O): protocols `GeocodingProvider`, `PlacesProvider`, `GuideSourceProvider`; frozen dataclasses `BBox`, `GeoCandidate`, `GeoPlace`, `OsmElement`, `WikiSection`; errors `LiveDataUnavailable`, `LiveDataRateLimited`, `LiveDataTimeout`. It also holds the fixed tag list `OVERPASS_TAGS` and the query builders `overpass_places_query` and `overpass_city_query`, which take numbers only. That way the user's text cannot reach Overpass QL, and the pure normaliser can read the tag list without importing httpx.
- `apps/api/app/livedata/providers/osm.py` (create): `NominatimGeocoder` (`/search` with `format=jsonv2`, `addressdetails=1`, `namedetails=1`, `limit=10`, `accept-language=en`, the query as a URL-encoded parameter; only city, town, village and municipality, at most 8; `/lookup` by `osm_ids`, an invalid reference sends no request) and `OverpassPlaces` (POST of the fixed query; node coordinates or way and relation `center`; `largest_city_near` by the highest `population`).
- `apps/api/app/livedata/providers/wiki.py` (create): `MediaWikiGuides` with the Wikivoyage and Wikipedia API URLs as code constants. Requests are serial with `maxlag=5`, `prop=extracts|info`, `explaintext=1`, `inprop=url`, `redirects=1`. A geosearch runs when the title is missing. Sections split at level-2 headings. A missing page gives no sections. A `maxlag` error raises `LiveDataUnavailable`.
- `apps/api/app/livedata/providers/fake.py` (create): `FakeGeocoder`, `FakePlaces`, `FakeGuides` with scenarios `ok`, `small`, `empty`, `timeout`, `rate_limited`, `malformed`. The data is SAMPLE only: "Liveton (SAMPLE)" (R9000001) with 48 elements including 4 near-duplicates, which passes the gate (44 usable, 12 food, 32 non-food), and "Tinyham (SAMPLE)" (R9000002) with 8 places, which gives `insufficient_data` and the nearby city "Bigtown (SAMPLE)". Construction is refused unless `APP_ENV` is local or test. The file is named `fake.py` because `vendor-adapters` protects `app.*.providers.mock`.
- `apps/api/app/livedata/factory.py` (create): `get_providers()` (cached per process) builds FAKE or LIVE from `LIVE_DATA_PROVIDER`; FAKE is refused in staging and production. The FastAPI dependencies `get_geocoder`, `get_places_provider`, `get_guide_provider` can be overridden by tests. `reset_cache()` is for tests.
- `apps/api/tests/fixtures/livedata/*.json` (create): recorded-shape Nominatim, Overpass and MediaWiki bodies with SAMPLE names.
- `apps/api/tests/unit/livedata/test_clients.py` (create, respx): TC-468, TC-469, TC-470.
- `apps/api/tests/unit/livedata/test_fakes.py` (create): TC-471 (every scenario of each fake; the factory picks FAKE in local and test; FAKE refused in staging and production; fakes refused outside local and test).
- `docs/progress/parts/IMP-723-providers.md` (this record).

Adapter conventions (from `app/routing/client.py`): one attempt, no retry; timeout from settings; base URLs from settings (Nominatim, Overpass) or code constants (MediaWiki); every failure becomes a domain exception with a safe message (`timeout`, `http 429`, `http <status>`, `connection`, `malformed response`); no body or query text in the module's own logs; `User-Agent: <WIKI_USER_AGENT>` on every request.

## Commands

| Command | Result line |
| --- | --- |
| `make test-unit ARGS='-k livedata'` (all livedata parts present) | `567 passed, 1255 deselected, 1 warning in 1.25s` |
| `.venv/bin/ruff check app/livedata tests/unit/livedata` | `All checks passed!` |
| `.venv/bin/ruff format --check app/livedata tests/unit/livedata` | `15 files already formatted` |
| `.venv/bin/mypy app` | `Success: no issues found in 134 source files` |

`make imports` and `make check` on the branch head are in the SYNC REPORT of RUN-089.

## Acceptance

- Each client sends the User-Agent, makes one attempt and maps every failure to a domain exception without logging bodies: **verified** (TC-468 to TC-470, respx; caplog on the `app.livedata` loggers).
- The fakes cover every scenario: **verified** (TC-471).
- The factory picks FAKE in local and test and refuses FAKE when deployed: **verified** (`test_fakes.py`).

## Open issues

- **The query text can reach logs through httpx.** httpx logs `HTTP Request: GET <full URL>` at INFO, and a Nominatim search URL holds `q=<text>` (A2 §11: logs never keep the query text). The adapters' own logs hold counts only. The fix is to set the `httpx` and `httpcore` loggers to WARNING in `app/core/logging.py`. That file is in no C1a card, so it is left for C1b (IMP-725) or IMP-731, before the first LIVE call. No LIVE call happens while the switch is OFF or the provider is FAKE.
- One `# type: ignore[arg-type]` in `test_fakes.py`, with its reason, tests that an unknown scenario is refused.
- The usage-policy check of IMP-723 step 8 is in `IMP-723-throttle-isolation.md` (Junaid's part).

## Proposed decisions

none

## Blockers

none
