import type { Page } from "@playwright/test";

import type { components } from "../lib/api/schema";
import { expect, test, type TestUsers } from "./fixtures/users";

// IMD-173 (FR-080 AC3, TC-240; IMP-508): with the OpenFreeMap style and tiles aborted, the map
// gives way to the numbered list; with a local style the OpenStreetMap credit is visible. Local:
// the local stack, `make seed` (Sampleton) and the API with AI_PROVIDER=MOCK. No request leaves
// for OpenFreeMap: every request to its host is aborted or answered here.

type Item = components["schemas"]["Item"];
type Itinerary = components["schemas"]["ItineraryOut"];

const OPENFREEMAP = "https://tiles.openfreemap.org/**";
const STYLE_URL = "https://tiles.openfreemap.org/styles/liberty";

// A minimal style with no sources: the credit under test comes from MapPanel (customAttribution).
const LOCAL_STYLE = {
  version: 8,
  sources: {},
  layers: [
    {
      id: "background",
      type: "background",
      paint: { "background-color": "#F1F5F9" },
    },
  ],
};

/** A days-from-today date, so the run never reaches a fixed date. */
const daysFromNow = (days: number) =>
  new Date(Date.now() + days * 86_400_000).toISOString().slice(0, 10);

/** Sign in, create a Sampleton trip, generate with MOCK and return the first day's stops. */
async function generatedPlan(page: Page, users: TestUsers): Promise<Item[]> {
  const user = await users.create("map");
  await page.goto("/sign-in?next=%2Ftrips%2Fnew");
  await page.getByLabel("Email").fill(user.email);
  await page.getByLabel("Password", { exact: true }).fill(user.password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { level: 1, name: "Plan a new trip" }),
  ).toBeVisible();

  await page
    .getByLabel("Destination")
    .selectOption({ label: "Sampleton (sample)" });
  await page.getByLabel("Trip title").fill("Map in Sampleton");
  await page.getByLabel("Start date").fill(daysFromNow(30));
  await page.getByLabel("End date").fill(daysFromNow(31));
  await page.getByLabel("Adults").fill("2");
  const created = page.waitForResponse(
    (r) => r.url().endsWith("/api/v1/trips") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Next", exact: true }).click();
  const tripId = (await (await created).json()).id as string;
  for (const step of ["Your preferences", "Must-visit places"]) {
    await expect(
      page.getByRole("heading", { level: 2, name: step }),
    ).toBeFocused();
    await page.getByRole("button", { name: "Next", exact: true }).click();
  }
  await page.getByRole("link", { name: "Generate itinerary" }).click();

  const read = page.waitForResponse(
    (r) =>
      new URL(r.url()).pathname === `/api/v1/trips/${tripId}/itinerary` &&
      r.request().method() === "GET" &&
      r.ok(),
    { timeout: 30_000 },
  );
  await page.getByRole("button", { name: "I understand, continue" }).click();
  await expect(page).toHaveURL(`/trips/${tripId}/itinerary`);
  const { days } = (await (await read).json()) as Itinerary;
  // Below 768 px the map sits behind the Map tab.
  if ((page.viewportSize()?.width ?? 0) < 768) {
    await page.getByRole("tab", { name: "Map" }).click();
  }
  return [...days[0].items].sort((a, b) => a.position - b.position);
}

async function expectListFallback(page: Page, stops: Item[]) {
  await expect(
    page
      .getByRole("status")
      .filter({ hasText: "Map unavailable; list view shown" }),
  ).toBeVisible();
  const entries = page.getByRole("list", { name: "Stops" }).getByRole("button");
  await expect(entries).toHaveCount(stops.length);
  for (const [index, item] of stops.entries()) {
    // The visible text forms the name: "Stop N <place> <times>".
    await expect(entries.nth(index)).toHaveAccessibleName(
      new RegExp(
        `^Stop\\s*${index + 1}\\s*${item.place.name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}`,
      ),
    );
  }
}

test(
  "map: aborted style and tiles show the numbered list (IMD-173, TC-240)",
  { tag: "@map" },
  async ({ page, users }) => {
    test.setTimeout(90_000);
    await page.route(OPENFREEMAP, (route) => route.abort());
    const stops = await generatedPlan(page, users);
    expect(stops.length).toBeGreaterThan(0);
    await expectListFallback(page, stops);
  },
);

test(
  "map: with a local style the map attribution is visible (IMD-173)",
  { tag: "@map" },
  async ({ page, users }) => {
    test.setTimeout(90_000);
    await page.route(OPENFREEMAP, (route) =>
      route.request().url() === STYLE_URL
        ? route.fulfill({ json: LOCAL_STYLE })
        : route.abort(),
    );
    const stops = await generatedPlan(page, users);
    const webgl = await page.evaluate(() => {
      const canvas = document.createElement("canvas");
      return Boolean(canvas.getContext("webgl2") ?? canvas.getContext("webgl"));
    });
    test.info().annotations.push({ type: "webgl", description: String(webgl) });
    if (!webgl) {
      // No WebGL in this browser: MapPanel never builds a map, so the list is the answer.
      await expectListFallback(page, stops);
      return;
    }
    const attribution = page.locator(".maplibregl-ctrl-attrib");
    await expect(attribution).toBeVisible();
    await expect(attribution).toContainText("OpenStreetMap");
    await expect(
      attribution.getByRole("link", { name: "© OpenStreetMap contributors" }),
    ).toHaveAttribute("href", "https://www.openstreetmap.org/copyright");
    await expect(
      page.getByText("Map unavailable; list view shown"),
    ).toHaveCount(0);
  },
);
