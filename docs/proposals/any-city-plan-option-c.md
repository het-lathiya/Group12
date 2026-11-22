Source proposal; superseded where Amendment A2 differs

# Any-City Mode: plan for Option C (proposal, 18 Nov 2026)

Status: PROPOSED. It becomes binding only as Amendment A2 + IMD-210 after the team votes C. Until then nothing here is a requirement.
Owner of this document: the planner. Work: 0 points (outside the contribution plan, IMD-210).

---

## 1. Goal in one sentence

A user types any city; within about a minute the app builds a real, routed, budget-checked itinerary from live open data, every fact carries its source, and the AI never invents a place, an opening time or a price.

## 2. What makes it better than typical AI travel planners

| Typical AI planner | Ours (any-city mode) |
|---|---|
| LLM writes the whole plan; places, hours and prices can be invented | The LLM only chooses from a fetched, structured place set; the validator rejects anything else |
| No sources | Every stop, tip and fact cites its source (OpenStreetMap, Wikivoyage, official page, Google Maps grounding) |
| Prices guessed by the model | Costs computed by our budget engine; unknown prices shown as unknown |
| Travel times guessed | Real travel-time matrix from OpenRouteService |
| One LLM call, no checks | Agentic pipeline: retrieve → plan with tools → validate → self-repair once → fallback planner if the AI fails |
| No evaluation | Measured: validity rate, citation coverage, hallucination rate, latency and cost per plan, compared across curated vs live cities |
| Prompt-injection blind | Untrusted web text is quoted data, filtered, and covered by injection tests |

## 3. Design principles (non-negotiable)

1. One switch `any_city_mode`, OFF by default. With it off, the app is exactly today's app and every existing test passes unchanged.
2. Two data tiers, always labelled: **Curated** (Ahmedabad and destination 2; checked by the team) and **Live** (fetched from open providers; "not checked by our team").
3. Facts come from sources, costs come from code, the model plans. No runtime LLM-supplied hours or prices (PR-02, §5.6, TC-357/ACC-15 still hold).
4. Every external service is optional enrichment behind an interface with a fallback; nothing external can break a curated-city plan.
5. Tests run offline with fake providers; real providers are called only in development and staging.
6. Licences respected: ODbL attribution for OpenStreetMap, CC BY-SA attribution for Wikivoyage/Wikipedia, Google Maps attribution and no long-term storage of Google content.

## 4. Architecture

```
User types a city
  │
  ▼
[1] City resolve ── Nominatim (cached; ≤1 req/s; custom User-Agent) → name, country, bbox, lat/lng
  │                  country → currency + time zone (static table in code)
  ▼
[2] Destination create (tier = live) + import job (async, like generation jobs)
  │
  ├─[3] Places spine ── Overpass API (OpenStreetMap): tourism/historic/leisure/amenity tags in bbox
  │        → normalise to our places schema (category map, coordinates, opening_hours tag if present,
  │          website, wikidata id) → dedupe → quality gate (min usable places, e.g. 40) → store (ODbL)
  │
  ├─[4] Guide corpus ── Wikivoyage + Wikipedia via MediaWiki API (CC BY-SA) → chunk → embed → pgvector
  │        optional: Firecrawl scrape of ALLOWLISTED official tourism pages only (licence/attribution recorded)
  │
  └─[5] Freshness (optional, plan time) ── Gemini grounding:
           • Google Maps grounding: confirm the chosen stops exist/are open, current hours, Maps link
             (place IDs only stored; text shown with Google Maps attribution; not persisted long-term)
           • Google Search grounding: closures, festivals, advisories for the trip dates, with citations
  ▼
[6] Agentic planner (Gemini, structured output + function calling)
       tools: search_places(dest, filters) · travel_matrix(ids) [ORS] · retrieve_guides(query) [RAG]
              · budget_estimate(plan) [our engine] · check_hours(place, day) [stored data]
       output: JSON schema of the itinerary (existing contract)
  ▼
[7] Validator (existing) → one self-repair round with the validator's errors → else rule-based fallback planner (IMD-33)
  ▼
[8] UI: itinerary + map + costs, each item with source badges (Curated ✓ / OpenStreetMap / Wikivoyage / Google Maps)
```

## 5. Data sources, limits and cost

| Source | Used for | Licence / terms | Limits | Cost |
|---|---|---|---|---|
| Nominatim (OSM) | City search and geocoding | ODbL attribution; usage policy: ≤1 req/s, identify the app, cache results | Public server is for light use | Free |
| Overpass API (OSM) | Places of a city | ODbL attribution | Public instances throttle heavy users (HTTP 429); one query per city, cached | Free |
| Wikivoyage / Wikipedia (MediaWiki API) | Guide text for RAG | CC BY-SA with attribution | Polite rate, User-Agent | Free |
| Firecrawl (optional) | Official tourism pages on an allowlist | Only allowlisted domains; licence recorded per page | 1,000 credits/month free | Free for our volume |
| OpenRouteService (existing) | Travel-time matrix | Existing key | Existing limits | Free |
| Gemini (existing) | Planning, embeddings, grounding | Existing | Free key today; grounding needs a paid-tier key (5,000 grounded prompts/month free on Gemini 3 models, then about $14 per 1,000) | $0 for demo with a spend cap |
| Google Maps grounding (optional) | Freshness check of chosen stops | Google Maps Platform terms: show attribution, store only place IDs | Paid tier + free monthly allowance | $0 for demo with a spend cap |

Not used: Serper (Gemini Search grounding covers discovery), Google Places API (billing + storage terms; Maps grounding gives the freshness benefit without storing Google data).

Prices: OpenStreetMap has none. The budget engine shows known costs (curated cities, or a fee stated on an official page with citation) and marks the rest "price unknown"; totals say "known costs + N unpriced items". No model-made prices.

## 6. GenAI techniques the professor will see

1. RAG with citations over a live-built corpus (pgvector, exact cosine as IMD-107), per city.
2. Agentic planning with function calling (tools for places, travel matrix, guides, budget, hours).
3. Structured output (JSON schema) + deterministic validator + one self-repair loop (LLM fixes its own errors from validator feedback).
4. Grounding with Google Maps and Google Search for freshness, with citations shown in the UI.
5. Guardrails: prompt-injection filtering of web text, quoted-data prompting, allowlists, refusal paths.
6. Graceful degradation: circuit breaker, rule-based fallback planner, lexical retrieval fallback (IMD-112).
7. Evaluation: automatic metrics (schema validity, validator pass rate, citation coverage, hallucinated-place rate = 0 by construction, travel-time feasibility, budget adherence) + LLM-as-judge rubric for plan quality, run on curated vs live cities; cost and latency per plan.
8. Observability: per-plan record of model, prompt version, tokens, latency, tools called, sources used.

## 7. Changes by area (proposed names; fixed in Amendment A2)

Backend (Het lead, Manal)
- API: city search (`GET /api/v1/destinations/search?q=`), resolve/create live destination + import job (`POST /api/v1/destinations/resolve`, `GET /api/v1/destinations/{id}/import`), existing places/generation endpoints reused.
- Import job (async, same job runner as generation), caching, rate limiting, minimum-places gate, refresh after N days.
- PlacesProvider interface: OSM implementation + fake implementation (tests). Google left as a future implementation.
- Country → currency/time-zone table (IMD-128 still holds: budget currency = destination currency).

Database (Jeel, Malhar)
- Migration 0008: `destinations.data_tier` (curated|live), `provider`, `external_ref`, `imported_at`, `expires_at`; `places.provider`, `external_id`, `licence`, `fetched_at`; `data_sources` rows for OpenStreetMap, Wikivoyage, Wikipedia. Drift test, downgrade, alembic heads = 1.
- OSM tag → category mapping table and dedupe rules.

AI (Nidhi lead, Manya)
- Live-city prompt variant (prompt v4-live) with tier labels; tools for function calling; self-repair round.
- Guide ingestion from MediaWiki (+ optional Firecrawl allowlist), chunking/embedding with the existing pipeline.
- Optional Maps/Search grounding step behind its own switch `live_grounding` (off unless a paid-tier key is configured).
- Evaluation set `trips/live-v1` (6–10 cities, mixed sizes) + report comparing curated vs live.

Frontend (Manasvi lead, Krrish)
- City search with autocomplete; "Building your city…" progress (import job states); "not enough data" state.
- Source badges per stop, tip and cost; "price unknown" chips; attribution footer (OSM, Wikivoyage, Google Maps when grounding used).
- Accessibility (axe, keyboard, 360 px) and E2E with the fake provider; @live tag.

DevOps / Security (Kirtan minimal, Junaid)
- Keys in AWS SSM (Firecrawl optional; Gemini paid-tier key only if grounding is used) with spend caps; User-Agent/contact for OSM services.
- Injection corpus extended with web-text cases; allowlist tests; authz for new routes; security report addendum.

## 8. Schedule (fits the 3 Dec end; hard cutoff 26 Nov)

| Date | Work | Who |
|---|---|---|
| 18 Nov night | Team votes C → planner drafts Amendment A2 + IMD-210 | Planner, team |
| 19 Nov | A2 approved (decision commit by Nidhi); keys created if wanted (Firecrawl free; Gemini paid tier with $5 cap optional) | Nidhi, Kirtan |
| 19–20 Nov | Batch C1: migration 0008, PlacesProvider (OSM + fake), Nominatim/Overpass clients with cache + rate limit, import job, city search/resolve API, currency table | Het, Manal, Jeel, Malhar |
| 21–22 Nov | Batch C2: guide ingestion (MediaWiki, optional Firecrawl allowlist), agentic planner tools + self-repair, prompt v4-live; frontend city search, progress, badges, unknown-price chips | Nidhi, Manya, Manasvi, Krrish |
| 23 Nov | Batch C3: E2E @live (fake provider), injection/allowlist tests, authz, evaluation run `trips/live-v1`, optional grounding step | Krrish, Junaid, Nidhi, Manya |
| 24 Nov | Staging window: real providers for 3–5 cities; record results | Kirtan, Het |
| 25 Nov | Fix round (one) | owners |
| **26 Nov** | **Cutoff:** green with switch OFF (full suite) and ON (@live + eval) → merge, switch available. Otherwise stays on its branch; final report shows it as designed future work | Planner, operator |
| 18–23 Nov (parallel) | Batch B (IMP-705/706/707/703), staging window for SG items | as planned |
| 26–27 Nov | SG-7 release candidate | Kirtan |
| 28 Nov–3 Dec | Production deploy, rehearsal fixes, report and presentation, SG-8, buffer | Sprint 8 owners |

## 9. Risks and controls

| Risk | Control |
|---|---|
| Release gates slip | Cutoff 26 Nov; switch OFF keeps today's app; separate branch until green |
| Public OSM servers throttle | One Overpass query per city, cached; 3–5 demo cities pre-imported in staging; retry with backoff; fake provider in tests |
| Poor data for small cities | Minimum-places gate with a clear message; suggest nearest larger city |
| Prompt injection via web text | Quoted-data prompting, filters, allowlist, new security tests |
| Gemini quota | Pre-import demo cities; embeddings cached; grounding optional and capped |
| Licence problems | Only ODbL/CC BY-SA/allowlisted sources stored; Google content not stored (IDs only) |
| Kirtan overload | DevOps share kept to keys + one staging run |

## 10. Demo script (2 minutes)

1. Ahmedabad (curated): "verified" badges, exact costs.
2. Type a new city (e.g. Udaipur or Jaipur, pre-imported): progress → plan with OpenStreetMap/Wikivoyage badges, real travel times, "price unknown" chips, citations.
3. Optional: "Check live" → Google Maps grounding confirms hours for today's stops with Maps attribution.
4. Show the evaluation table: curated vs live validity, citation coverage, latency, cost.
5. Kill the provider (switch to fake failure) → graceful message; curated city still works.

## 11. Decisions needed from the team

1. Vote C (vs A or B).
2. Optional extras: Firecrawl allowlist (yes/no); Gemini paid-tier key with spend cap for Maps/Search grounding (yes/no; if no, step [5] is skipped).
3. Leads: Het (backend), Nidhi (AI), Manasvi (frontend); support as in section 7.
4. Demo cities to pre-import (3–5).
