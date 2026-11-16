import {
  expect,
  type APIRequestContext,
  type Page,
  type Request,
} from "@playwright/test";

import type { components } from "../../lib/api/schema";
import { stagingAccount, test as usersTest } from "./users";

/**
 * Trip reset for the journey (IMP-414 step 2). Trips are listed (API-08) and deleted (API-12)
 * through the API with the signed-in page's own token, never by database access. The token stays
 * in memory and is never printed.
 */
export class TestTrips {
  private session?: { base: string; authorization: string };

  constructor(private readonly request: APIRequestContext) {}

  /** Take the API base and bearer token from a request the signed-in page sent to the API. */
  useSessionOf(request: Request): void {
    const authorization = request.headers()["authorization"];
    if (!authorization) throw new Error("The API request carried no token.");
    const url = new URL(request.url());
    this.session = {
      base: `${url.origin}${url.pathname.slice(0, url.pathname.indexOf("/api/v1/") + 7)}`,
      authorization,
    };
  }

  /** Delete every trip of the signed-in account, archived ones included. Returns how many. */
  async deleteAll(): Promise<number> {
    if (!this.session) throw new Error("Call useSessionOf first.");
    const { base, authorization } = this.session;
    const headers = { authorization };
    let deleted = 0;
    // API-12 hides a deleted trip from API-08, so each pass lists what is left.
    for (;;) {
      const list = await this.request.get(
        `${base}/trips?limit=50&include_archived=true`,
        { headers },
      );
      if (!list.ok()) throw new Error(`API-08 answered ${list.status()}.`);
      const { items } = (await list.json()) as { items: { id: string }[] };
      if (items.length === 0) return deleted;
      for (const { id } of items) {
        const response = await this.request.delete(`${base}/trips/${id}`, {
          headers,
        });
        if (response.status() !== 204) {
          throw new Error(
            `API-12 answered ${response.status()} when deleting a test trip.`,
          );
        }
        deleted += 1;
      }
    }
  }

  get hasSession(): boolean {
    return this.session !== undefined;
  }
}

export const test = usersTest.extend<{ trips: TestTrips }>({
  trips: async ({ request }, provide) => {
    const trips = new TestTrips(request);
    await provide(trips);
    // A local account is deleted with its trips by the users fixture (on delete cascade); the
    // shared staging account keeps living, so what the run created is deleted here.
    if (stagingAccount() && trips.hasSession) await trips.deleteAll();
  },
});

export { expect };

/**
 * Shared steps of the IMP-701 specs (contract §J): sign in through the UI, then set up a planned
 * SAMPLE trip through the API with the page's own token, as itinerary-edit.spec.ts does. No
 * database access and no second user helper: users come from the `users` fixture.
 */
export type Session = { base: string; headers: { authorization: string } };
type Itinerary = components["schemas"]["ItineraryOut"];
type Generation = components["schemas"]["GenerationOut"];

/** A date from today, so a run never reaches a fixed date. */
export const daysFromNow = (days: number) =>
  new Date(Date.now() + days * 86_400_000).toISOString().slice(0, 10);

/** Sign in with the form and return the API base and token of the page's first API call. */
export async function signIn(
  page: Page,
  user: { email: string; password: string },
): Promise<Session> {
  const apiCall = page.waitForRequest(
    (r) => r.url().includes("/api/v1/") && !!r.headers()["authorization"],
  );
  await page.goto("/sign-in?next=%2Fdashboard");
  await page.getByLabel("Email").fill(user.email);
  await page.getByLabel("Password", { exact: true }).fill(user.password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { level: 1, name: "Your trips" }),
  ).toBeVisible();
  const request = await apiCall;
  return {
    base: `${new URL(request.url()).origin}/api/v1`,
    headers: { authorization: request.headers()["authorization"] },
  };
}

/** Sign out from the account menu (IMP-109). */
export async function signOut(page: Page): Promise<void> {
  await page.getByRole("button", { name: "Account menu" }).click();
  await page.getByRole("menuitem", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/sign-in$/);
}

export async function readItinerary(
  page: Page,
  { base, headers }: Session,
  tripId: string,
): Promise<Itinerary> {
  const response = await page.request.get(`${base}/trips/${tripId}/itinerary`, {
    headers,
  });
  expect(response.status()).toBe(200);
  return (await response.json()) as Itinerary;
}

/** Wait for a generation's terminal status (API-23) and return it. */
export async function finishedGeneration(
  page: Page,
  { base, headers }: Session,
  generationId: string,
): Promise<Generation> {
  let generation: Generation | undefined;
  await expect
    .poll(
      async () => {
        const response = await page.request.get(
          `${base}/generations/${generationId}`,
          { headers },
        );
        generation = (await response.json()) as Generation;
        return generation.status;
      },
      { timeout: 45_000 },
    )
    .toMatch(/^(completed|failed)$/);
  return generation!;
}

/**
 * A three-day Sampleton trip for two adults with the AI notice acknowledged (API-03) unless
 * `acknowledgeNotice` is false, optionally
 * one must-visit place found by name (API-16), and, unless `generate` is false, a completed plan
 * built in `mode` (API-22, API-23).
 */
export async function plannedTrip(
  page: Page,
  session: Session,
  options: {
    title?: string;
    mustVisit?: string;
    mode?: "ai" | "rule_based";
    generate?: boolean;
    acknowledgeNotice?: boolean;
  } = {},
): Promise<{ tripId: string; itinerary?: Itinerary }> {
  const { base, headers } = session;
  const destinations = (await (
    await page.request.get(`${base}/destinations`, { headers })
  ).json()) as components["schemas"]["Destination"][];
  const destination = destinations.find((item) => item.slug === "sampleton");
  expect(destination, "the Sampleton seed (make seed)").toBeDefined();
  const created = await page.request.post(`${base}/trips`, {
    headers,
    data: {
      title: options.title ?? "Trip in Sampleton",
      destination_id: destination!.id,
      start_date: daysFromNow(30),
      end_date: daysFromNow(32),
      adults: 2,
    },
  });
  expect(created.status()).toBe(201);
  const { id: tripId } = (await created.json()) as { id: string };

  const mustVisit: string[] = [];
  if (options.mustVisit) {
    const found = await page.request.get(`${base}/places`, {
      headers,
      params: {
        destination_id: destination!.id,
        q: options.mustVisit,
        limit: 1,
      },
    });
    expect(found.status()).toBe(200);
    const { items } = (await found.json()) as { items: { id: string }[] };
    expect(items.length, `a place matching "${options.mustVisit}"`).toBe(1);
    mustVisit.push(items[0].id);
  }
  const preferences = await page.request.put(
    `${base}/trips/${tripId}/preferences`,
    {
      headers,
      data: {
        interests: ["museum", "nature"],
        must_visit_place_ids: mustVisit,
      },
    },
  );
  expect(preferences.status()).toBe(200);
  if (options.acknowledgeNotice !== false) {
    const notice = await page.request.patch(`${base}/me`, {
      headers,
      data: { ai_notice_acknowledged: true },
    });
    expect(notice.status()).toBe(200);
  }
  if (options.generate === false) return { tripId };

  const started = await page.request.post(
    `${base}/trips/${tripId}/generations`,
    { headers, data: { mode: options.mode ?? "ai" } },
  );
  expect(started.status()).toBe(202);
  const generation = await finishedGeneration(
    page,
    session,
    ((await started.json()) as { id: string }).id,
  );
  expect(generation.status).toBe("completed");
  return { tripId, itinerary: await readItinerary(page, session, tripId) };
}
