# IMP-315 · test-robustness part

- Run id: RUN-083 (batch run, agent F, part F1)
- Owner: Jeel (Jeel Fefar)
- Status: PR_OPEN (committed on the batch branch; the lead pushes and opens the pull request)
- Base commit: f75aa94
- Branch: S7B/fixes
- Points: 0 (test robustness fix; no product code changed)
- Traces to: TC-451 (IMP-315)

## Why

`test_tc_451_filters_and_must_visit_are_unchanged_by_the_semantic_part` compared the must-visit place's semantic similarity with `min(place_similarity.values())` by exact float equality. It failed on Apple Silicon only, from float rounding of about 4e-9 in the cosine similarity.

## Changed files

- `apps/api/tests/api/test_rag_retrieval.py` (modified): the assertion is now `abs(result.place_similarity[must.id] - least) <= 1e-6`, with `least = min(result.place_similarity.values())`. The test's intent is kept: the must-visit place is the least similar one and is still kept in the shortlist, and the step-free filter and the lexical superset checks are unchanged.
- `docs/progress/parts/IMP-315-test-robustness.md` (created): this record.

## Commands run

| Command | Result line (quoted exactly) |
| --- | --- |
| `pytest "tests/api/test_rag_retrieval.py::test_tc_451_filters_and_must_visit_are_unchanged_by_the_semantic_part" -q` (from `apps/api`, `DATABASE_URL`/`TEST_DATABASE_URL` = compose database `travel_fix`, migrated to 0007 with the auth stub) | `1 passed in 0.82s` |
| `ruff check tests/api/test_rag_retrieval.py` | `All checks passed!` |
| `ruff format --check tests/api/test_rag_retrieval.py` | `1 file already formatted` |

## Not run

| Command | Reason |
| --- | --- |
| `make test-api` | The lead runs the full API suite later on its own database (batch run rule); this part ran only the single changed test. |
| The test on Apple Silicon | This run is on a Linux container; the tolerance (1e-6) is about 250 times the reported rounding difference (about 4e-9). |

## Acceptance criteria

| Criterion | Status (verified / not verified) | How |
| --- | --- | --- |
| Must-visit similarity compared with `min(...)` within 1e-6 instead of exact equality | verified | diff of `test_rag_retrieval.py` |
| Test intent kept (must-visit place kept although least similar) | verified | the `must.id in {...}` and filter assertions are unchanged; the test passes on `travel_fix` |
| No product code changed | verified | the commit touches only the test file and this record |
| Passes on Apple Silicon | not verified | not run on that platform in this run |

## Blockers

none

## Proposed decisions

none

## Open issues

none
