# IMP-413 · whole-task part

- Run id: RUN-056 (grouped, IMD-121, with IMP-404 schedule-rules and reference-rules)
- Owner: Manya (manyarana)
- Status: PR open
- Base commit: f7f3c51
- Branch: feat/IMP-404-413-validator-eval
- Reviewer: Kirtan (kirtan-S111)
- Traces to: US-128; FR-119; NFR-046
- Card steps built: 1 to 5, narrowed as the run prompt says

## Changed files

- `apps/api/app/evaluation/run.py` (created): `python -m app.evaluation.run --dataset <id>/<version> --provider MOCK|GEMINI|RULE_BASED [--repeats 3] [--out eval/results/<run_id>/]`. Each attempt runs the production functions of steps 7 to 9 (`generate_itinerary`, `output_check.apply_limits` and `check_output`, `schedule.recalculate`, `budget.engine`, `validator.validate`) offline, with the §9.3.5 distance estimate as the routing. The provider is built from a copy of the settings, so `AI_PROVIDER` never changes. Writes `run.json`, `scores.json` and `raw/<case>_<repeat>.json`.
- `apps/api/app/evaluation/metrics.py` (created): `compute(scores)`, metrics version v1.
- `apps/api/app/evaluation/manifest.py` (created): dataset loading with the hash check, the run record and the git commit.
- `eval/metrics_v1.md` (created): the v1 definitions.
- `apps/api/tests/unit/evaluation/test_harness.py` (created).
- `eval/results/20261109T095227Z-mock/run.json`: the record of the MOCK run below. `scores.json` and `raw/` of that run were not committed (the prompt asks for `run.json`); `eval/results` is not gitignored.
- `Makefile`: not changed; the `eval` target already passes `DATASET`, `PROVIDER` and `$(ARGS)`.

## Commands and results

| Command | Result |
| --- | --- |
| `make test-unit ARGS='-k harness'` | `7 passed, 865 deselected, 1 warning` |
| `make eval DATASET=trips/v1 PROVIDER=MOCK` | `evaluation 20261109T095227Z-mock: 45 attempts, written to /home/hetlathiya/Group12/eval/results/20261109T095227Z-mock`; counts `schema_valid 45/45`, `place_ids_valid 45/45`, `usable 45/45` |
| `make test-unit` | `872 passed, 1 warning` |
| `make test-contract` | `87 passed, 2 deselected, 1 warning` |
| `make test-web` | `Tests  119 passed (119)` |
| `make lint` | exit 0 (`All matched files use Prettier code style!`) |
| `make typecheck` | `Success: no issues found in 110 source files` |
| `make imports` | `Contracts: 6 kept, 0 broken.` |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |
| `make test-api`, `make test-authz` | not run to a result: no PostgreSQL or Docker on this machine (connection refused on port 5432); the harness uses no database. Evidence comes from the CI `api` job |
| `make eval PROVIDER=GEMINI` | not run: GEMINI is never run in this session (card step 5) |

The `git_commit` in the committed `run.json` is the reference-rules commit the run was made on, before this part's own commit; a rebase changes commit IDs again.

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-119 AC1: a MOCK run completes offline with fixture results (TC-285) | verified | `test_tc_285_tc_387_mock_dry_run_completes_offline_and_writes_the_record` (the unit suite's socket guard blocks any network) and the `make eval` run above |
| FR-119 AC2: metric definitions are identical across providers (TC-286) | verified | `test_tc_286_metric_definitions_take_no_provider_and_score_alike`: `compute` has one parameter, `scores`; the run record holds the SHA-256 of `eval/metrics_v1.md` |
| Harness dry run with MOCK passes in CI (TC-387) | verified locally; CI not yet run | The same test runs in the CI `unit` job |
| Output validity uses the same validator as production (TC-041) | verified | `test_tc_041_scoring_uses_the_production_validator_and_output_check`: the harness calls `app.validation.validator.validate` and `app.validation.output_check` themselves, and the flawed mock answer gives MUST_VISIT_MISSING |
| GEMINI is refused without `GEMINI_API_KEY`, with no network call | verified | `test_gemini_is_refused_without_a_key_and_never_built` (exit 2, no provider built) |
| RULE_BASED exits 2 with "rule-based planner not available (IMP-402)" | verified | `test_rule_based_exits_2_until_the_planner_exists` |
| Metrics 1 to 6, 10, 11 and 13 implemented | not verified | Their definitions are not in the repository; see PD-IMP-413-3 |

## Blockers

- The numbered metrics of blueprint §21.4 cannot be computed: the blueprint is not in the repository (as PD-IMP-310-1 found), and no section of the specification defines metrics 1 to 13. The harness records each as `value: null` with its reason.

## Proposed decisions

- **PD-IMP-413-1: dataset name.** The card's objective says `--dataset itinerary/v1`; the dataset on main, its Interfaces row and §8.17 say `trips/v1`. Built with `trips/v1`, and no new dataset was created.
- **PD-IMP-413-2: RULE_BASED.** `generation/fallback_planner.py` is not on main (IMP-402), so `--provider RULE_BASED` exits 2 with "rule-based planner not available (IMP-402)". IMP-402 or a later run wires it in.
- **PD-IMP-413-3: numbered metrics.** With blueprint §21.4 missing, every numbered metric is "not computed in v1" (7 and 9 as the card says, 12 null without a dated price table, 8 Release 2). The run computes three counts whose rules the specification states exactly: schema-valid answers (§8.11 step 1), answers with every place ID valid (§8.11 step 3) and usable plans (§8.12). The team should put the §21.4 list in the specification so v2 can define metrics 1 to 13.
- **PD-IMP-413-4: routing and costs in the harness.** Step 9 uses the §9.3.5 distance estimate (`travel_time`) instead of the route cache and OpenRouteService, so a run needs no database or network. gr-1 has no price currency, so shortlist prices are read in the trip's budget currency, and the transport and stay inputs, which gr-1 does not carry, are null.
- **PD-IMP-413-5: no repair and no locks.** Step 10 (IMP-502), the re-insertion of locked items and the day-scope drop of §8.11 steps 2 and 4 are not built in `output_check`, so an attempt is scored on the provider's answer as step 8 and step 9 leave it. The day-scope case (trips-v1-013) is scored on its one returned day.

## Open issues

- The report `eval/reports/<run_id>.md` with Wilson intervals (§8.17) is IMP-514.
- Every MOCK attempt is usable because step 9 replaces the model's times; an overlap in an answer can never reach the validator. Metrics that look at the model's own times would need a definition first.
