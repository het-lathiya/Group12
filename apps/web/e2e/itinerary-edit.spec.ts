import type { components } from "../lib/api/schema";
import { checkA11y } from "./axe";
import { expect, test } from "./fixtures/users";

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
