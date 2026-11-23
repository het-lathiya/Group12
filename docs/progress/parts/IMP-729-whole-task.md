# IMP-729 · whole-task part (tier label, source badges, unknown chips and attribution)

- Card: IMP-729 (0 points, Amendment A2 §9.2, §9.3, §6.6, §12 Batch C2)
- Run id: RUN-091 (Batch C2, Sprint 7, inserted under IMD-215)
- Owner: Krrish (Krrish Kamani)
- Status: PR_OPEN candidate on `feat/S7-C2-any-city-ai-web`
- Base commit: 667c0d8 (on `main`)
- Traces to: A2 §9.2 table, §9.3 exact texts, §6.6 (known costs only), §10; TC-484, TC-485; IMD-118 (ui-design guide)

## Changed files

- `apps/web/components/labels/TierBadge.tsx` (created):
  - `TierBadge`: "Live data" with the §9.1 hint, or "Curated", in words and an icon, not colour only. It renders nothing with the switch OFF, for the SAMPLE destination (which keeps its own label) or while the tier is unknown.
  - `useDestinationTier`: reads API-79 through the any-city client, only with `any_city_mode` ON.
- `apps/web/components/labels/LiveAttribution.tsx` (created): the "Data sources" footer.
  - Each API-79 attribution text is shown verbatim, with an https-only source link (`noopener noreferrer`) and, for CC BY-SA sources, the licence link `https://creativecommons.org/licenses/by-sa/4.0/`.
  - It shows for live destinations only.
- `apps/web/components/labels/liveTier.ts` (created): the `LiveTierProvider` context and `useLiveTier`. They default to false, which keeps curated wording.
- `apps/web/components/labels/SourceBadge.tsx`: an "OpenStreetMap" source label. `live` turns `unavailable` into "Price unknown" or "Hours unknown".
- `apps/web/components/places/PlaceCard.tsx`, `PlaceDetailDrawer.tsx` and `components/itinerary/ItineraryItemCard.tsx`: the unknown chips and the OpenStreetMap source on live places only. Curated places keep "Unavailable". The `flex-wrap` on the item hours row applies to the live tier only.
- `apps/web/components/itinerary/WarningsPanel.tsx`: on the live tier, `HOURS_UNVERIFIED` rows are grouped into one line, "Opening hours unknown for N stops", which stays at severity info.
- `apps/web/components/costs/CostBreakdown.tsx`: on a live plan, "Known costs only: N stops have no price" (N = the API-33 `incomplete_items`, the items behind `COST_INCOMPLETE`). The budget status carries "covers known costs only".
- The explore, itinerary and costs pages (`app/(app)/trips/[tripId]/…/page.tsx`): `TierBadge` in the header, `LiveAttribution` at the foot, and the page wrapped in `LiveTierProvider`. The large raw diffs are re-indentation: `git diff -w` gives 9 to 19 changed lines per page.
- `apps/web/components/trips/PreferenceForm.tsx` and the single `TripWizard.tsx` prop line (`destinationId={trip?.destination_id}`): on a live destination with step-free required, "Few live places have step-free information; your list may be short". The step-free control lives in `PreferenceForm.tsx`, not `TripDetailsStep.tsx`, so this part does not touch `TripDetailsStep.tsx`.
- `apps/web/app/(public)/page.tsx`: the rendered text is the same as before with the switch OFF. With it ON, it reads "Plans are drafts built from curated or live open data."
- Tests (created):
  - `apps/web/tests/unit/labels/TierBadge.test.tsx`: 21 tests (badge, chips, OpenStreetMap badge, grouped hours, step-free warning, explore page);
  - `apps/web/tests/unit/labels/LiveAttribution.test.tsx`: 10 tests (texts, safe links, keyboard order, axe, landing copy);
  - `apps/web/tests/unit/costs/CostBreakdown.live.test.tsx`: 7 tests (known-costs note, budget note, curated unchanged, costs page).

No API, contract, `schema.d.ts` or `any-city-schema.d.ts` change. No existing test changed.

## Commands

| Command | Result line |
| --- | --- |
| `make test-web ARGS='TierBadge LiveAttribution CostBreakdown TripDetailsStep'` | Test Files  5 passed (5) · Tests  42 passed (42) |
| `make test-web` | Test Files  50 passed (50) · Tests  364 passed (364) |
| `npx tsc --noEmit -p .` (apps/web) | no output (exit 0) |
| `npx eslint` on the changed and new files | no output (exit 0) |
| `npx prettier --check` on the changed and new files | All matched files use Prettier code style! |

## Acceptance

- **TC-484: verified.** Live pages show the tier badge, the OpenStreetMap source badge, the "Price unknown" and "Hours unknown" chips, the grouped hours line and the attribution footer (`TierBadge.test.tsx`, `LiveAttribution.test.tsx`). Axe reports no serious or critical finding, and the footer links are reachable with the keyboard in order.
- **TC-485: verified.** The costs page shows "Known costs only: N stops have no price" and the budget note on live plans. Curated plans are unchanged (`CostBreakdown.live.test.tsx`).
- **Curated and SAMPLE pages unchanged; with the switch OFF nothing new renders and API-79 is never called: verified.** The tests cover "switch OFF renders nothing new" for the explore and costs pages, the badge and the footer; "curated keeps Unavailable"; and "SAMPLE keeps its own label". With the switch ON, a curated page gains the "Curated" badge, as the §9.2 table asks.
- **360 px without overflow and screenshots at 360 and 1280 px: not verified.** Screenshots are in C3 (IMP-730). No local stack was started with the switch ON, because that would need the `.env` files.

## Cut if late

none

## Proposed decisions

none

## Open issues

- The shared Wikivoyage and Wikipedia source rows carry the §9.3 text without the page title (IMP-726), so the footer shows "Guide text from Wikivoyage, by its contributors, …". Page titles reach the traveller through the item sources (title and page link).
- Places with an unknown `price_label` or `hours_label` show the chips only through the page's `LiveTierProvider`. A component rendered outside those three pages keeps "Unavailable".

## Blockers

none
