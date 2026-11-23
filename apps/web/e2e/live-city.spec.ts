import path from "node:path";

import type { Page, TestInfo } from "@playwright/test";

import { checkA11y } from "./axe";
import { expect, test } from "./fixtures/users";

// E2E-10, TC-486 (Amendment A2 §13.3; IMP-730): with `any_city_mode` ON and LIVE_DATA_PROVIDER=FAKE
// the traveller searches "Liveton (SAMPLE)", resolves it, watches the import, creates a trip,
// generates with MOCK and reads the itinerary and costs with the live labels and the attribution
// footer; "Tinyham (SAMPLE)" ends in the not-enough-data message with its nearby city. Needs the
// API and the web build started with the switch ON (the E2E workflow's live job); the other runs
// skip these tests, as the switch-OFF build has no city search.

const LIVE_ON = [
  process.env.FEATURES_DISABLED,
  process.env.NEXT_PUBLIC_FEATURES_DISABLED,
].every((raw) =>
  (raw ?? "").split(",").some((t) => t.trim() === "!any_city_mode"),
);

// Screenshots of IMP-730 at 360 and 1280 px, uploaded by the live job as an artifact.
const SCREENS = path.resolve(__dirname, "../test-results/live-city-screens");

async function screen(page: Page, info: TestInfo, name: string) {
  const width = page.viewportSize()?.width;
  if (width !== 360 && width !== 1280) return;
  await page.screenshot({
    path: path.join(SCREENS, `${name}-${width}-r${info.repeatEachIndex}.png`),
    fullPage: true,
  });
}

async function signIn(page: Page, email: string, password: string) {
  await page.goto("/sign-in?next=%2Ftrips%2Fnew");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { level: 1, name: "Plan a new trip" }),
  ).toBeVisible();
}

async function searchCity(page: Page, term: string, info: TestInfo) {
  await page.getByLabel("Any city (live data)").fill(term);
  await page.getByRole("button", { name: "Search", exact: true }).click();
  const results = page.getByRole("list", { name: "City search results" });
  await expect(results.getByRole("button")).toHaveCount(1);
  await expect(
    page.getByText("Search by Nominatim · © OpenStreetMap contributors"),
  ).toBeVisible();
  await screen(page, info, "1-city-search");
  return results;
}

// LiveAttribution's footer sits inside <main>, so it has no landmark role; its heading names it.
const dataSources = (page: Page) =>
  page.locator("footer").filter({
    has: page.getByRole("heading", { level: 2, name: "Data sources" }),
  });

const stepHeading = (page: Page, name: string) =>
  page.getByRole("heading", { level: 2, name });

test.describe("@live any-city mode", () => {
  test.skip(!LIVE_ON, "needs the API and web build with any_city_mode ON");

  test("E2E-10 TC-486: a live city from search to itinerary and costs, with live labels and attribution", async ({
    page,
    users,
  }, info) => {
    test.setTimeout(180_000);
    const user = await users.create("live");
    await signIn(page, user.email, user.password);

    const results = await searchCity(page, "Liveton", info);
    await results.getByRole("button", { name: /^Liveton \(SAMPLE\)/ }).click();
    // A first run shows the import building; a repeat finds the city ready at once.
    await expect(
      page.getByText(
        /^(Building your city: finding places…|Ready: \d+ places from OpenStreetMap)$/,
      ),
    ).toBeVisible();
    await screen(page, info, "2-import-progress");
    await expect(
      page.getByText(/^Ready: \d+ places from OpenStreetMap$/),
    ).toBeVisible({ timeout: 60_000 });
    await expect(page.getByLabel("Destination")).toHaveValue(/.+/);
    await expect(
      page.getByLabel("Destination").locator("option:checked"),
    ).toHaveText("Liveton (SAMPLE) (Live data)");
    await expect(page.getByLabel("Currency")).toHaveValue("INR");
    await checkA11y(page);

    await page.getByLabel("Trip title").fill("Weekend in Liveton (SAMPLE)");
    await page.getByLabel("Start date").fill("2026-12-04");
    await page.getByLabel("End date").fill("2026-12-05");
    await page.getByLabel("Adults").fill("2");
    const created = page.waitForResponse(
      (r) =>
        r.url().endsWith("/api/v1/trips") && r.request().method() === "POST",
    );
    await page.getByRole("button", { name: "Next", exact: true }).click();
    expect((await created).status()).toBe(201);
    const tripId = ((await (await created).json()) as { id: string }).id;

    await expect(stepHeading(page, "Your preferences")).toBeFocused();
    await page.getByRole("button", { name: "Museums" }).click();
    await page.getByRole("button", { name: "Next", exact: true }).click();
    await expect(stepHeading(page, "Must-visit places")).toBeFocused();
    await page.getByRole("button", { name: "Next", exact: true }).click();
    await expect(stepHeading(page, "Review your trip")).toBeFocused();
    await page.getByRole("link", { name: "Generate itinerary" }).click();
    await expect(page).toHaveURL(`/trips/${tripId}/generate`);

    await page.getByRole("button", { name: "I understand, continue" }).click();
    await expect(page).toHaveURL(`/trips/${tripId}/itinerary`, {
      timeout: 90_000,
    });
    await expect(
      page.getByRole("heading", { level: 1, name: "Your itinerary" }),
    ).toBeVisible();

    await test.step("Itinerary: tier badge, OSM badges, unknown chips, attribution", async () => {
      await expect(
        page.getByText("Live data", { exact: true }).first(),
      ).toBeVisible();
      await expect(page.getByText("Price unknown").first()).toBeVisible();
      await expect(page.getByText("Hours unknown").first()).toBeVisible();
      await expect(
        page.getByText("OpenStreetMap", { exact: true }).first(),
      ).toBeVisible();
      const footer = dataSources(page);
      await expect(footer).toContainText(
        "Place data © OpenStreetMap contributors, available under the Open Database Licence (ODbL)",
      );
      await expect(footer).toContainText(
        "Guide text from Wikivoyage (Liveton (SAMPLE)), by its contributors, under CC BY-SA 4.0; excerpts, some sections left out",
      );
      await screen(page, info, "4-live-itinerary");
      await checkA11y(page);
    });

    await test.step("Costs: known costs only, with the attribution footer", async () => {
      await page.goto(`/trips/${tripId}/costs`);
      await expect(
        page.getByText(/^Known costs only: \d+ stops? (has|have) no price$/),
      ).toBeVisible();
      await expect(
        page.getByText("Live data", { exact: true }).first(),
      ).toBeVisible();
      await expect(dataSources(page)).toBeVisible();
      await screen(page, info, "5-live-costs");
      await checkA11y(page);
    });
  });

  test("E2E-10 TC-486: a city with too few places shows the not-enough-data message with its nearby city", async ({
    page,
    users,
  }, info) => {
    const user = await users.create("live-small");
    await signIn(page, user.email, user.password);

    const results = await searchCity(page, "Tinyham", info);
    await results.getByRole("button", { name: /^Tinyham \(SAMPLE\)/ }).click();
    await expect(
      page.getByText(
        "We could not find enough places for Tinyham (SAMPLE) yet. Try Bigtown (SAMPLE), a larger city nearby.",
      ),
    ).toBeVisible({ timeout: 60_000 });
    await expect(
      page.getByRole("button", { name: "Search Bigtown (SAMPLE)" }),
    ).toBeVisible();
    await screen(page, info, "3-not-enough-data");
    await checkA11y(page);
  });
});
