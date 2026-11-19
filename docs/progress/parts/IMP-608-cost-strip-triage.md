# IMP-608 · cost-strip-triage part

- Run id: RUN-083 (batch run, agent F, part F3; Sprint 7 Batch B, IMD-202)
- Owner: Manal (Manal Patel), lead of IMP-608
- Status: PR_OPEN (documents only; committed on the batch branch, the lead pushes and opens the pull request)
- Base commit: f75aa94
- Branch: S7B/fixes
- Points: 0 (triage under the feature freeze, IMD-201)
- Traces to: IMP-608 step 4; FR-074, FR-075; §7.5.7; MOD-F04, MOD-F06; deferred item "IMP-608: budget alert banner in the itinerary cost strip" (`docs/progress/deferred.md`), gate finding of SG-6 (`docs/progress/gates.md`, minor (3))

## 1. What the card and the specification require

- **IMP-608 objective** (`docs/spec/TASK_REGISTER.md`, `### IMP-608`): "The costs page and itinerary cost strip show near-budget and over-budget alerts and a contingency line that the traveller can set from 0 to 50 percent."
- **IMP-608 step 4:** "Build BudgetAlert banners (role status, text not colour only) on the costs page and in the itinerary cost strip; add the contingency input to BudgetSettingsForm."
- **IMP-608 files:** the card lists `apps/web/components/costs/BudgetAlert.tsx` (create) and `BudgetSettingsForm.tsx` (modify). It does not list the itinerary page or a cost-strip component.
- **IMP-608 acceptance criteria:** FR-074 AC1-AC2 (TC-227, TC-228), FR-075 AC1-AC2 (TC-229, TC-230), the contingency applies to S_hi and the sums equal the planning total (TC-298, TC-300), and with both switches off "the costs page still shows the estimate and the validator budget warning" (TC-372). None of the acceptance criteria names the itinerary cost strip.
- **FR-074** (§2 register): "The system shall show a banner when the estimated cost reaches the near-budget threshold or exceeds the budget." AC1/AC2 say "when displayed"; they name no screen.
- **§7.5.7 Itinerary** (`docs/spec/IMPLEMENTATION_SPEC.md`): the header has "day tabs, cost strip (total and share of budget from API-33 `CostSummaryOut`), stale-plan banner".
- **MOD-F06** (§ module table): responsibility "Cost strip, breakdown, alerts, budget settings form, final summary and print view"; public interface `CostSummary`, `CostBreakdown`, `BudgetAlert`, `BudgetSettingsForm`, `PrintLayout`; "Depended on by: MOD-F04 (cost strip)".
- **§ file layout** (`components/costs/` row): "Sprint 3 (IMP-308 cost strip)". The IMP-308 card's file list is backend only (`generation/schedule.py`, `budget/engine.py`, `service.py`, `router.py`, `schemas.py` and tests); no card in `TASK_REGISTER.md` lists a cost-strip component or the itinerary page for a cost strip.
- **IMP-411 completion evidence:** "Screenshot of the cost strip with traveller-input lines". The IMP-411 record (`IMP-411-budget-form-badges.md`) states the screenshots were not run.

## 2. What exists on main (f75aa94)

- `apps/web/components/costs/BudgetAlert.tsx`: one `role="status"` banner per API-33 alert (BUDGET_NEAR, BUDGET_EXCEEDED), hidden when `budget_alerts` is off (IMP-608 budget-alert part, RUN-075).
- `apps/web/app/(app)/trips/[tripId]/costs/page.tsx`: renders `<BudgetAlert alerts={data.alerts} />`, the estimate and planning total, `BudgetSettingsForm` (with the contingency field) and `CostBreakdown`, from `useCosts(tripId)` (API-33).
- `apps/web/components/costs/BudgetSettingsForm.tsx`, `CostBreakdown.tsx`: present. No `CostSummary` or cost-strip component exists in `apps/web/components/costs/` (the directory holds only these three files).
- `apps/web/app/(app)/trips/[tripId]/itinerary/page.tsx` (511 lines): renders the title, day tabs or day list, `StalePlanBanner`, `WarningsPanel`, the map or list view and the item controls. It contains no reference to cost, budget, `totals`, `day_cost`, `useCosts` or `BudgetAlert` (searched with `grep -niE "cost|budget|price|estimate"` and `grep -rn "totals|day_cost"` in this run).
- `apps/web/components/itinerary/` (`DayColumn.tsx`, `ItineraryItemCard.tsx` and the others): no total or day-cost display. Item cards show each item's price with its label.
- API-33 `CostSummaryOut.budget` (`BudgetStatus`: amount, status, `ratio_pct`, excess) in `apps/api/app/budget/schemas.py` carries the share of budget.
- API-24 (`apps/api/app/itinerary/schemas.py`): `ItineraryOut.totals` (`Totals`: currency, estimate, planning_total, complete, incomplete_count) and `Day.day_cost` (`DayCost`) are returned, and API-33 (`CostSummaryOut`, with `alerts`) is available through `useCosts` (`apps/web/lib/api/queries.ts`). So the data a strip would need is already served; only the web display is missing.
- `apps/web/components/versions/PrintLayout.tsx` shows the day estimate and planning total on the summary print view.
- `apps/web/components/shell/AppShell.tsx`: the trip navigation has a "Costs" tab linking to `/trips/{tripId}/costs`, so the alerts are one tab away from the itinerary.
- Earlier records: `IMP-309-day-view.md` lists the cost strip as "still to come" and says `day_cost` and `totals` "are not shown yet"; `IMP-608-budget-alert.md` marks "Banner in the itinerary cost strip" not verified because no cost strip exists.

## 3. Gap

Yes, a gap exists: the itinerary page has no cost strip (no total and share of budget, §7.5.7), so IMP-608 step 4's banner "in the itinerary cost strip" has no place to render. FR-074 and FR-075 are met on the Costs page, which is where the card's acceptance criteria and TC-372 look.

Closing the gap is not a defect fix in an existing component: it needs a new cost-strip component (MOD-F06 `CostSummary` or a strip) and new wiring in the itinerary page. Under the feature freeze (IMD-201: "only defects, hardening, documents, data loading and planned Sprint 7 and 8 cards are merged") and because the card's acceptance criteria do not require the strip, **no code is changed in this part**. The gap is recorded with the proposed decision below.

## Changed files

- `docs/progress/parts/IMP-608-cost-strip-triage.md` (created): this record.

## Commands run

| Command | Result line (quoted exactly) |
| --- | --- |
| `grep -niE "cost\|budget\|price\|estimate" "apps/web/app/(app)/trips/[tripId]/itinerary/page.tsx" apps/web/components/itinerary/DayColumn.tsx` | no output (no match) |
| `grep -rn "planning_total\|day_cost\|\.totals" apps/web/app apps/web/components apps/web/lib` (excluding generated types) | matches only in `costs/page.tsx`, `components/versions/PrintLayout.tsx` and `lib/api/queries.ts:316` |
| `ls apps/web/components/costs` | `BudgetAlert.tsx`, `BudgetSettingsForm.tsx`, `CostBreakdown.tsx` |

## Not run

| Command | Reason |
| --- | --- |
| Tests | Documents only; no code changed. |

## Acceptance criteria (of this triage)

| Criterion | Status (verified / not verified) | How |
| --- | --- | --- |
| What the card requires for the cost strip is stated | verified | section 1, quoted from `TASK_REGISTER.md` and `IMPLEMENTATION_SPEC.md` |
| What exists on main is listed with paths | verified | section 2, from the searches above |
| Whether a gap exists is stated | verified | section 3 |
| No code change unless required by the card's acceptance and a defect fix in an existing component | verified | the card's acceptance criteria do not name the strip, and the strip would be a new component; no code changed |

## Blockers

none

## Proposed decisions

- **PD-RUN-083-1 (IMP-608 itinerary cost strip):** The itinerary cost strip of §7.5.7 and IMP-608 step 4 is not built in the MVP under the feature freeze (IMD-201). FR-074 and FR-075 are accepted as met on the Costs page (`BudgetAlert`, estimate, contingency line), which the card's acceptance criteria and TC-372 name, and which the trip navigation's "Costs" tab reaches from the itinerary. §7.5.7's cost strip, MOD-F06's `CostSummary`, IMP-608 step 4's "in the itinerary cost strip" and IMP-411's cost-strip screenshot are recorded as a known gap in `docs/progress/deferred.md` (post-MVP), and the SG-6 minor finding is closed as "deferred by decision". Alternative, if the team wants the strip in the MVP: a planned 0-point screen part owned by the MOD-F06 component owner (Krrish, with Manal reviewing) adds a strip in `components/costs/` that displays API-33 `planning_total`, the share of budget (`budget.ratio_pct`) and `<BudgetAlert alerts={costs.alerts} />` on the itinerary page, with a component test and an E2E check; this needs an explicit exception to IMD-201 and restarts the E2E evidence rounds.

## Open issues

- none. (The strip's "share of budget" is already served by API-33 as `CostSummaryOut.budget.ratio_pct` in `apps/api/app/budget/schemas.py`, so the alternative needs no contract change and no client arithmetic.)
