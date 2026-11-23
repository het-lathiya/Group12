# IMP-732 · gemini-commands part (operator GEMINI command list for trips/live-v1 and prompt v4)

- Card: IMP-732 (0 points, Amendment A2 §6.7, §12 Batch C3), step 5 "One GEMINI run for v4 only if quota allows (IMD-195, rule 16)"
- Part: gemini-commands (preparation only: nothing was run against Gemini, no code changed, `PROMPT_TEMPLATE_VERSION` unchanged)
- Run id: RUN-093 (batch F, Sprint 7, any-city follow-up)
- Owner: Manya (Manya Rana)
- Status: PR_OPEN candidate on `fix/IMP-730-run-093-followups`
- Base commit: 445080f (on `main`)
- Traces to: IMD-176, IMD-195, IMD-199, IMD-200, IMD-213; A2 §6.7; TC-489

## Sources used (every command below comes from one of these)

- `Makefile` target `eval` (lines 177 to 180): `cd apps/api && .venv/bin/python -m app.evaluation.run --dataset $(DATASET) --provider $(PROVIDER) $(ARGS)`.
- `apps/api/app/evaluation/run.py`, the CLI options:
  - `--dataset`, `--suite` (default `generation`);
  - `--provider` (`MOCK`, `GEMINI`, `RULE_BASED`);
  - `--repeats` (default **3**), `--out` (default `eval/results/<run_id>/`);
  - `--prompt-version` (the `itinerary_generate` versions in the registry: v1, v2, v3, v4).
  - A GEMINI run is refused (exit 2) without `GEMINI_API_KEY`.
- `eval/README.md` (the `--prompt-version` usage) and `eval/reports/RUN-079-prompt-v3.md` (how the last prompt-gate GEMINI run was made: clean worktree, commands, what is committed).
- `eval/reports/final-baseline.md` (IMD-213: the final GEMINI v2 run `20261120T165222Z-gemini`).
- The Gemini adapter, `apps/api/app/ai/providers/gemini.py`:
  - `MAX_ATTEMPTS = 2`, i.e. at most one retry, for timeouts, rate limits and outages only, as `GEMINI_MAX_RETRIES` (default 1) allows;
  - no repair call in the evaluation harness;
  - the generation suite makes **no embedding calls**, because gr-2 requests are grounded with no passages.
- `.env.example` (variable names) and `app/core/config.py` (defaults).

## Environment variable names (names only; values from the operator's own untracked env file or shell)

| Name | Needed for | Note |
| --- | --- | --- |
| `GEMINI_API_KEY` | every GEMINI command | Required; without it the run exits 2 with "GEMINI_API_KEY is not set". Do not set any other Google key variable (`.env.example`). |
| `GEMINI_MODEL_ID` | every GEMINI command | `gemini-3.5-flash-lite`, the model of baseline-1, RUN-079 and the final baseline |
| `GEMINI_TIMEOUT_S` | optional | default 35, as in all earlier GEMINI runs |
| `GEMINI_MAX_RETRIES` | optional | default 1. Each attempt is at most 2 calls. Setting 0 lowers the upper bound to 1 call per attempt but changes the settings the earlier runs used; keep the default for comparability. |
| `APP_ENV` | optional | leave unset or `local`/`test`; the staging/production start-up checks do not apply to the CLI |

`GEMINI_EMBEDDING_MODEL_ID` is not needed: the generation suite does not embed. `AI_PROVIDER` and `PROMPT_TEMPLATE_VERSION` do not affect these runs. `--provider` and `--prompt-version` choose them, and the run record states the version.

## Before the first command (IMD-176: clean tree at a commit on `main`)

This setup follows `RUN-079-prompt-v3.md`.

```sh
git fetch origin
git worktree add --detach ../group12-eval origin/main   # the evaluation worktree; keep it until the report merges (IMD-200)
cd ../group12-eval
git status --porcelain                                  # must print nothing
```

- **`make eval` inside the worktree.** It runs `apps/api/.venv/bin/python`, and a fresh worktree has no `apps/api/.venv` (an untracked directory). Use one of two ways:
  - (i) run `make setup` in the worktree first, then use the `make eval` commands below; or
  - (ii) as in RUN-079, run the same module with the main checkout's environment: `cd apps/api && PYTHONPATH=. <main checkout>/apps/api/.venv/bin/python -m app.evaluation.run …` with the same options.
  - Either way the record is written by the same module.
- The env names above are needed. Supply them for these commands only, by exporting them in that shell, not in a committed file. The worktree has no `apps/api/.env`.

## Command list, in order (minimum Gemini calls)

The counts are provider calls, i.e. attempts × (1 to 2). MOCK and RULE_BASED make no Gemini call.

| # | Purpose | Exact command (from the repository root of the worktree) | Gemini calls |
| --- | --- | --- | --- |
| 0 | MOCK v4 on trips/v1, the MOCK half of the IMD-195 gate | `make eval PROVIDER=MOCK DATASET=trips/v1 ARGS='--prompt-version v4'` | 0 (45 attempts) |
| (a) | GEMINI, trips/live-v1, prompt v2 | `make eval PROVIDER=GEMINI DATASET=trips/live-v1 ARGS='--prompt-version v2 --repeats 1'` | 8 attempts → 8 calls, at most 16 |
| (b) | GEMINI, trips/live-v1, prompt v4 | `make eval PROVIDER=GEMINI DATASET=trips/live-v1 ARGS='--prompt-version v4 --repeats 1'` | 8 attempts → 8 calls, at most 16 |
| (c) | GEMINI, trips/v1, prompt v4: **needed** if v4 is to be activated | `make eval PROVIDER=GEMINI DATASET=trips/v1 ARGS='--prompt-version v4'` | 45 attempts (15 × 3) → 45 calls, at most 90 |

Notes on the list:

- **Minimum total.** (a) + (b) = 16 calls (at most 32). With (c) the total is 61 calls (at most 122).
  - `--repeats 1` is the smallest valid live-v1 run.
  - With the default 3 repeats, (a) and (b) are 24 attempts each and directly comparable with the committed live-v1 MOCK and RULE_BASED records (24 attempts). That costs 48 calls instead of 16.
  - (c) keeps the default 3 repeats, so its counts stay comparable "out of 45" with baseline-1 (`20261114T104200Z-gemini`) and the final v2 run (`20261120T165222Z-gemini`).
- **Why (c) is needed.** A2 §6.7 activates v4 "only through the IMD-195 procedure". IMD-195's gate is a MOCK run and one GEMINI run **on trips/v1**. live-v1 alone cannot activate v4.
- **What (a) and (b) can and cannot show.** live-v1 cases are gr-1 requests with no passages, and the CLI grounds a gr-2 version with no passages. v4 changes only the sentence about `context_passages` source titles (A2 §6.7). So (a) and (b) show v4 does not harm live-city plans; they cannot show the passage-title wording at work. Citation coverage stays not measurable (IMP-732 record).
- **Quota (IMD-200).** On the free key, quota or rate-limit failures are counted as they are and never re-run. The final v2 run lost 22 of 45 attempts to `provider_unavailable`. If (a) or (b) already shows quota failures, stop before (c) and record it.
- **Not needed.** A GEMINI v2 run on trips/v1, because `20261120T165222Z-gemini` (IMD-213) is that run. A GEMINI RULE_BASED run does not exist (RULE_BASED makes no provider call).
- **Do not run** `make live-smoke` for this. It is a different check.

## (d) Committing or handing back the results

As in RUN-079 and IMP-732:

- Each run prints `evaluation <run_id>: <N> attempts, written to …/eval/results/<run_id>`. Keep the printed line for the report.
- Commit `eval/results/<run_id>/run.json` and `scores.json`, copied unchanged. **Do not commit `raw/`** (model outputs). The worktree keeps them until the report merges (IMD-200).
- Write `eval/reports/live-v1-gemini-<date>.md`, named like `live-v1-2026-11-23.md`. It holds:
  - the run ids and commands;
  - `git_commit`, `prompt_version` and `prompt_version_overridden` quoted from each `run.json`;
  - the tables below and the gate verdict.
- These go on a branch as one part commit by the IMP-732 owner (Manya, `docs(eval): IMP-732 …`), through the usual pull request. If the operator cannot commit, they can hand back the `eval/results/<run_id>/` folders (without `raw/`) and the printed lines, and Manya's next run writes the report.
- Check before committing: `git status` in the worktree shows only the new `eval/results/<run_id>/` folders.
- Never commit a key or env file. The records hold no key and no prompt body (`run.py`: "Keys and prompt bodies are never written").

## (e) IMD-195 activation criteria for v4, and the numbers to read

Read each record's `run.json` → `metrics.counts.<name>.k` / `.n`, plus `failures` and `prompt_version`. Read `scores.json` for per-attempt `duplicate_places` and `rejected_items`.

| Gate condition (IMD-195, as applied in RUN-079) | Read from | Holds when |
| --- | --- | --- |
| Record from a clean tree at a commit on `main` | `run.json` `git_commit` | it is a `main` commit |
| Prompt version is v4 | `run.json` `prompt_version`, `prompt_version_overridden` | `v4`, `true` |
| GEMINI v4 trips/v1, schema-valid | `metrics.counts.schema_valid` of (c) | ≥ 44/45 (baseline-1) |
| GEMINI v4 trips/v1, valid place IDs | `metrics.counts.place_ids_valid` of (c) | ≥ 44/45 |
| GEMINI v4 trips/v1, usable | `metrics.counts.usable` of (c) | ≥ 44/45 |
| GEMINI v4 trips/v1, failures | `failures` of (c) | ≤ 1 (baseline-1 had 1) |
| **Duplicate places 0** | `metrics.counts.no_duplicate_places` of (c) and `duplicate_places` per attempt in `scores.json` | 45/45, sum 0. Rejected duplicates still count (IMD-200). |
| MOCK v4 trips/v1 | `metrics.counts` of run 0 | 45/45 on all four |
| live-v1 GEMINI, not part of the gate | `metrics.counts` of (a) and (b) | reported; v4 should be no worse than v2 |

- If every gate row holds, propose activating v4 as a PD in the report. Changing `PROMPT_TEMPLATE_VERSION` to v4 needs a team decision and its own pull request. It is not done by the evaluation part.
- If any row fails, v2 stays active (IMD-200) and the report states the failing rows.
- Average daily travel is reported only, never gated.

## Changed files

- `docs/progress/parts/IMP-732-gemini-commands.md` (this record)

## Commands

| Command | Result line |
| --- | --- |
| `make check` on the head | see the SYNC REPORT of RUN-093 |

Nothing reached Gemini. No `make eval PROVIDER=GEMINI` and no `make live-smoke` was run. No env file was read.

## Acceptance

- **The operator GEMINI command list exists, and every command traces to the Makefile or the docs: verified** (sources listed above).
- **Expected provider calls and env names (names only) are given for each command: verified.**
- **No code change, no `PROMPT_TEMPLATE_VERSION` change: verified** (`git diff --stat` shows only this record).

## Proposed decisions

none

## Open issues

- **Does not exist:** a `make` variable for the prompt version or the repeat count. Both are passed through `ARGS` (`--prompt-version`, `--repeats`), as `eval/README.md` shows.
- **Does not exist:** a ready virtual environment in a fresh evaluation worktree for `make eval`. Use `make setup` there, or the RUN-079 direct-module form.
- live-v1 with no passages cannot show v4's passage-title sentence at work. A gr-2 live dataset with passages is future work (IMP-732 record).

## Blockers

none
