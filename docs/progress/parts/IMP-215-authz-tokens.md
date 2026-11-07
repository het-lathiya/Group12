# IMP-215 · authz-tokens part (follow-up)

- Run id: RUN-055 (grouped, IMD-121, with IMP-399)
- Owner: Junaid (Junaid-Kureshi)
- Status: PR_OPEN
- Base commit: 5eaf19f
- Branch: chore/IMP-399-sg3-gate
- Reviewer: Manya (manyarana)
- Traces to: IMP-215; TC-063, TC-064

## Why

RUN-054: `tests/authz/test_ownership.py[API-07 POST /api/v1/trips]` failed once in 8 runs. In `a_state`, one token passed the first two reads and got 401 on the third.

## Cause

Only the time claims can change between calls with the same token. `make_token` set `iat` to the current whole second, and PyJWT rejects `iat > now` with leeway 0. On this WSL machine `systemd-timesyncd` steps the wall clock back by up to about 0.35 s every 30 s or so: `dmesg` shows repeated "Time jumped backwards", and a 20 s sample measured one step of 0.26 s. A step just after a token is minted makes that token look issued in the future.

Measured with the real helper, each token verified 0.3 s after minting, for 120 s:

| Helper | Verified | Rejected |
| --- | --- | --- |
| Before | 11174 | 6, all `ImmatureSignatureError: The token is not yet valid (iat)` |
| After | 11153 | 0 |

The rejection reason of the RUN-054 failure itself was not logged, so this is a measured cause that matches it, not a replay of that failure.

## Changed files

- `apps/api/tests/fixtures/auth.py`: valid test tokens have `iat` 5 seconds in the past; `exp` stays 600 seconds ahead.
- `apps/api/tests/unit/auth/test_tokens.py`: `test_a_helper_token_outlasts_a_backward_clock_step`.

Product verification is unchanged: neither the specification nor Amendment A1 states a leeway.

## Commands and results

`make db-up`, then with `TEST_DATABASE_URL` on `pgvector/pgvector:pg16`.

| Command | Result line |
| --- | --- |
| `make test-authz`, 20 times in a loop | 20 of 20 exit 0, each `31 passed` |
| `make test-unit` | `844 passed, 1 warning in 20.85s` |

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| Cause found and fixed in the test helper | verified | Measurement above |
| `make test-authz` passes 20 of 20 | verified | Loop above |

## Blockers

None.

## Proposed decisions

- PD-IMP-215-1: `jwt.decode` has no leeway, so a real token is refused for a moment if the API's clock is slightly behind Supabase Auth's. The specification states no leeway, so the code is unchanged. Proposed: decide whether verification gets a small leeway.
