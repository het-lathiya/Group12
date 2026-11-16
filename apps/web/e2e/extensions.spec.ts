import { expect, plannedTrip, signIn, test } from "./fixtures/trips";

// TC-432 (§11.2, §13.4), tag @ext. The nine extensions are cut and not built (IMD-65), so their
// switches stay off and each scenario is skipped with that reason; a scenario is written in the
// extension card's own pull request if one is ever re-planned. The last test runs with the
// default settings and shows that no extension entry point is rendered and that the extension
// pages (/today, /packing) are not found.

const REASON = "cut by IMD-65 (switch off)";

const EXTENSIONS = [
  ["ranking_explain", "why-this-place"],
  ["nl_intake", "describe a trip"],
  ["day_explain", "explain a day"],
  ["optimise_order", "optimise a day"],
  ["rain_swap", "rain banner"],
  ["today_view", "Today view"],
  ["budget_fit", "budget-fit apply"],
  ["context_cards", "context card"],
  ["packing", "packing refine"],
] as const;

// Names an extension's button or link would carry (§7.5 extension screens).
const ENTRY_POINT =
  /why this place|describe (a|your) trip|explain (this |the )?day|optimi[sz]e|\brain\b|today view|open today|budget[- ]fit|context|packing/i;

test.describe("extensions", { tag: "@ext" }, () => {
  for (const [name, scenario] of EXTENSIONS) {
    test(`TC-432 ${name}: ${scenario}`, () => {
      test.skip(true, REASON);
    });
  }

  test("TC-432: with the default settings no extension entry point is rendered and the extension pages are not found", async ({
    page,
    users,
  }) => {
    test.setTimeout(90_000);
    const user = await users.create("extensions");
    const session = await test.step("Sign in", () => signIn(page, user));
    const { tripId } = await test.step("Have a planned trip", () =>
      plannedTrip(page, session, { title: "Extensions in Sampleton" }));

    // Each page is checked once its data has rendered.
    const pages = [
      ["/dashboard", page.getByRole("button", { name: "Open latest" })],
      ["/trips/new", page.getByLabel("Destination")],
      [
        `/trips/${tripId}/itinerary`,
        page.getByRole("heading", { level: 3 }).first(),
      ],
      [
        `/trips/${tripId}/costs`,
        page.getByRole("region", { name: "Planning total" }),
      ],
    ] as const;
    for (const [path, ready] of pages) {
      await test.step(`Open ${path} and find no extension entry point`, async () => {
        await page.goto(path);
        await expect(ready).toBeVisible();
        await expect(
          page.getByRole("button", { name: ENTRY_POINT }),
        ).toHaveCount(0);
        await expect(page.getByRole("link", { name: ENTRY_POINT })).toHaveCount(
          0,
        );
      });
    }

    for (const path of ["today", "packing"]) {
      await test.step(`Open the /trips/[tripId]/${path} URL and get not found`, async () => {
        const response = await page.goto(`/trips/${tripId}/${path}`);
        expect(response?.status()).toBe(404);
      });
    }
  });
});
