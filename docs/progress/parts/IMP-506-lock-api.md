# IMP-506 · lock-api

- Run id: RUN-069
- Owner: Het Lathiya (het-lathiya), 2 points
- Status: implemented; database acceptance awaiting CI
- Base commit: 4c6c693
- Steps: 1–4, API half of 6, 7; FR-066, TC-211, TC-212, TC-313, TC-372.

## Files changed

- apps/api/app/itinerary/edits.py: lock/unlock and atomic unlock plus move/retime; feature guard replaces interim 501; existing revision/ownership transaction retained.
- apps/api/app/itinerary/service.py: must-visit locks on generation save and owner-scoped fixed constraints.
- apps/api/app/generation/request_builder.py: read fixed constraints for full/day scope.
- apps/api/app/itinerary/repository.py: minimal extra file required to persist must-visit locks in both rows and snapshots in the same save transaction; optional locked_place_ids argument, no schema change.
- apps/api/tests/api/test_edits.py; apps/api/tests/unit/validation/test_repair.py; this record.
- Repair operations already skip locks; added explicit cases for every repair finding instead of changing working repair logic.

## Commands and results

- `make test-unit ARGS='-k locked'`: `19 passed, 1095 deselected, 1 warning in 2.25s`.
- `make test-unit ARGS='-k "request_builder or repair"'`: `64 passed, 1050 deselected, 1 warning in 1.92s`.
- Scoped `ruff check`: `All checks passed!`.
- `make typecheck`: `Success: no issues found in 121 source files`; `✓ Types generated successfully` (exit 0).
- `make db-up`: `make: *** [Makefile:74: db-up] Error 1`; Docker is unavailable in this WSL distro.
- Not run: `make test-api ARGS='-k lock'`, needs PostgreSQL; no system packages installed.

## Acceptance

- Verified TC-313 repair: each fix retains locked day/time/duration; existing request builder tests preserve constraints.
- Not verified TC-211/212 API, must-visit save, flag floor and owner-scoped database loading: API tests written; CI with PostgreSQL must run them.
- Regeneration endpoints are IMP-607; this part supplies their fixed request constraints only.
- Keyboard toggle belongs to lock-toggle.

## Proposed decisions and open issues

- No new decisions, migrations or contract shape changes.
- Database verification remains open.
