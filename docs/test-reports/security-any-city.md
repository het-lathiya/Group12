# Security addendum: any-city mode (IMP-731)

- Run: RUN-092 (Batch C3, Sprint 7, inserted under IMD-215)
- Owner: Junaid (Mohammad Junaid Kureshi)
- Base commit: 818c1d8 (on `main`)
- Scope: Amendment A2 §7.3 (etiquette and limits) and §11 (security and privacy), reviewed against the code on this branch; TC-487 and TC-488
- Adds to: `docs/test-reports/security-sprint7.md`

## Tests

| Command | Result line |
| --- | --- |
| `make test-authz ARGS='-k any_city'` | 4 passed, 101 deselected, 1 warning in 0.51s |
| `make test-api ARGS='-k injection'` | 27 passed, 653 deselected, 1 warning in 7.34s |
| the same two files with `ANY_CITY_SUITE_ON=1` (TC-490 mode) | 6 passed, 25 deselected in 1.48s |

- **TC-487** (`tests/authz/test_any_city_routes.py`):
  - With the switch ON, the app adds exactly API-76 to API-79 to the pinned switch-OFF app.
  - Each route answers 401 `UNAUTHENTICATED` without a token and with a malformed one.
  - Two users both read a destination one of them resolved (reference data).
  - No response key at any depth is `import_requested_by`, and the requester's id never appears in a body.
  - The daily cap is per user: one user's 429 `RATE_LIMITED` leaves another user's new city at 202, and a known city stays 200.
  - `route_matrix.py` is unchanged (§3.4).
- **TC-488** (`tests/api/test_injection.py`, corpus keys `osm_names` and `wiki_paragraphs` in `tests/fixtures/injection_corpus.json`):
  - One live destination is imported, planned, imported again with hostile text and planned again.
  - With hostile Wikivoyage paragraphs (stored, because they hold no price or hours pattern), the saved place IDs per day and API-33's costs are equal to the clean run. The paragraphs reach the provider only inside quoted guide `context_passages`, never in the shortlist.
  - With hostile OSM names on three places (no embeddings on either import, so a changed name cannot move vector similarity), places per day and costs are equal. The names are stored as plain text and reach the provider only as shortlist names.
  - No injected place id (`…bad0`) reaches the shortlist or the plan.

## Review of A2 §7.3 against the code

| Rule | Code | Result |
| --- | --- | --- |
| Nominatim: at most 1 request/s per process | `app/livedata/throttle.py` `NOMINATIM_SPACING_S = 1.0`, one `Throttle` per host, serialised | holds |
| Nominatim: identifying User-Agent | `app/livedata/providers/osm.py`: `headers={"User-Agent": user_agent}` on every request; `WIKI_USER_AGENT` (PD-A2-3) | holds; the staging value is set by Kirtan (IMP-733) |
| Nominatim: results cached 24 h, settlements stored, no type-ahead, no bulk | `live_service._SearchCache` (24 h, 1,000 keys); resolved settlements become `destinations` rows; the web searches on submit only (`CitySearch`, TC-482/483); one lookup per resolve | holds |
| Overpass: one places query per import, plus one nearby-city query when the gate fails | `live_jobs._import`: one `places.fetch`; `largest_city_near` only on `insufficient_data` | holds |
| Overpass: `[timeout:]` and `[maxsize:]` set; ≥ 2 s spacing; a 429 opens the breaker for 15 min | `providers/base.overpass_places_query`; `OVERPASS_SPACING_S = 2.0`; `throttle.py` (429 = quota, 15 min; 5 transient failures, 60 s) | holds |
| MediaWiki: serial requests, `maxlag=5`, identifying User-Agent | `providers/wiki.py`: one client, a sequential loop over the sources, `maxlag` in every request, the User-Agent header; `MEDIAWIKI_SPACING_S = 0.2` | holds |
| MediaWiki: at most 2 pages per import | `MediaWikiGuides.fetch` asks one page per source (Wikivoyage, then Wikipedia) | holds |
| Imports serialised | `live_jobs.IMPORT_MAX_CONCURRENT = 1` | holds |

**Policy pages: Junaid to confirm by reading.** The current usage policies of Nominatim, the Overpass API instance and the MediaWiki API (rate, User-Agent, caching, bulk use) are still "Unverified" in A2 §7.3 and §16. This review checks the code against the A2 table only. Reading each policy page and recording the date is open for Junaid before the first call outside tests (the staging pre-import, IMP-733).

## Review of A2 §11 against the code

| Rule | Code and evidence | Result |
| --- | --- | --- |
| Untrusted text reaches the model only as quoted data; instructions change neither places nor costs | TC-488 above; guide text is quoted in `context_passages`; names only in `ShortlistPlace.name`; prices and hours never come from text (IMP-726 content rule, `test_live_guides.py`) | holds |
| Names stored as text, never rendered as HTML | React text nodes only; no `dangerouslySetInnerHTML` in the any-city components | holds |
| Query safety: search text only to Nominatim, URL-encoded, without identity | `osm.NominatimGeocoder.search` passes `q` as an httpx query parameter; no user id or token is sent | holds |
| Overpass queries from numbers and a fixed tag list | `overpass_places_query` / `overpass_city_query` format numbers only (TC-469) | holds |
| Logs keep counts and ids, never the query text | `live_service.search` logs counts; `live_jobs` logs destination ids and counts. **RUN-090 log-privacy fix:** `app/core/logging.py` sets `httpx` and `httpcore` to WARNING (`QUIET_HTTP_LOGGERS`), so the request line with the Nominatim `q=` is never logged; `tests/unit/core/test_logging_live_query.py` fails if `httpx` logs at INFO | holds |
| Links `https://` only, `noopener noreferrer` | `normalise.website_url` keeps `https://` only; `LiveAttribution` and `PlaceDetailDrawer` links carry `rel="noopener noreferrer"`; non-https attribution URLs are not linked (IMP-729 test) | holds |
| Socket guard blocks the new hosts | `tests/conftest.py` `PROVIDER_HOSTS`: nominatim.openstreetmap.org, overpass-api.de, *.wikivoyage.org, *.wikipedia.org | holds |
| Abuse: API-76 limiter, API-77 daily caps, serial imports | `live_router`: API-76 has `Depends(expensive_request)`; caps 5 per user / 50 global (IMD-217 keeps 50); `IMPORT_MAX_CONCURRENT = 1`; TC-487 per-user cap | holds |
| Every route needs a bearer token; no route returns `import_requested_by` | TC-487 | holds |
| Account deletion sets `import_requested_by` to null | migration 0008 `on delete set null`; `test_live_destinations_schema_requester_is_set_null_on_profile_delete` | holds |

## Findings

none. No defect was found. The open item is reading the three policy pages (above).
