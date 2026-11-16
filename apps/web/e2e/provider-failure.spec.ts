import type { Page } from "@playwright/test";

import type { components } from "../lib/api/schema";
import { expectNoSeriousA11y } from "./axe";
import {
  expect,
  finishedGeneration,
  plannedTrip,
  readItinerary,
  type Session,
  signIn,
  test,
} from "./fixtures/trips";

// E2E-07 (§13.4; FR-036, FR-037; TC-371, TC-308; ACC-03, ACC-17), Playwright project
// "provider-failure" only (IMD-33): the web app on 3001 calls its own API on 8001, which runs
// AI_PROVIDER=MOCK with a failing MOCK_PROVIDER_SCENARIO. The scenario is fixed per API process, so
// the run sets the same MOCK_PROVIDER_SCENARIO for the API and for this run, once with timeout and
// once with quota (.github/workflows/e2e.yml); the test of the other scenario is skipped.
// Local run: start the API with `MOCK_PROVIDER_SCENARIO=timeout ALLOWED_ORIGINS=http://localhost:3001
// uvicorn app.main:app --port 8001`, the web app with NEXT_PUBLIC_API_BASE_URL=
// http://localhost:8001/api/v1 on port 3001, then
// `MOCK_PROVIDER_SCENARIO=timeout make e2e ARGS='--project=provider-failure'`.

type Version = components["schemas"]["VersionOut"];

const SCENARIO = process.env.MOCK_PROVIDER_SCENARIO ?? "";
// FALLBACK_TEXT of components/generation/FallbackNotice.tsx.
const FALLBACK_TEXT =
  "Built by rules because the AI service was unavailable or its answer failed checks";
// ERROR_CATALOGUE.AI_QUOTA_REACHED.what (lib/api/errors.ts), shown by PausedAiNotice.
const PAUSED_TEXT = "Today's AI planning limit is reached";

/** A trip with an earlier rule-based plan and a named version, as E2E-07's precondition. */
async function tripWithSavedVersion(page: Page, session: Session) {
  const { tripId, itinerary } = await plannedTrip(page, session, {
    title: `Provider ${SCENARIO} in Sampleton`,
    mode: "rule_based",
  });
  const saved = await page.request.post(
    `${session.base}/trips/${tripId}/versions`,
    {
      headers: session.headers,
      data: {
        name: "Before the failure",
        plan_revision: itinerary!.plan_revision,
      },
    },
  );
  expect(saved.status()).toBe(201);
  return { tripId, ...(await snapshot(page, session, tripId)) };
}

/** The trip's details, versions and plan revision, to show that a failure changed none of them. */
async function snapshot(
  page: Page,
  { base, headers }: Session,
  tripId: string,
) {
  const trip = (await (
    await page.request.get(`${base}/trips/${tripId}`, { headers })
  ).json()) as components["schemas"]["TripOut"];
  const versions = (await (
    await page.request.get(`${base}/trips/${tripId}/versions`, { headers })
  ).json()) as Version[];
  return {
    trip: {
      title: trip.title,
      destination_id: trip.destination_id,
      start_date: trip.start_date,
      end_date: trip.end_date,
      adults: trip.adults,
      budget: trip.budget,
    },
    versions,
  };
}

/** Start the AI generation from the generate page (the notice is already acknowledged). */
async function generateWithAi(page: Page, tripId: string) {
  await page.goto(`/trips/${tripId}/generate`);
  const started = page.waitForResponse(
    (r) =>
      new URL(r.url()).pathname === `/api/v1/trips/${tripId}/generations` &&
      r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Generate with AI" }).click();
  const response = await started;
  expect(response.status()).toBe(202);
  return ((await response.json()) as { id: string }).id;
}

/** Retime the first item of day 1 from the itinerary page; the edit must save (API-26). */
async function editStillWorks(page: Page, session: Session, tripId: string) {
  const plan = await readItinerary(page, session, tripId);
  const item = plan.days[0].items[0];
  if ((page.viewportSize()?.width ?? 0) < 768) {
    await page.getByRole("tab", { name: "Day 1" }).click();
  }
  await page
    .getByRole("button", { name: `Edit time of ${item.place.name}` })
    .click();
  const form = page.getByRole("form", {
    name: `Edit time of ${item.place.name}`,
  });
  await form
    .getByLabel("Duration (minutes)")
    .fill(
      String(
        item.duration_min < 465
          ? item.duration_min + 15
          : item.duration_min - 15,
      ),
    );
  const saved = page.waitForResponse(
    (r) =>
      new URL(r.url()).pathname === `/api/v1/itinerary/items/${item.id}` &&
      r.request().method() === "PATCH",
  );
  await form.getByRole("button", { name: "Save" }).click();
  expect((await saved).status()).toBe(200);
}

test("E2E-07 TC-371: a provider timeout gives the labelled rule-based plan and keeps the earlier version", async ({
  page,
  users,
}) => {
  test.skip(
    SCENARIO !== "timeout",
    "the API on 8001 runs another MOCK_PROVIDER_SCENARIO",
  );
  test.setTimeout(120_000);
  const user = await users.create("timeout");
  const session = await test.step("Sign in", () => signIn(page, user));
  const before = await test.step("Create a trip with a saved version", () =>
    tripWithSavedVersion(page, session));

  const generationId = await test.step("Generate with AI", () =>
    generateWithAi(page, before.tripId));

  await test.step("See the fallback notice on the saved rule-based plan", async () => {
    await expect(page).toHaveURL(`/trips/${before.tripId}/itinerary`, {
      timeout: 60_000,
    });
    await expect(page.getByText(FALLBACK_TEXT)).toBeVisible();
    const generation = await finishedGeneration(page, session, generationId);
    expect(generation.status).toBe("completed");
    expect(generation.outcome).toBe("fallback_rule_based");
    expect(generation.fallback_reason).toBe("provider_timeout");
    const after = await snapshot(page, session, before.tripId);
    expect(after.trip).toEqual(before.trip);
    for (const version of before.versions) {
      expect(after.versions).toContainEqual(version);
    }
    await expectNoSeriousA11y(page);
  });

  await test.step("Edit and save an item", () =>
    editStillWorks(page, session, before.tripId));
});

test("E2E-07 TC-371: a provider quota pause offers the rule-based plan and changes nothing", async ({
  page,
  users,
}) => {
  test.skip(
    SCENARIO !== "quota",
    "the API on 8001 runs another MOCK_PROVIDER_SCENARIO",
  );
  test.setTimeout(120_000);
  const user = await users.create("quota");
  const session = await test.step("Sign in", () => signIn(page, user));
  const before = await test.step("Create a trip with a saved version", () =>
    tripWithSavedVersion(page, session));
  const revision = (await readItinerary(page, session, before.tripId))
    .plan_revision;

  const generationId = await test.step("Generate with AI", () =>
    generateWithAi(page, before.tripId));

  await test.step("See the paused-AI message with the rule-based option", async () => {
    // GenerationProgress's terminal state for a quota failure (IMP-403).
    const paused = page.getByRole("status").filter({ hasText: PAUSED_TEXT });
    await expect(paused).toBeVisible({ timeout: 60_000 });
    await expect(
      paused.getByRole("button", { name: "Build a rule-based plan" }),
    ).toBeVisible();
    const generation = await finishedGeneration(page, session, generationId);
    expect(generation.status).toBe("failed");
    expect(generation.failure_reason).toBe("provider_quota_exhausted");
    expect(generation.next_action).toBe("retry_rule_based");
    // IMD-44: quota ends the job at once, with no retry and no repair call.
    expect(generation.repair_attempts).toBe(0);
    const after = await snapshot(page, session, before.tripId);
    expect(after).toEqual({ trip: before.trip, versions: before.versions });
    expect(
      (await readItinerary(page, session, before.tripId)).plan_revision,
    ).toBe(revision);
    await expectNoSeriousA11y(page);
  });

  await test.step("Build the rule-based plan", async () => {
    const started = page.waitForResponse(
      (r) =>
        new URL(r.url()).pathname ===
          `/api/v1/trips/${before.tripId}/generations` &&
        r.request().method() === "POST",
    );
    await page.getByRole("button", { name: "Build a rule-based plan" }).click();
    const response = await started;
    expect(response.status()).toBe(202);
    expect(response.request().postDataJSON()).toEqual({ mode: "rule_based" });
    await expect(page).toHaveURL(`/trips/${before.tripId}/itinerary`, {
      timeout: 60_000,
    });
    await expect(page.getByText(FALLBACK_TEXT)).toBeVisible();
    const generation = await finishedGeneration(
      page,
      session,
      ((await response.json()) as { id: string }).id,
    );
    // Mode rule_based makes no provider call (FR-036, pipeline step 2).
    expect(generation.mode).toBe("rule_based");
    expect(generation.outcome).toBe("fallback_rule_based");
  });

  await test.step("Edit and save an item", () =>
    editStillWorks(page, session, before.tripId));
});
