# GUI testing

RUN-099 · IMD-221 · owner: Krrish. Browser evidence is the latest completed E2E push run for
`77e52ba`: [E2E 45678353192](https://github.com/het-lathiya/Group12/actions/runs/45678353192),
conclusion `success`. Its logs were downloaded in this run using
`gh api repos/het-lathiya/Group12/actions/jobs/139431886144/logs` and
`gh api repos/het-lathiya/Group12/actions/jobs/139431885847/logs`.
Extracted raw result lines and provenance are in
[baseline-ci-summary.txt](../test-reports/course/baseline-ci-summary.txt).

## Playwright coverage by journey

Paths below are relative to `apps/web/e2e/`. “No explicit tag” means use the filename filter;
a TC/E2E identifier in a test title is not a Playwright tag.

| Spec file | Journey / IDs | Tag or selector |
| --- | --- | --- |
| `journey.spec.ts` | Combined sign-in → trip wizard → generation → itinerary → edit → costs, TC-369; floor behavior TC-372 | `@journey`; `floor-journey` project when configured |
| `auth.spec.ts` | Registration validation, neutral duplicate-account notice, sign-in/session and sign-out, E2E-01 | No explicit tag; `auth` filename |
| `trip-create.spec.ts` | Invalid date correction and wizard persistence to dashboard, E2E-02 / TC-068, TC-071 | No explicit tag; `trip-create` filename |
| `generate.spec.ts` | Privacy notice, generation progress and itinerary, E2E-03 | No explicit tag; `generate` filename |
| `validate-costs.spec.ts` | Warnings/fixes and costs agreeing with API, E2E-04 | No explicit tag; `validate-costs` filename |
| `itinerary-edit.spec.ts` | Move, retime, remove, lock, regeneration, saved versions and restore, E2E-05 / TC-376 | No explicit tag; `itinerary-edit` filename |
| `reopen.spec.ts` | Reopen saved state and stale-tab recovery, E2E-06 / TC-217 | No explicit tag; `reopen` filename |
| `provider-failure.spec.ts` | Timeout fallback and quota option preserving old data, E2E-07 / TC-371 | `provider-failure` project; timeout/quota scenarios run separately |
| `ownership.spec.ts` | Another user's itinerary, costs and versions stay private, E2E-08 / TC-375 | No explicit tag; `ownership` filename |
| `keyboard.spec.ts` | Core pages and navigation using keyboard only, TC-374 | No explicit tag; `keyboard` filename |
| `map.spec.ts` | Selected day, ordered pins/lines, map/list interaction and unavailable-map fallback | `@map` |
| `live-city.spec.ts` | City search/import → plan/costs; insufficient-data city with nearby option, E2E-10 / TC-486 | `@live` in describe title; CI uses FAKE data and MOCK generation |
| `extensions.spec.ts` | Cut extensions skip with decision reason; hidden entry points / not-found check, TC-432 | `@ext` |
| `smoke.spec.ts` | Landing/dashboard viewport and signed-out redirect; deployed smoke when selected, E2E-09 / TC-377 | `smoke` in test titles; filename selector |

`playwright.config.ts` defines Chromium viewport projects and separate provider-failure/floor
projects. CI runs the journey, map and edit specs across its configured width projects;
the regression step explicitly selects its desktop project. The configuration also retains
failure traces, rejects `test.only` in CI and disables retries. A successful run covers those
selected projects; it does not establish Safari/Firefox or physical-device support.

## Executed baseline result lines

All rows below come from [the downloaded E2E run](https://github.com/het-lathiya/Group12/actions/runs/45678353192),
MOCK on the local CI stack; the source commands are in `.github/workflows/e2e.yml`.

| Step / job | Result line |
| --- | --- |
| Journey / `e2e` | `4 passed (42.0s)` |
| Map / `e2e` | `8 passed (21.3s)` |
| Itinerary edit and restore / `e2e` | `8 passed (52.0s)` |
| Regression / `e2e` | `9 skipped`; `12 passed (24.4s)` |
| Floor journey / `e2e` | `1 passed (15.0s)` |
| Provider timeout / `e2e` | `1 skipped`; `1 passed (6.7s)` |
| Provider quota / `e2e` | `1 skipped`; `1 passed (7.6s)` |
| Any-city / `live` (FAKE, MOCK) | `4 passed (14.4s)` |
| `staging` | skipped — no deployed target supplied |

Regression skips are the cut extension scenarios. Each provider-failure step skips the case
for the other scenario. `live` is a job/tag name for any-city coverage, not proof of live
provider access. These lines are not added together as independent acceptance-case counts.

## Axe accessibility checks

`e2e/axe.ts::checkA11y` waits for animation/toast settlement, runs `@axe-core/playwright` with
layout rules enabled, logs each violation's affected nodes and attaches JSON to the report.
It fails critical violations and annotates serious ones. `expectNoSeriousA11y` additionally
fails serious annotations; the combined journey has its own equivalent serious check.
Consequently, not every caller of `checkA11y` alone enforces the stronger serious-error rule.
`tests/axe.ts` disables color-contrast in jsdom because it has no real layout; that unit helper
cannot prove browser contrast.

The downloaded baseline contains browser axe result lines such as
`axe scan 5 on /trips/new: []` and `axe scan 6 on /trips/new: []`
([E2E job](https://github.com/het-lathiya/Group12/actions/runs/45678353192/job/139431886144)).
An empty violation list applies to that scanned state; it is not a whole-product accessibility
score. [The accessibility report](../test-reports/accessibility-sprint7.md) and
[gates](../progress/gates.md) still leave screen-reader, real-device and usability sessions open.
NFR-025 / TC-374, TC-382, TC-383 remain subject to that manual evidence.

## Manual GUI checklist for the demo

Unchecked means **not run — pending staging window 1 Dec**. Record tester, date, candidate SHA,
provider/scenario, viewport/device, pass/fail and screenshot/defect link for each item.

- [ ] Open the public landing page and verify readable layout, visible focus and navigation.
- [ ] Try invalid registration/sign-in, duplicate account and sign-out/back navigation; confirm
      neutral messages and no private content after sign-out.
- [ ] Create a trip: invalid/reversed dates, maximum length, budget/currency, pace and must-visit
      places. Confirm field messages, back/next preservation and dashboard entry.
- [ ] Accept the privacy notice; generate; observe progress, loading and errors; confirm day/time,
      price labels, warnings, source citations and provider/fallback disclosure.
- [ ] Navigate map and list, select a day/pin, hide the map and simulate unavailable tiles;
      itinerary remains usable from the list.
- [ ] Use keyboard move controls, duration edit, remove and lock; confirm saving feedback,
      focus/announcement, recalculated costs and visible conflicts.
- [ ] Save/reopen, regenerate and restore; try a stale second tab and recover without losing
      the newer plan. Check another user's direct URLs return not-found.
- [ ] Rehearse timeout and quota screens with the approved MOCK scenario; old trip/version data
      remains available and the correct fallback or explicit option appears.
- [ ] Check narrow/wide layouts, zoom, contrast, labels and errors; complete the core journey with
      keyboard and the agreed screen reader on actual demo devices.
- [ ] With any-city mode enabled, inspect successful/insufficient-data imports and attribution;
      keep live-provider results separate from the FAKE CI evidence.

Local full E2E: **not run — operator fast mode; CI covers**. No GUI files were changed.
