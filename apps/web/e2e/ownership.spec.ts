import type { Response } from "@playwright/test";

import { expectNoSeriousA11y } from "./axe";
import { expect, plannedTrip, signIn, signOut, test } from "./fixtures/trips";

// E2E-08 (§13.4; FR-005; TC-375; ACC-08): user B opens user A's itinerary, costs and versions URLs
// and gets a not-found state each time, with no data of A's trip in the page or in the API answers.

const TITLE = "Private trip of user A";

test("E2E-08 TC-375: another user's itinerary, costs and versions URLs show nothing of the trip", async ({
  page,
  users,
}) => {
  test.setTimeout(120_000);
  const [userA, userB] = [
    await users.create("owner-a"),
    await users.create("owner-b"),
  ];

  const { tripId, itinerary } =
    await test.step("Sign in as A and plan a trip", async () => {
      const session = await signIn(page, userA);
      const planned = await plannedTrip(page, session, { title: TITLE });
      await signOut(page);
      return planned;
    });
  const placeNames = itinerary!.days.flatMap((day) =>
    day.items.map((item) => item.place.name),
  );

  await test.step("Sign in as B", () => signIn(page, userB));

  // Every API answer about A's trip that B's pages receive.
  const answers: Response[] = [];
  page.on("response", (response) => {
    const request = response.request();
    if (
      request.url().includes(`/api/v1/trips/${tripId}`) &&
      request.method() !== "OPTIONS"
    )
      answers.push(response);
  });

  const pages = [
    {
      path: "itinerary",
      shows: page.getByRole("heading", { name: "Trip not found" }),
    },
    {
      path: "costs",
      shows: page.getByRole("heading", { name: "We could not find that" }),
    },
    // The versions page reads API-24 first, and a 404 there shows its no-plan state (see the
    // IMP-701 part record, open issues).
    {
      path: "versions",
      shows: page
        .getByRole("heading", { name: "We could not find that" })
        .or(page.getByRole("heading", { name: "No itinerary yet" })),
    },
  ];
  for (const { path, shows } of pages) {
    await test.step(`As B, open A's /trips/[tripId]/${path} URL`, async () => {
      answers.length = 0;
      await page.goto(`/trips/${tripId}/${path}`);
      await expect(shows).toBeVisible();
      await expect(page.getByText(TITLE)).toHaveCount(0);
      for (const name of placeNames) {
        await expect(page.getByText(name, { exact: true })).toHaveCount(0);
      }
      expect(
        answers.length,
        "the page asked the API about the trip",
      ).toBeGreaterThan(0);
      for (const answer of answers) {
        expect(answer.status(), answer.url()).toBe(404);
        const body = await answer.text();
        expect(body).not.toContain(TITLE);
        for (const name of placeNames) expect(body).not.toContain(name);
      }
      await expectNoSeriousA11y(page);
    });
  }
});
