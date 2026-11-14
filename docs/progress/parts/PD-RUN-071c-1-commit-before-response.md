# PD-RUN-071c-1 · commit-before-response

- Run id: RUN-072
- Owner: Het (Het Lathiya)
- Status: verified locally; final integration checks and E2E evidence belong to the pull request
- Base commit: a72d07a
- Decision: IMD-184
- Traces to: IMP-407, IMP-504; FR-064, FR-069; TC-206, TC-207, TC-217, TC-312
- Scope: commit or roll back each request transaction before sending its response, without changing response shapes, status codes, error envelopes or the edit transaction's lock order.

## Files changed

- `apps/api/app/auth/deps.py`: the shared `DbSession` uses `Depends(db_session, scope="function")`; its docstring states the commit and rollback boundary. All implemented write routes already use this alias, so no router declaration or service needed changing.
- `apps/api/tests/api/test_commit_before_response.py`: two regression tests use the production dependency and real, independent request transactions. A dedicated migrated database isolates their committed writes and is dropped after each test; no existing fixture changed.
- This record.

## Cause and fix

The installed FastAPI is **0.162.0**. Its `routing.request_response` opens a request exit stack around `await response(scope, receive, send)`, with a function exit stack around the handler and response construction only. The default yield dependency exits on the request stack: `db_session`'s `transaction()` therefore committed after the response was sent. API-24 could read the old revision after an edit's 200 and overwrite the web cache, making the next edit send a stale revision and receive 409 STALE_PLAN. A commit failure could also occur after a success response had already started.

The installed `Depends` supports `scope="function"`. Setting it on the shared alias closes the transaction after response construction and before sending the response, and lets commit failures reach the existing §6 error handlers. The transaction helper still owns commit, rollback and cleanup. Edit services, SQL and lock order are unchanged.

## Commands and exact results

A fresh throwaway PostgreSQL **16.2** with pgvector **0.6.2** was started on loopback port 55432 using the existing scratch `pgserver` binaries from earlier runs. No system package or project dependency was installed. `TEST_DATABASE_URL` selected the throwaway database; its connection string was not logged. The server is kept only for the run's final local checks, then stopped and its data directory removed.

| Command | Result |
| --- | --- |
| Installed-version inspection | `FastAPI 0.162.0`; `Depends` accepts `scope="function"`; installed source closes the function stack before `await response(scope, receive, send)` |
| `git stash push` restricted to `apps/api/app/auth/deps.py`, then `make test-api ARGS='-k commit_before_response -q'` with the old dependency | `2 failed, 464 deselected, 1 warning in 4.00s` |
| Old dependency, visibility failure at `test_commit_before_response.py:174` | `assert current["plan_revision"] == edited.json()["plan_revision"]`; `E           assert 1 == 2` |
| Old dependency, commit-failure response at `test_commit_before_response.py:223` | `assert response.status_code == 500, response.text`; `E           assert 200 == 500` |
| Restore the stashed dependency fix, then `make test-api ARGS='-k commit_before_response -q'` | `2 passed, 464 deselected, 1 warning in 4.00s` |
| `make test-api` | `466 passed, 1 warning in 136.11s (0:02:16)` |
| `make test-authz` | `47 passed in 23.88s` |
| `ruff check apps/api/app/auth/deps.py apps/api/tests/api/test_commit_before_response.py` | `All checks passed!` |
| `ruff format --check apps/api/app/auth/deps.py apps/api/tests/api/test_commit_before_response.py` | `2 files already formatted` |
| `git diff --check` | no output, exit 0 |

The warning is the existing Starlette/httpx test-client deprecation. The old-code failures are the expected negative proof, not weakened or skipped tests.

## Acceptance

| Criterion | Status | Evidence |
| --- | --- | --- |
| API-26 retime is committed when its response reaches the client; API-24 immediately sees the new plan_revision | verified | The test forwards the final ASGI response body, then issues API-24 before request teardown resumes. The old dependency reads revision 1 after the edit returns 2; the fixed dependency reads 2 and the new start time. There are no sleeps or retries. |
| A second edit using the read revision returns 200, never 409 | verified | The same test sends the read revision with a second retime, asserts 200 and the next revision, then reads API-24 again and checks both revision and time. |
| A commit failure rolls back and returns the §6 error envelope | verified | A per-session SQLAlchemy `before_commit` event fails the outer commit after the edit has written. The test asserts 500 INTERNAL, the response request ID, empty details, no exception text, and an unchanged API-24 response after rollback. The old dependency incorrectly sends 200. |
| Existing API and authorization behavior is preserved | verified locally | Full `make test-api` and `make test-authz` pass. |
| Response shapes, status codes, edit lock order, generated contracts and migrations stay unchanged | verified | Diff changes only the dependency scope and its documentation; regression tests use existing routes and schemas. Final `make openapi-check` is recorded in the pull request. |

## Not run

None for this part's required database checks or before/after proof. The single E2E dispatch happens after all three parts and the one push; its result is recorded in the final pull request.

## Blockers

None.

## Proposed decisions

None; IMD-184 authorizes this fix.
