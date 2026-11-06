# IMP-305 · privacy-progress part

- Run id: RUN-047.2 (grouped, IMD-121, with IMP-312 and IMP-302)
- Owner: Krrish (Assassin-byte)
- Status: PR_OPEN
- Base commit: 7974da0
- Branch: feat/IMP-312-305-302-wave2
- Reviewer: Manya (manyarana)
- Traces to: US-048; FR-024, FR-025; NFR-021; IMD-12, IMD-24, IMD-118; OD-11; TC-369
- Card steps built: 7

## Changed files

- `apps/web/components/generation/PrivacyNotice.tsx` (created): heading, body, terms link and one primary button. All the strings are in the `PRIVACY_NOTICE` constants object. Focus moves to the heading when the notice is shown.
- `apps/web/app/(app)/trips/[tripId]/generate/page.tsx`: the notice replaces the start section until the account has acknowledged it; acknowledging starts the generation.
- `apps/web/lib/api/queries.ts`: `queryKeys.me`, `useProfile` (API-03) and `useAcknowledgeAiNotice` (API-04, which sets `me` as §7.4 says).
- `apps/web/lib/api/client.ts`: `OFFLINE_MESSAGE`, shared by the notice, the page and `GenerationProgress.tsx`, which held their own copies.
- `apps/web/components/generation/GenerationProgress.tsx`: that shared message only. The polling the card asks for (2 s backing off to 5 s, giving up at 160 s with a reload offer) was already built by IMP-213 and is unchanged.
- `apps/web/tests/unit/generation/PrivacyNotice.test.tsx` (created); `tests/unit/generation/GenerationProgress.test.tsx`: its fake API now answers API-03.
- `apps/web/e2e/journey.spec.ts`: acknowledges the notice once, in place of the Generate click.
- `docs/progress/parts/IMP-305-privacy-screens/`: the two screenshots.

## How the page knows

API-03 already exposes `ai_notice_ack_at` (`Profile`, see `IMP-305-job-progress.md`), so the page reads it: null shows the notice. The 422 on field `ai_notice` is kept as a backstop for a click before API-03 answers or when API-03 fails: the notice then appears, and acknowledging sends API-22 once more. Both paths are tested. A first-time user may see the start button for a moment until API-03 answers.

## Wording source

Operator-approved draft, given in the RUN-047.2 prompt and reviewed per OD-11. It is used exactly. It must be recorded as a decision before SG-3. The inline error shows the API's message or the existing offline message, so it adds no new wording.

## Commands and results

| Command | Result line |
| --- | --- |
| `make test-web ARGS='PrivacyNotice'` | `Tests  8 passed (8)` |
| `make test-web ARGS='GenerationProgress'` | `Tests  8 passed (8)` |
| `make e2e ARGS='journey'` (steps of `.github/workflows/e2e.yml`: local Supabase stack, API with MOCK, standalone web build, widths 360, 768, 1280 and 1920) | `4 passed` |
| `make check` (whole branch, `TEST_DATABASE_URL` on `pgvector/pgvector:pg16`) | exit 0: unit `578 passed, 1 warning`; contract `87 passed, 2 deselected, 1 warning`; api `279 passed, 1 warning`; authz `29 passed`; web `Tests  88 passed (88)` |

## Screenshots

From a temporary edit of the journey, which was not committed: `docs/progress/parts/IMP-305-privacy-screens/notice-360.png` and `notice-1280.png`. The same run checked that the page does not scroll sideways at any of the four widths.

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| The notice is shown before the account's first generation, with the provider named, the terms link and the warning (NFR-021) | verified | `PrivacyNotice.test.tsx`, exact text; the journey |
| Acknowledging calls API-04, then API-22, then polls API-23 | verified | "acknowledging sends API-04 and then API-22, once each"; the journey reaches `completed` |
| Polling 2 s to 5 s, giving up at 160 s with a reload offer | verified | existing `GenerationProgress.test.tsx`, unchanged code |
| An account that has acknowledged sees no notice; resuming a job shows none | verified | the two "is not shown" tests |
| Button disabled in flight; inline `role="alert"` if API-04 fails, with a retry | verified | the "disables the button" and "shows an alert" tests. The retry is the same primary button, so the notice keeps one action |
| Focus moves to the heading; keyboard reachable; visible focus ring | verified for focus; ring by code | unit test and the journey's `toBeFocused`; the link and `Button` carry the `focus-visible` ring classes. No axe tooling exists yet |
| Works at 360 px | verified | the journey at 360 px, the sideways-scroll check and `notice-360.png` |
| Theme tokens only, no hard-coded colours or radii | verified | code review of the component |

## Blockers

None.

## Proposed decisions

- **PD-IMP-305-6: record the notice wording.** Operator-approved in the run prompt; it needs a decision entry for OD-11 before SG-3.

## Open issues

- `IMP-305-job-progress.md` still says the journey fails until this part lands. This part closes that: the journey passes on this branch. That commit is left unchanged by instruction.
- Focus falls to the page body when the notice closes. The status changes are announced by the progress view's live region.
