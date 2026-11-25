# IMP-732 · gemini-v4-result part (operator v4 evaluation records; v4 not activated)

- Card: IMP-732 (0 points, Amendment A2 §6.7, §12 Batch C3), step 5
- Part: gemini-v4-result (records and report only; no code, prompt, dataset or configuration change)
- Run id: RUN-094 (Sprint 7, any-city follow-up)
- Owner: Manya (Manya Rana)
- Status: PR_OPEN candidate on `chore/IMP-732-gemini-v4-result`
- Base commit: 8d5febd (on `main`)
- Traces to: IMD-176, IMD-195, IMD-200, IMD-213; A2 §1.3, §6.7; TC-489

## Changed files

- `eval/results/<run id>/run.json` and `scores.json` for the five run ids in the table below (copied from the evaluation worktree `group12-eval`; only these two files were read there, never `raw/`)
- `eval/reports/live-v1-gemini-2026-11-25.md`
- `docs/progress/parts/IMP-732-gemini-v4-result.md` (this record)

## SHA-256, source against copy (`shasum -a 256`; `cmp` also silent for each pair)

| File under `eval/results/` | Source | Copy |
| --- | --- | --- |
| `20261124T160444Z-mock/run.json` | `e8a8148e98b8bb71f784b71e85b1e6e044b137c0fa268370f8bdbf3ab2770a45` | `e8a8148e98b8bb71f784b71e85b1e6e044b137c0fa268370f8bdbf3ab2770a45` |
| `20261124T160444Z-mock/scores.json` | `bfbd2c7194e8d748fb96ae0ee74dbc211c72b6b121e0adea38a5fdcfcd57db1e` | `bfbd2c7194e8d748fb96ae0ee74dbc211c72b6b121e0adea38a5fdcfcd57db1e` |
| `20261125T155020Z-mock/run.json` | `19305336340c51ec0a89860006944aa151553ee4f058bb5de61bdd567d026b62` | `19305336340c51ec0a89860006944aa151553ee4f058bb5de61bdd567d026b62` |
| `20261125T155020Z-mock/scores.json` | `bfbd2c7194e8d748fb96ae0ee74dbc211c72b6b121e0adea38a5fdcfcd57db1e` | `bfbd2c7194e8d748fb96ae0ee74dbc211c72b6b121e0adea38a5fdcfcd57db1e` |
| `20261124T160457Z-gemini/run.json` | `03e66b76ae27580dd758e0324746abf8b6df08f021220daa8552edac6f32b8ad` | `03e66b76ae27580dd758e0324746abf8b6df08f021220daa8552edac6f32b8ad` |
| `20261124T160457Z-gemini/scores.json` | `c2bd201bec9a784e140633543b06e6d55cc1ed7687c4d0baeab3b51ce1dbcbbe` | `c2bd201bec9a784e140633543b06e6d55cc1ed7687c4d0baeab3b51ce1dbcbbe` |
| `20261124T163607Z-gemini/run.json` | `bc728f9a666a02d206899b241fc506cef8562c90f16be4cdab5fd931599d9e05` | `bc728f9a666a02d206899b241fc506cef8562c90f16be4cdab5fd931599d9e05` |
| `20261124T163607Z-gemini/scores.json` | `0c08b84d8dbbe8084bba97e6ad31938e4a3f1dc9586345daa96a2da82095788f` | `0c08b84d8dbbe8084bba97e6ad31938e4a3f1dc9586345daa96a2da82095788f` |
| `20261125T155029Z-gemini/run.json` | `c3c968fa1fce856879adab64fa2c9ddd50f1dda0e1994005bafb30cafce39144` | `c3c968fa1fce856879adab64fa2c9ddd50f1dda0e1994005bafb30cafce39144` |
| `20261125T155029Z-gemini/scores.json` | `b7c99d3bee06f3c4d49e6c80adb9ef6cd3236da1838874bb50c0767a75f8afda` | `b7c99d3bee06f3c4d49e6c80adb9ef6cd3236da1838874bb50c0767a75f8afda` |

A search of the ten files for `api_key`, `AIza`, `secret`, `password` and `postgres:` found no match.

## Commands

| Command | Result line |
| --- | --- |
| `make lint` | `All checks passed!`, `269 files already formatted`, `All matched files use Prettier code style!` |
| `make typecheck` | `Success: no issues found in 139 source files` and `✓ Types generated successfully` (tsc printed no error) |
| `make imports` | `Contracts: 7 kept, 0 broken.` |
| `make openapi-check` | `openapi-check: contracts/, apps/web/lib/api/schema.d.ts and apps/web/lib/api/any-city-schema.d.ts are up to date` |
| `make test` (exit 0): test-unit | `1851 passed, 1 warning in 8.82s` |
| test-contract | `99 passed, 2 deselected, 1 warning in 19.19s` |
| test-api | `680 passed, 1 warning in 140.17s (0:02:20)` |
| test-authz | `91 passed, 14 skipped, 1 warning in 25.12s` |
| test-web | `Test Files  50 passed (50)`, `Tests  364 passed (364)` |

The tests used the compose PostgreSQL (`make db-up`). Not run, by the run prompt: `make eval`, `make live-smoke`, anything that calls Gemini. `make e2e` was not run: no journey is touched.

## Acceptance

- **Five record pairs on the branch, byte-identical: verified** (table above).
- **No `raw/` in the diff: verified.** `git diff --name-only origin/main | grep -c '/raw/'` printed 0 on the branch head.
- **The report holds the seven sections with numbers matching the records: verified.** The run table was printed by a script from the copied JSON files; sections 2, 3 and the attempt figures were read from the same files. Section 4 is the operator's observation and is labelled so; it is not verifiable here.
- **`git_commit` is a `main` commit: verified.** `8d5febd424dcf269a3b8c34dbadf3a4ad3309c53` in all five; it is an ancestor of `origin/main`.
- **`PROMPT_TEMPLATE_VERSION` unchanged: verified** (`v2` in `.env.example`, `app/core/config.py` and the staging template; none of them is in the diff).

## Proposed decisions

- PD-IMP-732-1 (optional, future work): re-run (c), GEMINI v4 on trips/v1, after release if quota and availability allow.

## Open issues

- Command (b) was started three times, although IMP-732 step 5 foresees one GEMINI run and IMD-200 says quota or rate-limit failures are never re-run (the first run holds one `provider_rate_limited`). All three are committed and counted; the verdict does not depend on it. The report states it in section 3.
- Command (a), GEMINI v2 on live-v1, has no record, so the reported-only row "v4 no worse than v2" is not run.
- The printed `evaluation <run_id>: …` lines of the five runs were not handed back, so the report does not quote them.
- The records do not hold the state of the tree, and whether earlier result folders were moved out before each later run is not recorded. IMD-176 is judged by `git_commit`, as section (e) says.
- Keep the evaluation worktree `group12-eval` until this report merges (IMD-200).

## Blockers

none
