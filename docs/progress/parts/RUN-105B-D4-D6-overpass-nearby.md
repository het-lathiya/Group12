# RUN-105B · D4 Overpass refusals and D6 bounded nearby suggestion

- Owner: Jeel Fefar; 0 points, follow-up of IMP-723, IMP-724 and IMP-725.
- Status: PR candidate on `fix/live-import-retry`.
- Base: `a461804` (`origin/main`); follows the Manal D2 commit on this branch.
- Traces: local live report D4/D6; A2 §6.3, §6.4, §7.1, §7.3, §16;
  FR-142, TC-467, TC-469, TC-471, TC-475, TC-483; IMD-217.

## Change

- Overpass HTTP errors log their status and at most 256 characters of diagnostic body text.
  HTML, echoed query text, credential values, bearer/basic credentials, email addresses, URLs
  and IP addresses are removed or redacted before logging. No request headers or configured
  contact text are logged. Exceptions keep their existing safe messages and taxonomy.
- A 429 defers subsequent Overpass calls for at least A2's 15 minutes. A longer `Retry-After`
  wins. A 504 uses `Retry-After` or exponential backoff starting at 2 seconds, capped at
  60 seconds; the existing breaker still opens for 60 seconds after five transient failures.
  Both delay-seconds and HTTP-date headers work; invalid headers use the local backoff.
  Cooldown calls fail locally, and D2 resolve reads the same deadline. There is one HTTP attempt
  per query; no sleeping retry loop and no new endpoint, setting or dependency.
- The nearby query previously used `out tags`, omitting node coordinates. `_element` therefore
  discarded the real response's nodes (D6). It now uses `out center tags` and the same 64 MiB
  query memory bound as the places query.
- One nearby response is searched through 25, 50, 100 and 150 km bands; the most populous named
  city in the first populated band wins, with name as a tie-breaker. The requested distance may
  reduce the maximum; it cannot exceed A2's 150 km. Coordinates are checked locally even when
  the provider returns out-of-radius elements. The node at the settlement centre is excluded.
- A missing, failed or self-only nearby lookup leaves `nearby_city = null`. The empty state says
  "No larger city nearby." and offers no nearby-search button. No capital with an unverified
  distance is substituted.

`live_service.py` is untouched in this part. The only `live_jobs.py` change is the nearby helper
and its now-unused capital import. Job completion, embedding/ingestion and routing are unchanged.
The two web files contain only the empty-state copy and its component test; package and lockfiles
are unchanged for parallel RUN-105A.

## Verification

Tests use respx recordings/synthetic responses, fake clocks and fake providers. The socket guard
is active. API tests use the isolated PostgreSQL 16 / pgvector instance prepared for D2 under
`/tmp`, with `TEST_DATABASE_URL` selecting `travel_test_r105b` on loopback port 55435.

| Command | Result |
| --- | --- |
| `AI_PROVIDER=MOCK LIVE_DATA_PROVIDER=FAKE .venv/bin/pytest tests/unit/livedata tests/api/test_live_destinations.py tests/api/test_live_destinations_schema.py tests/api/test_live_import_jobs.py tests/api/test_live_import_retry.py tests/api/test_live_guides_index.py tests/api/test_live_generation.py tests/contract/test_any_city_contract.py -m 'not live' -q --tb=short` (isolated `TEST_DATABASE_URL`) | `731 passed, 1 warning in 31.24s` |
| `npm test -- tests/unit/trips/ImportProgress.test.tsx` (apps/web) | `Tests  13 passed (13)` |
| `make lint` | `All checks passed!`; `273 files already formatted`; `All matched files use Prettier code style!` (ESLint exit 0) |
| `make typecheck` | `Success: no issues found in 139 source files`; `✓ Types generated successfully` (TypeScript exit 0) |
| `make imports` | `Contracts: 7 kept, 0 broken.` |
| `make openapi-check` | `openapi-check: contracts/, apps/web/lib/api/schema.d.ts and apps/web/lib/api/any-city-schema.d.ts are up to date` |
| `git diff --check` | exit 0 |

The first combined pytest invocation inherited GEMINI from the copied local `.env`; the CLI
repeat-import test attempted an embedding call, which the socket guard blocked before connection
(`1 failed, 730 passed, 1 warning in 30.96s`). The explicit MOCK/FAKE rerun above passes. No live
provider request was made and no embedding code was changed.

Verified: 406/429/504 status diagnostics with redaction; one failed-query attempt; integer and
date Retry-After; the 900-second minimum; 504 backoff and breaker/reset; no places or nearby
HTTP call during cooldown; all distance bands and one nearby query; an oversized requested
radius still capped at 150 km; out-of-radius and coordinate-less cities rejected; no unbounded
capital on missing/error/self results; empty-state copy and no search action. D2 retry and
IMD-217 preservation tests also pass in the combined run. Contracts and generated types are
byte-identical to the base.

Not run: live provider checks or staging acceptance; E2E/browser screenshots (text-only empty
state, covered by the component test). No E2E spec or layout changed.

## Proposed decisions

- **PD-RUN-105B-1 (D4 endpoint fallback):** A2 §7.2 and the implementation configure one
  `OVERPASS_BASE_URL`; neither provides an approved second public endpoint. No endpoint was
  added. An operator-approved secondary endpoint and its usage policy are needed before adding
  fallback. Deferred calls remain on the configured endpoint.
- **PD-RUN-105B-2 (D6 selection/copy):** the RUN-105B instruction replaces A2 §6.4/§9.1's
  unconditional capital fallback with null and the explicit no-nearby message. Expanding bands
  use the nearest populated band rather than the largest population anywhere within 150 km.
  This follows the run's requested expanding-radius search without exceeding A2's one extra
  query. The 150 km maximum itself is already defined by A2, so no new distance is proposed.
- The run explicitly requests a body snippet for D4, replacing A2 §7.1's blanket no-body logging
  for Overpass HTTP refusals only. The bound and redaction tests above cover that exception.

## Blockers and open issues

No implementation blocker. Real-provider recovery and a secondary endpoint remain unverified.
Population tags are optional and may be stale; when absent, the existing name tie-breaker is
retained. The nearby hint identifies a city, without verifying comparative settlement size.
