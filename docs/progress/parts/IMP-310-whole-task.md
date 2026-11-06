# IMP-310 · whole-task part

- Run id: RUN-045 (grouped, IMD-121, with IMP-304, IMP-307 and IMP-310)
- Owner: Junaid (Junaid-Kureshi)
- Status: PR_OPEN
- Base commit: 4f20bfc
- Branch: feat/IMP-304-307-310-wave1
- Reviewer: Manal (manalPatel2557)
- Traces to: US-127; FR-118; NFR-046; TC-283, TC-386
- Card steps built: 1 to 4; step 5 is Kirtan's peer review on the pull request

## Changed files

- `eval/datasets/trips/schema.json` (created): id, version, category, tags, request, hard_constraints, expected_properties.
- `eval/datasets/trips/v1/cases.jsonl` (created): 15 cases on the SAMPLE fixture destination.
- `eval/datasets/trips/v1/manifest.json` (created): dataset id, version, case count, category counts, the SHA-256 of `cases.jsonl` and `schema.json`, and `set_sha256` over both.
- `apps/api/tests/unit/evaluation/test_dataset.py` (created, 40 tests).

Each shortlist was produced by the real `apply_filters` and `rank_shortlist` on the SAMPLE CSV files, and the test compares every place field with `places.csv`.

## Cases

| Category | Cases | Content |
| --- | --- | --- |
| standard | 3 | 2, 3 and 5 days |
| tight_budget | 2 | 40.00 for 2 days, and 150.00 for a family of 4 over 3 days, both `saving` |
| step_free_group | 2 | Step-free with reduced mobility; 6 adults and 3 children |
| must_visit_conflict | 2 | Step-free with two unsuitable places; a Monday with two places closed on Monday |
| pace_extreme | 2 | relaxed and busy |
| long_trip | 1 | 14 days |
| day_regeneration | 1 | Day 2 of 3 with two locked items |
| hostile_notes | 2 | The TC-028 pattern with a redacted e-mail address; a false system message |

Cases tagged `regression` are the regression subset (IMD-39): eight cases from seven categories (all but pace_extreme).

## Commands and results

| Command | Result line |
| --- | --- |
| `make test-unit ARGS='-k dataset'` | `40 passed, 427 deselected, 1 warning in 0.41s` |
| `make lint` | `All checks passed!` (ruff); `All matched files use Prettier code style!` |
| `make typecheck` | `Success: no issues found in 89 source files` |
| `make imports` | `Contracts: 5 kept, 0 broken.` |
| `make test` (via `make check`, `TEST_DATABASE_URL` = the §4.7 default on `pgvector/pgvector:pg16`) | unit `467 passed, 1 warning`; contract `35 passed, 1 warning`; api `250 passed, 1 warning`; authz `28 passed`; web `Tests  80 passed (80)` |
| `make check` | exit 0 (`openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date`) |

Not run: `make e2e` and `make eval` (the harness is IMP-413).

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| Every case has ID, inputs, hard constraints and version (FR-118 AC1, TC-283) | verified | `test_tc_283_every_case_has_id_inputs_hard_constraints_and_version`, `test_tc_283_every_request_is_a_valid_gr_1_request` |
| Dataset integrity check passes (TC-386) | verified | `test_tc_386_ids_are_unique_and_there_are_15_cases`, `test_tc_386_the_manifest_matches_the_files` |
| FR-118 AC2 (TC-284) | not verified | Stage 2: no training set exists |
| No case contains personal data | verified | `test_no_case_contains_personal_data`; also part of Kirtan's review |
| Category shares of blueprint §21.4 | not verified | The blueprint is not in the repository, see PD-IMP-310-1 |
| Peer review of constraint coverage and injection cases (step 5) | not verified | Peer review pending (Kirtan, on the pull request) |

## Blockers

None.

## Proposed decisions

- **PD-IMP-310-1: category shares.** Blueprint §21.4 is not in the repository, so its shares could not be read. The card's eight categories are all covered, with the counts above. Kirtan should check them against the blueprint.
- **PD-IMP-310-2: place IDs.** The fixture has `external_ref` values, not UUIDs, and the seed gives each row a random ID, but gr-1 needs UUIDs. Frozen requests use UUID v5 under the namespace stated in `schema.json`, derived from `external_ref`. No ID refers to a place outside the fixture; the test rebuilds each ID from `places.csv`. IMP-413 can use the frozen shortlist as it stands, and it must map IDs by `external_ref` if it reads database rows.
- **PD-IMP-310-3: schema check.** The project has no JSON Schema library, so the test checks `schema.json` with a short function for the keywords the file uses, and gr-1 with the strict `GenerationRequest` model. `contracts/ai/gr-1.schema.json` is generated from that model.

## Open issues

- **Thin step-free coverage.** SAMPLE has only two places with `step_free` true (sample-001, sample-005), neither of them food, so `trips-v1-006` has a two-place shortlist and no lunch option.
- `hours_summary` is the label form that `request_builder.py` sends today (`hours estimate`); IMP-303 changes it to the trip weekdays' hours, which would need a new dataset version to match.
- The dataset is frozen against pm-1, and pm-2 (IMP-315) would need the same.
- The generator script is not in the repository, as the card does not list it.
