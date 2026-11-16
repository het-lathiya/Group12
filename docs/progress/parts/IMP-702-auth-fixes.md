# IMP-702 · auth-fixes part

- Run id: RUN-081b
- Owner: Het (Het Lathiya), 2 points; issue #147
- Status: fixed — F-1 against TC-347
- Base commit: 16bd6b9
- Decision: IMD-204 resolves PD-RUN-081-2. TC-347 was not met at 16bd6b9: a correctly signed foreign-issuer token was accepted.

## Changed files

- `apps/api/app/auth/tokens.py`: require `iss` and check it against `settings.supabase_url.rstrip("/") + "/auth/v1"` for HS256 and JWKS. Audience, expiry, algorithms and 30 s leeway are unchanged.
- `apps/api/tests/unit/auth/test_tokens.py`: failing-then-passing foreign-issuer regression with the same 401 UNAUTHENTICATED envelope as a bad signature; required issuer, configured host, trailing slash, RS256 and ES256 cases.
- `apps/api/tests/fixtures/auth.py`: shared token helper supplies the local issuer, and test settings use the same Supabase URL.
- This part record.

## Commands and result lines

| Command | Result line |
| --- | --- |
| `apps/api/.venv/bin/pytest apps/api/tests/unit/auth/test_tokens.py -k wrong_issuer -q` (before fix) | `1 failed, 30 deselected in 0.16s`; `E       Failed: DID NOT RAISE Unauthenticated` |
| `apps/api/.venv/bin/pytest apps/api/tests/unit/auth/test_tokens.py -k wrong_issuer -q` (after fix) | `1 passed, 35 deselected in 0.27s` |
| `apps/api/.venv/bin/pytest apps/api/tests/unit/auth/test_tokens.py -q` | `36 passed in 1.11s` |
| `apps/api/.venv/bin/ruff check apps/api/app/auth/tokens.py apps/api/tests/fixtures/auth.py apps/api/tests/unit/auth/test_tokens.py` | `All checks passed!` |
| `supabase status -o env` (only API_URL inspected) and the running auth container issuer | `API_URL=http://127.0.0.1:54321`; `GOTRUE_JWT_ISSUER=http://127.0.0.1:54321/auth/v1` |

## Acceptance

- F-1 / TC-347: verified. The regression failed before the implementation and passes after it; both foreign issuer and bad signature return 401 UNAUTHENTICATED with the same message and empty details, before database access.
- Existing signing modes and clock leeway: verified by all 36 token tests.
- Local host consistency: verified. `.env.example` sets `SUPABASE_URL=http://127.0.0.1:54321`; e2e.yml exports `SUPABASE_URL=$API_URL` from the pinned local CLI, whose observed API_URL is exactly that address. CI backend tests use the fixture's matching URL. Neither environment file nor workflow needed a change.
- Staging: not verified — staging SUPABASE_URL to confirm in the staging window. Production SUPABASE_URL also needs confirmation there (IMD-204).

## Blockers, proposed decisions and open issues

- No local blocker or proposed decision. Staging and production configuration confirmation remains due in the staging window.
