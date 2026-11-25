# IMP-726 · live-embed-backfill part (embed a live city's missing chunks on a re-run)

- Card: IMP-726 (0 points, Amendment A2 §12); follow-up of the any-city readiness audit
- Part: PD-733-G9 — **built**
- Run id: RUN-096 (batch H, Sprint 7 close)
- Owner: Nidhi (Nidhi Chauhan)
- Status: PR_OPEN candidate on `fix/RUN-096-batch-h`
- Base commit: 5fa8e6d (on `main`)
- Traces to: A2 §6.2, §6.5; IMD-112; TC-478

## What was built, and the reading taken

- Running the import CLI again on a completed, unexpired city now embeds the chunks that an earlier embedding outage left without a vector. It makes no Nominatim lookup, Overpass or MediaWiki call (with `--query` there is the one search, as before). It prints `embedded_on_re_run: N`, with "(incomplete: provider failed)" when the provider fails again; the exit code stays 0 (IMD-112).
- Narrowest reading of "missing": only chunks with **no** vector (`missing_only`). Vectors of another model are kept. So a re-run while staging is on MOCK (ACC-22) cannot replace Gemini vectors.
- `embed_destinations` and `pending_chunks` behave as before without `missing_only`. The release index still covers curated destinations only.

## Changed files

- `apps/api/app/rag/service.py`, `repository.py` (the `missing_only` option)
- `apps/api/app/places/live_import.py`: the import CLI, which the card prompt names ("service and the import CLI"); it is outside `app/rag/`
- `apps/api/tests/api/test_live_guides_index.py` (two tests and one helper added)
- `docs/progress/parts/IMP-726-live-embed-backfill.md` (this record)

## Commands

| Command | Result line |
| --- | --- |
| `.venv/bin/pytest` on the rag, livedata and live API test files | `783 passed in 24.63s` |
| `.venv/bin/ruff check app tests` / `.venv/bin/mypy app` | `All checks passed!` / `Success: no issues found in 139 source files` |
| `.venv/bin/lint-imports --config .importlinter` | `Contracts: 7 kept, 0 broken.` |

The run checks on the branch head are in the SYNC REPORT of RUN-096.

## Acceptance

- **Missing chunks are filled on a re-run, and a second re-run has nothing left to embed: verified** (`test_live_guides_cli_re_run_embeds_what_an_outage_left_out`).
- **Another model's vectors are kept: verified** (`test_live_guides_cli_re_run_keeps_another_models_vectors`).
- **Offline, MOCK embeddings only; no contract, schema, migration or environment change: verified** by the tests and the diff.

## Proposed decisions

none

## Open issues

- A city imported with MOCK and then used with GEMINI keeps its MOCK vectors and lexical ranking; `--force` imports it again.
- The API has no such re-run; only the operator's CLI does. An imported city a traveller chose stays without vectors until the CLI runs or it expires.

## Blockers

none
