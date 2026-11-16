# IMP-702 · authz-injection part

- Run id: RUN-081
- Owner: Junaid (Mohammad Junaid Kureshi), 2 points (lead)
- Status: implemented and verified locally; staging items open
- Base commit: a4c2a0b
- Steps: 1, 2, 3, 5, 6, 7 of the card; TC-344 to TC-351, TC-353 to TC-358, TC-431, TC-432; US-144, NFR-011 to NFR-016, NFR-018, NFR-024

## Changed files

- `apps/api/tests/authz/test_route_inventory.py`: append-only `# IMP-702` block. TC-344 against `contracts/openapi.v1.json` (every operation except API-01/02 is in the matrix or reference data and declares `HTTPBearer`; no matrix entry the contract lacks). TC-347 with six more bad tokens on every protected route: signed by another issuer's key, `alg none`, no `exp`, `sub` not a UUID, not a JWT, Basic scheme. TC-432: none of API-43, API-63..75 is mounted and each answers 404 NOT_FOUND with a valid token. TC-431: one case per extension route, skipped "cut by IMD-65".
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
- TC-344 to TC-351, TC-353 to TC-358 on the candidate commit: verified locally on a4c2a0b plus this part's tests (rows in the report); the integration re-runs on the merged commit.
- TC-352 on staging: not verified, needs the staging window (IMD-137), Kirtan runs.
- No secret in history, logs or bundle (CHK-03): verified (gitleaks full history, log tests, bundle search on the webpack build).
- Report lists every check with commit, date and result; nothing marked passed that was not run: verified, `docs/test-reports/security-sprint7.md`.
- TC-431: extension cases skip "cut by IMD-65"; TC-432: routes not mounted (cut), verified by `test_tc_432_extension_routes_are_not_mounted_and_answer_404`.
- TC-433, TC-434, TC-436, ECR scan: not verified, staging window (IMD-137), Kirtan runs.

## Defects and findings

- F-1, severity 3, not a failed TC: the `iss` claim is not checked; a token signed with the project's key and a foreign `iss` is accepted. §3.4 rule 2 and §6.2 do not list issuer; card step 2 and IMD-140 wording do. Handed to part auth-fixes as a decision, not a defect.

## Blockers

- none locally. Staging rows wait for the staging window (IMD-137).

## Proposed decisions

- PD-RUN-081-2: whether token verification must also pin `iss` (for example to `${SUPABASE_URL}/auth/v1`), and confirm the API's `SUPABASE_URL` on every environment before any such check.

## Open issues

- The bundle search ran on a webpack build; repeat it on the Turbopack build in CI or the integration run (the worktree's symlinked `node_modules` stops Turbopack).
