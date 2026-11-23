# IMP-728 · wording part (one live label across the trip form)

- Card: IMP-728 Web: city search, import progress and the switch (Amendment A2 §9.1, §9.2; 0 points)
- Part: wording (follow-up of the RUN-091 open issue "(Live data)" vs "(live data)")
- Run id: RUN-092 (Batch C3, Sprint 7, inserted under IMD-215)
- Owner: Manasvi (Manasvi Rathore)
- Status: PR_OPEN candidate on `feat/S7-C3-any-city-verify`
- Base commit: 818c1d8 (on `main`)
- Traces to: A2 §9.1, §9.2 (TierBadge "Live data"); TC-482, TC-483

## Changed files

- `apps/web/components/trips/TripDetailsStep.tsx`: the destination option of a city chosen through the search now reads "{name} (Live data)", the same form as the resumed-draft option and the TierBadge. One line changed.
- `apps/web/tests/unit/trips/CitySearch.test.tsx` (written in RUN-090): the one option-name assertion now expects "Udaipur (Live data)". `TripDetailsStep.live-draft.test.tsx` already checks the resumed-draft option "Udaipur (Live data)", so both options are covered.

The A2 §9.1 field label "Any city (live data)" and the hint text stay as the amendment writes them. With the switch OFF, the form is unchanged: the option only exists for a live destination.

## Floor-journey defect

STEP 0 of RUN-092 found the cause in the E2E spec, not in the trip form. The fix and the diagnosis are in `docs/progress/parts/IMP-730-whole-task.md` (Krrish). This part holds only the wording change.

## Commands

| Command | Result line |
| --- | --- |
| `make test-web ARGS='CitySearch TripDetailsStep'` | Test Files  2 passed (2) · Tests  22 passed (22) |
| `npx prettier --check` (the two files) | All matched files use Prettier code style! |

The full `make check` ran once on the branch head. Its lines are in the SYNC REPORT of RUN-092.

## Acceptance

- One live label form, "(Live data)", across the trip form's destination options: **verified** by `CitySearch.test.tsx` (search option) and `TripDetailsStep.live-draft.test.tsx` (resumed draft).
- Switch OFF unchanged: **verified** by the existing switch-OFF tests in both files, which still pass.

## Proposed decisions

none

## Blockers and open issues

none
