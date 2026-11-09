# IMP-406 · ai-text-labels part

- Run id: RUN-057 (grouped, IMD-121, with IMP-401, IMP-402 and FIX IMD-126)
- Owner: Krrish (Assassin-byte)
- Status: PR open
- Base commit: 16839a0
- Branch: feat/IMP-401-402-406-generation-reliability
- Reviewer: Manasvi (Manasvi1704)
- Traces to: US-057; FR-035 (UI side); IMD-118
- Card steps built: 5

## Changed files

- `apps/web/components/itinerary/ItineraryItemCard.tsx`: the AiBadge now comes before the item note (the run's design: after the day theme, before the item note), so the label is read first. It still shows only when `note_origin` is `ai`. The badge itself (`components/labels/AiBadge.tsx`, IMP-309) already matched the design: the "AI-written" text, a decorative 12 px `Sparkles` icon, the `ai` soft token pair (`bg-ai-soft`, `text-ai`), never colour alone. The day theme badge in `DayColumn.tsx` already follows the theme and is unchanged. SourceBadge stays on hours and price, unchanged.
- `apps/web/tests/unit/labels/AiBadge.test.tsx` (created): the badge's text and hidden icon; it comes first on an AI-written note; it is distinct from the price's SourceBadge on the same card; no badge on a rule-based or sample item (`note_origin none`, no note) or on a traveller's note; a theme badge for `theme_origin ai` and none for a template theme.

## Commands and results

| Command | Result |
| --- | --- |
| `make test-web ARGS='AiBadge'` | `Tests  6 passed (6)` |
| `make test-web` | `Tests  125 passed (125)` |
| `make lint` | exit 0 (`✖ 1 problem (0 errors, 1 warning)`: the existing `no-location-assign-relative-destination` warning in a file this run does not touch) |
| `make typecheck` | `Success: no issues found in 112 source files` |
| `make test-unit` | `985 passed, 1 warning` |
| `make imports` | `Contracts: 6 kept, 0 broken.` |
| `make openapi-check` | `openapi-check: contracts/ and apps/web/lib/api/schema.d.ts are up to date` |

## Acceptance criteria

| Criterion | Status | How |
| --- | --- | --- |
| FR-035 UI side: AI note and retrieved fact have distinct labels | verified | `AiBadge.test.tsx` "is distinct from the price's source label on the same card" |
| AiBadge only when note_origin is ai; none on fallback and sample items | verified | `AiBadge.test.tsx` cases for `none` and `user` |
| Badges wrap with no horizontal scroll at 375 and 1280 px | not verified | No browser run in this session (the itinerary page needs the local stack and a signed-in user). The note line keeps `flex flex-wrap` with `min-w-0` text; screenshot evidence is missing and should be taken by Krrish |
| Completion evidence: screenshot of an AI-written label beside a source-labelled price | not verified | Same reason; to be added by the part owner |

## Blockers

none

## Proposed decisions

none

## Open issues

- The screenshot of the card evidence (card completion evidence) is missing; see above.
