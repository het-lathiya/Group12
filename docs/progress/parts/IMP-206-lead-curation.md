# IMP-206 · lead-curation part

- Run id: RUN-040
- Owner: Jeel (jeelfefar2141), card lead
- Status: PR_OPEN
- Base commit: 94849c6
- Branch: feat/IMP-206-destination-1 (one branch and pull request for the card, IMD-66; Malhar's hours-prices part is the middle commit)
- Reviewer: Kirtan (kirtan-S111)
- Traces to: US-026, NFR-040; TC-109, TC-113; PR-01, PR-02, PR-03; IMD-120
- Card steps built: 1 (place list with sources), 4 (gate run) and the local load; step 5 (staging load) is not done

## Changed files

- `data/places/ahmedabad/destination.json` (created): Ahmedabad, `is_sample` false, `min_usable_places` 100.
- `data/places/ahmedabad/sources.csv` (created): 29 sources, each with licence and retrieved date.
- `data/places/ahmedabad/places.csv` (created): 103 places. In this part's commit the hours and price columns were blank (`unavailable`); the hours-prices part restored them. Every other column is identical to the desk-checked input of IMD-120.
- `data/places/ahmedabad/opening_hours.csv` (created, header row only): the gate refuses a directory without this file, so the first commit carries the header and no hour rows (every place `unavailable`); the hours-prices part adds the rows.
- `data/places/ahmedabad/verification_log.md` (created): the per-row desk-check results of IMD-120, copied unchanged.
- `data/places/ahmedabad/quality_report.md` (created, written by the seed).
- `docs/progress/parts/IMP-206-lead-curation.md` (created): this record.

All data files are copies of `~/data_inputs/IMP-206/` (checked with `cmp`). No place fact, price, hour or coordinate was added, corrected or removed in this run.

## Commands run

All commands ran against the compose database (`make db-up`, `Container group12-db-1 Healthy`) with `DATABASE_URL` set to the §4.7 test default and `APP_ENV=test`. `make db-migrate` alone stopped on `schema "auth" does not exist` (plain PostgreSQL); `make db-bootstrap` applied the auth stub and migrated to 0007.

| Command | Result line |
| --- | --- |
| `cd apps/api && .venv/bin/python -m app.places.seed <scratch copy of the lead-curation commit> --check --strict` | `seed ahmedabad: read 103 places, 0 opening-hours rows, 29 source(s)` / `seed ahmedabad: gate loaded 103, rejected 0, flagged 0` (exit 0) |
| `cd apps/api && .venv/bin/python -m app.places.seed ../../data/places/ahmedabad --check --strict` (final files) | `seed ahmedabad: read 103 places, 364 opening-hours rows, 29 source(s)` / `seed ahmedabad: gate loaded 103, rejected 0, flagged 0` / `seed: --check: nothing was written to the database` (exit 0) |
| `cd apps/api && .venv/bin/python -m app.places.seed ../../data/places/ahmedabad` (first load) | `data_sources inserted 29, updated 0, unchanged 0` / `destinations inserted 1, updated 0, unchanged 0` / `places inserted 103, updated 0, unchanged 0, deactivated 0` / `opening hours replaced for 48 places, unchanged for 55` |
| the same load, second run | `data_sources inserted 0, updated 0, unchanged 29` / `destinations inserted 0, updated 0, unchanged 1` / `places inserted 0, updated 0, unchanged 103, deactivated 0` / `opening hours replaced for 0 places, unchanged for 103`; `quality_report.md` byte-identical to the first run (`cmp`) |
| `make lint` | `All checks passed!` / `All matched files use Prettier code style!` (exit 0) |
| `make check` (on the final files, before the last commit) | lint as above; ESLint `✖ 1 problem (0 errors, 1 warning)` (existing warning in `apps/web/lib/api/client.ts`, not touched here); `Success: no issues found in 85 source files`; `Contracts: 4 kept, 0 broken.`; `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date`; unit `385 passed, 1 warning in 8.20s`; contract `35 passed, 1 warning in 0.90s`; api `231 passed, 1 warning in 58.85s`; authz `28 passed in 15.12s`; web `Tests  80 passed (80)` (exit 0) |
| CI step "Place quality gate in check mode", run locally over `data/fixtures/*/` and `data/places/*/` | `seed sampleton: gate loaded 30, rejected 0, flagged 0` / `seed ahmedabad: gate loaded 103, rejected 0, flagged 0` / `seed: --check: nothing was written to the database` (exit 0); `quality_report.md` unchanged |

## Results

| Measure | Count |
| --- | --- |
| Rows read / loaded / rejected / flagged | 103 / 103 / 0 / 0 |
| Usable places against the minimum | 103 against 100 (minimum met) |
| `verification_status` curated_checked / unverified | 43 / 60 |

Under IMD-120 a row is `curated_checked` only where existence, hours, price, coordinates and description facts were confirmed on loaded pages; every other row stays `unverified`. The per-row results are in `verification_log.md`.

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| The import loads at least 100 usable places and the report lists rejects (US-026 AC1, TC-109, TC-113) | verified | gate and load lines above; `quality_report.md`: 103 usable against 100, rejected rows "None" |
| Every place has source, licence and last-checked date (US-026 AC2) | verified | the gate rejects a row whose source lacks a licence or a retrieved date; 0 rejected |
| Every price and hour cites a public page; the 20 percent review found no unsourced fact (US-026 AC3) | not verified | the gate half holds (see the hours-prices record); Junaid's 20 percent review (card step 3) is not done and is not in the report |
| Importing twice changes nothing | verified | second load: inserted 0, updated 0, all unchanged |
| Loaded on staging (card step 5) | not verified | the staging load (run by Kirtan) waits for IMP-217 and IMP-218 |

## Blockers

none

## Proposed decisions

none

## Open issues

- IMD-120: 60 rows are `unverified`. Before SG-3 Jeel and Malhar check them against their sources and upgrade them to `curated_checked` or remove them; Malhar confirms the plan answers and Junaid reviews the plan.
- Staging load not verified until IMP-217 and IMP-218; its output then goes into `docs/progress/sprint-2.md`.
- The 20 percent review sample of card step 3 is not recorded in `quality_report.md`, which the seed writes and nobody edits; where the sample is recorded needs a decision at the gate.
