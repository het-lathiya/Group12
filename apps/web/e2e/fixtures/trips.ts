import type { APIRequestContext, Request } from "@playwright/test";

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

export { expect } from "@playwright/test";
