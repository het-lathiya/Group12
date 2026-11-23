# IMP-728 · whole-task part (web: switch, city search, import progress)

- Card: IMP-728 Web: city search, import progress and the switch (Amendment A2 §3.1, §9.1, §12; 0 points)
- Part: whole card
- Run id: RUN-090 (Batch C1b, Sprint 7, inserted under IMD-215)
- Owner: Manasvi (Manasvi Rathore)
- Status: PR_OPEN candidate on `feat/S7-C1b-any-city-import`
- Base commit: 4c4df80 (on `main`)
- Traces to: IMD-11, IMD-47, IMD-128, IMD-210, IMD-216 (PD-A2-1); A2 §3.1, §5, §9.1; TC-460 (web), TC-482, TC-483

## Changed files

- `apps/web/lib/flags.ts`: `DEFAULT_OFF_FEATURES = ["any_city_mode"]` kept outside `FEATURE_NAMES`, type `DefaultOffFeatureName`. `isEnabled` accepts both kinds of name; a default-off name is ON only with `!any_city_mode` listed and `any_city_mode` not listed. Every other name behaves as before. `flags.test.ts` and `playwright.config.ts` are unchanged.
- `apps/web/lib/api/anyCityClient.ts` (create): a second openapi-fetch client typed by `any-city-schema.d.ts`. It reuses `apiOrigin` and `authFetch` from `client.ts` (bearer token, request id, 401 handling).
- `apps/web/lib/api/queries.ts`: `useCitySearch` (only for a submitted term), `useResolveCity` (seeds the import-status cache), `useImportStatus` (polls at 2/3/4/5 s, then 5 s, and stops at `completed`, `insufficient_data` or `failed`) and `useDestinationDetail` (API-79). Each is enabled only when `isEnabled("any_city_mode")`, so with the switch OFF no any-city request is made.
- `apps/web/components/trips/CitySearch.tsx` (create): the "Any city (live data)" field and Search button below the existing select. Search runs on submit only (button or Enter; Enter does not submit the trip form), with result buttons like "Udaipur, Rajasthan, India · city", the line "Search by Nominatim · © OpenStreetMap contributors", the exact §9.1 hint, and 422/503 messages from the error envelope. It renders nothing when OFF.
- `apps/web/components/trips/ImportProgress.tsx` (create): the §9.1 states with exact copy in a polite `role="status"` region, with an icon and text (no colour-only meaning). `insufficient_data` offers a button that searches `nearby_city`; `failed` offers "Try again" (resolve queues a failed import again, A2 §6.1).
- `apps/web/components/trips/TripDetailsStep.tsx`: with the switch ON, `CitySearch` sits below the select. A completed live destination is added to the select as "{name} (live data)" and chosen, and the currency comes from `LiveDestinationOut.currency` (IMD-128). OFF: same output and behaviour as before (the "Sampleton (sample)" pick is tested).
- `apps/web/components/trips/PlacesStep.tsx`: when API-79 says the destination is live and its import is not completed, the step shows "Places can be chosen once your city is ready: its live data is still being built." and nothing else. OFF: unchanged (API-79 is not called).
- `apps/web/tests/unit/trips/CitySearch.test.tsx` (create, 18 tests), `apps/web/tests/unit/trips/ImportProgress.test.tsx` (create, 12 tests), `apps/web/tests/unit/lib/flags.default-off.test.ts` (create, 7 tests): TC-482, TC-483, the token rule, keyboard operation and the repository's axe helper on both components.
- `docs/progress/parts/IMP-728-whole-task.md` (this record).

## Commands

| Command | Result line |
| --- | --- |
| `make test-web ARGS='CitySearch ImportProgress flags'` | `Test Files  4 passed (4)` · `Tests  40 passed (40)` |
| `make test-web` | `Test Files  46 passed (46)` · `Tests  325 passed (325)` |
| `npm run lint --prefix apps/web` | no findings |
| `npm run format:check --prefix apps/web` | `All matched files use Prettier code style!` |
| `npm run typecheck --prefix apps/web` | `✓ Types generated successfully` (tsc: no errors) |

`make check` and the other run checks ran once on the branch head; result lines in the SYNC REPORT of RUN-090.

## Acceptance

- OFF: no control is rendered and no request is made: **verified** (TC-482 tests).
- ON: every state of §9.1 renders its exact copy: **verified** (TC-483 tests).
- Search calls happen only on submit: **verified** (typing alone sends no request).
- Keyboard and axe pass: **verified** in component tests (axe helper, keyboard operation). 360 px without overflow: **not verified** — screenshots in C3 (IMP-730).
- Screenshots at 360 and 1280 px: **not verified — screenshots in C3 (IMP-730)**. No local stack was started, and no `.env` file was read.

## Open issues

- A resumed draft with a live destination shows "Choose a destination" in the details select, because API-06 lists curated destinations only. The form value and currency stay correct. A fix needs API-79 in the details step or a change in `TripWizard` (not in this card's files).
- A search result marked `data_tier: curated` would be picked in the select directly (`onPickCurated`) instead of resolved. Curated destinations have no OSM reference, so API-76 does not mark any result curated today; the branch is a guard.
- The places-step lock is a safety net: trip create already refuses a live destination until its import is completed.
- The web caches a search answer for 5 minutes (on top of the API's 24 h cache).

## Proposed decisions

none

## Blockers

none
