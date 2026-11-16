import type { Page, Response } from "@playwright/test";

import type { components } from "../lib/api/schema";
import { expectNoSeriousA11y } from "./axe";
import {
  expect,
  plannedTrip,
  readItinerary,
  signIn,
  signOut,
  test,
} from "./fixtures/trips";

// E2E-06 (§13.4; FR-013, FR-014, FR-069; TC-217; ACC-10, ACC-18): an edited plan reopens exactly as
// saved after signing out and in, and an edit from a second tab with an older plan revision gets
// the reload message (409 STALE_PLAN).

type Itinerary = components["schemas"]["ItineraryOut"];

// The text of STALE_PLAN_MESSAGE (lib/api/client.ts).
const STALE_PLAN_MESSAGE = "This plan changed since you opened it";

async function openDay(page: Page, dayNumber: number) {
  if ((page.viewportSize()?.width ?? 0) < 768) {
    await page.getByRole("tab", { name: `Day ${dayNumber}` }).click();
  }
  return page.getByRole("region", { name: `Day ${dayNumber}` });
}

/** Every day's places and start times, and the plan checks summary, as API-24 answered. */
async function expectShowsPlan(page: Page, plan: Itinerary) {
  for (const day of plan.days) {
    const column = await openDay(page, day.day_number);
    await expect(column.getByRole("heading", { level: 3 })).toHaveText(
      day.items.map((item) => item.place.name),
    );
    await expect(column.locator("time")).toHaveText(
      day.items.map((item) => item.start_time),
    );
  }
  const panel = page.getByRole("region", { name: /^Plan checks/ });
  for (const finding of plan.findings) {
    await expect(panel).toContainText(finding.message);
  }
}

const isRetime = (itemId: string) => (r: Response) =>
  new URL(r.url()).pathname === `/api/v1/itinerary/items/${itemId}` &&
  r.request().method() === "PATCH";

async function retime(page: Page, itemName: string, durationMin: number) {
  await page.getByRole("button", { name: `Edit time of ${itemName}` }).click();
  const form = page.getByRole("form", { name: `Edit time of ${itemName}` });
  await form.getByLabel("Duration (minutes)").fill(String(durationMin));
  await form.getByRole("button", { name: "Save" }).click();
}

test("E2E-06 TC-217: reopen the saved plan after signing in again, and a stale second tab must reload", async ({
  page,
  users,
}) => {
  test.setTimeout(120_000);
  const user = await users.create("reopen");
  const session = await test.step("Sign in", () => signIn(page, user));
  const { tripId, itinerary } =
    await test.step("Create, generate and edit a trip", async () => {
      const planned = await plannedTrip(page, session, {
        title: "Reopen in Sampleton",
      });
      const item = planned.itinerary!.days[0].items[0];
      const edited = await page.request.patch(
        `${session.base}/itinerary/items/${item.id}`,
        {
          headers: session.headers,
          data: {
            plan_revision: planned.itinerary!.plan_revision,
            duration_min:
              item.duration_min < 465
                ? item.duration_min + 15
                : item.duration_min - 15,
          },
        },
      );
      expect(edited.status()).toBe(200);
      return {
        tripId: planned.tripId,
        itinerary: await readItinerary(page, session, planned.tripId),
      };
    });

  await test.step("Sign out and sign in again", async () => {
    await signOut(page);
    await signIn(page, user);
  });

  await test.step("Open the latest itinerary from the dashboard", async () => {
    const openLatest = page.getByRole("button", { name: "Open latest" });
    await expect(openLatest).toBeEnabled();
    await openLatest.click();
    await expect(page).toHaveURL(`/trips/${tripId}/itinerary`);
    await expectShowsPlan(page, itinerary);
    await expectNoSeriousA11y(page);
  });

  const second = await page.context().newPage();
  await test.step("Open the same itinerary in a second tab", async () => {
    await second.goto(`/trips/${tripId}/itinerary`);
    await expectShowsPlan(second, itinerary);
  });

  const day = itinerary.days.find((d) => d.items.length >= 2)!;
  const [a, b] = day.items;
  await test.step("Edit in the first tab", async () => {
    await openDay(page, day.day_number);
    const saved = page.waitForResponse(isRetime(a.id));
    await retime(
      page,
      a.place.name,
      a.duration_min < 465 ? a.duration_min + 15 : a.duration_min - 15,
    );
    expect((await saved).status()).toBe(200);
  });

  await test.step("Edit in the second tab and get the reload message", async () => {
    await openDay(second, day.day_number);
    const refused = second.waitForResponse(isRetime(b.id));
    await retime(
      second,
      b.place.name,
      b.duration_min < 465 ? b.duration_min + 15 : b.duration_min - 15,
    );
    const response = await refused;
    expect(response.status()).toBe(409);
    expect(
      ((await response.json()) as { error: { code: string } }).error.code,
    ).toBe("STALE_PLAN");
    await expect(second.getByText(STALE_PLAN_MESSAGE)).toBeVisible();
  });
});
