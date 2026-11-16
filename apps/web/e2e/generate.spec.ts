import type { Page } from "@playwright/test";

import type { components } from "../lib/api/schema";
import { expectNoSeriousA11y } from "./axe";
import {
  expect,
  plannedTrip,
  readItinerary,
  signIn,
  test,
} from "./fixtures/trips";

// E2E-03 (§13.4; FR-024, FR-025, FR-059; ACC-01, ACC-02): accept the privacy notice, generate and
// watch the progress until the itinerary opens. Local stack, `make seed` and the API with
// AI_PROVIDER=MOCK and MOCK_PROVIDER_SCENARIO=ok (the default).

type Generation = components["schemas"]["GenerationOut"];

/** The day's column; below 768 px the days are tabs, so its tab is opened first. */
async function openDay(page: Page, dayNumber: number) {
  if ((page.viewportSize()?.width ?? 0) < 768) {
    await page.getByRole("tab", { name: `Day ${dayNumber}` }).click();
  }
  return page.getByRole("region", { name: `Day ${dayNumber}` });
}

test("E2E-03: accept the notice, generate with MOCK and open a three-day itinerary", async ({
  page,
  users,
}) => {
  test.setTimeout(90_000);
  const user = await users.create("generate");
  const session = await test.step("Sign in", () => signIn(page, user));
  // A new account has not acknowledged the notice, so the generate page shows it.
  const { tripId } = await test.step("Create a three-day trip", () =>
    plannedTrip(page, session, {
      title: "Generate in Sampleton",
      generate: false,
      acknowledgeNotice: false,
    }));

  await test.step("Open the generate page and read the privacy notice", async () => {
    await page.goto(`/trips/${tripId}/generate`);
    await expect(
      page.getByRole("heading", { level: 1, name: "Generate your itinerary" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", {
        level: 2,
        name: "Before your first AI-written plan",
      }),
    ).toBeVisible();
    await expectNoSeriousA11y(page);
  });

  const started = page.waitForResponse(
    (r) =>
      new URL(r.url()).pathname === `/api/v1/trips/${tripId}/generations` &&
      r.request().method() === "POST",
  );
  await test.step("Accept the notice, which starts the generation", async () => {
    await page.getByRole("button", { name: "I understand, continue" }).click();
    expect((await started).status()).toBe(202);
    await expect(
      page.getByRole("heading", { level: 2, name: "Progress" }),
    ).toBeVisible();
  });
  const generationId = ((await (await started).json()) as { id: string }).id;

  await test.step("Watch the progress until the itinerary opens", async () => {
    // GenerationProgress's terminal state for completed is "Plan ready", then the itinerary.
    await expect(page).toHaveURL(`/trips/${tripId}/itinerary`, {
      timeout: 45_000,
    });
    await expect(
      page.getByRole("heading", { level: 1, name: "Your itinerary" }),
    ).toBeVisible();
  });

  await test.step("See three days with times, labels and no fallback notice", async () => {
    const generation = (await (
      await page.request.get(`${session.base}/generations/${generationId}`, {
        headers: session.headers,
      })
    ).json()) as Generation;
    expect(generation.status).toBe("completed");
    expect(generation.provider).toBe("MOCK");
    expect(generation.outcome).toBe("model");
    const itinerary = await readItinerary(page, session, tripId);
    expect(itinerary.days.map((day) => day.day_number)).toEqual([1, 2, 3]);
    expect(itinerary.source?.provider).toBe("MOCK");
    for (const day of itinerary.days) {
      const column = await openDay(page, day.day_number);
      await expect(column.locator("time")).toHaveText(
        day.items.map((item) => item.start_time),
      );
      // Each item labels the source of its opening hours (§7.8).
      await expect(column.getByText(/^Hours/).first()).toBeVisible();
    }
    await expect(
      page.getByText(
        "Built by rules because the AI service was unavailable or its answer failed checks",
      ),
    ).toHaveCount(0);
    await expectNoSeriousA11y(page);
  });
});
