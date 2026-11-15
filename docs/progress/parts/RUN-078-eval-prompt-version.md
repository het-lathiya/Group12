# RUN-078 · eval-prompt-version part (prompt version option of the evaluation CLI)

- Part: E1, `--prompt-version` for `python -m app.evaluation.run` and the prompt version in reports (0 points)
- Run id: RUN-078
- Owner: Manya (Manya Rana)
- Status: PR_OPEN candidate: committed on `part/eval-prompt-version`, not pushed
- Base commit: b715d26 (on `main`)
- Traces to: IMD-195 (added to the decision register in the same pull request), IMD-176, IMD-188, PD-RUN-077-E1, PD-RUN-077-E2

## Changed files

- `apps/api/app/evaluation/run.py`: `--prompt-version` option, choices read from the prompt registry (`itinerary_generate` versions); when given, every frozen request is sent with that version, and a request whose template reads gr-2 is grounded with `request_builder.ground(request, None)` (no passages, lexical fallback), as the pipeline builds it. Refused with `--suite retrieval`. The retrieval report quotes `prompt_version` from the record and says that MOCK does not read the prompt text.
- `apps/api/app/evaluation/manifest.py`: `build` takes the `PromptTemplate` actually used; the record states its id, version, `prompt_sha256` (sha256 of each template file), `input_schema_version` and `output_schema_version` from its `meta.json`, and `prompt_version_overridden`.
- `apps/api/tests/unit/evaluation/test_run_record.py`: five tests (below).
- `eval/README.md`: how to pass the version, what the record states, reports quote the record, MOCK ignores the prompt text.
- `docs/progress/parts/RUN-078-eval-prompt-version.md` (this record).

No evaluation run record was produced or committed (IMD-176). No Gemini call, no API contract, migration, environment variable or dataset change.

## How the override is recorded

Without the option the requests are sent as frozen (`trips/v1`: v1, gr-1) and the record is as before plus `prompt_sha256` and `prompt_version_overridden: false`. With `--prompt-version vN` each request's `prompt_version` is replaced for this run only; the record states `prompt_version` vN, the vN file hashes, vN's schema versions and `prompt_version_overridden: true`. The generation suite writes no report; a report about it must quote these fields from `run.json`.

## Commands

Run from `apps/api` of the worktree with the shared venv, `PYTHONPATH=.` (`app` resolves to `/home/hetlathiya/wt-e/apps/api/app/__init__.py`).

- `ruff check app/evaluation/run.py app/evaluation/manifest.py tests/unit/evaluation/test_run_record.py` → `All checks passed!`
- `ruff format --check` (same files) → `3 files already formatted`
- `mypy app` → `Success: no issues found in 123 source files`
- `lint-imports --config .importlinter` → `Contracts: 6 kept, 0 broken.`
- `python -m pytest tests/unit/evaluation -q` → `80 passed in 0.97s`
- `python -m pytest tests/unit tests/contract -q` → `1287 passed, 2 skipped, 1 warning in 38.90s`

Not run: `make test-api` (no database code changed), `make openapi-check` (no API change), `make test-web` (no web change), any evaluation run (IMD-176) or Gemini call.

## Acceptance criteria

- `--prompt-version` accepts the registry's itinerary_generate versions, not a hard-coded list: **verified** by `test_run_record_an_unknown_prompt_version_is_a_cli_error` (v9 → argparse exit 2, `invalid choice: 'v9'`, nothing written); choices come from `registry.load_all()`.
- `--prompt-version v3` drives the request, the template hash and the record: **verified** by `test_run_record_prompt_version_v3_drives_every_request_imd_195` (all 15 requests reach the provider as v3 gr-2; record `prompt_version` v3, `prompt_sha256` equal to the registry's v3 hashes, gr-2/io-2, `prompt_version_overridden` true, no failures).
- Default unchanged: **verified** by `test_run_record_default_keeps_the_version_the_requests_name` (v1, v1 hashes, gr-1/io-1, overridden false) and the existing TC-285, TC-287, TC-390 tests.
- Reports quote the version from the record and say MOCK ignores the prompt: **verified** for the retrieval report by `test_run_record_retrieval_report_quotes_the_record_prompt_version`; stated in `eval/README.md` for reports written by hand (the generation suite writes none).
- `--prompt-version` is not silently ignored by the retrieval suite: **verified** by `test_run_record_prompt_version_is_refused_for_the_retrieval_suite`.

## Blockers

none

## Proposed decisions

none. Reading of the task: "default = the active version, exactly as today" is taken as "behaviour unchanged when the option is omitted", that is, the version each frozen request names (v1 for `trips/v1`), not `PROMPT_TEMPLATE_VERSION`; changing the default would change every existing run's meaning.

## Open issues

- A gr-2 version is evaluated with no passages (`context_passages` empty, retrieval mode `lexical_fallback`), because `trips/v1` holds gr-1 requests and the generation suite has no database; citation behaviour of v2 or v3 is measured only by the retrieval suite.
- IMD-195 still needs the recorded MOCK run and one Gemini run of v3 on `trips/v1`, from a clean tree at a commit on main (IMD-176), before v3 is activated.
