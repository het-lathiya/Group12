# IMP-601 · whole-task

- Run id: RUN-075
- Owner: Het Lathiya, 2 points
- Status: implemented; API and component tests pass locally
- Base commit: a6307c3
- Steps: 1–5; FR-004 AC1–AC3 (TC-060 to TC-062); IMD-14, IMD-16, IMD-45.

## Files changed

- apps/api/app/auth/service.py: `update_profile` now accepts every field of API-04:
  - `display_name`: 1 to 60 characters, checked by ProfilePatch; null clears it.
  - `preferred_currency`: ISO 4217, three capital letters; otherwise 422 with field `preferred_currency`.
  - `home_country`: ISO 3166-1 alpha-2.
  - `default_preferences`: validated with the PreferencesIn rules. `notes` and `must_visit_place_ids` are refused as `default_preferences.<key>`. Omitted keys are stored with the PreferencesIn defaults (IMD-16).
  - Every rule is checked before anything is written.
- apps/api/app/auth/repository.py: `update_profile` writes the given columns of the caller's own row. `set_ai_notice_ack` is folded into it (`acknowledge=True`).
- apps/api/app/auth/router.py and auth/schemas.py: docstrings only. The wire shape is unchanged: `default_preferences` stays a JSON object, and the rules are enforced in the service.
- apps/web/app/(app)/profile/page.tsx (new): /profile with LoadingSkeleton, ErrorState and ProfileForm. A success Toast reads "Profile saved". 422 details appear on their fields; other errors appear in an error Toast.
- apps/web/components/profile/ProfileForm.tsx (new): react-hook-form with a zod schema that mirrors the server rules (name up to 60, three-letter currency and two-letter country, uppercased, and the PreferencesIn default fields). Empty text fields are sent as null.
- apps/web/components/trips/TripWizard.tsx: preferences not yet saved for a trip start from the profile's `default_preferences` (only the keys that pass the form's rules; saved trip preferences are never replaced).
- apps/web/lib/api/queries.ts: one appended block, `// IMP-601 profile`, with `useUpdateProfile`.
- apps/api/tests/api/test_me.py: TC-060, TC-061, TC-062, default-preference rules, null clearing, and token id with a body `user_id` refused. The IMP-305 parametrised test of the minimal form ("only the notice flag") is updated, because IMP-601 now allows the other fields. Its false and null flag cases are kept.
- apps/web/tests/unit/profile/ProfileForm.test.tsx (new); apps/web/tests/unit/trips/TripWizard.test.tsx (one appended prefill case); this record.

## Commands and results

The database was a throwaway local PostgreSQL 16.2 + pgvector on 127.0.0.1:55432 (travel_test_t). `PYTHONPATH=apps/api` was set for every API command.

- `make test-api ARGS='-k me'`: `238 passed, 257 deselected, 1 warning in 51.23s`
- `make test-authz`: `53 passed in 30.00s`
- `make test-web ARGS='tests/unit/profile tests/unit/trips'`: `Tests  40 passed (40)`, `Duration  6.44s`
- `make test-web ARGS='tests/unit/profile'` (after a typing fix): `Tests  6 passed (6)`
- `make lint`: exit 0. The one existing AppShell warning is not from this part.
- `make typecheck`: `Success: no issues found in 122 source files`; tsc clean
- `make imports`: `Contracts: 6 kept, 0 broken.`
- `make openapi-check`: `stale contract`. The only drift is the ProfilePatch description text (its docstring). The lead regenerates the contract.

## Not run

- `make e2e`: Docker is not available on this machine.

## Acceptance

- FR-004 AC1 (TC-060): verified. Names of 1, 60 and padded length are saved trimmed and shown by API-03. Empty, blank and 61-character names return 422 `display_name` and change nothing. Web: the form refuses 61 characters before calling the API.
- FR-004 AC2 (TC-061): verified by the API test (defaults, currency and country saved and returned). The web prefill test checks that an unsaved trip's preferences start from the profile defaults (Relaxed).
- FR-004 AC3 (TC-062): verified. `inr`, `IN`, `RUPEE`, `12A` and an empty string return 422 with field `preferred_currency`. Web: the form refuses an invalid code.
- Profile id equals the token user, and a body `user_id` returns 422 as an unknown field: verified (`test_the_profile_id_is_the_token_user_*`).
- Screenshot of the profile page: not taken (no local stack). The member adds it.

## Proposed decisions / open issues

- PD-RUN-075-T3: step 5 says to prefill the budget currency from the profile. API-07 and §9.3.2 require the budget to be in the destination's currency, and TripDetailsStep sets it from the chosen destination. A home currency that differs would always be refused. Built: the preferences are prefilled, the budget currency is not. Options: keep this, or prefill only when the destination's currency matches (it already does then).
- Navigation: the account menu in AppShell already links to /profile, so no new link is needed.
