import path from "node:path";

import type { Page } from "@playwright/test";

import type { components } from "../lib/api/schema";
import { expect, test } from "./fixtures/users";

// TC-369 (US-153 AC1): the walking skeleton from the browser. Sign in, create a trip with the
// wizard, generate with MOCK and see the saved itinerary that API-24 returns. Needs the local
// stack, `make seed` (Sampleton) and the API with AI_PROVIDER=MOCK.

// UPDATE_SCREENSHOTS=1 refreshes the evidence screenshots of the IMP-309 day-view part record.
const SCREENSHOT_DIR = path.resolve(
  __dirname,
  "../../../docs/progress/parts/IMP-309-day-view-screens",
);

type Day = components["schemas"]["Day"];

/** A date from today, so the nightly e2e run never reaches a fixed date. */
const daysFromNow = (days: number) =>
  new Date(Date.now() + days * 86_400_000).toISOString().slice(0, 10);

const stepHeading = (page: Page, name: string) =>
  page.getByRole("heading", { level: 2, name });

/** Every day's places and start times, in API-24's order. Below 768 px the days are tabs. */
async function expectSavedDays(page: Page, days: Day[]) {
  const dayTabs = (page.viewportSize()?.width ?? 0) < 768;
  for (const day of days) {
    if (dayTabs) {
      await page.getByRole("tab", { name: `Day ${day.day_number}` }).click();
    }
    const column = page.getByRole("region", { name: `Day ${day.day_number}` });
    await expect(column.getByRole("heading", { level: 3 })).toHaveText(
      day.items.map((item) => item.place.name),
    );
    await expect(column.locator("time")).toHaveText(
      day.items.map((item) => item.start_time),
    );
  }
}

test(
  "journey: sign in, create a trip, generate with MOCK and see the saved itinerary (TC-369)",
  { tag: "@journey" },
  async ({ page, users }) => {
    const hosts = new Set<string>();
    page.on("request", (request) => hosts.add(new URL(request.url()).hostname));

    const user = await users.create("journey");
    await page.goto("/sign-in?next=%2Ftrips%2Fnew");
    await page.getByLabel("Email").fill(user.email);
    await page.getByLabel("Password", { exact: true }).fill(user.password);
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await expect(
      page.getByRole("heading", { level: 1, name: "Plan a new trip" }),
    ).toBeVisible();

    // Wizard step 1: details.
    await page
      .getByLabel("Destination")
      .selectOption({ label: "Sampleton (sample)" });
    await page.getByLabel("Trip title").fill("Journey in Sampleton");
    await page.getByLabel("Start date").fill(daysFromNow(30));
    await page.getByLabel("End date").fill(daysFromNow(32));
    await page.getByLabel("Adults").fill("2");
    const created = page.waitForResponse(
      (r) =>
        r.url().endsWith("/api/v1/trips") && r.request().method() === "POST",
    );
    await page.getByRole("button", { name: "Next", exact: true }).click();
    expect((await created).status()).toBe(201);
    const tripId = (await (await created).json()).id as string;

    // Steps 2 to 4: preferences, must-visit places (none chosen), review.
    await expect(stepHeading(page, "Your preferences")).toBeFocused();
    await page.getByRole("button", { name: "Museums" }).click();
    await page.getByRole("button", { name: "Next", exact: true }).click();
    await expect(stepHeading(page, "Must-visit places")).toBeFocused();
    await page.getByRole("button", { name: "Next", exact: true }).click();
    await expect(stepHeading(page, "Review your trip")).toBeFocused();
    await page.getByRole("link", { name: "Generate itinerary" }).click();
    await expect(page).toHaveURL(`/trips/${tripId}/generate`);

    // Generate: API-22, then API-23 until completed, then the itinerary page reads API-24.
    const completed = page.waitForResponse(async (r) => {
      const isStatus =
        /\/api\/v1\/generations\/[^/]+$/.test(new URL(r.url()).pathname) &&
        r.request().method() === "GET" &&
        r.ok();
      return isStatus && (await r.json()).status === "completed";
    });
    const itinerary = page.waitForResponse(
      (r) =>
        new URL(r.url()).pathname === `/api/v1/trips/${tripId}/itinerary` &&
        r.request().method() === "GET" &&
        r.ok(),
    );
    // The account's first generation: the notice sends API-04, then starts API-22.
    await expect(
      page.getByRole("heading", {
        level: 2,
        name: "Before your first AI-written plan",
      }),
    ).toBeFocused();
    await page.getByRole("button", { name: "I understand, continue" }).click();

    const generation = await (await completed).json();
    expect(generation.provider).toBe("MOCK");
    expect(generation.outcome).toBe("model");

    await expect(page).toHaveURL(`/trips/${tripId}/itinerary`);
    const days = (await (await itinerary).json()).days as Day[];
    expect(days.length).toBeGreaterThan(0);
    expect(days.flatMap((day) => day.items).length).toBeGreaterThan(0);
    await expectSavedDays(page, days);

    // The plan is saved, not held by the page.
    await page.reload();
    await expectSavedDays(page, days);

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

    expect(
      [...hosts].filter((host) => host.includes("generativelanguage")),
    ).toEqual([]);
  },
);
