# Keyboard map

The keyboard path through the core journey (sign in, create a trip, generate, review and edit the itinerary, costs) for FR-115 and NFR-025 (IMP-513). Every action works from the keyboard with a visible focus ring (`docs/guides/ui-design.md`). The app adds no shortcut keys of its own; only the standard keys of native controls and of the widgets listed below are used.

## Every signed-in page (AppShell)

| Order | Element | Keys |
| --- | --- | --- |
| 1 | "Skip to content" link, hidden until focused | Tab reaches it first; Enter moves focus to the main content, and the next Tab continues from there |
| 2 | "AI Travel Planner" link (to the dashboard) | Enter |
| 3 | Main navigation: Trips, Itinerary, Costs, Profile. From 768 px it sits in the header; below 768 px it is a bottom bar that comes after the page content in the Tab order | Enter. Itinerary and Costs are not focusable until a trip is open; screen readers hear "(open a trip first)" |
| 4 | "Account menu" button | Enter or Space opens it; arrow keys move between Profile and Sign out; Escape closes it and returns focus to the button |
| 5 | Main content (`#main-content`) | See the pages below |

The public pages (landing, sign-in, sign-up) have the same skip link and header without the navigation.

## Sign in and sign up

Email, Password, then the submit button. Enter in a field submits the form. A field error is linked to its field (`aria-describedby`) and announced.

## Create a trip (wizard)

| Step | Focus order |
| --- | --- |
| 1 Details | Destination, Trip title, Start date, End date, Adults and the other fields, Next |
| 2 Preferences | Focus moves to the step heading; then the interest buttons (Enter or Space toggles one, `aria-pressed`), the other fields, Back, Next |
| 3 Must-visit places | Focus moves to the step heading; then the place search and list, Back, Next |
| 4 Review | Focus moves to the step heading; then the Edit button of each section, Generate itinerary |

## Generate

The first-generation notice is a dialog: focus moves into it, Tab stays inside it, "I understand, continue" closes it. Status changes (Queued, Running, Validating, Repairing) are announced in a polite live region; the elapsed-time counter is not announced. A failure shows its message and the next action as buttons (Try again, Build a rule-based plan, Edit trip).

## Itinerary

| Order | Element | Keys |
| --- | --- | --- |
| 1 | Out-of-date plan message (when the plan is stale) and its Regenerate link | Enter; the message is a status region |
| 2 | Add a place | Enter opens the place picker dialog; Escape closes it and focus returns to the button |
| 3 | From 1024 px: the day index | Enter moves focus to that day |
| 3 | Below 768 px: the List and Map tabs, then the day tabs | Arrow Left and Right move between tabs and open the focused one; Tab moves into the open day |
| 4 | Each day: a region named "Day N" with the heading "Day N, <date>" and its items in an ordered list, time first | |
| 5 | Each item card, in order: Sources (on AI-written notes), Lock, Edit time, Remove, the drag grip, Up, Down, the day select, Move, Replace | Enter or Space on buttons; the day select uses the arrow keys |
| 6 | Map (from 768 px) and Plan checks | "Show" or "Hide" toggles Plan checks below 1280 px; "Go to item" moves focus to the item's card |

Edits from the keyboard:

- **Move within a day:** Up and Down. Focus stays on the same button of the moved item, or on its other move button when the item reaches the top or bottom.
- **Move to another day:** choose the day in the select, then Move. Focus moves to the same controls in the item's new day. Below 768 px the new day is a closed tab, so focus goes to that day's tab, which opens it.
- **Drag by keyboard:** focus the grip, press Space to pick the item up, use the arrow keys to move it, press Space to drop it or Escape to cancel. The same instructions are read when the grip is focused.
- **Remove:** Remove opens a confirmation dialog (Cancel, Remove). Afterwards focus moves to the next card, else to the previous card, else to the day heading when the day is empty.
- **Edit time:** Edit time opens Start time and Duration fields in the card. Save or Cancel returns focus to the card.

Each move is announced in a polite live region ("Moved <place> to day N position P"). Removals and retimes are announced by a toast. The Plan checks counts are announced in a polite live region when they change.

## Costs

The page heading, then the totals and the cost rows in reading order. Every amount carries its "Estimate" label in text.

## Checks

- `apps/web/e2e/journey.spec.ts`: the journey uses Enter on focused controls, checks the skip link, moves an item to another day by keyboard at every project width (360 px with day tabs), and runs axe on each core page. Serious or critical findings fail the test (TC-279, TC-374, TC-383).
- `apps/web/tests/unit/itinerary/DayColumn.test.tsx`: focus after a removal and after a move to another day, and the move announcement (TC-280).
- The manual screen-reader pass (TC-382) is part of IMP-703.
