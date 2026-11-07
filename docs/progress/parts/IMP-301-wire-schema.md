# IMP-301 · wire-schema part

- Run id: RUN-053
- Owner: Nidhi (Nidhi9864)
- Status: PR_OPEN
- Base commit: 73008e4
- Branch: fix/IMP-301-wire-schema
- Reviewer: Manya (manyarana)
- Traces to: IMP-301, IMP-316; FR-041; TC-029; proposed D13

## Why

The key holder's diagnostic of 7 November 2026 (`docs/decisions/gemini-setup.md`): a small `response_format` schema succeeds, and the io-1 wire schema is refused with HTTP 400 `invalid_request`, "The specified schema produces a constraint that has too many states for serving".

## Changed files

- `apps/api/app/ai/providers/gemini.py`: `wire_schema`, already the one builder for every `response_format`, now also removes `minimum`, `maximum`, `exclusiveMinimum`, `exclusiveMaximum`, `minItems`, `maxItems`, `minLength`, `maxLength`, `format` and `multipleOf`. The walk no longer treats a field name under `properties` or `$defs` as a keyword, so a field called `format` would survive.
- `apps/api/tests/unit/ai/test_gemini_adapter.py`: the wire schema tests.
- `docs/decisions/gemini-setup.md`: the dated diagnostic line.

`contracts/ai/*.json`, the Pydantic models and all validation are unchanged. The one repair call does not exist yet (IMP-502); it must pass `wire_schema(output_model)` to `_call_vendor`, as `generate_itinerary` does.

## Wire schema size (characters of the JSON)

| Schema | Before | After |
| --- | --- | --- |
| io-1 | 1740 | 1533 |
| io-2 | 1892 | 1670 |

## Commands and results

`make db-up`, then with `TEST_DATABASE_URL` at the §4.7 default on `pgvector/pgvector:pg16`.

| Command | Result line |
| --- | --- |
| `make lint` | `All checks passed!` (ruff); `All matched files use Prettier code style!` |
| `make typecheck` | `Success: no issues found in 105 source files` |
| `make imports` | `Contracts: 6 kept, 0 broken.` |
| `make test-unit ARGS='-k "gemini or wire_schema"'` | `114 passed, 709 deselected, 1 warning in 9.81s` |
| `make test-contract` | `87 passed, 2 deselected, 1 warning in 4.29s` |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |
| `make check` | exit 0: unit `823 passed, 1 warning`; contract `87 passed, 2 deselected, 1 warning`; api `334 passed, 1 warning`; authz `31 passed`; web `Tests  119 passed (119)` |

Not run: `make live-smoke` (key holder only, by instruction) and `make e2e` (no journey touched).

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| The io-1 and io-2 wire schemas hold none of the removed keywords at any depth | verified | `test_wire_schema_has_no_serving_limit_at_any_depth` |
| They list every property and required field of the repository schema | verified | `test_wire_schema_keeps_every_property_required_field_and_enum` |
| The captured request carries the wire schema | verified | `test_wire_schema_is_what_the_request_carries` |
| An answer that breaks a removed limit is still `schema_violation` | verified | `test_wire_schema_a_removed_limit_is_still_rejected_after_parsing`, 11 cases on each of io-1 and io-2 |
| Exported contracts unchanged | verified | `make openapi-check`; no file under `contracts/` in the diff |
| Gemini accepts the wire schema (TC-029) | not verified | Pending, the key holder re-runs `make live-smoke` on this branch before merge |

## Blockers

None.

## Proposed decisions

- **D13: Gemini wire schema omits numeric, length, count and format limits; code enforces them.** §8.7 and card IMP-301 step 3 name only `$schema`, `$id` and `pattern`. The larger set above is what this run built, and the reason is the refusal quoted under Why. The spec text needs this change when the decision is taken.

## Open issues

- **The model no longer sees these limits.** The schema was the only place it was told duration 15 to 480, note up to 200, theme up to 80, summary up to 500 and at most 20 assumptions; the v1 and v2 prompts do not state them. An answer over a limit fails the whole plan as `schema_violation`, and until the repair call (IMP-502) and fallback (IMP-402) exist, the generation ends `failed`. Proposed follow-up, if live runs show it: state the limits in the prompt, as a new template version.
- `source_ids` is the exception: its `maxItems` was only a hint to the model. The v2 system text still says at most three, and `output_check` cuts the list (TC-455), so an extra citation fails nothing.
- If TC-029 is still refused, `anyOf` (the nullable `summary`), `enum` and `$ref` are what remain of the schema's structure, and the next diagnostic should test them.
