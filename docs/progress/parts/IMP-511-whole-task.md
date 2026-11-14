# IMP-511 · whole-task

- Run id: RUN-069
- Owner: chaudhari kirtan sandipbhai (kirtan-S111), 5 points
- Status: implemented; database and provider-account evidence awaiting validation
- Base commit: 4c6c693
- Steps: 1–6; FR-046, FR-126, TC-171/172/173/294/310/311/353, IMD-31.

## Files changed

- core/rate_limit.py: monotonic sliding windows per user and address, atomic rejection, Retry-After, stale-key cleanup. The limiter belongs to each app instance; API fixtures create a fresh app per test, so limits do not leak between tests.
- generation/service.py: count UTC-day attempts before insert/submit, excluding explicit rule-based runs; one-process lock holds through commit to serialise caps across trips. Quota errors name scope, next UTC reset and rule_based mode.
- generation/jobs.py: purge at startup and every 24 hours, through the owning repository; existing SET NULL foreign keys preserve plans/versions.
- ai/providers/gemini.py: apply existing input limiter on every call, including repair; existing AI_MAX_OUTPUT_TOKENS config is reused. ai/limits.py already trims passages/shortlists and protects locks/must-visits; no rewrite needed.
- apps/web/app/(app)/trips/[tripId]/generate/page.tsx and its existing GenerationProgress.test.tsx: quota reset and explicit rule-based action using the existing generation mutation. No additional hook needed.
- tests/unit/core/test_rate_limit.py; tests/api/test_generations.py; docs/guides/usage-queries.md; docs/decisions/provider-spend-limit.md; this record.
- Minimal extra scope: generation/repository.py owns indexed count/purge queries; generation/router.py, itinerary/router.py and places/router.py attach the required dependency to API-16/22/25–31. These are needed to apply step 1 and keep SQL in the repository. No new routes or packages.
- All five environment names already exist in .env.example and Settings; no environment contract change.

## Commands and results

- `make test-unit ARGS='-k rate_limit'`: `12 passed, 1126 deselected, 1 warning in 2.11s`.
- `make test-web ARGS='GenerationProgress'`: `Test Files  1 passed (1)`; `Tests  9 passed (9)`.
- `make test-unit`: `1138 passed, 1 warning in 22.83s`.
- `make typecheck`: `Success: no issues found in 122 source files`; `✓ Types generated successfully` (exit 0).
- `ruff check apps/api/app apps/api/tests`: `All checks passed!`.
- `make imports`: `Contracts: 6 kept, 0 broken.`
- Not run: `make test-api ARGS='-k "quota or rate_limit"'` and `make test-api ARGS='-k purge'`; PostgreSQL unavailable in this WSL distro.

## Acceptance

- Verified TC-294: user/address independence, exact 60-second expiry, rounded Retry-After, rejected attempts do not consume another key, expired keys pruned.
- Verified cap boundary and next-UTC-midnight fields in unit tests; web action sends mode rule_based.
- Verified existing token-limit unit cases in the full unit run; provider output config already uses AI_MAX_OUTPUT_TOKENS.
- API quota/no-insert/no-provider, rate-limit/no-submit, rule-based bypass and retention-preserves-plan tests written, not verified without PostgreSQL (TC-171/172/173/310/311/353).
- Provider account spending/quota settings are Awaiting validation; no provider-side setting claimed.

## Proposed decisions / open issues

- No new contract shapes, migrations or decisions. Single-instance concurrency follows IMD-12; scale-out needs shared synchronisation.
- API suites and real provider-account spending-limit evidence remain open.

## Also in this run

- RUN-069 part 6b, owner Kirtan, IMD-159: Money.currency keeps its JSON Schema pattern and maps malformed strings to exactly `Currency must be a three-letter ISO 4217 code.` through a custom validation error.
- Files: apps/api/app/schemas/common.py and apps/api/tests/unit/core/test_money_currency.py.
- `make test-unit ARGS='-k money_currency'`: `8 passed, 1131 deselected, 1 warning in 1.43s`. Plain-language message verified; no API shape or migration changed.
