# User guide

| Field | Value |
| --- | --- |
| Document | User guide for travellers (IMP-707, user-guide part; US-146) |
| Owner | Jeel |
| Version | 0.1, draft of 19 November 2026 |
| Based on | `main` at `f75aa94`: the screens in `apps/web` and the API rules in `apps/api` |
| Status | Written from the code. It has not yet been followed by a new member, and no screenshots are in it yet (card step 6) |

This guide explains how to plan a trip with the AI Travel Planner: create an account, describe a trip, generate a day-by-day itinerary, change it, and read its costs and labels. It describes only what the built app does. Places marked "Screenshot to be added by Jeel" are for the team's screenshots (card step 3).

## 1. What the app does and does not do

- You describe a trip: destination, dates, group, optional budget, preferences and up to 10 must-visit places. The app builds a day-by-day plan with start times, travel time between stops and estimated costs.
- An AI model (Gemini) proposes which places to visit, in what order and at what times, choosing only from a shortlist of curated places for the destination. The app then checks every place and works out every time, travel gap and price itself. If the AI service fails, or its answer fails these checks, a rule-based planner builds the plan instead, and the plan says so.
- You can move, add, remove, retime, lock and replace stops. After every change the app works out the times, costs and checks for the day again.
- The app does **not** book flights, hotels or tickets, take payments or show live prices (IMD-46). Prices, opening hours and travel times are estimates or curated values, and each one is labelled (section 9).

The landing page says this too: "Plans are drafts built from curated sample data. Prices, opening hours and travel times are estimates and are labelled as such; check them before you travel."

> Screenshot to be added by Jeel: landing page

## 2. Create an account and sign in

1. On the landing page, choose **Create an account**.
2. Enter your **Email** and a **Password** of at least 8 characters, then choose **Create account**.
3. If the app shows "Check your email to finish creating your account. If you already have an account, try signing in instead.", open the confirmation email and follow its link. The link brings you back to the app, signed in, on your trips page. The message is the same whether or not the address already has an account.
4. Next time, choose **Sign in** and enter your email and password. A wrong email or password shows "Email or password is incorrect." Too many attempts show "Too many attempts. Try again later."

To sign out, open the **Account menu** (the person icon in the header) and choose **Sign out**.

> Screenshot to be added by Jeel: sign-up form
>
> Screenshot to be added by Jeel: sign-in form

## 3. Your trips (dashboard)

After signing in you see **Your trips**. From here:

- **New trip** starts the trip wizard (section 4).
- **Open latest** opens your newest saved itinerary.
- Each trip card shows its status (**Draft**, **Ready** or **Archived**) and one main action:
  - **Continue draft** reopens an unfinished trip at its first incomplete step;
  - **Generate plan** opens the generate page of a trip that has no plan yet;
  - **Open itinerary** opens the trip's plan.
- The **Actions for <trip>** menu offers **Rename**, **Duplicate**, **Archive** (or **Restore** for an archived trip) and **Delete**.
  - An archived trip is read-only until you restore it, and it is hidden unless you choose **Show archived**.
  - A deleted trip disappears from your trips. The confirmation says it is kept for 30 days and then removed for good.

The navigation (in the header from 768 px wide, as a bottom bar on narrower screens) has **Trips**, **Itinerary**, **Costs**, **Explore**, **Summary**, **Versions** and **Profile**. The trip entries work once a trip is open.

> Screenshot to be added by Jeel: dashboard with trip cards

## 4. Create a trip

Choose **New trip**. The wizard has four steps: **Details**, **Preferences**, **Must-visit places** and **Review**. Each step is saved when you choose **Next**, and the header shows "Saving…", "Draft saved" or "Not saved". If you leave, the trip stays as a **Draft** on your trips page and **Continue draft** brings you back.

### 4.1 Details

| Field | Rule |
| --- | --- |
| Destination | Choose one of the listed destinations (section 11) |
| Trip title | 1 to 120 characters |
| Start date, End date | The end date is on or after the start date; a trip is 1 to 14 days long |
| Adults | 1 to 20 |
| Children | 0 to 20 |
| Group needs | Any of Children, Older adults, Reduced mobility |
| Budget (optional) | Total for the whole group, greater than 0 with at most 2 decimal places. Leave it empty for no budget |
| Currency | The currency of the destination; the app does not convert currencies (IMD-128) |

Once **Next** has saved the details, the step shows "These details are saved with your trip and cannot be changed here."

> Screenshot to be added by Jeel: trip wizard, Details step

### 4.2 Preferences

- **Interests:** Sights, Museums, Nature, Food, Shopping, Entertainment, Religious sites, Activities.
- **Pace:** Relaxed, Balanced or Busy. Pace sets how many stops fit into each day.
- **Budget priority:** Saving, Balanced or Comfort.
- **Getting around:** Walking, Local transport or Car.
- **Accommodation type:** Budget, Mid-range, Premium or No preference.
- **I need step-free access.**
- **Notes:** up to 1,000 characters. Do not enter personal details: notes are sent to the AI service (section 5).

New trips start from the defaults saved on your **Profile**. Some fields show a badge for what they do in planning: **Filters**, **Ranks** or **Note only**.

### 4.3 Must-visit places

Search by name, then choose a place to add it. You can add up to 10 places. Remove one with the cross on its chip.

### 4.4 Review

The review lists the trip details, preferences and must-visit places, each with an edit button that takes you back to that step. Below it, **Transport and stay budget** asks for your own figures:

- **Transport per day** and **Stay per night**: your own amounts, shown as **Traveller input** in the costs. Without them, these lines show **Unavailable** in the costs.
- **Contingency buffer (%)**: 0 to 50, added to the high estimate as its own line.

Choose **Save budget inputs**, then **Generate itinerary**.

> Screenshot to be added by Jeel: trip wizard, Review step with the budget inputs

## 5. Generate the itinerary

1. On the generate page, before your first AI-written plan, a notice explains that your trip details, preferences and notes are sent to Google's Gemini API, and that your name and email address are not sent. Choose **I understand, continue**. This is asked once per account.
2. Choose **Generate with AI**. The page shows the steps **Queued**, **Running**, **Validating** and, when needed, **Repairing**, with the elapsed time.
3. When the plan is ready, the page says "Plan ready. Opening your itinerary." and opens it.

What can happen instead:

| You see | What it means and what to do |
| --- | --- |
| "Built by rules because the AI service was unavailable or its answer failed checks" above the plan | The AI service failed or its answer did not pass the checks, so the rule-based planner built the plan. It is a normal, usable plan; it has no AI-written notes |
| "Some details were adjusted" above the plan | The AI answer needed a repair before it passed the checks |
| "Today's AI planning limit is reached" with **Build a rule-based plan** | The daily AI limit is used up (10 AI plans per account per UTC day in the staging configuration, plus a limit for all users). The page shows when the limit resets (UTC). **Build a rule-based plan** builds a plan now without the AI |
| "The plan could not be built" | The generation failed. The message names the next step (for example a retry or a rule-based plan) and a reference |
| "An itinerary is still being generated" | A generation for this trip is already running; the page follows it |
| A reload offer after about 160 seconds | The page stopped waiting. Reload to check again |

A trip has one plan. To build it again, use **Regenerate all** on the itinerary page (section 7.6), not the generate page.

> Screenshot to be added by Jeel: privacy notice before the first plan
>
> Screenshot to be added by Jeel: generation progress

## 6. Read the itinerary

**Your itinerary** shows one section per day, headed "Day N" and the date. A day may have a short theme; if the AI wrote it, it carries the **AI-written** badge. On a narrow screen each day is a tab, and a **List** or **Map** switch shows the stops as a list or on a map. From 768 px the map of the selected day and the plan checks appear above the plan, and from 1280 px they sit beside it. The list always has the same stops and times as the map.

Each stop shows:

- the travel from the previous stop: minutes, mode (Walking, Local transport or Car) and how the time was found: "Estimated travel time from a routing service" or "Estimated travel time (distance based)";
- the start time, the place name, start and end time, duration and the kind of stop (**Activity**, **Meal** or **Rest**);
- the cost with its label (section 9), or **Unavailable** when there is no price;
- **Hours** with the label of the opening hours;
- a short note, if any. A note written by the AI starts with the **AI-written** badge and may have a **Sources (n)** button. It lists the guide passages or place records the note was based on: title, "Guide" or "Place record", source name, licence or attribution, retrieval date and a link when there is one.

**Plan checks** lists the plan's findings by severity (**Errors**, **Warnings**, **Infos**), then by day or "Whole trip". **Go to item** moves to the stop concerned. With no findings it shows "No issues found".

If the trip's settings changed after the plan was built, a banner says "Trip settings changed after this plan was built. This plan is out of date."

> Screenshot to be added by Jeel: itinerary page, desktop
>
> Screenshot to be added by Jeel: itinerary page at phone width with the List and Map switch
>
> Screenshot to be added by Jeel: an AI-written note with its sources open

## 7. Change the itinerary

Every change is saved at once, and the times, costs and checks of the affected days are worked out again by the app. If the plan was changed somewhere else in the meantime (for example in another tab), the app says "This plan changed since you opened it" and shows the current plan.

### 7.1 Change a time

Choose **Edit** on a stop, change **Start time** (HH:MM, for example 09:30) or **Duration (minutes)**, then **Save**.

### 7.2 Remove a stop

Choose **Remove** and confirm. A message "Removed <place>" offers **Undo**.

### 7.3 Add a place

Choose **Add a place**, pick the **Day**, search by place name, then choose a result. A message "Added <place>" offers **Undo**.

### 7.4 Move a stop

- **Up** and **Down** move a stop within its day.
- Pick another day in the list next to them and choose **Move** to move the stop to that day.
- You can also drag a stop by its grip ("Drag <place> to reorder"). Every drag has a button alternative, so a keyboard or a single tap is enough.

### 7.5 Lock or replace a stop

- **Lock** keeps a stop in place when you regenerate; the button then reads **Locked**. Choose it again to unlock.
- **Replace** (on unlocked stops) opens "Alternatives for <place>": ranked alternatives for the same slot. Choose one to apply it; the day is checked again. If nothing fits, it says "No alternative fits this slot".

### 7.6 Regenerate

- **Regenerate day N** rebuilds one day.
- **Regenerate all** rebuilds the whole plan after a confirmation. Unlocked items are rebuilt around your locked items, and your current plan is kept in **Versions** (or as a backup when Versions is switched off).

Regeneration counts against the daily AI limit (section 5). When the limit is reached, **Build a rule-based plan** is offered.

> Screenshot to be added by Jeel: a stop with its edit, move, lock and replace controls

## 8. Costs

Open **Costs** in the trip navigation (**Trip costs**).

- **Planning total**, **Estimate range** (low to high) and **About per traveller** always carry the **Estimate** label. "Cost not available yet" appears while no cost can be worked out.
- **Contingency (n %)** shows the buffer you set.
- When some costs are missing, it says "Some costs are unavailable or estimated. Treat this total as incomplete." and how many items have unavailable costs.
- **Your budget** shows your total budget as **Traveller input**. Without a budget it says "Set an allowance to see the remaining budget."
- **Over budget** or **Near budget** banners appear when the plan's estimate is over or close to your budget.
- **Daily cost estimates** (Day, Low, High, Contingency share, Label) and a table by category (Activities, Food, Transport, Accommodation, Other, Contingency) break the total down.
- **Your allowances** is the same transport, stay and contingency form as in the wizard (section 4.4).

All amounts come from the server; the page adds nothing up itself.

> Screenshot to be added by Jeel: costs page

## 9. Labels

| Label | Where | Meaning |
| --- | --- | --- |
| **Estimate** | Prices, hours, every total | A calculated or estimated value. Check it before you travel |
| **Curated** | Prices, hours | A value the team collected and checked for this place. Prices show no date. In the place details (Explore), curated hours show "Curated, checked on <date>" |
| **Unavailable** | Prices, hours, budget lines | No value is known. The app never shows a guessed number instead |
| **Traveller input** | Budget, transport per day, stay per night | Your own figure |
| **AI-written** | Day themes, stop notes | Text written by the AI model |
| "Estimated travel time from a routing service" / "Estimated travel time (distance based)" | Travel between stops | Travel times are always estimates: from the routing service, or from straight-line distance when it is not available |
| "Built by rules because the AI service was unavailable or its answer failed checks" | Above the plan | The plan was built by the rule-based planner, not the AI |

Nothing in the app claims that a price, opening time or route is live or verified.

## 10. Other pages

- **Explore** lists the destination's places with filters: search by name or tag, maximum price, maximum duration, category, interests and "Step-free only". **Details of <place>** shows its hours, price, verification, location and source, each with its label. **Save** adds a place to your saved places.
- **Summary** shows the whole trip on one page. **Print** prints it, one day per page after the first, without the app navigation.
- **Versions** lists saved versions of the plan (automatic ones, such as "Generated plan", "Before regeneration" and "After an edit", and named ones). Enter a **Version name** and choose **Save version** to keep the current plan. **Restore** makes an older version the current plan; the current plan is kept in the history, and costs, travel times and warnings are worked out again.
- **Profile** holds your display name, home currency, home country and the default preferences for new trips.

> Screenshot to be added by Jeel: explore page with the place details open
>
> Screenshot to be added by Jeel: summary page
>
> Screenshot to be added by Jeel: versions page

## 11. Known limits

- **Curated destinations only.** You can plan only for destinations the team has curated and loaded. At this version that is Ahmedabad (`data/places/ahmedabad`), which the staging configuration loads. A second demo destination is waiting for the members' curated files (IMP-603, IMD-201). The SAMPLE test destination "Sampleton" exists only in local and test set-ups and is marked "SAMPLE destination: its places and prices are synthetic test data."
- **Places come from the shortlist.** The AI cannot add places that are not in the curated data. You can add only curated places yourself.
- **Estimates, not live data.** Prices, opening hours and travel times are curated or estimated values with labels, never live. There is no booking, payment or live price (IMD-46).
- **One currency.** The budget is in the destination's currency, with no conversion (IMD-128).
- **Trip size.** 1 to 14 days, 1 to 20 adults, 0 to 20 children, up to 10 must-visit places, notes up to 1,000 characters.
- **Daily AI limit.** 10 AI generations per account per UTC day in the staging configuration, plus a limit for all users together. The rule-based plan is always offered instead.
- **Privacy.** Trip details, preferences and notes are sent to Google's Gemini API; your name and email address are not.
- **Deleting your account.** There is no delete-account button. An operator deletes the account on request (deployment guide, section 9).
- **Switched-off features.** A deployment can switch off Versions, trip actions, contingency, budget alerts, saved places, Replace, regeneration, locks and meal slots. A switched-off feature's buttons and pages are hidden.
- **Cut extensions.** Natural-language trip entry, day explanations, route optimisation, weather swaps, a today view, budget fitting, context cards and packing lists are not built (IMD-65).

## 12. Differences between the specification and the built app

Found while writing this guide from the code at `f75aa94`. None was checked in a running app in this run.

1. **Trip settings after creation.** The page `/trips/<id>/edit` reopens the wizard for a saved trip, but no screen links to it. In the normal flow, saved trip details "cannot be changed here", so the out-of-date banner (section 6) mostly follows a change made through that address.
2. **Regenerate from the out-of-date banner.** The banner's **Regenerate** button opens the generate page. For a trip that already has a plan, the API refuses a new generation there with "This trip already has an itinerary. Regenerate it instead." (`apps/api/app/generation/service.py`). **Regenerate all** on the itinerary page works.
3. **SAMPLE banner.** Specification §7.8 names a SampleBanner "SAMPLE data, not a real destination". The built app shows a SAMPLE hint under the destination field in the wizard and a sample notice on Explore, and no banner on the itinerary page.
4. **Itinerary header.** The §7.9 wireframe shows the estimated total and budget percentage in the itinerary header and a day-tab row on desktop. The built page shows **Your itinerary** with **Regenerate all**; the totals are on **Costs**, and day tabs appear only below 768 px.
5. **Two-pane breakpoint.** Specification §7.9 puts the itinerary in two panes from 1024 px. The built page uses the `xl` breakpoint (1280 px) for two panes; from 768 to 1279 px the map and plan checks sit above the plan.
6. **Curated hours on the itinerary.** The item card shows "Hours" with the label only. The "checked on <date>" form of §7.8 appears in the place details on Explore.
