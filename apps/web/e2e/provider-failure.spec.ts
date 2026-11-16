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

const SCENARIO = process.env.MOCK_PROVIDER_SCENARIO ?? "";
// FALLBACK_TEXT of components/generation/FallbackNotice.tsx.
const FALLBACK_TEXT =
  "Built by rules because the AI service was unavailable or its answer failed checks";
// ERROR_CATALOGUE.AI_QUOTA_REACHED.what (lib/api/errors.ts), shown by PausedAiNotice.
const PAUSED_TEXT = "Today's AI planning limit is reached";
// Mode rule_based stores this model id and makes no provider call (app/generation/service.py).
const RULE_BASED_MODEL = "rule_based_planner_v1";

/**
 * IMD-206: a fresh trip with no itinerary, so API-22 accepts the generation (it answers 409
 * CONFLICT for a trip that already has one, §6.4).
 */
async function freshTrip(page: Page, session: Session) {
  const { tripId } = await plannedTrip(page, session, {
    title: `Provider ${SCENARIO} in Sampleton`,
    generate: false,
  });
  return { tripId, trip: await tripDetails(page, session, tripId) };
}

/** The trip's details, to show that a failure changed none of them. */
async function tripDetails(
  page: Page,
  { base, headers }: Session,
  tripId: string,
) {
  const trip = (await (
    await page.request.get(`${base}/trips/${tripId}`, { headers })
  ).json()) as components["schemas"]["TripOut"];
  return {
    title: trip.title,
    destination_id: trip.destination_id,
    start_date: trip.start_date,
    end_date: trip.end_date,
    adults: trip.adults,
    budget: trip.budget,
  };
}

/** Wait for a POST of API-22 and return its generation id; a non-202 answer logs its body. */
async function startedGeneration(page: Page, tripId: string, mode: string) {
  const response = await page.waitForResponse(
    (r) =>
      new URL(r.url()).pathname === `/api/v1/trips/${tripId}/generations` &&
      r.request().method() === "POST",
  );
  expect(response.status(), await response.text()).toBe(202);
  expect(response.request().postDataJSON()).toEqual({ mode });
  return ((await response.json()) as { id: string }).id;
}

/** Start the AI generation from the generate page (the notice is already acknowledged). */
async function generateWithAi(page: Page, tripId: string) {
  await page.goto(`/trips/${tripId}/generate`);
  const started = startedGeneration(page, tripId, "ai");
  await page.getByRole("button", { name: "Generate with AI" }).click();
  return started;
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

test("E2E-07 TC-371: a provider timeout gives the labelled rule-based plan and saves it", async ({
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
  const before = await test.step("Create a trip without a plan", () =>
    freshTrip(page, session));

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
    const plan = await readItinerary(page, session, before.tripId);
    expect(plan.days.flatMap((day) => day.items).length).toBeGreaterThan(0);
    expect(await tripDetails(page, session, before.tripId)).toEqual(
      before.trip,
    );
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
  const before = await test.step("Create a trip without a plan", () =>
    freshTrip(page, session));

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
    expect(await tripDetails(page, session, before.tripId)).toEqual(
      before.trip,
    );
    // Nothing was saved: the trip still has no itinerary (API-24).
    const plan = await page.request.get(
      `${session.base}/trips/${before.tripId}/itinerary`,
      { headers: session.headers },
    );
    expect(plan.status()).toBe(404);
    await expectNoSeriousA11y(page);
  });

  await test.step("Build the rule-based plan", async () => {
    const started = startedGeneration(page, before.tripId, "rule_based");
    await page.getByRole("button", { name: "Build a rule-based plan" }).click();
    const generationId = await started;
    await expect(page).toHaveURL(`/trips/${before.tripId}/itinerary`, {
      timeout: 60_000,
    });
    await expect(page.getByText(FALLBACK_TEXT)).toBeVisible();
    const generation = await finishedGeneration(page, session, generationId);
    // Mode rule_based makes no further provider call (FR-036, ACC-17).
    expect(generation.mode).toBe("rule_based");
    expect(generation.model_id).toBe(RULE_BASED_MODEL);
    expect(generation.outcome).toBe("fallback_rule_based");
  });

  await test.step("Edit and save an item", () =>
    editStillWorks(page, session, before.tripId));
});
