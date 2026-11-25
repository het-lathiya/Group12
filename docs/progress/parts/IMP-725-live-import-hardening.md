# IMP-725 · live-import-hardening part (Overpass error note, guide-page coordinates, CLI start-up checks)

- Card: IMP-725 (0 points, Amendment A2 §12), with IMP-723 files; follow-up of the any-city readiness audit
- Part: PD-733-G8, PD-733-G10, PD-733-G11
- Run id: RUN-096 (batch H, Sprint 7 close)
- Owner: Manal (Manal Patel)
- Status: PR_OPEN candidate on `fix/RUN-096-batch-h`
- Base commit: 5fa8e6d (on `main`)
- Traces to: A2 §6.2, §6.3, §6.5, §7.1, §7.2, §11; IMD-210 (a), IMD-217, IMD-218, IMD-220; TC-462, TC-469, TC-470, TC-475

## What was built, and the reading taken

- **G8, "treat an Overpass answer with an error note as a failed import, and allow a forced re-import".**
  - `OverpassPlaces` raises `LiveDataUnavailable("error note")` when the body's `remark` is text that contains "error" (any case). The import then ends `failed` / `provider_unavailable`, so nothing partial is stored and nothing is kept for 30 days. The nearby-city lookup falls back to the capital, as for any other error. The note is never logged.
  - Narrowest reading: a `remark` without the word "error" is not a failure.
  - `live_import --force` queues a completed or `insufficient_data` destination again before it expires. It never touches a running import. It is a CLI option only: no route, schema or setting changed.
- **G10, "check the guide page's coordinates against the city".** The MediaWiki request also asks for the page's `coordinates`; `WikiSection` carries them (two optional fields, not a stored or API shape). `rag.live_guides.sections_inside` keeps only sections whose page lies inside the destination's clipped box. A page without coordinates is left out, because it cannot be checked.
- **G11, "run the start-up checks in the import CLI".** The CLI runs `check_settings` before any work. With `LIVE` it also refuses an empty or placeholder `WIKI_USER_AGENT` whatever the switch, because A2 §7.2 says "required when `LIVE_DATA_PROVIDER=LIVE`" and the CLI calls the services with the switch ON or OFF. It prints variable names only, and exits 1. The API's own checks are unchanged.

## Changed files

- `apps/api/app/livedata/providers/osm.py`, `wiki.py`, `base.py`, `fake.py` (the fakes give the SAMPLE pages their settlement's coordinates)
- `apps/api/app/rag/live_guides.py` (`sections_inside` only)
- `apps/api/app/places/live_jobs.py`, `live_import.py`
- `apps/api/tests/unit/livedata/test_live_import_hardening.py` (created, marked `any_city`)
- `apps/api/tests/api/test_live_import_jobs.py` (tests added)
- `apps/api/tests/api/test_live_guides_index.py`, `test_injection.py`: their synthetic guide sections gain Liveton's coordinates; no assertion changed
- `docs/progress/parts/IMP-725-live-import-hardening.md` (this record)

## Commands

| Command | Result line |
| --- | --- |
| `.venv/bin/pytest` on the livedata, rag and live API test files | `790 passed in 18.23s` |
| `.venv/bin/ruff check app tests` / `.venv/bin/mypy app` | `All checks passed!` / `Success: no issues found in 139 source files` |

The run checks on the branch head are in the SYNC REPORT of RUN-096.

## Acceptance

- **An error note never counts as data: verified** (`test_overpass_error_note_is_a_failure`, empty and partial answers).
- **A forced re-import works and respects a running import: verified** (`test_cli_force_*`).
- **Guides only from a page inside the box: verified** (`test_sections_inside_keeps_only_pages_in_the_box`, `test_guides_are_stored_only_from_a_page_inside_the_box`).
- **The CLI start-up checks: verified** (`test_cli_refuses_*`, `test_cli_main_stops_before_any_work`).
- **No contract, schema, migration, Settings default or environment change: verified** by the diff; `make openapi-check` on the branch head.

## Proposed decisions

none

## Open issues

- That Overpass sends such a `remark`, and that real Wikivoyage and Wikipedia pages carry coordinates, are not verified: no live call was made. If a real city page has none, its guides are left out and the plan cites no guide.
- When the page found by title is elsewhere, its sections are dropped. No second lookup by coordinates is made.
- A remark without "error" that still means partial data would pass. The local check (readiness audit, section 6) should look for it.

## Blockers

none
