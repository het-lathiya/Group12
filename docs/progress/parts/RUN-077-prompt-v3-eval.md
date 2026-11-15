# RUN-077 · prompt-v3-eval part (itinerary_generate v3 evaluation and activation)

- Part: MOCK evaluation of itinerary_generate v3 against v2 and, if it passes, activation (0 points)
- Run id: RUN-077
- Owner: Manya (Manya Rana)
- Status: PARTIAL: evaluation runs recorded; v3 **not activated** (PD-RUN-077-E1). Committed on `part/e`, not pushed
- Base commit: 0e15ae7 (on `main`)
- Traces to: IMD-176, IMD-180, IMD-181, IMD-188, PD-RUN-075-G3

## Changed files

- `eval/results/20261115T194621Z-mock/run.json` (created by the tool, unchanged): run with Settings default (`PROMPT_TEMPLATE_VERSION` unset, v2).
- `eval/results/20261115T194622Z-mock/run.json` (created by the tool, unchanged): run with `PROMPT_TEMPLATE_VERSION=v3`.
- `eval/reports/RUN-077-prompt-v3-mock.md` (created): the tool writes no report for the generation suite, so the report is written in the style of `baseline-1.md`.
- `docs/progress/parts/RUN-077-prompt-v3-eval.md` (this record).

As for every earlier run, only `run.json` is committed; the tool's `scores.json` and `raw/` were read for the counts below and then removed (MOCK output is deterministic and the two runs' raw outputs were byte-identical). Between the two runs the first run's folder was moved out of the working tree so that the second run also started from an empty `git status --porcelain`, then moved back unchanged.

## Commands

Run from the worktree root at BASE 0e15ae7, MOCK provider only, no Gemini call.

- `git status --porcelain` → empty before each run
- `make eval PROVIDER=MOCK DATASET=trips/v1` → `evaluation 20261115T194621Z-mock: 45 attempts, written to /home/hetlathiya/wt-e/eval/results/20261115T194621Z-mock`
- `PROMPT_TEMPLATE_VERSION=v3 make eval PROVIDER=MOCK DATASET=trips/v1` → `evaluation 20261115T194622Z-mock: 45 attempts, written to /home/hetlathiya/wt-e/eval/results/20261115T194622Z-mock`
- `cd apps/api && .venv/bin/python -m pytest tests/unit tests/contract -q` → `1276 passed, 2 skipped, 1 warning in 38.46s` (no code changed; baseline at BASE)

Not run: `make openapi-check` (nothing activated, no API or schema change); `make test-api` (no code change); any Gemini evaluation.

## Results

Both records: `prompt_version` **v1**, `input_schema_version` gr-1, `output_schema_version` io-1, `git_commit` 0e15ae75…, metrics v2. Counts identical in both: schema_valid 45/45, place_ids_valid 45/45, usable 45/45, no_duplicate_places 45/45 (duplicate-place items 0), avg daily travel 120.8 min, 0 failures; "AI-written" in 0 of 558 notes and assumptions. Details in `eval/reports/RUN-077-prompt-v3-mock.md`.

The generation suite sends the frozen requests of `trips/v1`, which all name `prompt_version: "v1"`; the record and the adapters use the version in the request. `PROMPT_TEMPLATE_VERSION` only sets the default of `registry.load` (start-up check and generation pipeline), so the override had no effect. MOCK also ignores the prompt text, so equal metrics would be expected even with v3.

## Acceptance criteria

- E1: two MOCK runs over trips/v1 recorded from a clean tree at a commit on main (IMD-176): **verified** by the two `run.json` files (`git_commit` 0e15ae7, empty `git status --porcelain` before each run).
- E1: the record states the prompt version actually used: **verified**; it is v1 in both, so the requested v2 and v3 runs **were not** evaluations of v2 or v3.
- E1: duplicate count (IMD-181) and label check (IMD-180) reported: **verified** from `scores.json` (`duplicate_places` summed: 0 and 0) and the raw outputs (0 "AI-written").
- E2: activate v3 only if a run really evaluated v3: **not met**, so v3 was not activated; Settings default and `.env.example` stay `v2`.

## Blockers

- No evaluation path sends itinerary_generate v3: the dataset `trips/v1` pins v1 (gr-1) in every request and the harness has no prompt-version option. IMD-188's condition for activation (a MOCK evaluation of v3 recorded from main) cannot be met as the tooling stands.

## Proposed decisions

- **PD-RUN-077-E1: do not activate v3 yet; make the harness evaluate the active prompt version.** The RUN-077 runs evaluated v1, not v2 or v3, because the generation suite uses the dataset's frozen gr-1 requests. Proposed: either a new dataset version (`trips/v2`) whose frozen requests are gr-2 with `prompt_version` v3 (and one with v2 for comparison), or a harness `--prompt-version` option that rebuilds each request for that version through `request_builder`; then a recorded MOCK run (IMD-176) and, because MOCK ignores the prompt, a recorded Gemini run of v2 against v3 before activation. Until then v2 stays active.
- **PD-RUN-077-E2: label the prompt version in reports by the record, not the setting.** A report must quote `prompt_version` from `run.json`; an environment variable set for the command is not evidence of the version evaluated.

## Open issues

- IMD-188's MOCK-only gate cannot show any effect of a prompt change, since MOCK does not read the prompt; a Gemini comparison is needed to judge IMD-180 and IMD-181 behaviour of v3.
