# IMP-702 · authz-injection part

- Run id: RUN-081b (correction of RUN-081)
- Owner: Junaid (Mohammad Junaid Kureshi), 2 points (lead)
- Status: implemented and verified locally; staging items open
- Base commit: 16bd6b9; issuer fix: 85282ce (Het, IMD-204)
- Steps: 1, 2, 3, 5, 6, 7 of the card; TC-344 to TC-351, TC-353 to TC-358, TC-431, TC-432; US-144, NFR-011 to NFR-016, NFR-018, NFR-024

## Changed files

- `apps/api/tests/authz/test_route_inventory.py`: append-only `# IMP-702` block. TC-344 against `contracts/openapi.v1.json` (every operation except API-01/02 is in the matrix or reference data and declares `HTTPBearer`; no matrix entry the contract lacks). TC-347 with seven more bad tokens on every protected route: a foreign `iss` with the valid project signature, signed by another issuer's key, `alg none`, no `exp`, `sub` not a UUID, not a JWT, Basic scheme. TC-432: none of API-43, API-63..75 is mounted and each answers 404 NOT_FOUND with a valid token. TC-431: one case per extension route, skipped "cut by IMD-65".
- `apps/api/tests/authz/test_ownership.py`: append-only `# IMP-702` block. TC-348 on every real owned route with a body: A's own request plus `user_id` naming B is 422 VALIDATION_ERROR on field `user_id`, A unchanged. TC-346: A's version restored through B's own trip is 404 with no A data.
- `apps/api/tests/api/test_injection.py` (new): TC-349 (10 SQL strings in title, notes, rename and place search) and TC-357 (5 prompt-injection notes through API-22 with MOCK: same shortlist, saved places and API-33 costs as a harmless note; saved places are active places of the destination; note, e-mail and provider request body absent from the log, TC-358/TC-025).
- `apps/api/tests/fixtures/injection_corpus.json` (new): the attack strings only.
- `docs/test-reports/security-sprint7.md` (new): one row per check.
- Existing coverage reused, not duplicated: the ten-token walk and TC-348 static check (IMP-108), the matrix and two-user suite (IMP-215), TC-028 unit cases, logging redaction unit tests, TC-351 in `tests/api/test_health.py`, TC-353 in `tests/api/test_generations.py`. `tests/authz/route_matrix.py` needed no change: every implemented route is listed.

## Commands and results

`TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:55432/travel_test` (throwaway PostgreSQL 16 + pgvector).

| Command | Result line |
| --- | --- |
| `make test-authz` | `81 passed, 14 skipped in 40.29s` (14 skipped: `cut by IMD-65`) |
| `make test-api ARGS='-k injection'` | `25 passed, 565 deselected, 1 warning in 11.46s` |
| `make test-api` | `590 passed, 1 warning in 222.59s (0:03:42)` |
| `make test-unit ARGS="-k 'logging or config'"` | `76 passed, 1128 deselected, 1 warning in 7.21s` |
| `make test-unit ARGS='-k injection'` | `22 passed, 1182 deselected, 1 warning in 1.50s` |
| `make lint` | exit 0: `All checks passed!`, `All matched files use Prettier code style!` |
| `make typecheck` | `Success: no issues found in 123 source files` |
| `make imports` | `Contracts: 6 kept, 0 broken.` |
| gitleaks 8.30.1 (checksum matched the ci.yml pin) `gitleaks git --redact --no-banner --verbose .` | `832 commits scanned.`, `no leaks found` |
| pip-audit as in ci.yml | `No known vulnerabilities found` |
| `npm audit --audit-level=critical` (apps/web) | exit 0, `13 vulnerabilities (2 low, 11 moderate)` |
| `npx next build --webpack` + bundle search (see report) | exit 0; only `NEXT_PUBLIC_*` names, no server variable name, no `process.env.` |

Note on `make test-api ARGS=...`: the target always passes `tests/api`, so a file path in `ARGS` still runs the whole folder; `-k injection` selects this file.

## Acceptance

- make test-authz passes and fails on a new protected route without an ownership case (NFR-012, CHK-04): verified, `make test-authz`; `test_tc_065_*` (app walk) and the new contract check both fail on an unlisted route.
- TC-347 was NOT met at 16bd6b9 (F-1): the prior bad-signature case did not test a foreign issuer with a valid signature. It is verified on 85282ce plus this part's explicit wrong-issuer case on every protected route; commands and result lines are recorded below. Other historical checks retain their original commit and result lines.
- TC-352 on staging: not verified. Under IMD-205, check HTTPS and CORS and record the deployment's observed response headers in the staging window (IMD-137); no middleware is added.
- No secret in history, logs or bundle (CHK-03): verified (gitleaks full history, log tests, bundle search on the webpack build).
- Report lists every check with commit, date and result; nothing marked passed that was not run: verified, `docs/test-reports/security-sprint7.md`.
- TC-431: extension cases skip "cut by IMD-65"; TC-432: routes not mounted (cut), verified by `test_tc_432_extension_routes_are_not_mounted_and_answer_404`.
- TC-433, TC-434, TC-436, ECR scan: not verified, staging window (IMD-137), Kirtan runs.

## Defects and findings

- F-1, severity 3: TC-347 failed at 16bd6b9. Fixed by Het in 85282ce, with the failing-then-passing unit regression and this part's same-key, wrong-issuer token case (IMD-204). Every protected route must return 401 UNAUTHENTICATED for that token.

## Blockers

- none locally. Staging rows wait for the staging window (IMD-137).

## Proposed decisions

- none. PD-RUN-081-2 is resolved by IMD-204. Staging and production SUPABASE_URL confirmation remains due in the staging window.

## Open issues

- The bundle search ran on a webpack build; repeat it on the Turbopack build in CI or the integration run (the worktree's symlinked `node_modules` stops Turbopack).

## RUN-081b correction evidence (16 November 2026)

F-1 was open and TC-347 was NOT met at 16bd6b9. IMD-204 resolves the issuer decision; Het's fix is 85282ce. This verification tree includes that fix and the explicit `wrong issuer with valid signature` case in the IMP-702 block of `test_route_inventory.py`, which walks every protected route and requires 401 UNAUTHENTICATED before database access.

| Command | Result line |
| --- | --- |
| `apps/api/.venv/bin/pytest apps/api/tests/unit/auth/test_tokens.py -k wrong_issuer -q` (before fix) | `1 failed, 30 deselected in 0.16s`; `E       Failed: DID NOT RAISE Unauthenticated` |
| Same command after fix | `1 passed, 35 deselected in 0.27s` |
| `apps/api/.venv/bin/pytest apps/api/tests/unit/auth/test_tokens.py -q` | `36 passed in 1.11s` |
| `make test-authz` (throwaway PostgreSQL 16 + pgvector) | `87 passed, 14 skipped, 1 warning in 62.96s (0:01:02)` |

TC-347: verified on the new verification tree, F-1 fixed in 85282ce. TC-352: not verified until staging; check HTTPS and CORS, record observed deployment response headers (IMD-205), with no new middleware. Staging SUPABASE_URL to confirm in the staging window. Historical rows above retain their original commands and results; they do not establish a pass at this head.
