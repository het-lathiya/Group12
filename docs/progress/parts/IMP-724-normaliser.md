# IMP-724 · normaliser part (OSM normaliser, dedupe, cap and minimum-places gate)

- Card: IMP-724 Normaliser, country table and minimum-places gate (Amendment A2 §6.3, §6.4, §12; 0 points)
- Part: normaliser, dedupe, cap and gate (lead)
- Run id: RUN-089 (Batch C1a, Sprint 7, inserted under IMD-215)
- Owner: Jeel (Jeel Fefar)
- Status: PR_OPEN candidate on `feat/S7-C1a-any-city-foundation`
- Base commit: 08587c0 (on `main`)
- Traces to: IMD-210, IMD-216, PR-02, IMD-46; A2 §6.3, §6.4; TC-465, TC-466, TC-467

## Changed files

- `apps/api/app/livedata/normalise.py` (create, pure; in the `pure-domain` import contract): `LivePlace` (the `places` fields plus OSM type and id), the A2 §6.3 mapping table in table order (first row wins; vocabulary values only; `stay` never produced), the field rules (`external_ref` = `<destination ref>:<n|w|r><id>`, `verification_status = imported_osm`, prices and price currency null, `price_label` and `hours_label` `unavailable`, `hours_checked_on` and `description` null, address from `addr:*` at most 150 characters, `https://` websites only, `booking_url` never set, `step_free` from `wheelchair`, `indoor` true for museum and false for nature, `child_friendly` null, coordinates inside the clipped bbox), dedupe (same category, same folded name, within 75 m; keep more of wikidata/wikipedia/website, then lower OSM id), cap (`LIVE_MAX_PLACES = 300` by richness, food at most 105 = 35 %), `normalise(...)` with drop counters, and the gate (`evaluate_gate`, 40 usable by default from the caller's setting, at least 6 food and 12 non-food) with `choose_nearby_city` (nearby city, else the capital, never the settlement itself).
- `apps/api/tests/unit/livedata/test_normalise.py` (create): TC-465, TC-466, TC-467 (96 tests; shuffled inputs use a fixed seed).
- `docs/progress/parts/IMP-724-normaliser.md` (this record).

## Interpretations (for review)

- "As applicable" nature tags: park → outdoor, walking; garden → outdoor, garden; nature_reserve → outdoor, walking; beach → outdoor, water; peak → outdoor, views.
- Entertainment tags: theatre → theatre, music, evening; arts_centre → art, music, evening.
- Sight: every sight gets history and architecture; `views` is added whenever `tourism=viewpoint`, also when a `historic` value took the row first.
- Websites: `website` and `contact:website` are read; a value must start with `https://`, contain no whitespace and be at most 2,048 characters.
- Names: stripped; an empty name or one longer than the 160-character `places.name` CHECK drops the element (counted in `dropped_invalid`), never truncated.
- Dedupe keep order: (more of wikidata/wikipedia/website, OSM id ascending, then n < w < r); the same element given twice is collapsed first.

## Commands

| Command | Result line |
| --- | --- |
| `make test-unit ARGS='-k normalise'` | `99 passed, 1283 deselected, 1 warning in 0.73s` |
| `make test-unit ARGS='-k "countries or normalise"'` | `440 passed, 1352 deselected, 1 warning in 1.00s` |
| `.venv/bin/ruff check` / `ruff format --check` / `mypy` (the two files) | `All checks passed!` / `2 files already formatted` / `Success: no issues found in 2 source files` |
| purity check (`import app.livedata.normalise`; fastapi, sqlalchemy, httpx loaded) | `[]` |

`make imports` and `make check` ran once on the branch head; result lines in the SYNC REPORT of RUN-089.

## Acceptance

- Only vocabulary values are produced, and `stay` never is: **verified** (TC-465 tests over every key and value of the fixed tag list; each emitted value constructs `Category(...)` and `Tag(...)`).
- Price and hours are always unknown; description null; https websites only: **verified** (TC-465).
- Dedupe and cap are deterministic: **verified** (TC-466, shuffled inputs give the same result).
- The gate gives `insufficient_data` with a nearby city or capital, never the settlement itself: **verified** (TC-467, boundary cases at 39/40 usable, 5/6 food, 11/12 non-food).

## Open issues

- `LivePlace.category`, `tags` and the labels are `StrEnum` values; the places part that stores them (IMP-725) writes them as plain strings.

## Proposed decisions

none

## Blockers

none
