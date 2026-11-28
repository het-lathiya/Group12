# Local live any-city re-check after the D1–D7 fixes, 28 November 2026 (RUN-107, IMD-220)

This re-runs the local live check of `live-local-2026-11-28.md` (RUN-104), after the merges of #309 (D1), #308 (D3, D5, D7) and #310 (D2, D4, D6). It used real providers on one workstation and is not ACC-20, ACC-21 or TC-491, which need staging. No code was changed in this run.

## Set-up

| Item | Value |
| --- | --- |
| Base commit | `8e7dd4f` (`origin/main` at the start of the run) |
| Database | repository compose `db` (`pgvector/pgvector:pg16`, blank tmpfs, so the daily import cap started at 0), auth stub applied, migrations at head `0008` |
| Auth | local Supabase CLI stack; one new test account made with the local sign-up endpoint |
| API | `uvicorn app.main:app` with `AI_PROVIDER=GEMINI`, `LIVE_DATA_PROVIDER=LIVE`, `FEATURES_DISABLED='!any_city_mode'`, `DB_AUTH_STUB=true`; `/health/ready` gave `ready`, database `ok`, migration `0008`, provider GEMINI `ok` (`gemini-3.5-flash-lite`) |
| Web | `next dev` on Next.js 16.4.5; answered 200 throughout. It was restarted once with `NEXT_PUBLIC_FEATURES_DISABLED='!any_city_mode'`, because the city search is hidden without it |
| Driver | an HTTP script outside the repository: API-76 search → API-77 resolve → API-78 poll → chunk count (database) → wait until 3 min after completion → chunk count → API-07 trip → API-14 default preferences → API-22 generate → API-23 → API-24 itinerary |
| Trip | 3 days (14–16 Dec 2026), 1 adult, budget INR 30,000 / EUR 900 / JPY 150,000, default preferences |
| Gemini use | 3 generations, 1 per city; no `AI_QUOTA_REACHED`. The daily embedding quota was reached during Kyoto's re-embed (see N3) |

Overpass outage: the first Jaipur import (16:12 UTC) failed with HTTP 502 "This Overpass API server is currently at capacity". `overpass-api.de` then gave no answer until about 17:30 UTC. The run waited for it and did not use a mirror. All results below come from the run of 17:31–17:46 UTC.

## Results per city

| | Jaipur | Pushkar | Bundi | Lisbon | Kyoto |
| --- | --- | --- | --- | --- | --- |
| Search / resolve | 200 / 202 (a retry of the 16:12 failed import, D2) | 200 / 202 | 200 / 202; retry 202 | 200 / 202; retry 202 | 200 / 202 |
| OSM reference, kind | N315734346, city | N82799646, town | N520367191, city | R5400890, city | R357794, city |
| Import state | completed | completed | failed `provider_unavailable` (Overpass 502, N1) | failed `provider_unavailable` (Overpass 502, N1) | completed |
| Import time (search to final state) | 139.3 s | 48.9 s | 4.9 s | 3.9 s | 157.8 s |
| Places found / usable | 781 / 300 | 88 / 87 | – | – | 10,617 / 300 |
| Guide documents (chunks) | 19 (54) | 12 (31) | – | – | 22 (99), 3 capped |
| Chunks embedded / total at import end | 128 / 354 (budget spent, 226 queued) | 118 / 118 | – | – | 128 / 399 (271 queued) |
| Chunks embedded / total 3 min later | 354 / 354 | 118 / 118 | – | – | 320 / 399 (daily embedding quota, N3) |
| Retrieval mode | `vector` (597 ms) | `vector` (668 ms) | – | – | `lexical_fallback` (partial index, 4 ms) |
| Generation outcome | `model_repaired` (1 deterministic repair) | `model` | – | – | `model` |
| Model used | `gemini-3.5-flash-lite`, prompt v2; embeddings `gemini-embedding-2` | same | – | – | same |
| Validator (errors / warnings / infos) | 1 / 1 / 14 (error repaired) | 0 / 1 / 9 | – | – | 0 / 1 / 15 |
| Days filled, items | 3/3, 14 | 3/3, 9 | – | – | 3/3, 15 |
| Travel legs: ORS / estimate | 11 / 0 | 6 / 0 | – | – | 12 / 0 |
| Items with sources / guide citations / place citations | 6 / 0 / 6 | 3 / 0 / 3 | – | – | 0 / 0 / 0 |
| Totals | INR 0.00, incomplete 14 | INR 0.00, incomplete 9 | – | – | JPY 0.00, incomplete 15 |
| Generation latency (`latency_ms`) | 11,957 ms | 7,582 ms | – | – | 11,320 ms |
| Bundi nearby suggestion | – | – | not observable (import failed before the gate) | – | – |

The API log shows 29 travel legs from the routing service and no `route fallback` line. Unknown prices and zero totals are expected for live places (A2 §6.6).

Browser: `live-local/2026-11-28b-jaipur-itinerary.png` (Jaipur itinerary; each leg reads "Estimated travel time from a routing service"; the map panel shows "© OpenStreetMap contributors"; map tiles did not render in the headless screenshot) and `live-local/2026-11-28b-city-search.png` (city search for "Jaipur" with the Nominatim and OpenStreetMap attribution). Both pages show the Next.js dev-mode badge.

## Status of D1–D7

| ID | Status | Evidence |
| --- | --- | --- |
| D1 Next.js advisory, web cannot run | fixed (dev) | Next.js 16.4.5; `next dev` answered 200 for the whole run and served both screenshots. `next build` was not run |
| D2 retry of a failed import returns 500 | fixed | Jaipur (failed at 16:12) resolved again with 202 and completed; Bundi and Lisbon retries returned 202 `queued` ("queued again" in the log) |
| D3 embedding rate limited, nothing re-embeds | fixed | Jaipur: 128/354 at completion, then re-embed rounds 160 (after a 429) and 66 → 354/354 within 2.5 min. Kyoto stayed partial only because the daily embedding quota ran out (N3); retrieval used `lexical_fallback` for it, as designed |
| D4 Overpass failures without status or reason | partly fixed | The log now gives the status and body (`overpass http failure status=502 body=… at capacity …`). A 502 "at capacity" is neither deferred nor retried (N1) |
| D5 every ORS call returns 410 | fixed | 29 legs from the routing service, 0 fallbacks; Jaipur generation 12.0 s (16.7 s in RUN-104) |
| D6 Bundi suggests a city 400 km away | not observable | Bundi's import failed at Overpass before the minimum-places gate |
| D7 `completed` before embedding ends | fixed (state); see N2 | The state changed to `completed` in the same second as the embedding run ended (Jaipur 17:33:20, Kyoto 17:42:34); generations retrieved against the stated corpus |

## New defects

| ID | Severity | Defect | Evidence |
| --- | --- | --- | --- |
| N1 | Medium | Overpass HTTP 502 "at capacity" fails the import at once. The client defers later calls only on 429 and 504 (`app/livedata/providers/osm.py:297`), and never retries a query inside an import. Kyoto's query 3 s later succeeded, so a short wait and one retry would have saved Bundi and Lisbon. The 502 body itself asks for exponential backoff | Bundi 17:40:01 and 17:40:04, Lisbon 17:40:05 and 17:40:07: `overpass http failure status=502` → `failed: provider_unavailable`; Kyoto 17:40:08 completed |
| N2 | Low | `imported_at` is set when the places are stored, not when the import completes, so it is about 90 s before the state turns `completed` | Jaipur `imported_at` 17:31:48, completed (row `updated_at`) 17:33:20; Kyoto 17:41:03 and 17:42:34 |
| N3 | Low | After `provider_quota_exhausted`, the re-embed round still calls the embedding API every minute and logs a warning each time, until the daily quota resets | `re-embed round embedded=0 queued=79` after `embeddings incomplete (provider_quota_exhausted)` at 17:44:44, 17:45:42 and later |
| N4 | Low (cause not determined) | No item cited a guide passage, although Jaipur and Pushkar retrieved with `vector` and all their guide chunks were embedded (54 and 31). Place citations worked (6 and 3). Whether the guide passages reached the prompt is not recorded | API-24 `sources` of all items: `kind = guide` 0 |

Notes:

- The web hides the any-city search unless `NEXT_PUBLIC_FEATURES_DISABLED` switches `any_city_mode` on, as the API's `FEATURES_DISABLED` does. A local live check needs both values.
- 5 new cities (with 2 retries) stayed within the per-user daily cap; the cap was not raised.
