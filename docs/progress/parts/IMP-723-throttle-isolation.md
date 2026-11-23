# IMP-723 · throttle-isolation part (throttle, breakers, socket guard, isolation contract, query safety, usage policy)

- Card: IMP-723 Live-data providers (Amendment A2 §7, §8.2, §11, §12; 0 points)
- Part: throttle, socket-guard hosts, `livedata-isolation` contract, query-safety tests and the usage-policy check of §7.3
- Run id: RUN-089 (Batch C1a, Sprint 7, inserted under IMD-215)
- Owner: Junaid (Mohammad Junaid Kureshi)
- Status: PR_OPEN candidate on `feat/S7-C1a-any-city-foundation`
- Base commit: 08587c0 (on `main`)
- Traces to: IMD-12, IMD-210, IMD-216 (PD-A2-3); A2 §7.1, §7.3, §8.2, §11, §16; TC-468, TC-469, TC-471

## Changed files

- `apps/api/app/livedata/throttle.py` (create): `Throttle(spacing_s)`, an async per-host spacing gate with one lock (calls serialised; spacing measured from the end of the previous call; a failed call counts). Constants `NOMINATIM_SPACING_S = 1.0`, `OVERPASS_SPACING_S = 2.0`, `MEDIAWIKI_SPACING_S = 0.2`. Wrappers `GuardedGeocoder`, `GuardedPlaces` (throttle and `app.ai.breaker.CircuitBreaker`) and `GuardedGuides` (throttle only). An open breaker fails fast with `LiveDataRateLimited` without calling the provider. Errors are recorded as rate limited → quota (15 minutes open), timeout → timeout, unavailable → unavailable (5 in a row → 60 s open). Per-process singletons (`nominatim_throttle()`, `overpass_breaker()`, …) and `guard_geocoder()`, `guard_places()`, `guard_guides()`.
- `apps/api/app/livedata/factory.py`: the LIVE branch wraps the real adapters with `guard_geocoder`, `guard_places` and `guard_guides` (IMP-723 lists the factory; the fakes are not wrapped).
- `apps/api/tests/unit/livedata/test_fakes.py`: the LIVE factory test now expects the real clients inside `GuardedGeocoder`, `GuardedPlaces` and `GuardedGuides` (same card, IMP-723).
- `apps/api/tests/conftest.py`: `PROVIDER_HOSTS` adds `nominatim.openstreetmap.org`, `overpass-api.de`, `*.wikivoyage.org`, `*.wikipedia.org` (nothing else changed).
- `apps/api/.importlinter`: new contract `livedata-isolation` (one contract): sources `app.livedata`, `app.places`, `app.rag`; forbidden `httpx`, `app.generation`, `app.itinerary`, `app.budget`, `app.validation`, `app.trips`, `app.db`; ignored imports `app.livedata.providers.osm -> httpx`, `app.livedata.providers.wiki -> httpx`, and the places and RAG modules' existing imports of the six app modules (the "no generation … db" rule of §8.2 is for `app.livedata` only; places and RAG own their tables). `allow_indirect_imports = True`, as in `routing-isolation`. Today neither `app.places` nor `app.rag` imports httpx. The contract was shown to break when the `osm -> httpx` ignore is removed or when `app.ai` is forbidden (scratch configs).
- `apps/api/tests/unit/livedata/test_throttle.py` (create, 67 tests): spacing with a fake clock, serialised concurrent calls, MediaWiki 0.2 s, Nominatim 1 s through the wrapper; breaker (5 transient failures → fail fast without calling the provider; 429 → 15 minutes; success resets; half-open probe); TC-469 query safety (exact templates and an allow-list of words and characters for both builders; the builders' only parameters are numbers; NaN, ±inf, str, bool and None refused); TC-471 socket guard for the four hosts and their subdomains.
- `docs/progress/parts/IMP-723-throttle-isolation.md` (this record).

The `pure-domain` entries for `app.livedata.normalise` and `app.livedata.countries` are **not** in this commit: import-linter refuses a listed module that does not exist yet (`Module 'app.livedata.doesnotexist_xyz' does not exist.`, scratch config), so they are added in the countries part's commit (`IMP-724-countries.md`), as the run prompt directs.

## Usage policy check (IMP-723 step 8; A2 §7.3, §16)

| Service | URL | Date read | Differences from A2 §7.3 / §16 |
| --- | --- | --- | --- |
| Nominatim | https://operations.osmfoundation.org/policies/nominatim/ | 23 Nov 2026 | **Not verified — Junaid to confirm**: the policy page could not be read (connection reset twice). The summary at https://wiki.openstreetmap.org/wiki/Nominatim (read 23 Nov 2026) says "no more than 1 request per second for the whole application, summed over all its users". A2 says per process; that holds only while one API task runs (IMD-12). The summary also asks for attribution and a custom User-Agent or Referer, and forbids client-side autocomplete and bulk geocoding. All three match A2. |
| Overpass API (overpass-api.de) | https://wiki.openstreetmap.org/wiki/Overpass_API | 23 Nov 2026 | Limits not in A2: about 10,000 queries and 1 GB a day in total, with "for regular use, divide by 100" (about 100 queries and 10 MB a day). That is below what `[maxsize:]` 64 MiB and `LIVE_DAILY_IMPORTS_GLOBAL = 50` allow. No parallel scripts; one process with the throttle meets this. After a 429 or 406, pause about 30 s; the 15-minute breaker is stricter. A User-Agent or Referer is required. Heavy or commercial use should go to a self-hosted or paid instance. |
| MediaWiki API | https://www.mediawiki.org/wiki/API:Etiquette | 23 Nov 2026 | Matches A2: serial requests, `maxlag` for non-interactive jobs, descriptive User-Agent. Extra: User-Agent form `client/version (contact) framework/version`, `Accept-Encoding: gzip`, caching, back off on `ratelimited`. |
| OSM copyright | https://www.openstreetmap.org/copyright | 23 Nov 2026 | ODbL 1.0 confirmed. The page defers the exact credit wording to the OSMF attribution guidelines, which could not be read (connection reset). The exact "© OpenStreetMap contributors" text is **not verified — Junaid to confirm**. A link to the copyright page is recommended; where links are impossible, the URL is written out. |

## Commands

| Command | Result line |
| --- | --- |
| `.venv/bin/pytest tests/unit/livedata/test_throttle.py -q` | `67 passed in 0.10s` |
| `make imports` (with every livedata module present) | `Contracts: 7 kept, 0 broken.` |
| `ruff check` / `ruff format --check` (three files) | `All checks passed!` / `3 files already formatted` |
| `mypy` strict (throttle and its test) | `Success: no issues found in 2 source files` |

`make test-unit ARGS='-k livedata'`, `make imports` and `make check` on the branch head are in the SYNC REPORT of RUN-089.

## Acceptance

- The throttle spaces calls: **verified** (fake-clock tests).
- The Overpass query contains no user text: **verified** (TC-469; the builders take only numbers).
- The socket guard blocks the new hosts: **verified** (TC-471 guard tests).
- `make imports` prints `Contracts: 7 kept, 0 broken.`: **verified** on the branch head (SYNC REPORT).
- Each service's usage policy recorded with the date read: **verified** for Overpass, MediaWiki and the OSM copyright page. Nominatim and the exact OSM credit text are **not verified — Junaid to confirm**.

## Open issues

- The limits are per process (A2 §7.1, §7.3); the Nominatim limit is per application. This needs one API task (IMD-12) or a shared limiter.
- The Overpass "regular use" budget is about 1 % of the stated maximum, far below the A2 caps (see the table).
- `BBox` accepts `True`/`False` as coordinates (bool is an int). The query builders refuse them and a test covers that.

## Proposed decisions

- PD-A2-8 (proposed): bring the live-data caps under the Overpass "regular use" budget: lower `LIVE_DAILY_IMPORTS_GLOBAL` and `[maxsize:]`, or use a self-hosted or paid Overpass instance. Also confirm that the API runs as a single task while any-city mode is ON.

## Blockers

none
