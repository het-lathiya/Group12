# IMP-304 · ranking part

- Run id: RUN-045 (grouped, IMD-121, with IMP-304, IMP-307 and IMP-310)
- Owner: Jeel (jeelfefar2141)
- Status: PR_OPEN
- Base commit: 4f20bfc
- Branch: feat/IMP-304-307-310-wave1
- Reviewer: Manal (manalPatel2557)
- Traces to: US-047; FR-028; NFR-002; TC-126, TC-127, TC-128; IMD-29
- Card steps built: 3 to 6

## Changed files

- `apps/api/app/generation/ranking.py` (created, pure):
  - `score()` returns `ScoreParts`.
  - `build_context()` sets the centre and radius.
  - `shortlist_size()` gives `min(40, max(12, 8 x days))`.
  - `rank_shortlist(candidates, ctx)` returns a `Shortlist` with its `mapping_version`.
  - Weights and pace factors are read only from `app/trips/preference_mapping.py`. Score parts are logged at DEBUG with the place ID and numbers only.
- `apps/api/.importlinter`: `app.generation.ranking` joins the `pure-domain` contract (§4.4). The contract name no longer names one module.
- `apps/api/tests/unit/generation/test_ranking.py` (created, 25 tests).

`retrieval.py` needed no line for this part: the caller passes its result to `rank_shortlist`.

## SAMPLE shortlist with score parts

Two-day trip from Monday 1 March 2027, 2 adults, budget 250.00 GBP (activity budget 227.27 with 10 percent contingency), interests museum and nature, balanced pace, must-visit sample-028, mapping `pm-1`. The centre is sample-028, so distance is measured from there. The size rule gives 16 places; the must-visit place is added as the 17th.

| Rank | Place | Category | Must-visit | Interest | Price | Distance | Pace | Signal | Total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | sample-012 Sample Cliff Meadow (sample) | nature | no | 0.500 | 1.000 | 0.324 | 0.917 | 0.000 | 0.656 |
| 2 | sample-006 Sample Maritime Museum (sample) | museum | no | 0.500 | 1.000 | 0.283 | 0.867 | 0.000 | 0.644 |
| 3 | sample-011 Sample Heron Marsh (sample) | nature | no | 0.500 | 1.000 | 0.214 | 0.900 | 0.000 | 0.636 |
| 4 | sample-005 Sample Museum of Small Things (sample) | museum | no | 0.500 | 1.000 | 0.212 | 0.900 | 0.000 | 0.635 |
| 5 | sample-008 Fixture History House (sample) | museum | no | 0.500 | 1.000 | 0.124 | 0.917 | 0.000 | 0.622 |
| 6 | sample-009 Sample Dune Walk (sample) | nature | no | 0.500 | 1.000 | 0.155 | 0.867 | 0.000 | 0.622 |
| 7 | sample-010 Sample Tide Pool Garden (sample) | nature | no | 0.500 | 1.000 | 0.104 | 0.933 | 0.000 | 0.621 |
| 8 | sample-029 Sample Bike Hire Point (sample) | activity | no | 0.000 | 1.000 | 0.890 | 0.800 | 0.000 | 0.515 |
| 9 | sample-027 Sample Temple Garden (sample) | religious | no | 0.000 | 1.000 | 0.749 | 0.956 | 0.000 | 0.509 |
| 10 | sample-026 Sample Quiet Abbey Ruins (sample) | religious | no | 0.000 | 1.000 | 0.719 | 0.950 | 0.000 | 0.503 |
| 11 | sample-018 Sample Lighthouse Tea Room (sample) | food | no | 0.000 | 1.000 | 0.695 | 0.967 | 0.000 | 0.501 |
| 12 | sample-019 Sample Covered Market (sample) | shopping | no | 0.000 | 1.000 | 0.714 | 0.933 | 0.000 | 0.500 |
| 13 | sample-025 Sample Chapel on the Hill (sample) | religious | no | 0.000 | 1.000 | 0.654 | 0.967 | 0.000 | 0.494 |
| 14 | sample-007 Sample Gallery of Patterns (sample) | museum | no | 0.500 | 0.500 | 0.080 | 0.933 | 0.000 | 0.478 |
| 15 | sample-016 Sample Green Plate Cafe (sample) | food | no | 0.000 | 1.000 | 0.566 | 0.950 | 0.000 | 0.478 |
| 16 | sample-024 Sample Arcade by the Sea (sample) | entertainment | no | 0.000 | 1.000 | 0.570 | 0.933 | 0.000 | 0.477 |
| 17 | sample-028 Sample Kayak Launch (sample) | activity | yes | 0.000 | 0.240 | 1.000 | 0.867 | 0.000 | 0.330 |

Produced by running `apply_filters` and `rank_shortlist` on `data/fixtures/sampleton/*.csv` outside the database.

## Commands and results

| Command | Result line |
| --- | --- |
| `make test-unit ARGS='-k ranking'` | `25 passed, 442 deselected, 1 warning in 0.30s` |
| `make lint` | `All checks passed!` (ruff); `All matched files use Prettier code style!` |
| `make typecheck` | `Success: no issues found in 89 source files` |
| `make imports` | `Contracts: 5 kept, 0 broken.` |
| `make test` (via `make check`, `TEST_DATABASE_URL` = the §4.7 default on `pgvector/pgvector:pg16`) | unit `467 passed, 1 warning`; contract `35 passed, 1 warning`; api `250 passed, 1 warning`; authz `28 passed`; web `Tests  80 passed (80)` |
| `make check` | exit 0 (`openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date`) |

Not run: `make e2e` (no journey changes; nothing in the pipeline calls this code yet).

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| A better interest match ranks higher (FR-028 AC1, TC-126) | verified | `test_tc_126_a_better_interest_match_ranks_higher` |
| Two runs give identical order (FR-028 AC2, TC-127) | verified | `test_tc_127_two_runs_give_the_same_order_and_ties_break_on_place_id` |
| Score parts are logged in debug mode (FR-028 AC3, TC-128) | verified | `test_tc_128_score_parts_are_logged_at_debug_only`, which also checks that no note text appears |
| Shortlist size rule and must-visit retention on SAMPLE | verified | `test_the_shortlist_size_rule`, `test_sample_ranking_keeps_the_size_rule_food_and_must_visit`, `test_sample_three_day_trip_keeps_all_the_size_rule_allows` |

## Blockers

None.

## Proposed decisions

Blueprint §20.2 is not in the repository, so these fill what §8.9 leaves open:

- **PD-IMP-304-4: per-item share and radius.** The per-item share is the activity budget ÷ (days x the pace's items per day). The radius is half the diagonal of the destination's bounding box. The price component uses the minimum group cost of the filter step.
- **PD-IMP-304-5: interest match.** §8.9 says "matching tags ÷ interests", but interests are category names and tags are not, so a museum could never match "museum". A place matches an interest by tag or by category. With no interests the component is 0 for every place.
- **PD-IMP-304-6: shortlist limits.** §8.9 says must-visit and food places are added to the size, so the list can exceed 40; IMP-303 cuts it to the token limit. The card's "exclude category stay" and §8.9's "a must-visit place is never removed" conflict for a must-visit stay place: it stays, with its conflict note. Food places needed = days x meal slots per day.
- **PD-IMP-304-7: budget priority wording.** The card says "a high budget priority moves 0.10 from interest to price"; §8.9 and pm-1 say `saving`. `saving` is what is built.

## Open issues

- `explain_components()` (API-63) belongs to IMP-515, which is cut.
