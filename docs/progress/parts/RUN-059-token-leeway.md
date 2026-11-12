# RUN-059 · token-leeway part

- Run id: RUN-059 (grouped)
- Owner: Het (het-lathiya)
- Status: PR open
- Base commit: 8c3997b
- Branch: chore/RUN-059-decisions-and-fixes
- Traces to: IMD-140 (PD-IMP-215-1); SG-3 open item "No committed ES256 token test"; §6.2; IMD-04

## Changed files

- `apps/api/app/auth/tokens.py`: `CLOCK_LEEWAY_S = 30`, a named constant with its one-line reason, passed as `leeway=` to `jwt.decode`. It covers HS256 and JWKS alike, since both go through `_decode`. Audience (`authenticated`), required claims (`exp`, `sub`, `aud`) and the algorithm lists (`HS256`; `ES256`, `RS256`, `EdDSA` for JWKS) are unchanged. There is no issuer check before or after. The module docstring states the leeway.
- `apps/api/tests/unit/auth/test_tokens.py`: three tests. They use a generated P-256 key served as a JWKS key set through the real `jwt.PyJWKClient`, with `fetch_data` overridden to return the local set, so there is no network call and the `kid` lookup is the library's own.
  - an ES256 token is accepted;
  - `iat` 20 s in the future is accepted and 40 s is refused;
  - an expired token (`exp` 60 s ago) is refused.
- `docs/progress/parts/RUN-059-token-leeway.md`: this record.

## Commands and results

| Command | Result |
| --- | --- |
| `make test-unit ARGS='-k token'` | `36 passed, 981 deselected, 1 warning in 2.16s` |
| `make test-authz` (throwaway local PostgreSQL 16.2 + pgvector, port 55432) | `41 passed in 18.94s` |
| `CLOCK_LEEWAY_S = 0` temporarily, `pytest tests/unit/auth/test_tokens.py` | `1 failed, 29 passed` (the 20 s case), so the test depends on the leeway; restored to 30 |
| `make typecheck` | `Success: no issues found in 116 source files` |

## Acceptance

| Criterion | Status | How |
| --- | --- | --- |
| IMD-140: 30 s leeway as one named constant with a reason; no other rule changed | verified | diff of `tokens.py`; the existing HS256, RS256, audience and tampering tests still pass |
| ES256 token through a fake JWKS (no network) accepted | verified | `test_an_es256_token_from_the_jwks_key_set_is_accepted` |
| `iat` +20 s accepted, +40 s refused | verified | `test_iat_20_s_ahead_is_accepted_and_40_s_ahead_is_refused` |
| Expired token refused | verified | `test_an_expired_es256_token_is_refused` |

## Blockers

None.

## Open issues

- `tests/fixtures/auth.py` still says "PyJWT has no leeway" in a comment on the `iat` of `make_token`. The helper is still correct; the comment can be updated in the next change to that file (not in this part's file list).

## Proposed decisions

None.
