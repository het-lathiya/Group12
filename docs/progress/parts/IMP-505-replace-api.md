# IMP-505 · replace-api part

- Run id: RUN-068 (Sprint 5 batch A)
- Owner: Het (het-lathiya)
- Status: committed on the part branch on top of IMP-504 add-place-api, not pushed (the lead integrates)
- Base commit: 26bac9d (the branch's first commit is IMP-504 add-place-api)
- Branch: part/IMP-504-add-place-api
- Traces to: US-075; FR-065; NFR-003; IMD-11, A1 §6.10
- Card steps built: 1, 2, 3, and the route half of 5. Step 4 and the dialog half of step 5 are Krrish's AlternativesDialog part.

## Changed files

- `apps/api/app/generation/ranking.py`: `rank(candidates, ctx)` is the score sort that was inline in `rank_shortlist`: best first, ties broken by place ID. `rank_shortlist` now calls it. There is no second copy of the formula, and the shortlist behaviour is unchanged (the existing ranking tests pass).
- `apps/api/app/itinerary/edits.py`:
  - `alternatives` (API-28) builds the candidate set:
    - candidates are the trip's places that pass the IMP-304 hard filters (`generation.retrieval.retrieve_candidates`);
    - a must-visit place that fails a filter is dropped, and so are places already in the plan;
    - the slot family must match: a meal takes food, an activity takes any other category.
  - Ranking for API-28:
    - candidates are scored with `ranking.build_context` and `ranking.rank`, the same as generation;
    - the context is built from the full candidate list, the same as `ranked_shortlist`;
    - the ranking is lexical (`semantic=False`, since there is no query text);
    - the top 3 are returned.
  - Each alternative carries:
    - `cost_delta`: new minus current group cost through `budget.engine.item_cost`, in minor units, sent as two-decimal strings;
    - `time_delta_min`: the change in visit length plus the estimated travel to and from the day's neighbours (`routing.estimate`);
    - `reason`: a sentence built in code from the matched interests.
  - A locked item gets an empty list with the message "This item is locked; unlock it to replace it." No item left gets "No alternative fits" (FR-065 AC3).
  - `replace_item` (API-29) runs `Replace(..., ranked=True)` through `apply_edit`. The lock, generation and revision checks come first, so a stale revision is 409 STALE_PLAN before anything else.
  - Inside the transaction, a locked item is 422 INVALID_EDIT. So is a place that is not one of the item's current alternatives (§6.6.5).
  - The replace keeps `start_time`, takes the new place's `typical_duration_min`, sets `origin user` and clears `note` and `source_chunk_ids` (A1 §6.10). It then recalculates, revalidates and returns `EditResultOut`.
  - The IMP-407 core `Replace` without `ranked` is unchanged.
  - The IMD-11 switch `alternatives`: when it is off, both routes raise 404 NOT_FOUND before any read.
- `apps/api/app/itinerary/router.py`: API-28 and API-29 are wired (they answered 501). The IMD-158 501 for `is_locked` on API-26 is untouched.
- `apps/api/tests/api/test_edits.py`:
  - TC-208 (at most three, not in the plan, same family, money strings, repeatable, read only);
  - TC-209 (start kept, typical duration, `origin user`, sources cleared, equal to API-24);
  - a place that is not an alternative gives 422, and a stale revision gives 409, with nothing changed;
  - TC-210 ("No alternative fits");
  - a locked item gives an empty list and a 422 replace;
  - another user's item gives 404 on both routes;
  - TC-372, API side: with `FEATURES_DISABLED=alternatives` both routes give 404, and removing an item and adding a place still work.
- `apps/api/tests/unit/generation/test_ranking.py`: the unit check on equal inputs. `rank` returns each candidate with its `score`, in the shortlist's order.
- `apps/api/tests/authz/route_matrix.py`: API-28 and API-29 entries (TC-065 needs every built owned route in the matrix). This file is outside the card's list.
- `apps/api/app/itinerary/schemas.py`: unchanged. `AlternativesOut`, `Alternative` and `ReplaceIn` are already contract v1. The card's `duration_delta_min` is the contract's `time_delta_min`. The exported OpenAPI was diffed against `contracts/`, with no difference.

## Commands and results

Python tools were run from the worktree's `apps/api` with `PYTHONPATH=.`.

| Command | Result |
| --- | --- |
| `.venv/bin/ruff check app tests` | `All checks passed!` |
| `.venv/bin/ruff format --check app tests` | `205 files already formatted` |
| `.venv/bin/mypy app` | `Success: no issues found in 118 source files` |
| `.venv/bin/lint-imports` | `Contracts: 6 kept, 0 broken.` |
| `pytest -q tests/unit/generation/test_ranking.py` | `31 passed in 0.05s` |
| `pytest -q tests/authz/test_ownership.py -k tc_065` | `2 passed, 36 deselected in 0.24s` |
| `pytest -q tests/contract/test_openapi_contract.py` | `7 passed, 1 warning in 0.65s` |
| `pytest -q --collect-only tests/api/test_edits.py -k alternative` | `8/45 tests collected (37 deselected) in 0.03s` |
| `python -m app.openapi_export` diffed with `contracts/` | no difference |

Not run: `make test-api ARGS='-k alternative'` and `make test-authz` (no PostgreSQL in this run, as the run prompt says). Deferred to integration.

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-065 AC1 / TC-208: up to three alternatives with cost and time differences | not verified (deferred to integration) | `test_tc_208_alternatives_route_lists_up_to_three_ranked_places_with_deltas` |
| FR-065 AC2 / TC-209: applied, the day is recalculated and revalidated | not verified (deferred to integration) | `test_tc_209_replace_route_applies_an_alternative_keeping_the_start_time` |
| FR-065 AC3 / TC-210: none fit gives a message | not verified (deferred to integration) | `test_tc_210_alternatives_route_says_none_fit_when_no_place_is_left` |
| Ordered by the same ranking score as generation (unit check on equal inputs) | verified | `test_alternatives_rank_by_the_same_score_and_order_as_the_shortlist` (31 passed) |
| FEATURES_DISABLED with 'alternatives': both routes 404, and the floor still passes (TC-372) | not verified (deferred to integration) | `test_tc_372_alternative_routes_are_not_found_when_switched_off_and_the_floor_works` (API side; the E2E half is not this part) |
| Stale plan_revision on API-29 returns 409 STALE_PLAN | not verified (deferred to integration) | `test_replace_route_refuses_a_non_alternative_or_a_stale_revision[stale]` |

## Blockers

none

## Proposed decisions

- **PD-IMP-505-1: itinerary imports `generation.ranking` and `generation.retrieval`.** `generation` already imports `itinerary` (service, schemas), so this is a package-level cycle, although there is no module-level cycle: `ranking` and `retrieval` import nothing from `itinerary`. No import-linter contract forbids it, and `make imports` passes. It is the only way to reuse the IMP-304 filters and the score without a copy. Proposal: accept it, or move the filters and ranking assembly into a module that both use.
- **PD-IMP-505-2: shared ranking-context builder.** `edits._alternatives` repeats the pm-2 `map_preferences` call of `retrieval.ranked_shortlist` and calls the private `retrieval._trip_activity_budget` (marked `shortcut:`), because `retrieval.py` is outside this card's files. Proposal: a later card exposes one public `ranking_context(session, trip, prefs, candidates, semantic)` in `generation/retrieval.py`, used by both.
- **PD-IMP-505-3: `cost_delta` when a price is unavailable.** Contract v1 makes `cost_delta` a required `{min, max}`. When either place has no price in the trip's currency, the delta counts that price as 0, and `reason` ends with "; price unavailable". The dialog also has the place's `price_label`. Proposal: keep it, or make `cost_delta` nullable in a contract change.
- **PD-IMP-505-4: alternatives are lexical.** API-28 has no traveller query, so it ranks with `semantic=False`, the same as generation's lexical fallback. Ranking by the stored place similarity would need a retrieval call per request.

## Open issues

- `route_matrix.py` (authz) and `tests/unit/generation/test_ranking.py` were edited outside the card's file list (see Changed files).
- The locked-item test locks through the core `Lock` operation, because API-26 locking answers 501 until IMP-506 (IMD-158).
