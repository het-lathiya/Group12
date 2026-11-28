import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ImportProgress } from "@/components/trips/ImportProgress";
import type { ImportState, LiveDestination } from "@/lib/api/anyCityClient";
import { anyCityKeys } from "@/lib/api/queries";

import { axeViolations } from "../../axe";

// TC-483 (Amendment A2 §9.1, IMP-728): every import state with its exact copy, the nearby-city
// action, and API-78 polling that stops at completed, insufficient_data and failed. Fake API and
// fake interval clock; no Supabase and no network.
vi.mock("@/lib/auth/supabase", () => ({
  getSupabase: () => ({
    auth: {
      getSession: async () => ({ data: { session: { access_token: "t" } } }),
    },
  }),
}));
vi.mock("@/lib/flags", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/flags")>()),
  isEnabled: () => true,
}));
vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test/api/v1");

const DEST_ID = "00000000-0000-4000-8000-0000000000d1";

function state(
  status: ImportState["status"],
  extra: Partial<ImportState> = {},
): ImportState {
  return {
    status,
    failure_reason: null,
    places_found: null,
    places_usable: null,
    nearby_city: null,
    started_at: null,
    imported_at: null,
    expires_at: null,
    ...extra,
  };
}

function live(importState: ImportState): LiveDestination {
  return {
    destination_id: DEST_ID,
    slug: "live-nathdwara-r123",
    name: "Nathdwara",
    region: "Rajasthan",
    country_code: "IN",
    timezone: "Asia/Kolkata",
    currency: "INR",
    data_tier: "live",
    import: importState,
  };
}

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

/** API-78 answers the `states` in turn, repeating the last one. */
function fakeApi(states: ImportState[]) {
  const polls: string[] = [];
  vi.stubGlobal("fetch", async (request: Request) => {
    const path = new URL(request.url).pathname;
    if (
      request.method === "GET" &&
      path === `/api/v1/destinations/${DEST_ID}/import`
    ) {
      polls.push(path);
      return json(live(states[Math.min(polls.length - 1, states.length - 1)]));
    }
    throw new Error(`unexpected ${request.method} ${path}`);
  });
  return polls;
}

function renderProgress(
  seed: LiveDestination,
  handlers: {
    onReady?: (value: LiveDestination) => void;
    onSearchNearby?: (city: string) => void;
    onRetry?: () => void;
  } = {},
) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  // As useResolveCity does: the API-77 answer is the first status.
  client.setQueryData(anyCityKeys.importStatus(seed.destination_id), seed);
  const view = render(
    <QueryClientProvider client={client}>
      <ImportProgress
        live={seed}
        onReady={handlers.onReady ?? vi.fn()}
        onSearchNearby={handlers.onSearchNearby ?? vi.fn()}
        onRetry={handlers.onRetry}
      />
    </QueryClientProvider>,
  );
  return view;
}

async function advance(ms: number) {
  await act(() => vi.advanceTimersByTimeAsync(ms));
  for (let turn = 0; turn < 5; turn += 1) {
    await act(() => new Promise((resolve) => setTimeout(resolve, 0)));
  }
}

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("ImportProgress states (TC-483)", () => {
  it.each(["queued", "running"] as const)(
    "%s says the city is being built",
    (status) => {
      fakeApi([state(status)]);
      renderProgress(live(state(status)));
      expect(screen.getByRole("status")).toHaveTextContent(
        "Building your city: finding places…",
      );
    },
  );

  it("completed says how many places are ready and hands the destination over", async () => {
    fakeApi([]);
    const onReady = vi.fn();
    const ready = live(
      state("completed", { places_found: 80, places_usable: 42 }),
    );
    renderProgress(ready, { onReady });
    expect(screen.getByRole("status")).toHaveTextContent(
      "Ready: 42 places from OpenStreetMap",
    );
    expect(onReady).toHaveBeenCalledTimes(1);
    expect(onReady).toHaveBeenCalledWith(ready);
  });

  it("insufficient_data names the nearby city and its button searches it", async () => {
    fakeApi([]);
    const onSearchNearby = vi.fn();
    renderProgress(
      live(state("insufficient_data", { nearby_city: "Udaipur" })),
      { onSearchNearby },
    );
    expect(screen.getByRole("status")).toHaveTextContent(
      "We could not find enough places for Nathdwara yet. Try Udaipur, a larger city nearby.",
    );
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Search Udaipur" }));
    expect(onSearchNearby).toHaveBeenCalledWith("Udaipur");
  });

  it("insufficient_data without a bounded suggestion says no larger city nearby", () => {
    fakeApi([]);
    renderProgress(live(state("insufficient_data")));
    expect(screen.getByRole("status")).toHaveTextContent(
      "We could not find enough places for Nathdwara yet. No larger city nearby.",
    );
    expect(
      screen.queryByRole("button", { name: /^Search / }),
    ).not.toBeInTheDocument();
  });

  it("failed says the map data service could not be reached", () => {
    fakeApi([]);
    renderProgress(
      live(state("failed", { failure_reason: "provider_unavailable" })),
    );
    const status = screen.getByRole("status");
    expect(status).toHaveTextContent(
      "We could not reach the map data service. Try again in a few minutes.",
    );
    expect(status).not.toHaveTextContent("The service is busy.");
  });

  it("failed with rate_limited adds the busy sentence", () => {
    fakeApi([]);
    renderProgress(live(state("failed", { failure_reason: "rate_limited" })));
    expect(screen.getByRole("status")).toHaveTextContent(
      "We could not reach the map data service. Try again in a few minutes. The service is busy.",
    );
  });

  it("failed offers a retry when the caller can resolve again", async () => {
    fakeApi([]);
    const onRetry = vi.fn();
    renderProgress(live(state("failed", { failure_reason: "timeout" })), {
      onRetry,
    });
    await userEvent
      .setup()
      .click(screen.getByRole("button", { name: "Try again" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("announces changes politely and has no axe violation", async () => {
    fakeApi([]);
    const { container } = renderProgress(
      live(state("insufficient_data", { nearby_city: "Udaipur" })),
    );
    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
    expect(await axeViolations(container)).toEqual([]);
  });
});

describe("ImportProgress polling (TC-483, §9.1 delays 2/3/4/5 s)", () => {
  it.each([
    ["completed", state("completed", { places_usable: 30 })],
    [
      "insufficient_data",
      state("insufficient_data", { nearby_city: "Udaipur" }),
    ],
    ["failed", state("failed", { failure_reason: "internal" })],
  ] as const)("polls 2, 3 and 4 s apart and stops at %s", async (_, end) => {
    vi.useFakeTimers({ toFake: ["setInterval", "clearInterval", "Date"] });
    const polls = fakeApi([state("running"), state("running"), end]);
    const onReady = vi.fn();
    renderProgress(live(state("queued")), { onReady });

    await advance(1900);
    expect(polls).toHaveLength(0);
    await advance(100);
    expect(polls).toHaveLength(1);
    await advance(3000);
    expect(polls).toHaveLength(2);
    await advance(4000);
    expect(polls).toHaveLength(3);

    await advance(60_000);
    expect(polls).toHaveLength(3);
    expect(onReady).toHaveBeenCalledTimes(end.status === "completed" ? 1 : 0);
  });

  it("keeps polling every 5 s after the first four delays", async () => {
    vi.useFakeTimers({ toFake: ["setInterval", "clearInterval", "Date"] });
    const polls = fakeApi([state("running")]);
    renderProgress(live(state("queued")));
    await advance(2000 + 3000 + 4000 + 5000);
    expect(polls).toHaveLength(4);
    await advance(5000);
    expect(polls).toHaveLength(5);
    await advance(5000);
    expect(polls).toHaveLength(6);
    expect(screen.getByRole("status")).toHaveTextContent(
      "Building your city: finding places…",
    );
  });
});
