# RUN-075 · hover-contrast

- Run id: RUN-075
- Owner: Manasvi Rathore, 0 points
- Status: implemented; component tests pass locally
- Base commit: a6307c3
- Scope: PD-RUN-071b-1 (IMD-183). The destructive Button's hover text contrast must be at least 4.5:1 over the page background. Fixed with design tokens only (IMD-182: colours animate, never opacity).

## Change

The destructive Button's surfaces were the `--destructive` colour mixed with opacity (`bg-destructive/10`, `hover:bg-destructive/20`). They are replaced by two solid tokens:

- `--destructive-soft`: #FEF2F2, `oklch(0.971 0.013 17.4)`
- `--destructive-soft-hover`: #FEE2E2, `oklch(0.936 0.031 17.7)`

The opacity-based `dark:bg-destructive/20` and `dark:hover:bg-destructive/30` overrides are removed.

## Contrast (text #B91C1C, page background #FAFAF9; WCAG 2.1, computed with a local script that is not committed)

| State | Before: surface (blended) | Before | After: surface | After |
| --- | --- | --- | --- | --- |
| Rest, light | /10 → #F3E4E3 | 5.24:1 | #FEF2F2 | 5.91:1 |
| Hover, light | /20 → #EDCECD | 4.40:1 | #FEE2E2 | 5.30:1 |
| Rest, `dark:` variant | /20 → #EDCECD | 4.40:1 | #FEF2F2 (same token) | 5.91:1 |
| Hover, `dark:` variant | /30 → #E6B7B7 | 3.66:1 | #FEE2E2 (same token) | 5.30:1 |

Dark theme: globals.css defines no dark token set, and ui-design.md §2 says the app is light only with no theme toggle. So the `dark:` classes never applied. Now no opacity-based dark override remains, and under a future `.dark` class the button would use the same solid tokens (5.30:1 or more). A real dark palette needs its own tokens and a decision.

## Files changed

- apps/web/app/globals.css: the two tokens and their `--color-*` theme entries.
- apps/web/components/ui/button.tsx: the destructive variant classes.
- apps/web/tests/unit/ui/button.test.tsx: one new case. Destructive uses the solid tokens and no opacity-mixed background.
- docs/guides/ui-design.md: the token table and contrast table rows. The guide requires an update in the same change when a token changes.
- This record.

## Commands and results

- `make test-web ARGS='tests/unit/ui tests/unit/trips tests/unit/states'`: `Tests  52 passed (52)`, `Duration  5.79s`
- `make lint`: exit 0. The one existing AppShell warning is not from this part.
- `make typecheck`: exit 0

## Not run

- `make e2e` (axe): Docker is not available on this machine. axe does not scan hover states anyway (gates.md, PD-RUN-071b-1).

## Acceptance

- Destructive hover is at least 4.5:1 over the page background: verified by calculation, 5.30:1 (it was 4.40:1).
- Tokens only, no opacity: verified by the button test and the diff.

## Open issues

- Other places still use `bg-destructive/10`: WarningsPanel, SignIn and SignUp alerts, PrivacyNotice, and the destructive dropdown item focus. They measure 5.24:1 at rest and are outside this item's scope. They could move to `destructive-soft` later.
