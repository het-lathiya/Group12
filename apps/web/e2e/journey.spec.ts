import path from "node:path";

import type { Locator, Page, Response } from "@playwright/test";

import type { components } from "../lib/api/schema";
import { checkA11y } from "./axe";
import { expect, test } from "./fixtures/trips";
import { randomPassword, stagingAccount, uniqueEmail } from "./fixtures/users";

// TC-372 (IMP-701): the same journey is the floor journey, run by the floor-journey project when
// FEATURES_DISABLED and NEXT_PUBLIC_FEATURES_DISABLED list the nine cut-list switches; TC-373 is
// its chromium-360 run.
// TC-369 (US-153 AC1, IMP-414): sign up, create a trip with the wizard, generate, remove one item
// and retime another, reload, open latest, and see the edits and the server totals persist. Local:
// the local stack, `make seed` (Sampleton) and the API with AI_PROVIDER=MOCK. TC-370: the same spec
// against BASE_URL=<staging> with E2E_STAGING_EMAIL and E2E_STAGING_PASSWORD set.
// TC-374, TC-279, TC-383 (IMP-513): every control of the journey is activated from the keyboard
// (Enter on a focused control, typing into native fields), the skip link and the focus moves are
// checked, a move to another day is made by keyboard and announced, and axe scans each core page.

// Staging signs in with its pre-created account instead of signing up, and may run Gemini, which
// needs a longer wait for completed; the provider is a property of staging, not of the test.
const STAGING = stagingAccount();
const GENERATION_TIMEOUT_MS = STAGING ? 180_000 : 30_000;

// UPDATE_SCREENSHOTS=1 refreshes the evidence screenshots of the IMP-309 day-view part record.
const SCREENSHOT_DIR = path.resolve(
  __dirname,
  "../../../docs/progress/parts/IMP-309-day-view-screens",
);

type Day = components["schemas"]["Day"];
type Itinerary = components["schemas"]["ItineraryOut"];
type EditResult = components["schemas"]["EditResultOut"];

/** A date from today, so the nightly e2e run never reaches a fixed date. */
const daysFromNow = (days: number) =>
  new Date(Date.now() + days * 86_400_000).toISOString().slice(0, 10);

/**
 * TC-383: axe on the page as it is now. checkA11y fails on critical violations and records serious
 * ones as an "axe-serious" annotation; IMP-513 step 5 fails on serious ones too.
 */
async function scan(page: Page) {
  const before = test.info().annotations.length;
  await checkA11y(page);
  expect(
    test
      .info()
      .annotations.slice(before)
      .filter((annotation) => annotation.type === "axe-serious")
      .map((annotation) => annotation.description),
    "serious axe violations (TC-383)",
  ).toEqual([]);
}

const stepHeading = (page: Page, name: string) =>
  page.getByRole("heading", { level: 2, name });

/** The day's column; below 768 px the days are tabs, so its tab is opened first. */
async function openDay(page: Page, dayNumber: number) {
  if ((page.viewportSize()?.width ?? 0) < 768) {
    await page.getByRole("tab", { name: `Day ${dayNumber}` }).click();
  }
  return page.getByRole("region", { name: `Day ${dayNumber}` });
}

const isItineraryRead = (tripId: string) => (r: Response) =>
  new URL(r.url()).pathname === `/api/v1/trips/${tripId}/itinerary` &&
  r.request().method() === "GET" &&
  r.ok();

/** Every day's places and start times, in API-24's order. */
async function expectSavedDays(page: Page, days: Day[]) {
  for (const day of days) {
    const column = await openDay(page, day.day_number);
    await expect(column.getByRole("heading", { level: 3 })).toHaveText(
      day.items.map((item) => item.place.name),
    );
    await expect(column.locator("time")).toHaveText(
      day.items.map((item) => item.start_time),
    );
  }
}

test(
  "TC-369 TC-370 TC-372 TC-373 TC-374: journey: sign up, create a trip, generate, edit, reload and open latest",
  { tag: "@journey" },
  async ({ page, users, trips }) => {
    test.setTimeout(GENERATION_TIMEOUT_MS + 90_000);
    const hosts = new Set<string>();
    page.on("request", (request) => hosts.add(new URL(request.url()).hostname));

    // The dashboard's first API call carries the token the trip reset uses.
    const apiCall = page.waitForRequest(
      (r) => r.url().includes("/api/v1/") && !!r.headers()["authorization"],
    );
    if (STAGING) {
      await page.goto("/sign-in?next=%2Fdashboard");
      await page.getByLabel("Email").fill(STAGING.email);
      await scan(page);
      await page.getByLabel("Password", { exact: true }).fill(STAGING.password);
      await page
        .getByRole("button", { name: "Sign in", exact: true })
        .press("Enter");
    } else {
      const email = uniqueEmail("journey");
      users.track(email);
      await page.goto("/sign-up");
      await page.getByLabel("Email").fill(email);
      await scan(page);
      await page.getByLabel("Password", { exact: true }).fill(randomPassword());
      await page.getByRole("button", { name: "Create account" }).press("Enter");
    }
    await expect(
      page.getByRole("heading", { level: 1, name: "Your trips" }),
    ).toBeVisible();
    await scan(page);
    trips.useSessionOf(await apiCall);
    // Reset: the account starts with no trips (a new local account has none).
    await trips.deleteAll();

    // Wizard step 1: details.
    await page.goto("/trips/new");
    await expect(
      page.getByRole("heading", { level: 1, name: "Plan a new trip" }),
    ).toBeVisible();
    await page
      .getByLabel("Destination")
      .selectOption({ label: "Sampleton (sample)" });
    await page.getByLabel("Trip title").fill("Journey in Sampleton");
    await page.getByLabel("Start date").fill(daysFromNow(30));
    await page.getByLabel("End date").fill(daysFromNow(32));
    await page.getByLabel("Adults").fill("2");
    await scan(page);
    const created = page.waitForResponse(
      (r) =>
        r.url().endsWith("/api/v1/trips") && r.request().method() === "POST",
    );
    await page
      .getByRole("button", { name: "Next", exact: true })
      .press("Enter");
    expect((await created).status()).toBe(201);
    const tripId = (await (await created).json()).id as string;

    // Steps 2 to 4: preferences, must-visit places (none chosen), review.
    await expect(stepHeading(page, "Your preferences")).toBeFocused();
    await scan(page);
    await page.getByRole("button", { name: "Museums" }).press("Enter");
    await page
      .getByRole("button", { name: "Next", exact: true })
      .press("Enter");
    await expect(stepHeading(page, "Must-visit places")).toBeFocused();
    await scan(page);
    await page
      .getByRole("button", { name: "Next", exact: true })
      .press("Enter");
    await expect(stepHeading(page, "Review your trip")).toBeFocused();
    await scan(page);
    await page.getByRole("link", { name: "Generate itinerary" }).press("Enter");
    await expect(page).toHaveURL(`/trips/${tripId}/generate`);

    // Generate: API-22, then API-23 until completed, then the itinerary page reads API-24.
    const startedAt = Date.now();
    const completed = page.waitForResponse(
      async (r) => {
        const isStatus =
          /\/api\/v1\/generations\/[^/]+$/.test(new URL(r.url()).pathname) &&
          r.request().method() === "GET" &&
          r.ok();
        return isStatus && (await r.json()).status === "completed";
      },
      { timeout: GENERATION_TIMEOUT_MS },
    );
    const firstRead = page.waitForResponse(isItineraryRead(tripId), {
      timeout: GENERATION_TIMEOUT_MS,
    });
    // An account's first generation shows the notice (API-04) before API-22; a staging account
    // that has seen it before goes straight on.
    const notice = page.getByRole("button", { name: "I understand, continue" });
    if (STAGING) {
      const yourItinerary = page.getByRole("heading", {
        level: 1,
        name: "Your itinerary",
      });
      await expect(notice.or(yourItinerary)).toBeVisible({
        timeout: GENERATION_TIMEOUT_MS,
      });
      if (await notice.isVisible()) await notice.press("Enter");
    } else {
      await expect(
        page.getByRole("heading", {
          level: 2,
          name: "Before your first AI-written plan",
        }),
      ).toBeFocused();
      await scan(page);
      await notice.press("Enter");
    }

    const generation = await (await completed).json();
    // Printed for the test report (docs/test-reports/journey-sprint4.md).
    const summary = `provider ${generation.provider}, outcome ${generation.outcome}, ${Date.now() - startedAt} ms to completed`;
    test.info().annotations.push({ type: "generation", description: summary });
    console.log(`generation: ${summary}`);
    if (!STAGING) {
      expect(generation.provider).toBe("MOCK");
      // PD-RUN-069-1: the MOCK proposal fits the curated hours, so nothing is repaired.
      expect(generation.outcome).toBe("model");
      expect(generation.deterministic_repairs).toBe(0);
      expect(generation.repair_attempts).toBeLessThanOrEqual(1);
    }

    await expect(page).toHaveURL(`/trips/${tripId}/itinerary`);
    const saved = (await (await firstRead).json()) as Itinerary;
    const days = saved.days;
    expect(
      saved.findings.filter((finding) =>
        [
          "UNKNOWN_PLACE",
          "OUTSIDE_TRIP_DATES",
          "OVERLAP",
          "CLOSED_ON_DAY",
        ].includes(finding.code),
      ),
    ).toEqual([]);
    expect(days.flatMap((day) => day.items).length).toBeGreaterThan(0);
    await expectSavedDays(page, days);
    await scan(page);

    // Edit: remove the day's first item (API-27, after the confirm dialog) and retime its last
    // (API-26). Each answer carries the server's recalculated totals.
    const day = days.find((d) => d.items.length >= 2);
    expect(day, "a day with two items to edit").toBeDefined();
    const { day_number: dayNumber, items } = day!;
    const removed = items[0];
    const retimed = items[items.length - 1];
    let column = await openDay(page, dayNumber);
    const goneHeading = (where: Locator) =>
      where.getByRole("heading", {
        level: 3,
        name: removed.place.name,
        exact: true,
      });

    await column
      .getByRole("button", { name: `Remove ${removed.place.name}` })
      .press("Enter");
    const dialog = page.getByRole("dialog", {
      name: `Remove ${removed.place.name} from day ${dayNumber}?`,
    });
    const removal = page.waitForResponse(
      (r) =>
        new URL(r.url()).pathname === `/api/v1/itinerary/items/${removed.id}` &&
        r.request().method() === "DELETE",
    );
    await dialog.getByRole("button", { name: "Remove" }).press("Enter");
    expect((await removal).status()).toBe(200);
    await expect(page.getByText(`Removed ${removed.place.name}`)).toBeVisible();
    // Focus moves to the next card of the day (IMP-408).
    await expect(page.locator(`[id="item-${items[1].id}"]`)).toBeFocused();
    await expect(goneHeading(column)).toHaveCount(0);

    const newDuration =
      retimed.duration_min + 15 <= 480
        ? retimed.duration_min + 15
        : retimed.duration_min - 15;
    await column
      .getByRole("button", { name: `Edit time of ${retimed.place.name}` })
      .press("Enter");
    const form = column.getByRole("form", {
      name: `Edit time of ${retimed.place.name}`,
    });
    await form.getByLabel("Duration (minutes)").fill(String(newDuration));
    const retime = page.waitForResponse(
      (r) =>
        new URL(r.url()).pathname === `/api/v1/itinerary/items/${retimed.id}` &&
        r.request().method() === "PATCH",
    );
    await form.getByRole("button", { name: "Save" }).press("Enter");
    expect((await retime).status()).toBe(200);
    const edited = (await (await retime).json()) as EditResult;
    await expect(form).toBeHidden();

    /** API-24 shows both edits and the totals and revision of the last edit's answer. */
    const expectEditsSaved = (itinerary: Itinerary) => {
      const all = itinerary.days.flatMap((d) => d.items);
      expect(all.map((item) => item.id)).not.toContain(removed.id);
      expect(all.find((item) => item.id === retimed.id)?.duration_min).toBe(
        newDuration,
      );
      expect(itinerary.plan_revision).toBe(edited.plan_revision);
      expect(itinerary.totals).toEqual(edited.totals);
    };

    // Reload: the edits are saved, not held by the page.
    const reread = page.waitForResponse(isItineraryRead(tripId));
    await page.reload();
    const afterReload = (await (await reread).json()) as Itinerary;
    expectEditsSaved(afterReload);
    await expectSavedDays(page, afterReload.days);

    // Open latest (API-09, IMP-410) reopens the same saved plan.
    await page.goto("/dashboard");
    await expect(
      page.getByRole("heading", { level: 1, name: "Your trips" }),
    ).toBeVisible();
    // TC-279: on a fresh page the first Tab reaches the skip link, which moves focus to the main
    // content.
    await page.keyboard.press("Tab");
    const skip = page.getByRole("link", { name: "Skip to content" });
    await expect(skip).toBeFocused();
    await expect(skip).toBeInViewport();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("main")).toBeFocused();
    // Open latest stays disabled until API-09 answers, and press() does not wait for enabled.
    const openLatest = page.getByRole("button", { name: "Open latest" });
    await expect(openLatest).toBeEnabled();
    const latestRead = page.waitForResponse(isItineraryRead(tripId));
    await openLatest.press("Enter");
    await expect(page).toHaveURL(`/trips/${tripId}/itinerary`);
    const latest = (await (await latestRead).json()) as Itinerary;
    expectEditsSaved(latest);
    await expectSavedDays(page, latest.days);
    column = await openDay(page, dayNumber);
    await expect(goneHeading(column)).toHaveCount(0);

    // TC-374, TC-280: move an item to another day by keyboard. The move is announced in the polite
    // live region; focus stays on the item's controls in its new day, or below 768 px (day tabs)
    // goes to the new day's tab, which opens it.
    const from = latest.days.find((d) => d.items.length > 0)!;
    const to = latest.days.find((d) => d.day_number !== from.day_number);
    expect(to, "a second day to move to").toBeDefined();
    const mover = from.items[from.items.length - 1];
    column = await openDay(page, from.day_number);
    const daySelect = column.getByLabel(`Day to move ${mover.place.name} to`);
    // selectOption does not focus the select; a keyboard user is on it, so Tab reaches Move.
    await daySelect.focus();
    await daySelect.selectOption(String(to!.day_number));
    const moveButton = column.getByRole("button", {
      name: `Move ${mover.place.name} to day ${to!.day_number}`,
    });
    await page.keyboard.press("Tab");
    await expect(moveButton).toBeFocused();
    const moved = page.waitForResponse(
      (r) =>
        new URL(r.url()).pathname === `/api/v1/itinerary/items/${mover.id}` &&
        r.request().method() === "PATCH",
    );
    await page.keyboard.press("Enter");
    expect((await moved).status()).toBe(200);
    await expect(
      page.getByRole("status").filter({
        hasText: `Moved ${mover.place.name} to day ${to!.day_number} position`,
      }),
    ).toHaveAttribute("aria-live", "polite");
    if ((page.viewportSize()?.width ?? 0) < 768) {
      const dayTab = page.getByRole("tab", { name: `Day ${to!.day_number}` });
      await expect(dayTab).toBeFocused();
      await expect(dayTab).toHaveAttribute("aria-selected", "true");
    } else {
      await expect(
        page
          .getByRole("region", { name: `Day ${to!.day_number}` })
          .locator(`[data-move-for="${mover.id}"] [data-action="day"]`),
      ).toBeFocused();
    }
    await expect(
      page
        .getByRole("region", { name: `Day ${to!.day_number}` })
        .getByRole("heading", {
          level: 3,
          name: mover.place.name,
          exact: true,
        }),
    ).toBeVisible();
    await scan(page);

    // IMP-309: no horizontal scroll at the card's widths, and the evidence screenshots.
    for (const width of [375, 1280]) {
      await page.setViewportSize({ width, height: 900 });
      await expect(
        page.getByRole("heading", { level: 3 }).first(),
      ).toBeVisible();
      expect(
        await page.evaluate(
          () =>
            document.documentElement.scrollWidth <=
            document.documentElement.clientWidth,
        ),
      ).toBe(true);
      if (process.env.UPDATE_SCREENSHOTS === "1") {
        await page.screenshot({
          path: path.join(SCREENSHOT_DIR, `itinerary-${width}.png`),
          fullPage: true,
        });
      }
    }

    // Costs: the last core page, reached from the main navigation by keyboard.
    await page
      .getByRole("navigation", { name: "Main" })
      .getByRole("link", { name: "Costs" })
      .press("Enter");
    await expect(page).toHaveURL(`/trips/${tripId}/costs`);
    await expect(
      page.getByRole("heading", { level: 1, name: "Trip costs" }),
    ).toBeVisible();
    await scan(page);

    expect(
      [...hosts].filter((host) => host.includes("generativelanguage")),
    ).toEqual([]);
  },
);
