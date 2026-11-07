# IMP-317 · whole task

- Run id: RUN-052
- Owner: Manasvi (Manasvi1704)
- Status: PR_OPEN
- Base commit: 85137d3
- Branch: feat/IMP-317-whole-task
- Reviewer: Krrish (Assassin-byte)
- Traces to: US-165; FR-139, FR-035; NFR-025, NFR-040; TC-457; Amendment A1 §7.1, §11
- Card steps built: 1 to 6
- Merge order: after PR #254 (IMP-316), which fills `sources`. Until then API-24 returns `[]` and the page shows nothing new.

## Changed files

- `apps/web/components/itinerary/ItemSources.tsx` (created): the disclosure and its list.
- `apps/web/components/itinerary/ItineraryItemCard.tsx`: renders `ItemSources` under the note when `note_origin` is `ai`. The AiBadge stays.
- `apps/web/tests/unit/itinerary/ItemSources.test.tsx` (created): TC-457 and the placement on the card.
- `apps/web/tests/axe.ts` (created): the axe helper, for any component test.
- `apps/web/package.json`, `apps/web/package-lock.json`: the dependency below.
- `docs/progress/parts/IMP-317-screens/`: `item-sources-375.png`, `item-sources-1280.png`.

## Dependency added

`axe-core` `^4.14.0` (resolved 4.14.0), dev only. It closes the component-test part of the SG-2 open item "no axe tooling". It was already in the lockfile through `eslint-plugin-jsx-a11y`, so no new package is installed. `vitest-axe` was not needed. No runtime dependency is added.

The helper turns off `color-contrast`, because jsdom has no layout. A throwaway check confirmed that it reports `button-name` and `image-alt` on a broken fragment. Contrast was checked once in Chromium, below. Playwright specs still have no axe helper.

## Screenshot source

PR #254 was not merged at push time, so the screenshots come from a Playwright page whose API-24 response is served from a test fixture with `page.route`. Sign-in used the real local stack. The fixture is the API-24 response recorded in `IMP-316-saved-sources.md` (MOCK, SAMPLE index), with two edits to show the link and the text URL: one synthetic guide source with an https URL was added to the first item, and the second item's source was given a long `http` URL. All values are synthetic SAMPLE data.

The spec was temporary and is not committed. Both lists are open in the screenshots. At each width it opened them by keyboard (Enter and Space), asserted the lists were visible, and then checked:

| Check at 375 px and 1280 px | Result |
| --- | --- |
| No horizontal scroll, lists open | passed |
| axe on `main` in Chromium, colour contrast on, lists open | `axe open 375 []`, `axe open 1280 []` |
| Link has `target="_blank"` and `rel="noopener noreferrer"`; the `http` URL is text, not a link | passed |
| No chunk ID in the page text | passed |

The bar across `item-sources-375.png` is the fixed bottom navigation, caught by the full-page capture. It covers part of the text URL.

## Commands

| Command | Result |
| --- | --- |
| `make test-web ARGS='ItemSources'` | `Test Files  1 passed (1)`, `Tests  14 passed (14)` |
| `make test-web` | `Test Files  18 passed (18)`, `Tests  119 passed (119)` |
| `make lint` | `All checks passed!`, `All matched files use Prettier code style!` |
| `make typecheck` | `Success: no issues found in 105 source files`; `tsc --noEmit` clean |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |
| `make e2e ARGS='journey'` (steps of `.github/workflows/e2e.yml`, `BASE_URL=http://localhost:3000`) | `4 passed (7.4s)` |
| `make check` (`make db-up`, `TEST_DATABASE_URL` on the compose database) | exit 0: unit `755 passed, 1 warning`; contract `87 passed, 2 deselected, 1 warning`; api `326 passed, 1 warning`; authz `31 passed`; web `Tests  119 passed (119)` |

## Acceptance

| Criterion | Status | How |
| --- | --- | --- |
| FR-139 AC2, TC-457: the page shows an AI-written note's sources; items without citations show none | verified | `ItemSources.test.tsx`, "lists each source's…", "renders nothing for an empty list", "ItineraryItemCard sources"; page rendering from the fixture |
| FR-139 AC3, TC-457: links open outside the app with `noopener noreferrer`, and no internal ID is shown as text | verified | "links an https title…", "shows %s as text…", "shows no chunk ID"; Chromium check above |
| NFR-025, TC-457: the disclosure works by keyboard, and axe reports no violation | verified | "toggles with Enter" and "Space", "has no axe violation, closed or open"; Chromium check above |
| A plan saved by the real pipeline shows its sources on the page | not verified | Needs PR #254. The fixture is a recorded API-24 response, not a live one. The card's evidence line asks for the MOCK local stack, so these screenshots should be retaken once #254 is merged |

## Blockers

None.

## Proposed decisions

- **PD-IMP-317-1 (Files list).** The card leaves out `apps/web/tests/axe.ts`, `package.json` and `package-lock.json`, which the run prompt asks for. Proposed: add them.
- **PD-IMP-317-2 (retrieval date has no year).** `formatDayDate` gives "Sat 31 Oct" (guide §17). For a retrieval date, which is in the past and may be from another year, a year would be clearer. Proposed: decide whether sources show "31 Oct 2026". It is a small change in `lib/format.ts`.

## Open issues

- **Repeated titles.** Two passages cited from the same document show as two entries with the same title, because `sources` lists passages. Nothing is merged in the browser. Revisit if real plans read badly.
- **Open state resets at 768 px.** Crossing that width swaps the tabs and the columns, which remounts the cards and closes any open list. It is the page's existing behaviour and only affects a resize.
- **Screenshots** to be retaken from a real MOCK plan after PR #254 merges, as above.
