import type { Locator, Page } from "@playwright/test";

import { expectNoSeriousA11y } from "./axe";
import { expect, plannedTrip, test } from "./fixtures/trips";

// TC-374 (NFR-025, §7.9): the core pages are reached with the keyboard only (Tab to a control,
// type or press Enter; no click) and axe scans each page. The trip is set up through the API; the
// journey of journey.spec.ts covers the wizard and the edits by keyboard.

/** Press Tab until `target` has focus; fails when it is not reached in `max` presses. */
async function tabTo(page: Page, target: Locator, max = 300) {
  for (let presses = 0; presses < max; presses += 1) {
    if (await target.evaluate((element) => element === document.activeElement))
      return;
    await page.keyboard.press("Tab");
  }
  await expect(target, "reached with Tab").toBeFocused();
}

const mainNav = (page: Page, name: string) =>
  page
    .getByRole("navigation", { name: "Main" })
    .getByRole("link", { name, exact: true });

test("TC-374: sign in, open the itinerary, costs and versions with the keyboard only", async ({
  page,
  users,
}) => {
  test.setTimeout(120_000);
  const user = await users.create("keyboard");

  const session = await test.step("Sign in with the keyboard", async () => {
    const apiCall = page.waitForRequest(
      (r) => r.url().includes("/api/v1/") && !!r.headers()["authorization"],
    );
    await page.goto("/sign-in?next=%2Fdashboard");
    await expectNoSeriousA11y(page);
    await tabTo(page, page.getByLabel("Email"));
    await page.keyboard.type(user.email);
    await tabTo(page, page.getByLabel("Password", { exact: true }));
    await page.keyboard.type(user.password);
    await tabTo(
      page,
      page.getByRole("button", { name: "Sign in", exact: true }),
    );
    await page.keyboard.press("Enter");
    await expect(
      page.getByRole("heading", { level: 1, name: "Your trips" }),
    ).toBeVisible();
    const request = await apiCall;
    return {
      base: `${new URL(request.url()).origin}/api/v1`,
      headers: { authorization: request.headers()["authorization"] },
    };
  });

  const { tripId } = await test.step("Have a planned trip", () =>
    plannedTrip(page, session, { title: "Keyboard in Sampleton" }));

  await test.step("Open the latest itinerary from the dashboard", async () => {
    await page.reload();
    const openLatest = page.getByRole("button", { name: "Open latest" });
    await expect(openLatest).toBeEnabled();
    await expectNoSeriousA11y(page);
    await tabTo(page, openLatest);
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(`/trips/${tripId}/itinerary`);
    await expect(
      page.getByRole("heading", { level: 1, name: "Your itinerary" }),
    ).toBeVisible();
    await expectNoSeriousA11y(page);
  });

  await test.step("Go to the costs page from the main navigation", async () => {
    await tabTo(page, mainNav(page, "Costs"));
    await page.keyboard.press("Enter");
    await expect(
      page.getByRole("heading", { level: 1, name: "Trip costs" }),
    ).toBeVisible();
    await expectNoSeriousA11y(page);
  });

  await test.step("Go to the versions page from the main navigation", async () => {
    await tabTo(page, mainNav(page, "Versions"));
    await page.keyboard.press("Enter");
    await expect(
      page.getByRole("heading", { level: 1, name: "Versions" }),
    ).toBeVisible();
    await expectNoSeriousA11y(page);
  });

  await test.step("Go back to the itinerary", async () => {
    await tabTo(page, page.getByRole("link", { name: "Back to itinerary" }));
    await page.keyboard.press("Enter");
    await expect(
      page.getByRole("heading", { level: 1, name: "Your itinerary" }),
    ).toBeVisible();
  });
});
