# IMP-725 · jobs-cli part (job runner, claim, reaper, repository writes, import CLI)

- Card: IMP-725 Live import service, job runner, API-76 to API-79 and trip rule (Amendment A2 §6.2 to §6.4, §12; 0 points)
- Part: job runner, claim, reaper, repository writes and the import CLI
- Run id: RUN-090 (Batch C1b, Sprint 7, inserted under IMD-215)
- Owner: Manal (Manal Patel)
- Status: PR_OPEN candidate on `feat/S7-C1b-any-city-import`
- Base commit: 4c4df80 (on `main`)
- Traces to: IMD-12, IMD-29, IMD-33, IMD-112, IMD-210; A2 §6.2, §6.3 (storage), §6.4, §6.5 (place indexing); TC-474, TC-475, TC-479 (IMP-725 share)

## Changed files

- `apps/api/app/places/live_jobs.py` (create): its own semaphore `IMPORT_MAX_CONCURRENT = 1`, `IMPORT_TIMEOUT_S = 300`, `IMPORT_STALE_AFTER_S = 360`, queued rows reaped after `IMPORT_QUEUED_STALE_AFTER_S = 600`, reaper every 60 s (code constants, IMD-29). `submit(destination_id)` starts an asyncio task and keeps a strong reference; the service calls it after commit through `get_import_submitter`. `run_import(...)` steps:
  1. Claim with one `UPDATE … WHERE id = :id AND import_status = 'queued'`; if no row changes, the job ends.
  2. Fetch places from Overpass.
  3. Normalise, dedupe and cap.
  4. Gate with `LIVE_MIN_USABLE_PLACES`. On `insufficient_data` only the row's state, counts, `nearby_city` and `expires_at` are stored.
  5. In one transaction through the places service: OpenStreetMap source, place upsert, deactivation of missing places, counts, the RAG place documents and the completion. Embedding runs after the commit, and an embedding failure only logs (IMD-112).
  6. `completed`, `is_active = true`, `imported_at`, `expires_at`.

  Errors: timeout → `failed`/`timeout`; 429 or open breaker → `failed`/`rate_limited`; other provider errors → `failed`/`provider_unavailable`; anything else → `failed`/`internal`, logged with the destination id only. `reap_stale_imports` and `reap_imports_forever` (the loop survives a database outage). `_index_live_guides(...)` is the named no-op call site for IMP-726 (Nidhi, C2); no guide is fetched here.
- `apps/api/app/places/repository.py`: a marked write section at the end: claim, state and counts, data-source upsert by name, place upsert by `(source_id, external_ref)`, deactivation of missing places (never delete), and the reap. Existing functions are unchanged.
- `apps/api/app/places/service.py`: OpenStreetMap source constants (licence `ODbL 1.0`, the exact A2 §9.3 attribution text, the copyright URL), `store_live_places` (no `place_opening_hours` rows), and the claim, insufficient-data, complete, fail and reap service functions.
- `apps/api/app/main.py`: the C1a no-op hook is replaced by `reap_imports_forever` from `app.places.live_jobs`, still started only when `any_city_mode` is ON (the change is limited to that hook).
- `apps/api/app/places/live_import.py` (create): `python -m app.places.live_import --osm-ref R1234567` or `--query "<city>"` (first settlement). It runs synchronously and inline (not through `submit`), and is idempotent per `external_ref`. It prints the counts and the final state. A completed or `insufficient_data` destination that has not expired is only printed. A failed or expired one is queued again. A new one is created with `import_requested_by` null. Exit codes: 0 completed or `insufficient_data`, 1 failed, 2 bad arguments, 3 already running.
- `apps/api/tests/api/test_live_import_jobs.py` (create, 21 tests, all marked `any_city`; the app is built with the switch ON through a settings override): TC-474, TC-475, the claim, the reaper, the CLI, the capital fallback, an embedding failure, and the TC-479 share. That last path is: resolve twice through API-77 (202, then 200 with the same id), import, create a trip in INR (the destination currency), and run a MOCK generation that completes using stored place ids only, with `COST_INCOMPLETE` and `HOURS_UNVERIFIED`.
- `docs/progress/parts/IMP-725-jobs-cli.md` (this record).

## Commands

| Command | Result line |
| --- | --- |
| `make test-api ARGS='-k live_import_jobs -q'` | `21 passed, 642 deselected, 1 warning in 2.60s` |
| `make test-api` (whole API suite) | `663 passed in 118.81s (0:01:58)` |
| `make test-unit` | `1824 passed in 8.52s` |
| `make test-contract` | `99 passed, 2 deselected in 20.17s` |
| `ruff check app tests` / `ruff format --check app tests` / `mypy app` | `All checks passed!` / `253 files already formatted` / `Success: no issues found in 138 source files` |
| `make imports` | `Contracts: 7 kept, 0 broken.` |

The run checks on the branch head are in the SYNC REPORT of RUN-090.

## Acceptance

- The fake `ok` import completes and activates the destination, and a trip and a MOCK generation succeed with stored place IDs only: **verified** (TC-474, TC-479 share).
- `small` gives `insufficient_data` with a nearby city (or the capital): **verified**.
- `timeout` and `rate_limited` give `failed` with the reason (and `malformed` gives `provider_unavailable`): **verified** (TC-475).
- Stale imports are reaped: **verified** (running over 360 s, queued over 10 min).
- A second resolve returns the same destination: **verified** (API-77 202 then 200).
- A repeat import is idempotent and deactivates missing places without deleting them: **verified** (TC-474).

## Cut-if-late items

None cut. The Overpass nearby-city lookup is built: `largest_city_near(centre, 150 km)`, and any error falls back to the country capital. The refresh of expired destinations is built by the resolve re-queue (service-routes part) and the CLI.

## Open issues

- Place documents are written through private helpers of `rag.service` (`_write`, `_Loaded`, `_embed`), and place documents are built with `rag.documents.place_document`. No `app/rag` file is edited. A public `rag.service` function for one destination's documents would be cleaner; IMP-726 (C2) touches `rag/service.py` and can add it.
- `_write` deactivates documents missing from the run for the whole destination. When IMP-726 adds live guides, guides and places must be written in one `_Loaded`, or a place-only write deactivates the guides.
- The global corpus cap of A2 §6.5 (5,000 active chunks, oldest expired live destination first) is not built here (IMP-726). The 400-chunk per-destination cap holds, since at most 300 places give one chunk each.
- When the refresh of an active destination ends in `insufficient_data` or `failed`, `is_active` stays true: earlier places and existing trips keep working, but the row shows that state while active. For the team.
- The CLI has its own `build_live_row` and `_six`, duplicating the row building of `live_service.resolve`. The service-routes part is already committed, so the extraction is left for a follow-up.

## Proposed decisions

- PD-725-1 (proposed): a refresh that ends in `insufficient_data` or `failed` keeps an already active live destination active with its earlier places.

## Blockers

none
