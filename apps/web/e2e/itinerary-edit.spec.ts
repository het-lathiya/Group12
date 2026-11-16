import type { Page, Response } from "@playwright/test";

import type { components } from "../lib/api/schema";
import { checkA11y, expectNoSeriousA11y } from "./axe";
import {
  expect,
  plannedTrip,
  readItinerary,
  signIn,
  test,
} from "./fixtures/trips";

type Itinerary = components["schemas"]["ItineraryOut"];
type Version = components["schemas"]["VersionOut"];
const daysFromNow = (days: number) =>
  new Date(Date.now() + days * 86_400_000).toISOString().slice(0, 10);
const content = (plan: Itinerary) =>
  plan.days.map((day) => ({
    day: day.day_number,
    items: day.items.map((item) => [
      item.place.id,
      item.start_time,
      item.duration_min,
      item.is_locked,
      item.note,
    ]),
  }));

test("TC-376: regenerate a day and all, then restore each pre-regeneration version", async ({
  page,
  users,
}) => {
  test.setTimeout(150_000);
  await page.route("https://tiles.openfreemap.org/**", (route) =>
    route.abort(),
  );
  const user = await users.create("regenerate");
  const sessionRequest = page.waitForRequest(
    (request) =>
      request.url().includes("/api/v1/") &&
      !!request.headers()["authorization"],
  );
  await page.goto("/sign-in?next=%2Fdashboard");
  await page.getByLabel("Email").fill(user.email);
  await page.getByLabel("Password", { exact: true }).fill(user.password);
  await page
    .getByRole("button", { name: "Sign in", exact: true })
    .press("Enter");
  await expect(
    page.getByRole("heading", { name: "Your trips", level: 1 }),
  ).toBeVisible();
  const session = await sessionRequest;
  const base = `${new URL(session.url()).origin}/api/v1`;
  const headers = { authorization: session.headers()["authorization"] };
  const destinations = (await (
    await page.request.get(`${base}/destinations`, { headers })
  ).json()) as components["schemas"]["Destination"][];
  const destination = destinations.find((item) => item.slug === "sampleton");
  expect(destination).toBeDefined();
  const created = await page.request.post(`${base}/trips`, {
    headers,
    data: {
      title: "Regeneration in Sampleton",
      destination_id: destination!.id,
      start_date: daysFromNow(30),
      end_date: daysFromNow(32),
      adults: 2,
    },
  });
  expect(created.status()).toBe(201);
  const { id: tripId } = (await created.json()) as { id: string };
  expect(
    (
      await page.request.put(`${base}/trips/${tripId}/preferences`, {
        headers,
        data: { interests: ["museum", "nature"] },
      })
    ).status(),
  ).toBe(200);
  expect(
    (
      await page.request.patch(`${base}/me`, {
        headers,
        data: { ai_notice_acknowledged: true },
      })
    ).status(),
  ).toBe(200);
  const started = await page.request.post(
    `${base}/trips/${tripId}/generations`,
    { headers, data: { mode: "ai" } },
  );
  expect(started.status()).toBe(202);
  const generation = (await started.json()) as { id: string };
  await expect
    .poll(
      async () =>
        (
          await (
            await page.request.get(`${base}/generations/${generation.id}`, {
              headers,
            })
          ).json()
        ).status,
      { timeout: 30_000 },
    )
    .toBe("completed");
  let before = (await (
    await page.request.get(`${base}/trips/${tripId}/itinerary`, { headers })
  ).json()) as Itinerary;
  const first = before.days[0].items[0];
  expect(
    (
      await page.request.patch(`${base}/itinerary/items/${first.id}`, {
        headers,
        data: {
          plan_revision: before.plan_revision,
          duration_min:
            first.duration_min < 465
              ? first.duration_min + 15
              : first.duration_min - 15,
        },
      })
    ).status(),
  ).toBe(200);
  before = (await (
    await page.request.get(`${base}/trips/${tripId}/itinerary`, { headers })
  ).json()) as Itinerary;

  for (const scope of ["day", "all"] as const) {
    await page.goto(`/trips/${tripId}/itinerary`);
    const dayNumber = before.days[0].day_number;
    const startedRequest = page.waitForResponse(
      (response) =>
        response.url().endsWith("/regenerate") &&
        response.request().method() === "POST",
    );
    if (scope === "day") {
      await page
        .getByRole("button", {
          name: `Regenerate day ${dayNumber}`,
          exact: true,
        })
        .press("Enter");
    } else {
      await page
        .getByRole("button", { name: "Regenerate all", exact: true })
        .press("Enter");
      await page
        .getByRole("dialog")
        .getByRole("button", { name: "Regenerate all", exact: true })
        .press("Enter");
    }
    expect((await startedRequest).status()).toBe(202);
    await expect(
      page.getByText("Regeneration complete.", { exact: true }),
    ).toBeVisible({ timeout: 45_000 });
    const after = (await (
      await page.request.get(`${base}/trips/${tripId}/itinerary`, { headers })
    ).json()) as Itinerary;
    expect(after.plan_revision).toBe(before.plan_revision + 1);
    if (scope === "day")
      expect(content(after).slice(1)).toEqual(content(before).slice(1));
    const versions = (await (
      await page.request.get(`${base}/trips/${tripId}/versions`, { headers })
    ).json()) as Version[];
    const backup = versions.find(
      (version) =>
        version.reason === "regeneration" &&
        version.plan_revision === before.plan_revision,
    );
    expect(backup).toBeDefined();
    await page
      .getByRole("navigation", { name: "Main" })
      .getByRole("link", { name: "Versions", exact: true })
      .press("Enter");
    await page
      .getByRole("button", {
        name: `Restore version ${backup!.version_no}`,
        exact: true,
      })
      .press("Enter");
    const restoredResponse = page.waitForResponse(
      (response) =>
        response.url().endsWith(`/${backup!.id}/restore`) &&
        response.request().method() === "POST",
    );
    await page
      .getByRole("dialog")
      .getByRole("button", { name: "Restore", exact: true })
      .press("Enter");
    const response = await restoredResponse;
    expect(response.status()).toBe(200);
    const restored = (await response.json()) as Itinerary;
    expect(content(restored)).toEqual(content(before));
    before = restored;
    const restoreToast = page.locator("[data-sonner-toast]").filter({
      hasText: `Version ${backup!.version_no} restored`,
    });
    await expect(restoreToast).toHaveAttribute("data-mounted", "true");
    await page
      .getByRole("link", { name: "Back to itinerary", exact: true })
      .press("Enter");
    await expect(
      page.getByRole("heading", { name: "Your itinerary", level: 1 }),
    ).toBeVisible();
    const annotations = test.info().annotations.length;
    await checkA11y(page);
    expect(
      test
        .info()
        .annotations.slice(annotations)
        .filter((a) => a.type === "axe-serious"),
    ).toEqual([]);
  }
});

// E2E-05 and TC-376 card step 3 (IMP-701; FR-060, FR-061, FR-063, FR-064; TC-201; ACC-05, ACC-16):
// Every edit is made from the itinerary page and checked against the API's answer. The must-visit
// item is locked, so the moved, unlocked item is retimed into its interval to keep an overlap.

type EditResult = components["schemas"]["EditResultOut"];

async function openDay(page: Page, dayNumber: number) {
  if ((page.viewportSize()?.width ?? 0) < 768) {
    await page.getByRole("tab", { name: `Day ${dayNumber}` }).click();
  }
  return page.getByRole("region", { name: `Day ${dayNumber}` });
}

const isItemEdit = (itemId: string, method: string) => (r: Response) =>
  new URL(r.url()).pathname === `/api/v1/itinerary/items/${itemId}` &&
  r.request().method() === method;

/** Open an item's time editor, fill the given fields and save; returns API-26's answer. */
async function retime(
  page: Page,
  item: { id: string; place: { name: string } },
  values: { start?: string; duration?: number },
): Promise<EditResult> {
  await page
    .getByRole("button", { name: `Edit time of ${item.place.name}` })
    .click();
  const form = page.getByRole("form", {
    name: `Edit time of ${item.place.name}`,
  });
  const currentStart = await form.getByLabel("Start time").inputValue();
  const currentDuration = Number(
    await form.getByLabel("Duration (minutes)").inputValue(),
  );
  expect(
    (values.start !== undefined && values.start !== currentStart) ||
      (values.duration !== undefined && values.duration !== currentDuration),
    "the editor must receive a changed value before waiting for PATCH",
  ).toBe(true);
  if (values.start) expect(values.start).toMatch(/^([01]\d|2[0-3]):[0-5]\d$/);
  if (values.start) await form.getByLabel("Start time").fill(values.start);
  if (values.duration)
    await form.getByLabel("Duration (minutes)").fill(String(values.duration));
  const saved = page.waitForResponse(isItemEdit(item.id, "PATCH"));
  await form.getByRole("button", { name: "Save" }).click();
  const response = await saved;
  expect(response.status()).toBe(200);
  await expect(form).toBeHidden();
  return (await response.json()) as EditResult;
}

const otherDuration = (minutes: number) =>
  minutes < 465 ? minutes + 15 : minutes - 15;

test("E2E-05 TC-376: move, overlap, remove, retime, lock, regenerate day 2, save a version, change, restore and reload", async ({
  page,
  users,
}) => {
  test.setTimeout(180_000);
  await page.route("https://tiles.openfreemap.org/**", (route) =>
    route.abort(),
  );
  const user = await users.create("edit-regression");
  const session = await test.step("Sign in", () => signIn(page, user));
  const { tripId, itinerary } =
    await test.step("Create and generate a trip with a must-visit museum", () =>
      plannedTrip(page, session, {
        title: "Edits in Sampleton",
        mustVisit: "museum",
      }));
  const mustVisitDay = itinerary!.days.find((day) =>
    day.items.some((item) => item.must_visit),
  );
  const mustVisit = mustVisitDay?.items.find((item) => item.must_visit);
  expect(mustVisit, "the must-visit place is planned").toBeDefined();
  const day1 = itinerary!.days[0];
  expect(day1.items.length, "day 1 has two items").toBeGreaterThanOrEqual(2);
  const [a, b] = day1.items;
  await page.goto(`/trips/${tripId}/itinerary`);
  await expect(
    page.getByRole("heading", { level: 1, name: "Your itinerary" }),
  ).toBeVisible();

  await test.step("Move day 1's second item up with the keyboard", async () => {
    const column = await openDay(page, 1);
    const moved = page.waitForResponse(isItemEdit(b.id, "PATCH"));
    await column
      .getByRole("button", { name: `Move ${b.place.name} up` })
      .press("Enter");
    expect((await moved).status()).toBe(200);
    await expect(column.getByRole("heading", { level: 3 }).first()).toHaveText(
      b.place.name,
    );
  });

  await test.step("Retime the moved unlocked item to a different overlapping start", async () => {
    const plan = await readItinerary(page, session, tripId);
    const items = plan.days.flatMap((day) => day.items);
    const neighbour = items.find((item) => item.id === a.id)!;
    const moved = items.find((item) => item.id === b.id)!;
    expect(moved.is_locked).toBe(false);
    const [hours, minutes] = neighbour.start_time.split(":").map(Number);
    const minute =
      hours * 60 +
      minutes +
      (neighbour.start_time === moved.start_time ? 1 : 0);
    const start = `${String(Math.floor(minute / 60)).padStart(2, "0")}:${String(minute % 60).padStart(2, "0")}`;
    expect(start).not.toBe(moved.start_time);
    await openDay(page, 1);
    const result = await retime(page, moved, { start });
    const overlap = result.findings.find((f) => f.code === "OVERLAP");
    expect(overlap, "an OVERLAP finding").toBeDefined();
    await expect(
      page
        .getByRole("region", { name: /^Plan checks/ })
        .getByText(overlap!.message, { exact: true })
        .first(),
    ).toBeAttached();
  });

  await test.step("Remove the must-visit item", async () => {
    await openDay(page, mustVisitDay!.day_number);
    await page
      .getByRole("button", { name: `Remove ${mustVisit!.place.name}` })
      .click();
    const removed = page.waitForResponse(isItemEdit(mustVisit!.id, "DELETE"));
    await page
      .getByRole("dialog")
      .getByRole("button", { name: "Remove", exact: true })
      .click();
    const response = await removed;
    expect(response.status()).toBe(200);
    const result = (await response.json()) as EditResult;
    expect(result.findings.map((f) => f.code)).toContain("MUST_VISIT_MISSING");
    await expect(
      page.getByText(`Removed ${mustVisit!.place.name}`),
    ).toBeVisible();
  });

  const day2 = (await readItinerary(page, session, tripId)).days[1];
  expect(day2.items.length, "day 2 has two items").toBeGreaterThanOrEqual(2);
  const [locked, changed] = day2.items;

  await test.step("Change the duration of a day 2 item", async () => {
    await openDay(page, 2);
    const result = await retime(page, changed, {
      duration: otherDuration(changed.duration_min),
    });
    const after = result.changed_days
      .flatMap((day) => day.items)
      .find((item) => item.id === changed.id);
    expect(after?.duration_min).toBe(otherDuration(changed.duration_min));
  });

  await test.step("Lock the first item of day 2", async () => {
    const column = await openDay(page, 2);
    const locking = page.waitForResponse(isItemEdit(locked.id, "PATCH"));
    await column
      .getByRole("button", { name: `Lock ${locked.place.name}` })
      .click();
    expect((await locking).status()).toBe(200);
    await expect(
      column.getByRole("button", { name: `Locked ${locked.place.name}` }),
    ).toHaveAttribute("aria-pressed", "true");
  });

  await test.step("Regenerate day 2 and keep the locked item's time", async () => {
    const lockedBefore = (
      await readItinerary(page, session, tripId)
    ).days[1].items.find((item) => item.id === locked.id)!;
    const started = page.waitForResponse(
      (r) =>
        r.url().endsWith("/days/2/regenerate") &&
        r.request().method() === "POST",
    );
    await page
      .getByRole("button", { name: "Regenerate day 2", exact: true })
      .click();
    expect((await started).status()).toBe(202);
    // GenerationProgress's terminal state for an inline regeneration.
    await expect(
      page.getByText("Regeneration complete.", { exact: true }),
    ).toBeVisible({ timeout: 45_000 });
    const after = await readItinerary(page, session, tripId);
    const kept = after.days[1].items.find((item) => item.is_locked);
    expect(kept?.place.id).toBe(lockedBefore.place.id);
    expect(kept?.start_time).toBe(lockedBefore.start_time);
  });

  const savedPlan = content(await readItinerary(page, session, tripId));
  const versionNo = await test.step("Save a version", async () => {
    await page
      .getByRole("navigation", { name: "Main" })
      .getByRole("link", { name: "Versions", exact: true })
      .click();
    await expect(
      page.getByRole("heading", { level: 1, name: "Versions" }),
    ).toBeVisible();
    await page.getByLabel("Version name").fill("Before the change");
    const saved = page.waitForResponse(
      (r) =>
        r.url().endsWith(`/trips/${tripId}/versions`) &&
        r.request().method() === "POST",
    );
    await page.getByRole("button", { name: "Save version" }).click();
    const response = await saved;
    expect(response.status()).toBe(201);
    await expect(
      page.getByRole("list", { name: "Saved versions" }),
    ).toContainText("Before the change");
    return ((await response.json()) as Version).version_no;
  });

  await test.step("Change the plan", async () => {
    await page.getByRole("link", { name: "Back to itinerary" }).click();
    const plan = await readItinerary(page, session, tripId);
    const item = plan.days[0].items.find((i) => !i.is_locked)!;
    await openDay(page, 1);
    await retime(page, item, { duration: otherDuration(item.duration_min) });
    expect(content(await readItinerary(page, session, tripId))).not.toEqual(
      savedPlan,
    );
  });

  await test.step("Restore the saved version", async () => {
    await page
      .getByRole("navigation", { name: "Main" })
      .getByRole("link", { name: "Versions", exact: true })
      .click();
    await page
      .getByRole("button", {
        name: `Restore version ${versionNo}`,
        exact: true,
      })
      .click();
    const restored = page.waitForResponse(
      (r) => r.url().endsWith("/restore") && r.request().method() === "POST",
    );
    await page
      .getByRole("dialog")
      .getByRole("button", { name: "Restore", exact: true })
      .click();
    const response = await restored;
    expect(response.status()).toBe(200);
    expect(content((await response.json()) as Itinerary)).toEqual(savedPlan);
  });

  await test.step("Reload the itinerary and see the restored plan", async () => {
    await page.goto(`/trips/${tripId}/itinerary`);
    await page.reload();
    const plan = await readItinerary(page, session, tripId);
    expect(content(plan)).toEqual(savedPlan);
    for (const day of plan.days) {
      const column = await openDay(page, day.day_number);
      await expect(column.locator("time")).toHaveText(
        day.items.map((item) => item.start_time),
      );
    }
    await expectNoSeriousA11y(page);
  });
});
