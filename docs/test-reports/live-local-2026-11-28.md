# Local live any-city check, 28 November 2026 (RUN-104, IMD-220)

Operator-run rehearsal of `any-city-readiness.md` §6 with real providers on one workstation. It does not count as ACC-20, ACC-21 or TC-491, which need staging. No code was changed in this run.

## Set-up

| Item | Value |
| --- | --- |
| Base commit | `57b6209` (`origin/main`) |
| Database | repository compose `db` (`pgvector/pgvector:pg16`), auth stub applied, migrations at head `0008` |
| Auth | local Supabase CLI stack (`supabase start`); one test account made with the local sign-up endpoint |
| API | `uvicorn app.main:app` with `AI_PROVIDER=GEMINI`, `LIVE_DATA_PROVIDER=LIVE`, `FEATURES_DISABLED='!any_city_mode'`, `DB_AUTH_STUB=true`; `/health/ready` gave `ready`, database `ok`, migration `0008`, provider GEMINI `ok` |
| Web | `next dev` answered 200 at first, then exited (D1) |
| Driver | an HTTP script outside the repository: API-76 search → API-77 resolve → API-78 poll → API-07 trip → API-14 default preferences → API-22 generate → API-23 poll → API-24 itinerary |
| Trip | 3 days (14–16 Dec 2026), 1 adult, budget INR 30,000 (Lisbon EUR 900), default preferences (pace and budget priority `balanced`) |
| Gemini use | 3 generations, at most 1 per city; no `AI_QUOTA_REACHED` |

Differences from §6: the cities were imported through the API (as the web does), not the CLI. GEMINI was on from the start, so imports embedded with the real model. The per-user daily import cap (`LIVE_DAILY_IMPORTS_PER_USER`, default 5) was reached after the fifth import (Bundi and Pushkar used two). The API was restarted with the cap at 6 for Lisbon only (note N1).

## Results per city

| | Jaipur | Udaipur | Mumbai | Bundi | Pushkar | Lisbon |
| --- | --- | --- | --- | --- | --- | --- |
| Search / resolve | 200 / 202 | 200 / 202 | 200 / 202 | 200 / 202 | 200 / 202; retry 500 (D2) | 200 / 429 cap (N1); after restart 202 |
| OSM reference, kind | N315734346, city | N2409551371, city | N16173235, city | N520367191, city | N82799646, town | R5400890, city |
| Import state | completed | completed | completed | insufficient_data, nearby "New Delhi" (D6) | failed `provider_unavailable` (D4) | failed `provider_unavailable` (D4) |
| Import time (resolve to final state) | 53.2 s | 44.6 s | 46.6 s | 86.2 s | 4.7 s | 4.3 s |
| Places found / usable | 781 / 300 | 275 / 236 | 3,629 / 300 | 34 / 32 (14 food, 18 other) | – | – |
| RAG documents / chunks | 319 / 354 | 258 / 315 | 320 / 397 | 0 / 0 | 0 / 0 | 0 / 0 |
| Chunks embedded | 96 (D3) | 64 (D3) | 64 (D3) | – | – | – |
| Generation outcome | `model` | `model` | `model` | – | – | – |
| Model used | primary (`gemini-3.5-flash-lite`), prompt v2 | primary, v2 | primary, v2 | – | – | – |
| Validator (errors / warnings / infos) | 0 / 3 / 15 | 0 / 1 / 9 | 0 / 2 / 15 | – | – | – |
| Repairs (model / deterministic) | 0 / 0 | 0 / 0 | 0 / 0 | – | – | – |
| Days filled, items | 3/3, 15 | 3/3, 9 | 3/3, 15 | – | – | – |
| Unknown-price items | 15 of 15 | 9 of 9 | 15 of 15 | – | – | – |
| Items with sources / guide citations | 6 / 0 | 1 / 1 | 0 / 0 | – | – | – |
| Totals | INR 0.00, incomplete 15 | INR 0.00, incomplete 9 | INR 0.00, incomplete 15 | – | – | – |
| Attribution (API-79) | OpenStreetMap, Wikipedia, Wikivoyage | same | same | – | – | – |
| Attribution shown in the web | not verified (D1) | – | – | – | – | – |
| Generation latency (`latency_ms`) | 16,714 ms | 8,599 ms | 18,289 ms | – | – | – |
| Total (search to itinerary) | about 72 s* | 55.7 s | 69.3 s | 87.5 s | 5.6 s | 5.6 s |

\* Jaipur: import 53.2 s + generation 16.7 s + calls. The first two Jaipur trips stopped at 422 before generating (preferences not saved, then AI notice not acknowledged; both correct API answers fixed in the driver). The third trip generated.

Unknown prices, unknown hours and zero totals are expected for live places (A2 §6.6, readiness §5).

**Browser check (Jaipur itinerary page): not run.** The web app could not be kept running (D1), so there are no screenshots in `docs/test-reports/live-local/`.

## Defects

| ID | Severity | Defect | Evidence |
| --- | --- | --- | --- |
| D1 | High | The installed Next.js 16.4.3 is flagged by a security advisory: `next build` fails with `SecurityFatalError`, and `next dev` exits right after printing the notice (it stayed up once, then exited on both restarts). The web app cannot run locally, and CI and deploy builds may fail the same way (not verified). | `next build` → "Compiled successfully", then "Build error occurred / Error [SecurityFatalError]: Your version of Next.js is affected by a known security vulnerability."; `curl localhost:3000/sign-in` → connection refused once the notice is printed |
| D2 | High | Resolving a city whose import failed returns 500, so a failed city cannot be retried from the web. | `POST /api/v1/destinations/resolve` (Pushkar, second time) → 500 `INTERNAL`, request `22fe9747-d895-4cb4-b137-6fa8e703ef00`; `sqlalchemy.exc.InvalidRequestError: Can't operate on closed transaction inside context manager` from `app/places/live_service.py:255` (`_existing`) called at `:186` (`resolve`), `live_router.py:65` |
| D3 | High | Gemini embedding is rate limited during every completed import, so 66–82 % of each city's chunks stay unembedded, and nothing embeds them again (G9). Only 1 guide citation in 39 items. | `app.rag.service` WARNING "embeddings incomplete (provider_rate_limited): embedded=96" (Jaipur, 354 chunks), "=64" (Udaipur, 315), "=64" (Mumbai, 397) |
| D4 | Medium | After about 6 Overpass queries in 6 minutes, imports failed within 0.6 s as `provider_unavailable`, and a plain `GET https://overpass-api.de/api/status` answered HTTP 406. The log has no HTTP status or reason, so the cause (block, overload or User-Agent rule) cannot be read from the app. | `app.places.live_jobs` WARNING "live import 1dfb4b24-… failed: provider_unavailable" (Pushkar 09:53:47), "66b63c7e-… failed: provider_unavailable" (Lisbon 09:55:58) |
| D5 | Medium | Every OpenRouteService call returned HTTP 410, so every travel leg uses the distance fallback. The calls are made one by one, about 0.6 s each (about 8 s of Jaipur's 16.7 s). | `app.routing.service` INFO "route fallback mode=walking reason=http 410", 12 times for Jaipur |
| D6 | Medium | Bundi's "not enough data" answer suggests New Delhi, about 400 km away. The nearby-city Overpass query kept 0 of 8 elements, so the capital was used (`live_jobs.py:223-231`). The message calls it "a larger city nearby". The nearby query also took 49 s. | `app.livedata.providers.osm` "overpass elements=8 kept=0" (09:53:30); import `insufficient_data found=34 usable=32 food=14 non_food=18` |
| D7 | Low | The import state is `completed` before embedding ends (8–10 s later). A generation started straight away retrieves against a partly embedded corpus (Udaipur and Mumbai did). | Jaipur `imported_at` 09:47:49, embedding warning 09:48:01; the chunk count right after completion was 0 and later 96 |

Notes:

- **N1.** The per-user daily import cap of 5 (`live_service.py:67`, 429 `RATE_LIMITED` "The daily limit for new cities is reached. Try again tomorrow.") works as designed. A test session covering 6 cities needs a second account or a higher local cap.
- **N2.** A2 §7.3 asks for the usage-policy readings (G3) before the first call outside tests. This run did not check whether they were recorded.
