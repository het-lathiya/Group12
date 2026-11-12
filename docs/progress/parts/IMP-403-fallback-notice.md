# IMP-403 · fallback-notice part

- Run id: RUN-060 (grouped, IMD-121, with IMP-405 and IMP-407)
- Owner: Krrish (Assassin-byte)
- Status: PR open
- Base commit: 84d1973
- Branch: feat/IMP-403-405-407-failures-warnings-edits
- Reviewer: Kirtan (kirtan-S111)
- Traces to: US-059; FR-037 (UI side); IMD-44, IMD-118
- Card steps built: 4 (web side). Steps 1 to 3 and 5 are the failure-outcomes part.

## Changed files

- `apps/web/components/generation/FallbackNotice.tsx`:
  - `FallbackNotice` shows the exact text "Built by rules because the AI service was unavailable or failed checks" (`FALLBACK_TEXT`). It is an info notice (`info` soft pair, `Info` icon), not an error. It sits above the plan on the itinerary page, never hides it, and never carries an AI badge.
  - `PausedAiNotice` (new) shows the catalogue text of `ERROR_CATALOGUE.AI_QUOTA_REACHED` (IMP-412) and the primary button "Build a rule-based plan", with a busy state.
- `apps/web/components/generation/GenerationProgress.tsx`: on `failed`, `provider_quota_exhausted` shows `PausedAiNotice`. Any other failure shows the IMP-412 `ErrorState`, titled "The plan could not be built", with API-23's `failure_message`, a reference (the generation id) and the action `next_action` names:
  - `retry_rule_based` → "Build a rule-based plan";
  - `retry` → "Try again";
  - `edit_trip` → an "Edit trip" link to the trip wizard.

  The new prop `onRuleBased` carries the rule-based action. This file is not in the run's list, but its docstring said "Other `next_action` choices arrive with IMP-403", and the failed state is rendered here.
- `apps/web/app/(app)/trips/[tripId]/generate/page.tsx`: `generate(mode)`; "Build a rule-based plan" calls API-22 with `mode: "rule_based"` and then polls the new generation as before.
- `apps/web/lib/api/queries.ts`: `useStartGeneration`'s mutation takes the mode (default `ai`, so existing callers are unchanged).
- `apps/web/tests/unit/generation/FallbackNotice.test.tsx` (created): nine cases:
  - the exact text, info styling, not an alert and no AI badge;
  - no notice on a model plan, and the repaired note;
  - the paused notice's catalogue text, button and busy state;
  - GenerationProgress for quota (paused notice, no alert), config_error (ErrorState with reference and the rule-based action), unresolved_validation (Edit trip link) and internal (Try again);
  - the generate page posting `{mode: "rule_based"}` and polling the new generation.
- `apps/web/tests/unit/itinerary/ItineraryPage.test.tsx`: the FallbackNotice assertion uses the new text.

No new raw message strings: the failure text is API-23's `failure_message` (§6.4, from `outcomes.MESSAGES`), the paused text is the catalogue's, and the button labels are the ones the card and DESIGN name.

## Commands and results

| Command | Result |
| --- | --- |
| `make test-web ARGS='FallbackNotice'` (run as `npx vitest run FallbackNotice ItineraryPage GenerationProgress`) | `Tests  25 passed (25)` |
| `make test-web` | `Tests  170 passed (170)` |
| `make lint` | `All checks passed!`; ESLint `✖ 1 problem (0 errors, 1 warning)`, a warning that predates this run and is not in these files; `All matched files use Prettier code style!` |
| `make typecheck` | `Success: no issues found in 116 source files`; `tsc --noEmit` clean |
| `make test-unit` | `1006 passed, 1 warning` |
| `make imports` | `Contracts: 6 kept, 0 broken.` |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |

Not run: screenshots of the fallback notice and the paused-AI notice on the local stack, since no stack runs here. They are added on staging after deploy.

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-037 UI: the fallback notice is visible for `fallback_rule_based` | verified | `labels a rule-based plan with the exact text …`; ItineraryPage `shows FallbackNotice on a rule-based plan only` |
| FR-037 AC2 UI: the paused-AI notice and its rule-based action are visible for `provider_quota_exhausted` | verified | `FR-037 AC2: provider quota shows the paused-AI notice, not an error`; `Build a rule-based plan starts API-22 with mode rule_based` |
| `failed` shows the IMP-412 ErrorState with a reference | verified (with the generation id; see PD-IMP-403-2) | `a configuration failure shows ErrorState with its reference …` |

## Blockers

none

## Proposed decisions

- **PD-IMP-403-1: FallbackNotice wording.** The spec states two wordings. §7.5.6 and the §7.8 label table say "…unavailable or its answer failed checks". §8 (the fallback section) and the IMP-403 card say "…unavailable or failed checks". This part uses the card's text, which the run prompt requires exactly. The team should make §7 match, or tell this component to switch back.
- **PD-IMP-403-2: the reference of a failed generation.** A failed generation arrives as a 200 answer of API-23, which has no `request_id` field. The ErrorState footer therefore shows the generation id, which the team can look up in `ai_generations`. The alternative is to add `request_id` to `GenerationOut`, which is a contract change.

## Open issues

- The "Build without AI" button on the start screen (§7.5.6, a choice before any generation) is not part of this card; it is still missing.
