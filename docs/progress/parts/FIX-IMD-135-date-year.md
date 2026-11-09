# FIX IMD-135 · date-year

| Field | Value |
| --- | --- |
| Run | RUN-058 (grouped run, IMD-121), part 6 of 7 |
| Decision | IMD-135 Source retrieval dates show the year (PD-IMP-317-2) |
| Owner | Manasvi Rathore |
| Status | PR_OPEN |
| Base commit | 16839a0 |
| Branch | feat/IMP-410-411-412-trips-budget-states |

## Where the date was formatted

The retrieval date is formatted in `apps/web/components/itinerary/ItemSources.tsx`, the IMP-317 sources disclosure, through `formatDayDate` from `apps/web/lib/format.ts`. It is not formatted inside `ItineraryItemCard.tsx`, so this part was not skipped and that file was not edited.

## Changed files

- `apps/web/lib/format.ts`: adds `formatFullDate` ("2026-10-31" becomes "31 Oct 2026", read in UTC). `formatDayDate` ("Sat 14 Nov") is unchanged for day labels.
- `apps/web/components/itinerary/ItemSources.tsx`: "Retrieved <date>" now uses `formatFullDate`.
- `apps/web/tests/unit/itinerary/ItemSources.test.tsx`: expects "Retrieved 14 Nov 2026".
- `apps/web/tests/unit/lib/format.test.ts` (created): the year format and the unchanged day format.
- `docs/progress/parts/FIX-IMD-135-date-year.md`: this record.

## Commands

| Command | Result |
| --- | --- |
| `npx vitest run ItemSources format` | `Tests  16 passed (16)` |
| `make test-web` | `Tests  145 passed (145)` |
| `make lint` | `All checks passed!`; ESLint `✖ 1 problem (0 errors, 1 warning)`, a warning that predates this run; `All matched files use Prettier code style!` |
| `make typecheck` | `Success: no issues found in 111 source files` |

## Acceptance

| Criterion | Status | How |
| --- | --- | --- |
| IMD-135: source retrieval dates show the year, for example "31 Oct 2026" | verified | `format.test.ts` "IMD-135: source retrieval dates show the year"; `ItemSources.test.tsx` |

## Proposed decisions, blockers and open issues

None. The hours badge's "checked on <date>" (SourceBadge) still uses the short day format. IMD-135 covers only retrieval dates.
