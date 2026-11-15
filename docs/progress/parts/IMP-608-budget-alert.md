# IMP-608 · budget-alert

| Field | Value |
| --- | --- |
| Run | RUN-075 (Sprint 6 batch A), part 2 of 2 |
| Card | IMP-608 Budget alerts and contingency buffer |
| Part | BudgetAlert component (2 points), step 4 and the web half of step 5 |
| Owner | Krrish Kamani |
| Status | PR_OPEN (lead integrates) |
| Base commit | a6307c3 |
| Branch | part/b |

## Changed files

- `apps/web/components/costs/BudgetAlert.tsx` (created): one `role="status"` banner for each API-33 alert with the code BUDGET_NEAR or BUDGET_EXCEEDED. Each banner has a text title ("Near budget" / "Over budget"), an icon and the API's message, so it never relies on colour alone (guide §2, §12). The ratio and the excess come from the message, and nothing is computed. The banners are hidden when `budget_alerts` is off.
- `apps/web/components/costs/BudgetSettingsForm.tsx` (modified): adds a "Contingency buffer (%)" field (whole number 0 to 50, zod mirrors the API-34 422). It is sent only when changed, so saving the allowances never touches the buffer. The line under the field shows the API's `contingency.amount`. When `contingency.pct` is 0, or the `contingency` switch is off, the form states "No contingency buffer is included in this estimate." and does not show the field.
- `apps/web/tests/unit/costs/BudgetAlert.test.tsx` (created): 8 cases. Near banner (TC-227). Over banner with the excess (TC-228). No banner for other codes. Hidden with the switch off. The stored percentage and the API's line (TC-229). Saving 25 sends `contingency_pct: 25` and shows the returned line. 51 is refused and nothing is sent. With the switch off the form says no buffer is included and sends no contingency (TC-230).
- `docs/progress/parts/IMP-608-budget-alert.md`: this record.

## Commands

| Command | Result |
| --- | --- |
| `make test-web ARGS='BudgetAlert'` | `Tests  8 passed (8)` |
| `make test-web ARGS='tests/unit/costs'` | `Tests  15 passed (15)`, `Duration  2.93s` (load average 0.77) |
| `npm run lint --prefix apps/web` | `✖ 1 problem (0 errors, 1 warning)`: an existing `no-location-assign` warning in a file this part does not touch |
| `npm run typecheck --prefix apps/web` | exit 0 |
| `prettier --check apps/web/components/costs apps/web/tests/unit/costs` | `All matched files use Prettier code style!` |

Not run: `make e2e` (no Docker on this machine). No screenshots of the banners: the costs page does not render `BudgetAlert` until the wiring below is made.

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-074 AC1: near-budget banner at 92 percent (TC-227) | verified (component) | `TC-227: …` in BudgetAlert.test.tsx; the page shows it once wired |
| FR-074 AC2: over-budget banner shows the excess (TC-228) | verified (component) | `TC-228: …` |
| FR-075: the traveller sets 0 to 50 percent, and the buffer line is shown | verified | form cases (TC-229, save, refuse 51) |
| FR-075 AC2 / switch off: the estimate states that no buffer is included (TC-230) | verified | `TC-230: …` |
| Banner role status, text not colour only | verified | `getByRole("status", { name })` and the text title |
| With both switches off, the page still shows the estimate and the validator warning (TC-372) | not verified | needs the page wiring and E2E (not run) |
| Banner in the itinerary cost strip | not verified | no cost strip exists on the itinerary page; see open issues |

## Proposed decisions

- none

## Blockers and open issues

- Wiring (the costs page is not in the card's file list): in `apps/web/app/(app)/trips/[tripId]/costs/page.tsx`, replace the inline `isEnabled("budget_alerts") && data.alerts.map(...)` block with `<BudgetAlert alerts={data.alerts} />`, imported from `@/components/costs/BudgetAlert`.
- The itinerary page has no cost strip, so step 4's "in the itinerary cost strip" has nowhere to go. When one exists, it renders `<BudgetAlert alerts={costs.alerts} />` from `useCosts(tripId)`.
