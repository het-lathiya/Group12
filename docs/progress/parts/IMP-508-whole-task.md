# IMP-508 · whole-task part

- Run id: RUN-068 (Sprint 5 batch A)
- Owner: Manasvi (Manasvi Rathore)
- Status: PR_OPEN once the lead opens the pull request; committed on `part/IMP-508-whole-task`, not pushed
- Base commit: 26bac9d
- Traces to: US-089; FR-080; NFR-010, NFR-026; TC-238, TC-239, TC-240
- Card steps built: 1 to 6

## Changed files

- `apps/web/components/map/MapPanel.tsx` (created): MapLibre map with the OpenFreeMap style, one numbered marker per item of the selected day in position order (accessible name "Stop N: <place name>"), straight segments between consecutive stops, the selected card's marker marked `aria-current`, attribution control expanded. No WebGL at mount, or any map `error` event (style or tiles), swaps in MapListFallback.
- `apps/web/components/map/MapListFallback.tsx` (created): the notice "Map unavailable; list view shown" and an ordered list with the same numbers and the times API-24 sent; each entry goes to its item card.
- `apps/web/lib/map.ts` (created): `OPENFREEMAP_STYLE_URL`.
- `apps/web/app/(app)/trips/[tripId]/itinerary/page.tsx`: MapPanel loaded with `next/dynamic` and `ssr: false`. From 768 px the map is in the side pane above WarningsPanel (right pane from 1280 px); below 768 px a List or Map toggle (§7.5.7) holds it. The map shows the open day: the day tab, the day index link, or the day of the focused card. A marker or list entry calls the existing `goToItem` (switches back to List on a phone, scrolls to and focuses the card). Focusing or clicking a card highlights its marker. The browser computes nothing: positions, names and times are shown as API-24 returns them; items are only sorted by `position`.
- `apps/web/tests/unit/map/MapPanel.test.tsx` (created): TC-238, TC-239, TC-240 with MapLibre mocked (§9).
- `docs/decisions/map-tiles.md` (created): provider, style URL, terms as §9 states them, attribution, status **Unverified** (nobody has checked the terms).
- `apps/web/package.json`, `apps/web/package-lock.json`: `maplibre-gl` `^6.16.0`.

## Dependency reason

`maplibre-gl` is the map library the stack names (CLAUDE.md §2, specification §9: "OpenFreeMap tiles + MapLibre GL JS"); IMP-508 step 1 adds it. Version 6.16.0 was released on 2026-10-25, more than two weeks before this run; the caret range follows the other entries of `package.json`, and the lock file pins the exact version. It brings its own types; no other package was added by hand (the lock file gains its transitive packages).

## Commands

Run in `apps/web` of the worktree.

- `npx vitest run tests/unit/map` → `Tests  4 passed (4)` (`Test Files  1 passed (1)`)
- `npx vitest run tests/unit/itinerary` (the page test renders the changed page) → `Tests  62 passed (62)` (`Test Files  7 passed (7)`)
- `npm run typecheck` → `✓ Types generated successfully`, `tsc --noEmit` with no output (exit 0)
- `npx eslint components/map lib/map.ts tests/unit/map "app/(app)/trips/[tripId]/itinerary/page.tsx"` → no output (exit 0)
- `npx prettier --check components/map lib/map.ts tests/unit/map "app/(app)/trips/[tripId]/itinerary/page.tsx" package.json ../../docs/decisions/map-tiles.md ../../docs/progress/parts/IMP-508-whole-task.md` (after `prettier --write` on `map-tiles.md`, which aligned its table) → `All matched files use Prettier code style!`

Not run: `make check`, `make e2e ARGS='itinerary-edit'` (the run limits this part to component tests, lint and typecheck; left to CI), screenshots of the map and the list fallback (no dev server in this run).

## Acceptance criteria

- FR-080 AC1, markers in visit order (TC-238): **verified** by "TC-238: shows one numbered marker per stop in visit order, joined in that order" (items sent out of order; markers 1 to 3 by position; line coordinates in that order).
- FR-080 AC2, a selected marker opens the activity (TC-239): **verified at component level** by "TC-239: selecting a marker opens that stop's card; the selected card's marker is highlighted" (marker click calls `onSelectItem` with the item id; `aria-current` follows `selectedItemId`). The page wiring to `goToItem` and the card focus listener is **not verified** by a test (needs E2E or a real map).
- FR-080 AC3, the list view works on a tile failure (TC-240): **verified** by "TC-240: a tile or style error swaps the map for the numbered list, which still works" and "TC-240: without WebGL the list is shown and no map is created". The itinerary stays usable: the page tests (jsdom has no WebGL, so the page renders the fallback) still pass, with all day and edit controls present.
- Tile request blocked, list appears and itinerary usable: **verified** with a mocked error in the unit test; the Playwright route-abort check is **not verified** (E2E not run, see open issues).
- Markers named "Stop N: <place name>": **verified** in TC-238 and TC-240.
- Attribution shown on the map: **not verified** visually (the attribution control is enabled and expanded; the text comes from the style).

## Proposed decisions

- PD-IMP-508-1: The card's test list names `apps/web/e2e/itinerary-edit.spec.ts` (TC-240) but its Files list does not include that spec, so this part did not add the tile-abort E2E. Proposal: IMP-599 (or a follow-up run of this card) adds a Playwright check that routes `tiles.openfreemap.org` to an abort and expects "Map unavailable; list view shown" with the item cards still editable.
- PD-IMP-508-2: Between 768 and 1279 px the side pane stacks above the days, so the map sits above the plan with WarningsPanel; §7.5.7 describes only desktop (two panes) and phone. Proposal: keep this, or show the map only from 1280 px and use the List or Map toggle below that.

## Open issues

- A remote branch `feat/IMP-508-itinerary-map` (author Manasvi1704, 2026-11-10, based on an older `main`) holds an earlier attempt at this card that also edits `ItineraryItemCard.tsx`. This part was built fresh from `main` within the card's file list; the lead should close or delete that branch so only one pull request exists for the card.
- Terms of OpenFreeMap remain Unverified until a member checks them and updates `docs/decisions/map-tiles.md`.
- Screenshots for the completion evidence (map with markers on desktop, list fallback) are still to be taken.

## RUN-070 (IMD-173)

- Run id: RUN-070 (Sprint 5 batch C, part U3, slug map-e2e)
- Owner: Manasvi (Manasvi Rathore)
- Status: committed on `part/map-e2e`, not pushed; the lead opens the pull request
- Base commit: 15475eb
- Decision: IMD-173 (PD-IMP-508-1, tile-abort E2E and visible attribution check)

### Changed files

- `apps/web/e2e/map.spec.ts` (new, tag `@map`): signs in a confirmed user from the existing `users` fixture, creates a Sampleton trip with the wizard, generates with MOCK and opens the Map tab below 768 px. Every request to `tiles.openfreemap.org` is aborted or answered in the test, so the spec makes no OpenFreeMap request.
  - (a) aborts the style and tiles and expects the status "Map unavailable; list view shown" and the "Stops" list with one entry per first-day item, named "Stop N: <place>" in position order (the numbers the itinerary items and markers use).
  - (b) fulfils the style URL with an inline MapLibre style (version 8, a background layer and an empty inline GeoJSON source carrying the OpenFreeMap style's attribution string) and expects the attribution control to be visible with "OpenFreeMap" and "OpenStreetMap" and no fallback notice. If the browser has no WebGL (checked in the page), it expects the list fallback instead and records a `webgl: false` annotation.
- `docs/progress/parts/IMP-508-whole-task.md` (this section)

No fixture, component, contract or migration changed.

### Commands

- `npx eslint e2e/map.spec.ts` (apps/web): no output, exit 0
- `npx prettier --check e2e/map.spec.ts` (apps/web): `All matched files use Prettier code style!`
- `npm run typecheck` (apps/web, `next typegen && tsc --noEmit`, covers `e2e/`): `✓ Types generated successfully`, tsc exit 0
- `make e2e ARGS='--grep @map'`: not run (no local stack here); deferred to the integration or CI run, the lead fills in the run id

### Acceptance

- (a) Aborted style and tiles show MapListFallback with the itinerary's numbers and "Map unavailable; list view shown" (TC-240): **not verified** yet; the spec exists, the E2E run is deferred to CI (run id: to be filled by the lead). The notice copy in `MapListFallback.tsx` matches exactly.
- (b) Map attribution visible: **not verified** yet; E2E deferred to CI (run id: to be filled by the lead). If that run's browser has no WebGL, the test asserts the fallback instead and this criterion stays "not verified (no WebGL in CI)".

### Blockers

- None for the spec. The E2E evidence needs the CI or integration run.

### Proposed decisions

- PD-RUN-070-1: `MapPanel` sets `attributionControl: { compact: false }` without `customAttribution`, so MapLibre shows only attributions of the style's used sources. A local style with no sources would leave the control empty, so test (b) uses an empty inline GeoJSON source carrying the OpenFreeMap attribution string; this proves the control renders the style's attribution visibly, not the live wording of OpenFreeMap (still Unverified in `docs/decisions/map-tiles.md`). Proposal: accept, or add `customAttribution` with the OpenStreetMap credit in `MapPanel` so the credit does not depend on the remote style (a component change for a later run).

## RUN-070b (map-e2e, owner Manasvi)

- Owner: Manasvi. Base commit: 640fc89.
- PD-RUN-070-1 resolved: `MapPanel` now passes `attributionControl: { compact: false, customAttribution: <link "© OpenStreetMap contributors" to https://www.openstreetmap.org/copyright> }`, so the credit no longer depends on the remote style; the style's own attributions are kept. Unit test asserts the option. `e2e/map.spec.ts` (b) now fulfils the style URL with a minimal source-less local style and asserts the OpenStreetMap link and href coming from MapPanel (no external network; the no-WebGL branch still asserts the list fallback). Tile terms in `docs/decisions/map-tiles.md` stay **Unverified** (not checked by a person).
- Axe finding (E2E run 43586860101, itinerary page): `label-content-name-mismatch` (serious), 3 nodes `li:nth-child(N) > button` in `apps/web/components/map/MapListFallback.tsx`. Fixed by dropping the `aria-label`; a visually hidden "Stop " prefix plus the visible number, place and times now form the name ("Stop N <place> <times>"), so the visible text is contained in the accessible name. `map.spec.ts` (a) and the unit test now match `^Stop N <place>` by regex (same ordered numbers). Map markers keep their `Stop N: <place>` aria-label (their visible text is only the number, which that label contains).
- Commands (apps/web):
  - `npx vitest run tests/unit/map`: `Test Files  1 passed (1)` / `Tests  4 passed (4)`
  - `npx eslint e2e/map.spec.ts tests/unit/map components/map`: no output, exit 0
  - `npx prettier --check e2e/map.spec.ts tests/unit/map components/map`: `All matched files use Prettier code style!`
  - `npm run typecheck`: `✓ Types generated successfully`, tsc exit 0
- Acceptance: unit (credit configured; fallback names include visible text): verified. E2E map.spec and the axe re-scan: not verified, deferred to CI.
- Proposed decision PD-RUN-070b-1: `.github/workflows/e2e.yml` runs only `make e2e ARGS='journey'`, so `map.spec.ts` (tag `@map`) did not run in CI in RUN-070. Proposal: add `@map` (map.spec) to the E2E workflow. The workflow file is outside this part and was not edited.
