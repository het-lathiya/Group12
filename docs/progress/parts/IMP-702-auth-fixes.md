# IMP-702 · auth-fixes part

- Run id: RUN-081
- Owner: Het (Het Lathiya), 2 points
- Status: verified no-defect; no fix needed
- Base commit: a4c2a0b (after part authz-injection, 822041e)
- Traces to: IMP-702 step 2 follow-up; NFR-011, NFR-012

## Changed files

- This record only. No code change.

## Evidence

Part authz-injection (822041e) found no authorization or ownership defect:

| Command | Result line |
| --- | --- |
| `make test-authz` | `81 passed, 14 skipped in 40.29s` (14 skipped: `cut by IMD-65`) |
| `make test-api ARGS='-k injection'` | `25 passed, 565 deselected, 1 warning in 11.46s` |
| `make test-api` | `590 passed, 1 warning in 222.59s (0:03:42)` |

Every owned route answers user B with 404 NOT_FOUND and leaks nothing, A's version cannot be restored through B's trip, a body `user_id` is 422 on every real owned route, and sixteen kinds of bad token are 401 on every protected route.

## Finding F-1 (not fixed here)

The verifier does not check the `iss` claim (severity 3 in `docs/test-reports/security-sprint7.md`). It is not a defect against the binding rules: §3.4 rule 2 and §6.2 list missing, malformed, expired, wrong-audience and bad-signature tokens, not issuer. A token from another issuer fails its signature check and is refused. Adding an issuer check would add a verification rule that the specification does not state, and every environment would need the right expected issuer, otherwise sign-in breaks. So it waits for PD-RUN-081-2. No fix was invented.

## Acceptance

- Each auth or ownership defect from authz-injection is fixed with a test that failed before and passes after: verified, none found (evidence above).

## Blockers

- none

## Proposed decisions

- PD-RUN-081-2 (from authz-injection): decide whether token verification also pins `iss`, for example to `${SUPABASE_URL}/auth/v1`. If yes, it is a Het code change with a failing-then-passing test, after confirming the API's `SUPABASE_URL` on staging and production.

## Open issues

- none
