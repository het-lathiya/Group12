# UI design guide

How every screen of the web app looks: colour, type, spacing, layout, component patterns, states, motion and accessibility (IMD-118, which amends IMD-117). The values are applied through the theme tokens in `apps/web/app/globals.css`; components use the token names (`bg-primary`, `text-muted-foreground`, `bg-success-soft`), never raw colour values.

This guide decides look only. Where specification §7 states a rule (components, states, labels, accessibility), §7 wins. Changing a token or a pattern needs an update of this guide in the same pull request.

## 1. Principles

- **Calm and trustworthy.** Quiet surfaces, one accent colour, no decoration that competes with the plan.
- **One primary action per view.** Every other action is secondary or ghost.
- **Data first.** The itinerary, times and costs are the content; chrome stays out of the way.
- **Facts always carry their label.** Prices, hours, travel times and AI-written text show their label: Curated, Estimate, Unavailable or AI-written (§7.8).
- **Never show a placeholder value as a fact.** For example, a cost of 0.00 with `complete` false is shown as "Cost not available yet", never as a price.
- **§7 wins** where it states a rule.

## 2. Colour tokens

Light theme only; there is no theme toggle. The stylesheet stores each value in oklch; the hex value below is the source.

### Base tokens

| Token | Hex | Use |
| --- | --- | --- |
| `background` | #FAFAF9 | Page background |
| `foreground` | #1C1917 | Body text |
| `card`, `popover` | #FFFFFF | Cards, dialogs, menus |
| `card-foreground`, `popover-foreground` | #1C1917 | Text on cards and popovers |
| `muted` | #F5F5F4 | Quiet surfaces, segmented-control track, skeletons |
| `muted-foreground` | #57534E | Secondary text, descriptions, helper text |
| `border` | #E7E5E4 | Card and divider borders |
| `input` | #948E89 | Field borders (at least 3:1 on white) |
| `ring` | #0F766E | Focus ring |
| `primary` | #0F766E | Main action, links, current step |
| `primary-foreground` | #FFFFFF | Text on primary |
| `primary-hover` | #115E59 | Primary hover |
| `secondary` | #F0FDFA | Selected chips, soft primary surfaces |
| `secondary-foreground` | #134E4A | Text on secondary |
| `accent` | #F5F5F4 | Hover surface of ghost buttons and menu items |
| `accent-foreground` | #1C1917 | Text on accent |
| `destructive` | #B91C1C | Irreversible actions, error text |
| `destructive-foreground` | #FFFFFF | Text on destructive |

### Semantic soft pairs

Each pair is text (`<name>-foreground`, also available as `<name>`) on its soft background (`<name>-soft`).

| Name | Text | Background | Use |
| --- | --- | --- | --- |
| `success` | #15803D | #F0FDF4 | Curated label, success notices |
| `warning` | #B45309 | #FFFBEB | Estimate label, warnings |
| `info` | #1D4ED8 | #EFF6FF | Information notices |
| `ai` | #6D28D9 | #F5F3FF | AiBadge, AI-written text |

### Usage

- Primary only for the main action, links and the current step.
- Destructive only for irreversible actions (and error text).
- Semantic colours only for status and labels, never for decoration.

### Contrast (WCAG 2.1, checked for IMD-118)

| Pair | Ratio | Minimum |
| --- | --- | --- |
| foreground on background | 16.74:1 | 4.5 |
| muted-foreground on card | 7.63:1 | 4.5 |
| primary-foreground on primary | 5.47:1 | 4.5 |
| primary on card | 5.47:1 | 4.5 |
| destructive-foreground on destructive | 6.47:1 | 4.5 |
| input on card | 3.24:1 | 3.0 |
| success on success-soft | 4.79:1 | 4.5 |
| warning on warning-soft | 4.84:1 | 4.5 |
| info on info-soft | 6.16:1 | 4.5 |
| ai on ai-soft | 6.48:1 | 4.5 |

## 3. Typography

Inter, loaded with `next/font/google` (variable font, `display: swap`), with the system-ui stack as fallback.

| Style | Size / line height (px) | Weight |
| --- | --- | --- |
| Page title | 30/36 on desktop, 24/32 on phones | Semibold |
| Section title | 20/28 | Semibold |
| Card title | 16/24 | Semibold |
| Body | 16/24 | Regular |
| Small | 14/20 | Regular |
| Caption | 12/16 | Medium |

- All form inputs use 16 px text.
- Headings of 20 px and up use letter-spacing -0.01em.
- Times, durations, dates in tables and money use `tabular-nums`.
- Sentence case everywhere: titles, buttons, labels and menu items.

## 4. Spacing and layout

All spacing sits on a 4 px grid.

| Item | Phone (below 640) | From 640 | From 1024 |
| --- | --- | --- | --- |
| Page padding | 16 px | 24 px | 32 px |
| Section gap | 24 px | 24 px | 32 px |
| Card padding | 16 px | 24 px | 24 px |
| Field gap | 16 px | 16 px | 16 px |

| Content | Maximum width |
| --- | --- |
| Forms, the generate page and dialogs | 720 px |
| Itinerary and lists | 1120 px |
| Shell | 1200 px |

Breakpoints: phone below 640, tablet 640 to 1023, desktop 1024 and up. Day tabs are used below 768 px, as §7 states.

## 5. Shape and elevation

| Element | Radius |
| --- | --- |
| Cards and dialogs | 12 px |
| Buttons, inputs and chips' containers | 8 px |
| Chips and badges | Full (pill) |

- Cards: a 1 px border in the `border` colour plus a soft shadow, `0 1px 2px rgb(28 25 23 / 0.06)`.
- Popovers and dialogs: a larger soft shadow.
- No other shadows.

## 6. App shell

- Top bar: 64 px high on desktop and 56 px on phones, white, with a bottom border.
- Left: the brand "AI Travel Planner" with the lucide `Compass` icon in primary.
- Right: account actions.
- Content sits on the `background` colour.

## 7. Page header pattern

- Optional back link: a ghost button with the `ArrowLeft` icon.
- Page title.
- One muted line of description.
- Actions at the right on desktop, below the title on phones.

## 8. Buttons

- Height 40 px; at least 44 px on touch below 640.
- Variants: primary (filled), secondary (outline with the `input` border), ghost (tertiary), destructive.
- Icons are 16 px and sit before the label.
- Loading: a spinning `Loader2` replaces the icon, the label stays, the button sets `aria-busy` and is disabled.

## 9. Forms

- Label above the field: 14 px medium.
- Helper text below the field: 14 px muted.
- Error text below the field: 14 px destructive with a 16 px `AlertCircle` icon, linked to the field with `aria-describedby`.
- Required fields say "(required)" in the label.
- Fields are full width on phones.
- Related pairs (start and end date, adults and children, amount and currency) sit in two columns from 768 px.
- Native selects and textareas are styled exactly like inputs.

## 10. Chips and segmented controls

- **Chips** are pills 36 px high (44 px on touch), outlined in the `input` border.
- **Selected chips** use the secondary colours with a primary border and a `Check` icon, and set `aria-pressed`.
- **A segmented control** is a muted rounded track; the selected option is a white surface with the card shadow. It behaves as a radio group.

## 11. Stepper

- **Desktop:** numbered 28 px circles joined by a line, with labels. The current step is filled primary; finished steps are outlined primary with a `Check`; upcoming steps are muted.
- **Phones:** "Step 2 of 4 · <step name>" with a thin progress bar.

## 12. Badges and labels

Badges are rounded-full, 24 px high, in caption type.

| Badge | Look |
| --- | --- |
| SourceBadge, Curated | `success` soft pair |
| SourceBadge, Estimate | `warning` soft pair |
| SourceBadge, Unavailable | `muted` background with `muted-foreground` text |
| AiBadge | `ai` soft pair with a 12 px `Sparkles` icon and the text "AI-written" |
| Slot type | Outline, neutral |

The badge text comes from §7.8 ("Curated, checked on <date>", "Estimate", "Unavailable", "AI-written").

## 13. States

- **LoadingSkeleton** mirrors the shapes of the final layout. Never a full-page spinner.
- **EmptyState** is centred in a card: a 40 px muted icon circle, a 16 px semibold title, one muted line and one primary action.
- **ErrorState** is a destructive-soft alert with the message, "Request ID" in a 12 px monospace muted line, and a "Try again" button.
- **Inline alerts** use the semantic soft pairs with a leading icon.

## 14. Itinerary pattern

- **Day card header:** an overline "Day 1" (12 px, uppercase, wide tracking, muted), the date as the section title ("Sat 14 Nov"), and the theme in muted text with an AiBadge when it is AI-written.
- **Items as a vertical timeline:** a 56 px time column on the left (tabular, "09:30"), a thin vertical rule, and an item card on the right with the place name (16 px semibold) and a meta row (duration "1 h 30 min" · slot badge).

## 15. Motion

- 150 ms for colour and opacity; 200 ms for size and position; ease-out.
- Respect `prefers-reduced-motion` by removing non-essential animation.

## 16. Accessibility

- WCAG 2.1 AA contrast for text, and 3:1 for component boundaries.
- Visible focus on every interactive element: a 2 px ring in the `ring` colour with a 2 px offset, on `focus-visible` only.
- Targets at least 44 px on touch.
- One `h1` per page, and headings in order.
- Progress and errors are announced: `aria-live="polite"` for progress, assertive only for blocking errors.
- Never use colour alone to carry meaning; pair it with text or an icon.

## 17. Content

- Short, plain sentences.
- Dates as "Sat 14 Nov"; times in 24-hour form, "09:30"; durations as "1 h 30 min".
- Currency with its code or symbol.
- No exclamation marks.
- No placeholder or sample text in production code.
