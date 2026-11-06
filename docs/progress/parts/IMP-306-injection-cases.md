# IMP-306 · injection-cases part

- Run id: RUN-048 (grouped, IMD-121, with IMP-306 output-validation and IMP-313)
- Owner: Junaid (Junaid-Kureshi)
- Status: PR_OPEN
- Base commit: 654b4f7
- Branch: feat/IMP-306-313-wave3
- Reviewer: Nidhi (Nidhi9864)
- Traces to: US-050; FR-032; NFR-016; TC-028
- Card steps built: 5

## Changed files

- `apps/api/tests/unit/validation/test_injection_cases.py` (created): answers a model would give if it obeyed a hostile note, run through the pipeline and `check_output`. It reuses the note pattern of IMP-303's TC-028 and reads the two `hostile_notes` cases of `eval/datasets/trips/v1`.

No production code changed in this part.

## What the cases show

- An invented place ID is rejected under every hostile note, and nothing is saved.
- A price or cost on an item, or a total on the plan, stops the answer as `schema_violation` through the Gemini adapter's real parse.
- A price written inside a note stays note text: at the save boundary the plan holds only the io-1 fields, so no price or total field exists to save.
- MOCK under each hostile note saves only shortlisted places.

## Commands and results

| Command | Result line |
| --- | --- |
| `make test-unit ARGS='-k injection'` | `17 passed, 668 deselected, 1 warning in 1.80s` |
| `make check` (all three parts of RUN-048 in the tree) | exit 0: unit `685 passed, 1 warning`; contract `87 passed, 2 deselected, 1 warning`; api `298 passed, 1 warning`; authz `29 passed`; web `Tests  88 passed (88)` |

Not run: `make live-smoke` (no key, by instruction).

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| Injection notes cannot add places outside the shortlist (TC-028) | verified | `test_tc_028_an_invented_place_is_rejected_...`, `test_tc_028_the_check_itself_ignores_the_note`, `test_tc_028_mock_saves_only_shortlisted_places_...` |
| No model price or total field reaches a saved item | verified | `test_tc_028_a_model_price_on_an_item_...`, `test_tc_028_a_model_total_on_the_plan_...`, `test_tc_028_a_price_written_in_a_note_...` |
| How a real model responds to hostile notes | not verified | MOCK and recorded answers only; no live call in this run |

## Blockers

None.

## Proposed decisions

None.

## Open issues

- The save boundary is asserted in a unit test, on what the pipeline hands to `save_generated_plan`. The columns `itinerary_items` fills from it belong to IMP-308.
