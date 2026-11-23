# IMP-731 · whole-task part (any-city authorization, injection cases and etiquette review)

- Card: IMP-731 (0 points, Amendment A2 §7.3, §11, §12 Batch C3)
- Run id: RUN-092 (Batch C3, Sprint 7, inserted under IMD-215)
- Owner: Junaid (Mohammad Junaid Kureshi)
- Status: PR_OPEN candidate on `feat/S7-C3-any-city-verify`
- Base commit: 818c1d8 (on `main`)
- Traces to: TC-487, TC-488; A2 §3.4, §7.3, §11

## Changed files

- `apps/api/tests/authz/test_any_city_routes.py` (created): 4 TC-487 tests.
  - The route-set test pins the OFF app explicitly (`features_disabled=""`), so it stays correct under `ANY_CITY_SUITE_ON=1`.
- `apps/api/tests/fixtures/injection_corpus.json`: new keys `osm_names` and `wiki_paragraphs` (3 strings each); the comment names IMP-731. The `sql` and `prompt` lists are unchanged.
- `apps/api/tests/api/test_injection.py`: 2 TC-488 cases added at the end (with their helpers and imports). The existing TC-349 and TC-357 tests are unchanged.
- `docs/test-reports/security-any-city.md` (created): the A2 §7.3 and §11 review, the RUN-090 log-privacy fix, and the open item for the policy pages.

`route_matrix.py` is unchanged.

## Commands

| Command | Result line |
| --- | --- |
| `make test-authz ARGS='-k any_city'` | 4 passed, 101 deselected, 1 warning in 0.51s |
| `make test-api ARGS='-k injection'` | 27 passed, 653 deselected, 1 warning in 7.34s |
| `ANY_CITY_SUITE_ON=1 pytest tests/authz/test_any_city_routes.py tests/api/test_injection.py -k "any_city or tc_488"` | 6 passed, 25 deselected in 1.48s |

## Acceptance

- **Every new route is covered: verified.** `test_tc_487_any_city_the_four_routes_are_exactly_the_any_city_set` checks the set. Every route is also checked for 401 and for reference access.
- **An injected instruction changes neither the place set nor the costs: verified** (the two `test_tc_488_injection_*` tests).
- **The review is recorded: verified** (`docs/test-reports/security-any-city.md`).

## Proposed decisions

none

## Open issues

- **Policy pages: Junaid to confirm by reading.** The Nominatim, Overpass and MediaWiki usage policies still need reading, with the date recorded, before the staging pre-import.
- The OSM-name case runs without embeddings on purpose: a renamed place legitimately changes its vector similarity. The case with embeddings is covered by the wiki-paragraph test, where place documents are unchanged.

## Blockers

none
