# Deferred functionality (SG-6, IMP-699)

What the MVP feature freeze leaves unfinished, switched off or not started, with owner, reason and due date. Written by the SG-6 gate (RUN-080) on 16 November 2026 at `main` `fd7ae14`; see [gates.md, SG-6](gates.md#sg-6-end-of-week-6-mvp-feature-freeze-imp-699) and [sprint-6.md](sprint-6.md). Later gates update this file instead of starting a new one.

## Unfinished cards and stories

| Item | Card / story | Owner | Reason | Due |
| --- | --- | --- | --- | --- |
| Demo destination 2: curated places, import report against the minimum, source, licence and checked-on date on every row | IMP-603 (DATA, 5 points) · US-027, NFR-040 | Junaid (lead), Manya, Kirtan | Waiting for the members' curated files: place data and guides of real destinations are written by members (Amendment A1 §6.3) | Thu 19 November 2026; without the files destination 2 is recorded as deferred and the 5 points stay pending (IMD-201) |
| Usability session 1: five sessions with participant codes, findings with severity, top issues as backlog items | IMP-611 (HUMAN, 3 points) · US-142, NFR-027 | Junaid (lead), Krrish | Templates merged (#281); the session needs the staging deployment | In or right after the staging window of Wed 18 November 2026; findings scheduled for Sprint 7 (IMP-704) (IMD-201) |
| Discovery interviews: anonymous notes with participant codes; PR #201 (open, draft) | IMP-114 · US-151 | Junaid, Krrish | Human activity not yet recorded | Thu 19 November 2026 (carried from SG-4) |
| Ahmedabad saved samples (FR-036 AC3) | IMP-217 follow-up | Jeel | Waiting for two trip inputs | no date set (carried from SG-4) |

## Switches disabled

| Switch | Kind | State | Reason | Owner | Due |
| --- | --- | --- | --- | --- | --- |
| `versions`, `trip_management`, `contingency`, `budget_alerts`, `wishlist`, `alternatives`, `regeneration`, `locks`, `meal_slots` | MVP cut list (cut order 1 to 9, §1.2) | **all on**: no cut-list switch is applied in any configuration (`FEATURES_DISABLED` default `""` in `apps/api/app/core/config.py`; empty in `.env.example` and the workflows) | Every MVP-S feature is built (IMD-167, IMD-201); the floor journey with all nine off is green (TC-372, SG-6 row 2c) | Kirtan | — |
| `ranking_explain`, `nl_intake`, `day_explain`, `optimise_order`, `rain_swap`, `today_view`, `budget_fit`, `context_cards`, `packing` | Extensions (§2.5) | off **by decision**, not by configuration: never built, so there is no route, table or screen for a switch to hide (IMD-187 reasoning) | Extensions cut (IMD-65; IMP-515 and IMP-612 also IMD-186) | Kirtan | — (not built in this release) |

## Extension cards cut (IMD-65)

IMP-515 (`ranking_explain`), IMP-612 (`optimise_order`), IMP-613 (`packing`), IMP-708 (`nl_intake`), IMP-709 (`day_explain`), IMP-710 (`rain_swap`), IMP-711 (`today_view`), IMP-712 (`budget_fit`), IMP-713 (`context_cards`). Not built; no 501 placeholder routes exist for them (OpenAPI holds the 36 MVP operations only).

## Tier 1 (T1) items not started

Outside the release (§2.6); no task, endpoint, table or screen of Sprints 1 to 8 builds them. Owner: none assigned; they are not scheduled.

| Requirement | Title | Related contract |
| --- | --- | --- |
| FR-021 | Suggest nearby places | API-18 |
| FR-090 | Track bookings with a checklist | — |
| FR-091 | Suggest weather-aware clothing | — |
| FR-097 | Export an itinerary to PDF | — (the IMP-609 print view is the MVP substitute) |
| FR-098 | Share a read-only view | API-39 to API-41, MOD-B11 |
| FR-110 | Record booking links and confirmation references | — |
| FR-111 | Record place feedback | API-42 |
| FR-112 | Record saved and rejected signals | API-42 |

## AI prompt and evaluation

| Item | Owner | Reason | Due |
| --- | --- | --- | --- |
| itinerary_generate v3 stays inactive; v2 is the MVP prompt | Manya | IMD-195 gate not met in RUN-079 (Gemini v3: 14 duplicate-place items in 3 of 45 attempts); the gate is not relaxed (IMD-200) | — |
| Optional v4 with stronger place-uniqueness wording, evaluated by the IMD-195 procedure with one Gemini run | Manya | Sprint 7 hardening, only when the free-tier quota allows (IMD-200) | Sprint 7 |
| The model writes "AI-written" into its notes and reuses places for meals under v2 (baseline-1) | Manya, Nidhi | Fix is in v3, which is not activated (IMD-180, IMD-181, IMD-200) | Sprint 7 (with v4) |
| Final evaluation baseline and cost report | Nidhi | Sprint 7 card IMP-705 (FR-120 follow-up) | Sprint 7 |

## Staging items (staging off, IMD-137)

All in one staging window by **Wednesday 18 November 2026** (IMD-186, IMD-201). Owners Kirtan, with Het for the Gemini key.

| Item | Owner | Source |
| --- | --- | --- |
| Full primary journey on staging with GEMINI: sign in, create, generate, validate costs, edit, regenerate a day, restore a version, summary | Kirtan, Het | IMP-699 step 3 |
| `make smoke URL=<staging api url>` with the new cases of `apps/api/tests/smoke/test_deployed.py` | Kirtan | IMP-699 tests |
| Gemini `config_error` on staging: compare the key in SSM with the working local key, redeploy | Kirtan, Het | SG-4, SG-5 |
| SG-5 staging items: journey with all Sprint 5 functions, timeout fallback (IMD-33), generation cap 429 | Kirtan | SG-5 rows 3 to 6 |
| SG-4 and SG-3 staging items: edit totals in one response, RAG index line, ACC-19, NFR-050 p95, TC-438, CORS, IMP-216 walk-through, IMP-206 load | Kirtan, Het | SG-4 |
| Usability session 1 (IMP-611) on staging | Junaid, Krrish | IMD-201 |

## Evidence gaps carried from the part records

| Item | Owner | Due |
| --- | --- | --- |
| IMP-608: budget alert banner in the itinerary cost strip (no cost strip exists on the itinerary page) | Krrish, Manal | Sprint 7 (defect triage) |
| IMP-609: manual print preview with screenshot | Krrish | no date set |
| IMP-610: versions page screenshot after a restore | Jeel | no date set |
| Screenshots of the Sprint 5 and SG-4 screens; 44 px targets at 375 px | Malhar, Krrish, Manasvi | no date set |
| TC-385 live-stack label review | Manasvi | no date set |
| TC-382 manual screen-reader pass | Krrish | IMP-703 (Sprint 7) |
