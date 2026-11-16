import type { components } from "../lib/api/schema";
import { expectNoSeriousA11y } from "./axe";
import {
  expect,
  plannedTrip,
  readItinerary,
  signIn,
  test,
} from "./fixtures/trips";

// E2E-04 (§13.4; FR-050, FR-054, FR-071, FR-073, FR-076; ACC-06, ACC-07): the warnings panel and
// the costs page show the API's findings, alerts, breakdowns and labels. The shared CI API runs
// MOCK_PROVIDER_SCENARIO=ok, so the flawed plan is made by the traveller's own actions instead of
// the `flawed` scenario: a retime onto the previous item's start (OVERLAP, PR-06 keeps it) and a
// budget equal to the planning total (BUDGET_NEAR, IMD-29: at least 90 percent).

type Costs = components["schemas"]["CostSummaryOut"];
type EditResult = components["schemas"]["EditResultOut"];

const LABEL_TEXT = {
  curated: "Curated",
  estimate: "Estimate",
  unavailable: "Unavailable",
  traveller_input: "Traveller input",
} as const;

test("E2E-04: an overlap and a near budget show with their fixes, and the costs match the API", async ({
  page,
  users,
}) => {
  test.setTimeout(120_000);
  const user = await users.create("costs");
  const session = await test.step("Sign in", () => signIn(page, user));
  const { base, headers } = session;
  const { tripId, itinerary } =
    await test.step("Create and generate a trip", () =>
      plannedTrip(page, session, { title: "Costs in Sampleton" }));

  const costsUrl = `${base}/trips/${tripId}/costs`;
  await test.step("Set a budget equal to the planning total", async () => {
    const before = (await (
      await page.request.get(costsUrl, { headers })
    ).json()) as Costs;
    const patched = await page.request.patch(`${base}/trips/${tripId}`, {
      headers,
      data: {
        budget: { amount: before.planning_total, currency: before.currency },
      },
    });
    expect(patched.status()).toBe(200);
  });

  await test.step("Retime an item onto the previous item's start", async () => {
    const day = itinerary!.days.find((d) => d.items.length >= 2);
    expect(day, "a day with two items").toBeDefined();
    const [first, second] = day!.items;
    const response = await page.request.patch(
      `${base}/itinerary/items/${second.id}`,
      {
        headers,
        data: {
          plan_revision: itinerary!.plan_revision,
          start_time: first.start_time,
        },
      },
    );
    expect(response.status()).toBe(200);
    const result = (await response.json()) as EditResult;
    expect(result.findings.map((finding) => finding.code)).toContain("OVERLAP");
  });

  await test.step("Open the warnings panel on the itinerary", async () => {
    const saved = await readItinerary(page, session, tripId);
    await page.goto(`/trips/${tripId}/itinerary`);
    const panel = page.getByRole("region", { name: /^Plan checks/ });
    await expect(panel).toBeVisible();
    const show = panel.getByRole("button", { name: "Show" });
    if (await show.isVisible()) await show.click();
    const overlap = saved.findings.find((f) => f.code === "OVERLAP");
    expect(overlap?.suggested_fix).toBeTruthy();
    await expect(
      panel.getByText(overlap!.message, { exact: true }).first(),
    ).toBeVisible();
    await expect(
      panel
        .getByText(`Suggested fix: ${overlap!.suggested_fix!}`, { exact: true })
        .first(),
    ).toBeVisible();
    await expectNoSeriousA11y(page);
  });

  await test.step("Open the costs page", async () => {
    const costs = (await (
      await page.request.get(costsUrl, { headers })
    ).json()) as Costs;
    expect(costs.budget.status).toMatch(/^(near|exceeded)$/);
    const alert = costs.alerts.find((a) =>
      ["BUDGET_NEAR", "BUDGET_EXCEEDED"].includes(a.code),
    );
    expect(alert).toBeDefined();

    await page.goto(`/trips/${tripId}/costs`);
    await expect(
      page.getByRole("heading", { level: 1, name: "Trip costs" }),
    ).toBeVisible();
    // Totals are the API's strings; the browser computes nothing (IMD-172).
    const summary = page.getByRole("region", { name: "Planning total" });
    await expect(summary).toContainText(
      `${costs.currency} ${costs.planning_total}`,
    );
    await expect(summary).toContainText(
      `${costs.currency} ${costs.estimate.min}–${costs.estimate.max}`,
    );
    await expect(
      page.getByRole("status", {
        name: alert!.code === "BUDGET_NEAR" ? "Near budget" : "Over budget",
      }),
    ).toContainText(alert!.message);

    const daily = page.getByRole("table", { name: "Daily cost estimates" });
    for (const day of costs.by_day) {
      const row = daily.getByRole("row", {
        name: new RegExp(`^Day ${day.day_number}\\b`),
      });
      await expect(row).toContainText(`${costs.currency} ${day.min}`);
      await expect(row).toContainText(`${costs.currency} ${day.max}`);
      await expect(row).toContainText("Estimate");
    }
    // Every category row carries the label of its API line (FR-076).
    const byCategory = page.getByRole("table", { name: "Costs by category" });
    await expect(byCategory.getByRole("row")).toHaveCount(
      costs.by_category.length + 1,
    );
    for (const line of costs.by_category) {
      expect(Object.keys(LABEL_TEXT)).toContain(line.label);
      await expect(
        byCategory.getByRole("row").nth(costs.by_category.indexOf(line) + 1),
      ).toContainText(LABEL_TEXT[line.label as keyof typeof LABEL_TEXT]);
    }
    await expectNoSeriousA11y(page);
  });
});
