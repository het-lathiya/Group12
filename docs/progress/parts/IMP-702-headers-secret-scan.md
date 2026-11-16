# IMP-702 · headers-secret-scan part

- Run id: RUN-081
- Owner: Kirtan (chaudhari kirtan sandipbhai), 1 point
- Status: implemented and verified locally; TC-352 not verified
- Base commit: a4c2a0b (after parts authz-injection 822041e and auth-fixes cf3fd89)
- Traces to: IMP-702 steps 4 and 5; TC-351, TC-352, TC-354; NFR-015, CHK-05

## Changed files

- `apps/api/tests/authz/test_security_headers.py` (new): TC-351 on the protected prefix `/api/v1/trips`. The allowed origin gets the allow header on preflight and on a simple 401 response, `Authorization` and `Content-Type` are allowed headers, there is no allow-credentials, unknown origins (including `https://web.example.test.evil.example` and `null`) get no allow header, and a TRACE preflight is refused. `tests/api/test_health.py` already covers `/health`; this file does not repeat it.
- `docs/test-reports/security-sprint7.md`: added the CORS, headers and secret-scan review rows.
- No middleware and no product code change.

## Security headers

What the specification says:
- §6.1 CORS: "Allowed origins exactly `ALLOWED_ORIGINS`; methods GET, POST, PUT, PATCH, DELETE; headers `Authorization`, `Content-Type`, `X-Request-ID`; credentials not used (bearer token)".
- §6.1 Request ID: "Every response has `X-Request-ID`".
- The card's step 4: "against staging with make smoke, HTTPS and the security headers of §6 are present (TC-352)".
- §6 lists no other response header. Amendment A1 §11 covers secrets, the database, provider data, prompt injection and source links, and names no response header.

So no security-header middleware was added, and the header part of TC-352 is not verified.

## Commands and results

| Command | Result line |
| --- | --- |
| `make test-authz ARGS="-k security_headers"` | `5 passed, 95 deselected, 1 warning in 0.57s` |
| `make test-authz` | `86 passed, 14 skipped, 1 warning in 43.03s` |
| `make lint` | exit 0: `All checks passed!`, `All matched files use Prettier code style!` |
| `make typecheck` | `Success: no issues found in 123 source files` |
| `git ls-files \| grep -i gitleaks`; `git grep -n "gitleaks:allow"` | no output (no allowlist, no inline allow) |

## Acceptance

- TC-351, an unknown Origin gets no CORS allow header and the allowed origin gets it: verified, `make test-authz`.
- CORS and headers verified (CHK-05): CORS verified. Headers not verified, because the specification names none (PD-RUN-081-1).
- TC-352 on staging (HTTPS and headers): not verified. It needs the staging window (IMD-137), and Kirtan runs `make smoke URL=<staging API URL>`.
- Gitleaks configuration has no over-broad allowlist: verified. No config or allowlist is tracked, and the review rows are in the report.

## Blockers

- TC-352 needs the staging window (IMD-137).

## Proposed decisions

- PD-RUN-081-1: decide which response headers SG-7 requires and where they are set, in API middleware or at the ALB/CloudFront. Candidates are HSTS, `X-Content-Type-Options: nosniff`, `Referrer-Policy` and a frame policy for the web app.

## Open issues

- none
