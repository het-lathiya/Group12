# IMP-514 · run-records part

- Run id: RUN-068 (Sprint 5 batch A)
- Owner: Manya (Manya Rana)
- Status: committed on the part branch, not pushed (the lead integrates)
- Base commit: 26bac9d (on top of the IMP-503 pace-grouping commit 3796b05 on the same branch)
- Branch: part/IMP-503-pace-grouping
- Traces to: US-129, US-130; FR-120; NFR-041, NFR-042, NFR-046
- Card steps built: 1, 2 and 3. Steps 4 and 5 and `eval/reports/baseline-1.md` are Nidhi's part.

## Changed files

- `apps/api/app/evaluation/manifest.py`: `REQUIRED_FIELDS` (run_id, started_at, git_commit, dataset_id, dataset_version, provider, model_id, prompt_template_id, prompt_version, input and output schema versions, generation_settings, metrics, case_count, failures), `IncompleteRecordError` and `write(path, record)`, which refuses a record where a required field is absent or null and then writes nothing. `build` adds `case_count` and `failures`.
- `apps/api/app/evaluation/run.py`: the generation run builds `failures` (case_id, repeat, error of each errored attempt) and `case_count`, writes the record through `manifest.write` before `scores.json` and `raw/` (per-case outputs), and exits 3 with nothing written if the record is incomplete. The retrieval suite's record is unchanged.
- `apps/api/tests/unit/evaluation/test_run_record.py` (created).
- `.github/workflows/ci.yml`: one step in the `unit` job, `make eval PROVIDER=MOCK DATASET=trips/v1`, after `make test-unit` (CI did not run it before).
- `eval/results/20261114T055841Z-mock/run.json`: the MOCK record of dataset trips/v1 (3 repeats, 45 attempts, `failures: []`, `avg_daily_travel_min: 160.8`). As for the IMP-413 record, only `run.json` is committed; `scores.json` and `raw/` were written and not committed. Its `git_commit` is 3796b05 (the pace-grouping commit), which a rebase changes.

## Commands and results

Run from `apps/api` with `PYTHONPATH=.` (the shared virtual environment's editable install points at the main checkout).

| Command | Result |
| --- | --- |
| `.venv/bin/pytest tests/unit -k run_record` (= `make test-unit ARGS='-k run_record'`) | `18 passed, 1052 deselected, 1 warning` |
| `.venv/bin/pytest tests/unit` | `1070 passed, 1 warning` |
| `.venv/bin/ruff check .` | `All checks passed!` |
| `.venv/bin/ruff format --check .` | `219 files already formatted` |
| `.venv/bin/mypy app` | `Success: no issues found in 120 source files` |
| `.venv/bin/lint-imports --config .importlinter` | `Contracts: 6 kept, 0 broken.` |
| `PYTHONPATH=. make eval PROVIDER=MOCK DATASET=trips/v1` (repository root) | `evaluation 20261114T055841Z-mock: 45 attempts, written to /home/hetlathiya/wt-503-pace-grouping/eval/results/20261114T055841Z-mock` |
| `make eval PROVIDER=GEMINI DATASET=trips/v1` | not run: Nidhi's part (step 4), needs the staging key |
| `make test-api`, `make test-authz` | not run: deferred to integration (no PostgreSQL; the harness uses no database) |

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-120 AC1 / TC-287: a completed run has a record file with all fields | verified | `test_run_record_tc_287_a_completed_run_has_every_field` and the committed MOCK `run.json` |
| TC-390: an incomplete record cannot be saved | verified | `test_run_record_tc_390_an_incomplete_record_cannot_be_saved` (each required field absent and null) and `test_run_record_an_incomplete_run_writes_nothing` (exit 3, empty output folder) |
| Step 2: no API key or prompt body in the record; per-case outputs written | verified | TC-287 test checks the record text and the 15 `raw/` files |
| Step 3: MOCK run in CI | not verified | step added to the `unit` job; CI has not run it yet |
| GEMINI record or documented blocker (TC-391), baseline note (PR-12) | not verified | Nidhi's part |

## Blockers

none

## Proposed decisions

- **PD-IMP-514-1: missing means absent or null.** `write` treats a null required field as missing, so a run on a machine without git (null `git_commit`) or with a provider that gives no model metadata exits 3 without writing. An empty `generation_settings` (MOCK) or `failures` list is valid.
- **PD-IMP-514-2: retrieval record.** The retrieval suite's record (IMP-318) has a different field set and is not checked by `write`; a later card can give it its own required list.

## Open issues

- `make eval` with the shared virtual environment imports the main checkout unless `PYTHONPATH=.` is set; this is only a local worktree effect, not a CI one.

## RUN-069 fix

- Owner: Manya Rana; base commit: 4c6c693; status: verified.
- Replaced `eval/results/20261114T055841Z-mock/run.json` with `eval/results/20261114T064139Z-mock/run.json`.
- After the decision-only part, temporarily checked out detached BASE in the same checkout (no extra branch or worktree), verified a clean tracked tree, and ran `make eval PROVIDER=MOCK DATASET=trips/v1` before any batch code changes. Returned to the batch branch for this commit.
- Exact result: `evaluation 20261114T064139Z-mock: 45 attempts, written to /home/hetlathiya/Group12/eval/results/20261114T064139Z-mock`.
- Verified the record git_commit equals the full origin/main commit for BASE 4c6c693; 15 cases, 3 repeats, 45 attempts, no failures. This resolves the rewritten branch SHA reference under IMD-176. The metrics definition hash is that of BASE content, before IMD-169 documentation.
- TC-287 verified by the complete run record. TC-391 and baseline report not run: BASELINE=no. No new proposed decisions or open issues.
