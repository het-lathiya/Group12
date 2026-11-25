# Demo script (six minutes)

**DRAFT — completed after SG-7 (IMP-801): rehearsed and timed on the deployed release by Nidhi and the presenter**

| Item | Value |
| --- | --- |
| Card | IMP-801, part "Demo script and backup video" (US-147 AC1, AC2; CHK-17) |
| Owner | Nidhi |
| Presenter | pending (team) |
| Release shown | pending (IMP-801: tag and commit) |
| Switch `any_city_mode` in production | pending (Kirtan, IMP-801, under the conditions of IMD-220) |
| Measured total time | pending (rehearsal, [rehearsal-log.md](rehearsal-log.md)) |

The target of about six minutes is US-147 AC1. The times below are **targets to rehearse against, not measurements**. The card names the 12 steps of blueprint §31.7; the blueprint is not in this repository, so the script follows the specification's primary journey (§1.6) and the features that shipped. Nidhi checks it against the blueprint before the first rehearsal.

Screen texts are quoted from the app and the [user guide](../guides/user-guide.md). If a text differs on the day, say what the screen says.

## Before starting

- The [pre-demo checklist](pre-demo-checklist.md) is complete.
- Demo account signed out; account names and passwords are never written in this repository: pending (Jeel).
- Two browser tabs prepared: the app, and the saved sample itinerary: pending (Jeel).
- Choose the path: **A** if the switch is ON in production and the demo city is imported, else **B**.

## Path A — switch ON

| # | Segment | Target | What to do | What to say and show |
| --- | --- | --- | --- | --- |
| 1 | Sign in | 0:00 to 0:30 | Open the landing page, sign in, show the dashboard | Only a signed-in traveller sees their own trips |
| 2 | Create a trip in the curated city | 0:30 to 1:30 | Create a trip for Ahmedabad: dates, travellers, a budget; interests and pace; one must-visit place; Review | The list shows which preferences filter, which rank and which are notes only |
| 3 | Generate | 1:30 to 2:15 | **Generate itinerary**, the privacy notice if it appears, then the progress steps | Gemini proposes from a shortlist of stored places; code checks every place, time and price. If the plan is rule-based, use the fallback lines below |
| 4 | Read and edit | 2:15 to 3:30 | Open a stop's sources; move or remove one stop; show **Plan checks** | Every edit recalculates times, travel and costs; labels say what is curated, estimated or unavailable |
| 5 | Costs | 3:30 to 4:00 | Open **Costs** | Labelled estimate, contingency and the budget status; no booking and no live price (IMD-46) |
| 6 | Any city | 4:00 to 5:30 | New trip; in **Any city (live data)** search a pre-imported demo city (Jaipur, Udaipur or Mumbai); choose it; show "Ready: … places from OpenStreetMap"; open the prepared live trip | The **Live data** badge, the **OpenStreetMap** badges, **Price unknown** and **Hours unknown**, "Known costs only" on Costs, and the **Data sources** footer with the OpenStreetMap attribution. Live places are not checked by the team |
| 7 | Close | 5:30 to 6:00 | Open the summary | What is cut and what is next: see the [release notes](../release-notes/v1.0-mvp.md) |

Never import a new city in front of the audience: the import uses public services and can be slow or refused.

## Path B — switch OFF

Everything stays on curated Ahmedabad, and no any-city control is on screen.

| # | Segment | Target | What to do |
| --- | --- | --- | --- |
| 1 to 5 | As path A, rows 1 to 5 | 0:00 to 4:00 | Same |
| 6 | Versions and restore | 4:00 to 5:00 | Save a version, change a stop, restore the version |
| 7 | Map and summary | 5:00 to 5:40 | Show the day on the map (or its list), then the printable summary |
| 8 | Close | 5:40 to 6:00 | Say that any-city mode is "built but disabled" (IMD-215), and show the release notes |

## If Gemini is unavailable

Gemini can answer "high demand" (reported by the operator, [live-v1-gemini-2026-11-25.md](../../eval/reports/live-v1-gemini-2026-11-25.md) section 4). The app then builds the plan by rules and shows above it: "Built by rules because the AI service was unavailable or its answer failed checks". Say that this is the designed fallback (IMD-33, FR-036): a normal, usable plan, with no AI-written notes. Do not retry on stage more than once. If the page says the daily AI limit is reached, choose **Build a rule-based plan**.

If production itself does not answer, use the MOCK stack on the presenter machine ([README.md](README.md)) and say that its data is SAMPLE. If that fails too, play the backup video.

## What not to claim

- No timing, quality or reliability figure that the final report does not state.
- No booking, payment or live price.
- No result of a staging or production check that has no record.
