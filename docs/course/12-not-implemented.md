# 12 Not implemented

| Item | Value |
| --- | --- |
| Course document | 12 of the IT314 set ([index](README.md)), IMD-221 |
| Owner | Jeel Fefar |
| Built from | `docs/spec/IMPLEMENTATION_SPEC.md` §2.5 and §2.6, [Amendment A2 §1.2 and §1.3](../spec/AMENDMENT_A2_ANY_CITY.md), [DECISION_REGISTER](../spec/DECISION_REGISTER.md), [deferred.md](../progress/deferred.md), the card status table in [sprint-7.md](../progress/sprint-7.md), and `main` at `77e52ba` |

This document lists what the project does not build, or has not finished, with the reason recorded for each item.

## 1. Extensions cut (IMD-65)

All nine extensions are cut. IMD-65 cut 26 parts and 57 points. They are not built, there is no route, table or screen for them, and their switches stay off. The OpenAPI contract holds only the MVP operations ([deferred.md](../progress/deferred.md)).

| Card | Title | Points | Lead | Requirements | Switch (cut order) |
| --- | --- | --- | --- | --- | --- |
| IMP-515 | Explain the ranking: "Why this place?" panel | 4 | Jeel | FR-127 | `ranking_explain` (9 of 9) |
| IMP-612 | Optimise day order to cut travel time | 8 | Het | FR-130 | `optimise_order` (6 of 9) |
| IMP-613 | Packing checklist with AI free-text refinement | 9 | Kirtan | FR-088, FR-135 | `packing` (1 of 9) |
| IMP-708 | Natural-language trip intake with confirmation | 8 | Nidhi | FR-128 | `nl_intake` (8 of 9) |
| IMP-709 | "Why this plan" explanations for each day | 5 | Nidhi | FR-129 | `day_explain` (7 of 9) |
| IMP-710 | Rain-aware day swapping with the Open-Meteo forecast | 7 | Manal | FR-131 | `rain_swap` (5 of 9) |
| IMP-711 | "Today" companion view for trip days | 3 | Manasvi | FR-132 | `today_view` (4 of 9) |
| IMP-712 | Budget-fit suggestions when a plan is over budget | 7 | Junaid | FR-133 | `budget_fit` (3 of 9) |
| IMP-713 | Destination and place context cards from Wikivoyage and Wikipedia | 6 | Malhar | FR-134 | `context_cards` (2 of 9) |

As a result, the backend modules prep, weather and context, and the tables of extension migrations 0007 to 0010 of Appendix A, do not exist (IMD-65, IMD-113). The `0007` that does exist is `0007_rag_store` (Amendment A1).

**Cut-list switches of the MVP.** These are different from the extensions. `versions`, `trip_management`, `contingency`, `budget_alerts`, `wishlist`, `alternatives`, `regeneration`, `locks` and `meal_slots` are built and all ON. No cut-list switch is applied in any configuration (IMD-167, [deferred.md](../progress/deferred.md)).

## 2. Requirements outside the release

These keep their IDs, but no task, endpoint, table or screen of Sprints 1 to 8 implements them (specification §2.6). Release codes: R2 = Release 2, T1 = Tier 1 (optional), PP = post-project, Stage 2 = fine-tuned model stage.

| Release | Requirements |
| --- | --- |
| Tier 1 (T1) | FR-021 nearby places, FR-090 booking checklist, FR-091 weather-aware clothing, FR-097 PDF export (the IMP-609 print view is the MVP substitute), FR-098 read-only share view, FR-110 booking links and references, FR-111 place feedback, FR-112 saved and rejected signals |
| Release 2 (R2) | FR-006 account and data deletion, FR-070 natural-language modification, FR-077 cheaper alternatives, FR-081 transport to the destination, FR-082 local transport, FR-084 and FR-085 accommodation, FR-086 events calendar, FR-089 documents checklist, FR-093 reminders and emergency resources, FR-096 plan comparison, FR-099 to FR-106 receipts and expenses, FR-107 to FR-109 booking tasks and readiness |
| Post-project (PP) | FR-087 ratings and reviews, FR-092 local tips, FR-113 learning from feedback |
| Stage 2 | FR-048 fine-tuned model adapter (only the `FineTunedProvider` stub exists), FR-049 provider switching with a gate and rollback, FR-121 migration gate, FR-122 governed training data. Stage 2 go or no-go is not decided (OD-13); IMP-706 produced a readiness package of documents only |

**Excluded by decision (IMD-46).** The project never builds in-app flight or hotel booking, payments, live prices or any booking claim.

## 3. Any-city mode limits (Amendment A2)

### 3.1 Cut from any-city mode (A2 §1.2, future work)

- A function-calling ("agentic") planner. The model keeps the gr-2 and io-2 contract.
- Firecrawl or any scraping of web pages.
- Google Maps grounding, Google Search grounding, the Google Places API and the switch `live_grounding`.
- A paid Gemini key, or any spend beyond the existing free key.
- LLM-as-judge evaluation.
- Parsing the OpenStreetMap `opening_hours` tag. Live places have no hours rows, so their hours are shown as unknown.
- Prices from OpenStreetMap `fee` or `charge` tags or from guide text. Live places have no price.

### 3.2 Limits of what is built

| Limit | Source |
| --- | --- |
| The mode works only behind the switch `any_city_mode`. It is ON only when `!any_city_mode` is listed in `FEATURES_DISABLED` | A2 §3.1, `app/core/config.py` |
| Live destinations need a supported country and currency; others answer 422 | A2 §5, `app/livedata/countries.py` |
| A city with fewer than `LIVE_MIN_USABLE_PLACES` (default 40) usable places ends `insufficient_data` and names a larger nearby city | A2 §6.4 |
| Import caps: `LIVE_DAILY_IMPORTS_PER_USER` (default 5) and `LIVE_DAILY_IMPORTS_GLOBAL` (default 50) | A2 §7.2 |
| Public Nominatim, Overpass and MediaWiki usage rules: at most 1 Nominatim request per second, no type-ahead, at most 2 guide pages per import | A2 §7.3 |
| If the guide source fails, the import completes without guide documents and plans cite no guide passage | IMD-218 |
| Prompt `itinerary_generate/v4` exists but is not active; v2 stays active | IMD-220 (e), IMD-200 |
| The production switch state depends on the IMD-220 (c) checks (ACC-20 to ACC-23 on staging, demo cities imported with real providers, attribution footer, a real `WIKI_USER_AGENT`). At `77e52ba` ACC-20 to ACC-23 are "pending" and the switch state at release (CHK-26) is "to be recorded at the cutoff". If the checks fail, production ships OFF and the final report says "built but disabled" | IMD-215, IMD-220, [acceptance/any-city.md](../acceptance/any-city.md) |

## 4. Open human items (pending at `77e52ba`)

From the SG-7 card status table ([sprint-7.md](../progress/sprint-7.md)), checked against the commits up to `77e52ba`. No later commit closes any of them.

| Card | Item | Owner | Why it is still open |
| --- | --- | --- | --- |
| IMP-113 | Accounts, keys and email sender: account facts (Gemini tier, ORS key and email sender) | Kirtan, Junaid, Nidhi | Templates merged (#200); `docs/decisions/accounts.md` still reads "template; outcome pending" |
| IMP-114 | Stakeholder interviews round 1 with anonymous notes (US-151) | Junaid, Krrish | PR #288 open (#201 closed); the human activity is not recorded |
| IMP-603 | Demo destination 2: curated places and load | Junaid, Manya, Kirtan | No part record; `data/places/` holds only `ahmedabad`. Real destination data and guides are written by members only (A1 §6.3); deferred under IMD-201 |
| IMP-611 | Usability session 1 (five sessions) and findings | Junaid, Krrish | Templates merged; `docs/acceptance/usability-1/findings.md` is an empty template; the session needs staging |
| IMP-703 | Device and screen-reader accessibility sessions (TC-382), findings and fixes | Junaid (runs), Krrish (records) | Preparation merged; [accessibility-sprint7.md](../test-reports/accessibility-sprint7.md) sections 2 to 5 are empty |
| IMP-704 | Usability session 2 and fixes of the top issues | Manasvi, Junaid | Not started; needs IMP-611 session 1 |
| IMP-706 | Confirm E1 to E7 and the blueprint-based content of the Stage 2 package | Manya | Done with an open item |
| IMP-707 | Card step 6 trials of the README setup and deployment guide by a member outside the platform squad | see [sprint-7.md](../progress/sprint-7.md) | Done with an open item |

## 5. Sprint 8 work not done at `77e52ba`

| Card | What is missing | Source |
| --- | --- | --- |
| IMP-801 | Production deployment, production smoke tests, release tag and backup video; only the demo script and release notes drafts exist | [02-sprints/sprint-8.md](02-sprints/sprint-8.md) |
| IMP-802 | Rehearsal defect fixes: not started (needs the IMP-801 rehearsal) | same |
| IMP-803 | Pre-demo checklist: drafts exist, the checklist is not run | same |
| IMP-804 | Final report and presentation: drafts exist; human completion and the claims-check review pending | same |
| IMP-899 | Gate SG-8: not run | [gates.md](../progress/gates.md) |

## 6. Staging items carried since SG-3

Staging is off between planned windows (IMD-137). The SG-3 to SG-7 staging criteria were carried as open items for Kirtan's staging windows: the full journey with Gemini, `make smoke`, the timeout fallback demo, the 429 cap, the RAG index line and the NFR-050 retrieval p95 ([deferred.md](../progress/deferred.md), [gates.md](../progress/gates.md)). Their results after 22 November 2026 are not recorded at `77e52ba`.
