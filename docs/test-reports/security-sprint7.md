# Security test report, Sprint 7 (IMP-702)

Authorization, injection, secret, bundle, dependency and log checks of IMP-702 (US-144; NFR-011 to NFR-016, NFR-018, NFR-024), run locally on the candidate commit below. The integration run re-runs them on the merged commit; this table records only what ran here. Nothing is marked passed that was not run.

- Commit: `a4c2a0b` (worktree HEAD at run time, base of RUN-081; the IMP-702 authz-injection test files were in the working tree on top of it)
- Date: 2026-11-16
- Database: throwaway PostgreSQL 16 with pgvector on 127.0.0.1:55432 (`TEST_DATABASE_URL`), MOCK provider, no network provider call (socket guard)

## Checks

| TC | Check | Commit | Date | Command | Result line | Status |
| --- | --- | --- | --- | --- | --- | --- |
| TC-344 | Every non-public route answers 401 without a valid token; every contract operation except API-01/02 is in the ownership matrix or reference data and declares the bearer scheme | a4c2a0b | 2026-11-16 | `make test-authz` | `81 passed, 14 skipped in 40.29s` | passed |
| TC-345, TC-346 | User B gets 404 NOT_FOUND on every owned route with A's IDs, no A data, A unchanged; child resources (items, generation, versions) incl. A's version restored through B's own trip | a4c2a0b | 2026-11-16 | `make test-authz` | `81 passed, 14 skipped in 40.29s` | passed |
| TC-347 (historical) | No token, expired, wrong audience, tampered, signed by another issuer's key, `alg none`, no `exp`, `sub` not a UUID, not a JWT, Basic scheme: 401 UNAUTHENTICATED on every protected route | a4c2a0b | 2026-11-16 | `make test-authz` | `81 passed, 14 skipped in 40.29s` | NOT met at 16bd6b9 — F-1: the valid-signature wrong-issuer case was missing |
| TC-348 | A body `user_id` is refused with 422 VALIDATION_ERROR (field `user_id`) on every real owned route with a body, and every request model forbids unknown fields (IMD-45) | a4c2a0b | 2026-11-16 | `make test-authz` | `81 passed, 14 skipped in 40.29s` | passed |
| TC-349 | SQL attack strings in trip title, notes and place search are stored and read back as text or searched as text; no table they name changes | a4c2a0b | 2026-11-16 | `make test-api ARGS='-k injection'` | `25 passed, 565 deselected, 1 warning in 11.46s` | passed |
| TC-350 | Every request body is a Pydantic model with `extra="forbid"` (no TC-350-tagged test; covered by `test_tc_348_no_request_body_can_name_a_user`) | a4c2a0b | 2026-11-16 | `make test-authz` | `81 passed, 14 skipped in 40.29s` | passed |
| TC-351 | Unknown origin gets no CORS allow header (existing IMP-103 test) | a4c2a0b | 2026-11-16 | `make test-api` | `590 passed, 1 warning in 222.59s (0:03:42)` | passed |
| TC-352 | HTTPS and CORS on staging; record observed response headers (IMD-205) | — | — | `make smoke URL=<staging API URL>` | not run | not verified — needs staging window (IMD-137), Kirtan runs |
| TC-353 | Rate limit: 429 with Retry-After, no insert or submit (IMP-511 test) | a4c2a0b | 2026-11-16 | `make test-api` | `590 passed, 1 warning in 222.59s (0:03:42)` | passed |
| TC-354 | Secret scan of the full history with gitleaks 8.30.1 (release tarball, sha256 `551f6fc8…70eb` matched the ci.yml pin), as the ci.yml guards job runs it | a4c2a0b | 2026-11-16 | `gitleaks git --redact --no-banner --verbose .` | `832 commits scanned.` / `no leaks found` (exit 0) | passed |
| TC-355 | Browser bundle holds only NEXT_PUBLIC_* values: production build with the ci.yml placeholders, then `apps/web/.next/static` searched for each of the 37 non-NEXT_PUBLIC names of `.env.example` and for `process.env.` | a4c2a0b | 2026-11-16 | `npx next build --webpack` (in apps/web, ci.yml placeholder env) then `for n in <37 names>; do grep -rqP "(?<![A-Z_])$n(?![A-Z0-9_])" apps/web/.next/static && echo "server name in bundle: $n"; done; grep -rhoE 'NEXT_PUBLIC_[A-Z_]+\|process\.env\.[A-Za-z_]+' apps/web/.next/static \| sort -u` | build exit 0; no "server name in bundle" line; only `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_SUPABASE_URL`; no `process.env.` reference | passed (webpack build; see note 1) |
| TC-356 | pip-audit of the API dependencies, as ci.yml runs it | a4c2a0b | 2026-11-16 | `apps/api/.venv/bin/python -m pip freeze --exclude-editable > <tmp>/api-requirements.txt && apps/api/.venv/bin/pip-audit --requirement <tmp>/api-requirements.txt --no-deps --disable-pip` | `No known vulnerabilities found` (exit 0) | passed |
| TC-356 | npm audit, critical findings fail | a4c2a0b | 2026-11-16 | `npm audit --audit-level=critical` (in apps/web) | exit 0; `13 vulnerabilities (2 low, 11 moderate)`, none critical | passed |
| TC-357 | Prompt-injection notes from the corpus through the MOCK pipeline: same shortlist, same saved places (all active places of the destination), same API-33 costs as a harmless note | a4c2a0b | 2026-11-16 | `make test-api ARGS='-k injection'` | `25 passed, 565 deselected, 1 warning in 11.46s` | passed |
| TC-358, TC-025 | No e-mail, key, notes text or provider request body in log lines (unit redaction tests, config key test, and the TC-357 log assertions) | a4c2a0b | 2026-11-16 | `make test-unit ARGS="-k 'logging or config'"`; `make test-api ARGS='-k injection'` | `76 passed, 1128 deselected, 1 warning in 7.21s`; `25 passed, 565 deselected, 1 warning in 11.46s` | passed |
| TC-028 | Model answers that obey a hostile note never reach the plan (existing unit cases) | a4c2a0b | 2026-11-16 | `make test-unit ARGS='-k injection'` | `22 passed, 1182 deselected, 1 warning in 1.50s` | passed |
| TC-431 | Extension routes in the ownership suite | a4c2a0b | 2026-11-16 | `make test-authz` | `SKIPPED [14] … cut by IMD-65` | skipped — cut by IMD-65 |
| TC-432 | Disabled extension routes answer 404 | a4c2a0b | 2026-11-16 | `make test-authz` | `81 passed, 14 skipped in 40.29s` | routes not mounted (cut): `test_tc_432_extension_routes_are_not_mounted_and_answer_404` passes (none of API-43, API-63..75 is mounted; each answers 404 NOT_FOUND with a valid token) |
| TC-433 | RDS not reachable from outside the VPC, TLS required | — | — | — | not run | not verified — needs staging window (IMD-137), Kirtan runs |
| TC-434 | Task definitions hold secrets only as SSM references; images hold no secret | — | — | — | not run | not verified — needs staging window (IMD-137), Kirtan runs |
| TC-436 | OIDC deploy role trusts only main and v* tags | — | — | — | not run | not verified — needs staging window (IMD-137), Kirtan runs |
| ECR scan | No critical finding in the ECR image scan | — | — | — | not run | not verified — needs staging window (IMD-137), Kirtan runs |

Quality commands on the same tree: `make lint` exit 0 (`All checks passed!`, `All matched files use Prettier code style!`); `make typecheck` `Success: no issues found in 123 source files`; `make imports` `Contracts: 6 kept, 0 broken.`

Note 1: the default Turbopack build (`npm run build`) cannot run in this worktree because `apps/web/node_modules` is a symlink outside the Turbopack root (`Could not find the Next.js package (next/package.json)`); the same sources were built with `next build --webpack`. CI's lint-types job runs the Turbopack build but does not inspect the bundle; the integration run should repeat the search on the Turbopack output.

## Findings and defects

| ID | Severity | Finding | Status |
| --- | --- | --- | --- |
| F-1 | 3 (low), failed TC-347 at 16bd6b9 | A correctly signed token with `iss=https://evil.example/auth/v1` was accepted. The previous different-key test only proved signature rejection; it did not meet IMP-702 step 2 / TC-347 and IMD-140 issuer rules. | FIXED in 85282ce (Het, IMD-204); unit regression failed before and passed after; explicit wrong-issuer route case added in RUN-081b. Staging and production SUPABASE_URL confirmation remains due in the staging window. |

No severity-1 or severity-2 defect was found. TC-347 was not met at 16bd6b9; RUN-081b fixes F-1 with local regression evidence below. The staging rows above stay not verified.

## CORS, headers and secret-scan review (part headers-secret-scan)

| TC | Check | Commit | Date | Command | Result line | Status |
| --- | --- | --- | --- | --- | --- | --- |
| TC-351 | `/api/v1/trips`: the ALLOWED_ORIGINS origin gets Access-Control-Allow-Origin on preflight and on a simple (401) request, with no allow-credentials; three unknown origins (including a suffix look-alike and `null`) get none; TRACE preflight refused | cf3fd89 | 2026-11-16 | `make test-authz` | `86 passed, 14 skipped, 1 warning in 43.03s` | passed |
| TC-352 (headers) | Record the deployment's observed response headers alongside HTTPS and CORS (IMD-205) | — | 2026-11-16 | — | not run | not verified — IMD-205 resolves PD-RUN-081-1: no prescribed header list or new middleware; observe headers and verify HTTPS/CORS in the staging window (IMD-137), Kirtan runs |

Secret-scan configuration review (gitleaks 8.30.1):

| Item | Finding | Severity |
| --- | --- | --- |
| Allowlist files | No `.gitleaks.toml`, `.gitleaksignore` or other gitleaks config is tracked (`git ls-files \| grep -i gitleaks` prints nothing), so the default rule set runs with no allowlist | none: nothing over-broad |
| Inline allows | `git grep -n "gitleaks:allow"` prints nothing | none |
| ci.yml guards | Binary pinned to v8.30.1 with sha256 verified before use; `--redact` keeps any finding's value out of the log; pull requests scan `--no-merges BASE..HEAD`, pushes to main scan the full history; a tracked real `.env` file fails the job | none |
| Pre-commit | `.pre-commit-config.yaml` pins the gitleaks hook to the same v8.30.1 | none |
| Test secrets | Test signing keys are derived at import with sha256 (`tests/fixtures/auth.py`, the IMP-702 foreign-issuer key), so no secret-like literal is committed and no allowlist is needed | none |

## RUN-081b correction evidence (16 November 2026)

F-1 was open and TC-347 was NOT met at 16bd6b9. IMD-204 resolves the issuer decision; Het's fix is 85282ce. This verification tree includes that fix and the explicit `wrong issuer with valid signature` case in the IMP-702 block of `test_route_inventory.py`, which walks every protected route and requires 401 UNAUTHENTICATED before database access.

| Command | Result line |
| --- | --- |
| `apps/api/.venv/bin/pytest apps/api/tests/unit/auth/test_tokens.py -k wrong_issuer -q` (before fix) | `1 failed, 30 deselected in 0.16s`; `E       Failed: DID NOT RAISE Unauthenticated` |
| Same command after fix | `1 passed, 35 deselected in 0.27s` |
| `apps/api/.venv/bin/pytest apps/api/tests/unit/auth/test_tokens.py -q` | `36 passed in 1.11s` |
| `make test-authz` (throwaway PostgreSQL 16 + pgvector) | `87 passed, 14 skipped, 1 warning in 62.96s (0:01:02)` |

TC-347: verified on the new verification tree, F-1 fixed in 85282ce. TC-352: not verified until staging; check HTTPS and CORS, record observed deployment response headers (IMD-205), with no new middleware. Staging SUPABASE_URL to confirm in the staging window. Historical rows above retain their original commands and results; they do not establish a pass at this head.
