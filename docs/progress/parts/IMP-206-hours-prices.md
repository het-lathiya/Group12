# IMP-206 · hours-prices part

- Run id: RUN-040
- Owner: Malhar (Malhar1112-v)
- Status: PR_OPEN
- Base commit: 94849c6
- Branch: feat/IMP-206-destination-1 (one branch and pull request for the card, IMD-66; built on Jeel's lead-curation commit)
- Reviewer: Kirtan (kirtan-S111)
- Traces to: US-026, NFR-040; TC-109, TC-113; PR-01, PR-02, PR-03; IMD-120
- Card step built: 2 (hours and price ranges from public pages named in `sources.csv`; everything else unavailable)

## Changed files

- `data/places/ahmedabad/places.csv` (modified): the hours and price columns (`price_min`, `price_max`, `price_currency`, `price_label`, `hours_label`, `hours_checked_on`) restored to the desk-checked input of IMD-120. The committed file is byte-identical to the input (`cmp`).
- `data/places/ahmedabad/opening_hours.csv` (modified): the 364 weekly hour rows for 48 places, identical to the input (`cmp`). The lead-curation commit held only the header row.
- `docs/progress/parts/IMP-206-hours-prices.md` (created): this record.

No place fact, price, hour or coordinate was added, corrected or removed in this run.

## Hours and prices

| Measure | Count |
| --- | --- |
| Places | 103 |
| `hours_label` curated / estimate / unavailable | 25 / 23 / 55 |
| Places with hour rows (`opening_hours.csv`) | 48 (25 curated + 23 estimate) |
| Hour rows / closed-day rows / rows closing after midnight | 364 / 23 / 7 |
| `price_label` curated / estimate / unavailable | 45 / 0 / 58 |
| Priced places in INR / of which free (0.00 to 0.00) | 45 / 30 |

Under IMD-120, hours a page states without weekdays are labelled `estimate`, and hours or prices no loaded page supports are `unavailable` with empty cells and no hour rows.

## Commands run

All commands ran against the compose database (`make db-up`, `Container group12-db-1 Healthy`; `make db-bootstrap`, since plain PostgreSQL needs the auth stub before migration 0001) with `APP_ENV=test`.

| Command | Result line |
| --- | --- |
| `cmp` of `places.csv` and `opening_hours.csv` against `~/data_inputs/IMP-206/ahmedabad/` | identical (no output, exit 0) |
| `cd apps/api && .venv/bin/python -m app.places.seed ../../data/places/ahmedabad --check --strict` | `seed ahmedabad: read 103 places, 364 opening-hours rows, 29 source(s)` / `seed ahmedabad: gate loaded 103, rejected 0, flagged 0` (exit 0) |
| `cd apps/api && .venv/bin/python -m app.places.seed ../../data/places/ahmedabad` (load) | `seed ahmedabad: opening hours replaced for 48 places, unchanged for 55` |
| the same load, second run | `seed ahmedabad: opening hours replaced for 0 places, unchanged for 103` |
| `make check` | see the lead-curation part record and the pull request |

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| Every price and hour cites a public page in `sources.csv` (US-026 AC3), gate half | verified | the gate rejects a row whose source is missing or lacks a licence or retrieved date; 0 rejected |
| Hours or prices without a source stay unavailable, never guessed (PR-02) | verified | 58 unpriced rows have empty price cells and `price_label unavailable`; 55 places have no hour rows and `hours_label unavailable` |
| The 20 percent review found no unsourced fact (US-026 AC3), review half | not verified | the review sample by Junaid (card step 3) has not been done; IMD-120 records the desk check in `verification_log.md` instead |

## Blockers

none

## Proposed decisions

none

## Open issues

- IMD-120: the 60 rows with `verification_status unverified` (24 of them with hours, 15 curated and 9 estimate) are to be checked by Jeel and Malhar before SG-3, and upgraded to `curated_checked` or removed.
- 50 rows carry a `hours_checked_on` date (2026-11-05) but only 25 are `curated`; the gate accepts a date on an `estimate` row. Left as in the input.
