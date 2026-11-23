# IMP-728 · draft-destination part (web: resumed draft shows its live destination)

- Card: IMP-728 Web: city search, import progress and the switch (Amendment A2 §3.1, §9.1; 0 points)
- Part: draft-destination (fix for the first open issue of RUN-090)
- Run id: RUN-091
- Owner: Manasvi (Manasvi Rathore)
- Status: PR_OPEN
- Base commit: 667c0d8
- Traces to: IMD-128, IMD-210; A2 §3.1, §9.1; TC-482, TC-483

## Changed files

- `apps/web/components/trips/TripDetailsStep.tsx`: with the switch `any_city_mode` ON, when the resumed draft's `destination_id` is not in the API-06 list, the step reads it with the existing `useDestinationDetail` (API-79). Once that answer arrives, the step adds it to the select as "{name} (Live data)", selects it, and takes its currency from the answer (IMD-128). The hook gets an empty id (so it stays disabled) when the switch is OFF, when the draft has no destination, while API-06 is loading, or when the id is in the API-06 list. While API-79 is loading or after it fails, the select behaves as before. The select's label ("Destination") is unchanged. No API, contract or `queries.ts` change.
- `apps/web/tests/unit/trips/TripDetailsStep.live-draft.test.tsx` (create, 4 tests): ON + live draft (selected entry, "Live data" text, accessible name, currency, exactly one API-79 request, axe); ON + API-79 failure (unchanged, no crash); ON + curated draft (unchanged, no API-79 request); OFF + unknown id (unchanged, no any-city request, axe).
- `docs/progress/parts/IMP-728-draft-destination.md` (this record).

## Commands

| Command | Result line |
| --- | --- |
| `make test-web ARGS='TripDetailsStep'` | `Test Files  1 passed (1)` · `Tests  4 passed (4)` |
| `make test-web` | `Test Files  47 passed (47)` · `Tests  329 passed (329)` |
| `cd apps/web && npx tsc --noEmit -p .` | no output, exit 0 |
| `npx eslint` on the two files | no findings, exit 0 |
| `npx prettier --check` on the two files | `All matched files use Prettier code style!` |

`make check` and `make e2e` were not run in this run.

## Acceptance

- A resumed live draft shows its destination (switch ON): **verified** by the test "shows the live destination selected with its tier as text". It checks that the selected option is "Udaipur (Live data)", the value is the live id, the accessible name stays "Destination", the currency is INR, and axe finds nothing.
- Switch OFF unchanged: **verified** by the test "an unknown draft id is unchanged and makes no any-city request" (no live option, no any-city control, no any-city request, axe finds nothing).
- ON + curated draft unchanged with no API-79 request, and ON + API-79 failure without a crash: **verified** (tests 2 and 3).
- 360 px screenshot of the resumed draft: **not verified**. Screenshots are taken in C3 (IMP-730).

## Open issues

- When the switch is OFF, or API-79 fails, a resumed live draft still has no selected option in the select. In jsdom and in browsers the select shows no entry, not "Choose a destination". The form value is still the saved id. This is the same as the behaviour before this fix.
- The live-search option keeps its existing lowercase "(live data)" label. The resumed-draft option uses "(Live data)", as this fix asked. Aligning the two wording is a copy decision for C3.

## Proposed decisions

none

## Blockers

none
