# IMP-411 · budget-form-badges

| Field | Value |
| --- | --- |
| Run | RUN-058 (grouped run, IMD-121), part 4 of 7 |
| Card | IMP-411 Transport allowance, stay budget and price source labels |
| Part | BudgetSettingsForm and SourceBadge variants (2 points) |
| Owner | Krrish Kamani |
| Status | PR_OPEN |
| Base commit | 16839a0 |
| Branch | feat/IMP-410-411-412-trips-budget-states |

## Changed files

- `apps/web/components/labels/SourceBadge.tsx`
  - Exactly three variants: Estimate (amber, `warning` tokens), Curated (teal, `primary` tokens) and Unavailable (neutral `muted` tokens).
  - The badge is a pill with a 12 px radius (`rounded-xl`), and its label text is always visible.
  - A new `kind` prop (`price` by default, or `hours`): only curated opening hours show "checked on <date>", and a curated price shows "Curated" without a date (IMD-130).
  - A value outside the contract is shown as "Unavailable", so "Live" or "Verified" can never render.
  - The type now comes from the API's `SourceLabel` schema.
- `apps/web/components/costs/BudgetSettingsForm.tsx` (created)
  - Two fields, "Transport per day" and "Stay per night", in two columns at `md` and up and one column at 375 px.
  - Each field has the destination currency code as a prefix (IMD-128), `inputmode="decimal"`, and the helper "Your own figure. Shown as Traveller input in costs."
  - Inline errors are linked with `aria-describedby`, and zod mirrors the server rule (empty, or a decimal ≥ 0 with at most 2 places).
  - The form saves with API-34 through the generated client. Under each field it shows the line the API returned: "In costs: GBP 30.00, Traveller input" or "In costs: Unavailable". The browser computes no totals.
  - It has a loading skeleton, an ErrorState with Retry, and the server's 422 mapped onto the fields.
- `apps/web/components/trips/TripWizard.tsx` (budget step only): the Review step shows the "Transport and stay budget" section with BudgetSettingsForm, because API-34 needs the saved trip.
- `apps/web/lib/api/queries.ts`: `useCosts` (API-33) and `useUpdateBudgetSettings` (API-34). The second sets `costs` and invalidates `itinerary`, as §7.4 says.
- `apps/web/tests/unit/labels/SourceBadge.test.tsx`: this file already existed (IMP-309), so it was extended rather than created. It now covers the three variants with text and colour, the hours date, no date on a curated price, and TC-231.
- `apps/web/tests/unit/costs/BudgetSettingsForm.test.tsx` (created).
- `apps/web/tests/unit/trips/TripWizard.test.tsx`: the fake API answers API-33 for the Review step.
- `docs/progress/parts/IMP-411-budget-form-badges.md`: this record.

## Commands

| Command | Result |
| --- | --- |
| `make test-web ARGS='SourceBadge'` + `ARGS='BudgetSettingsForm'` (run together with `tests/unit/trips` as `npx vitest run BudgetSettingsForm tests/unit/trips SourceBadge`) | `Tests  32 passed (32)` |
| `make test-web` | `Tests  137 passed (137)` |
| `make lint` | `All checks passed!`; ESLint `✖ 1 problem (0 errors, 1 warning)`, a warning that predates this run; `All matched files use Prettier code style!` |
| `make typecheck` | `Success: no issues found in 111 source files` |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |

Not run: screenshots of the cost lines at 375 px and 1280 px, because no local stack runs here; the operator adds them.

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-076 AC1 (TC-231): only Estimate, Curated or Unavailable, with a date where one exists; no Live or Verified can render | verified | `SourceBadge.test.tsx`: the three variants, the hours date, IMD-130 (no price date), and "TC-231: a label … never renders as Live or Verified" |
| Text and colour on every badge | verified | each variant's test checks both the text and its token class, and that no raw hex is used |
| FR-072 web side: inputs saved and shown as Traveller input; empty shows Unavailable | verified | `BudgetSettingsForm.test.tsx` "TC-223 …" and the fields test |

## Proposed decisions

- **PD-IMP-411-4 (budget step location):** card step 4 says "wizard budget step". The wizard has four steps (§7.5.4, PD-IMP-212-1), and API-34 needs a saved trip, so the form sits in the Review step instead of a new fifth step. Proposed: accept this until the costs page (`/trips/[tripId]/costs`, §7.5) is built and hosts it too.
- **PD-IMP-411-5 (SourceBadge test file):** the run listed `SourceBadge.test.tsx` as a new file, but it existed already, so it was extended.

## Blockers and open issues

- Open issue: `ItineraryItemCard.tsx` uses SourceBadge for prices with no `kind`, so it keeps the default `price` and shows no date. That file belongs to RUN-057 and was not edited.
