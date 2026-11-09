import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DashboardPage from "@/app/(app)/dashboard/page";

// FR-013, FR-014 (TC-087, TC-088) web side: Open latest (API-09) and Continue draft (API-08).
vi.mock("@/lib/auth/supabase", () => ({
  getSupabase: () => ({
    auth: {
      getSession: async () => ({ data: { session: { access_token: "t" } } }),
    },
  }),
}));
const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test/api/v1");

const TRIP = {
  id: "00000000-0000-4000-8000-000000000002",
  title: "Weekend in Sampleton",
  destination_id: "00000000-0000-4000-8000-000000000001",
  start_date: "2026-12-04",
  end_date: "2026-12-06",
  num_days: 3,
  adults: 2,
  children: 0,
  group_needs: [],
  budget: null,
  status: "draft",
  plan_revision: 0,
  plan_stale: false,
  has_itinerary: false,
  destination: {
    id: "00000000-0000-4000-8000-000000000001",
    name: "Sampleton",
    timezone: "Europe/London",
    currency: "GBP",
    is_sample: true,
  },
  created_at: "2026-11-03T10:00:00Z",
  updated_at: "2026-11-03T10:00:00Z",
};

let latest: { trip_id: string | null };
let trips: (typeof TRIP)[];

const json = (body: unknown) =>
  new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
  });

beforeEach(() => {
  push.mockReset();
  latest = { trip_id: null };
  trips = [TRIP];
  vi.stubGlobal("fetch", async (request: Request) => {
    const path = new URL(request.url).pathname;
    if (path === "/api/v1/itineraries/latest") {
      return json({ plan_revision: null, updated_at: null, ...latest });
    }
    return json({ items: trips, total: trips.length, limit: 20, offset: 0 });
  });
});

function renderDashboard() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <DashboardPage />
    </QueryClientProvider>,
  );
  return userEvent.setup();
}

describe("dashboard (FR-013, FR-014)", () => {
  it("TC-088: Open latest with no saved itinerary offers Plan a trip, not an error", async () => {
    const user = renderDashboard();
    const open = await screen.findByRole("button", { name: "Open latest" });
    await vi.waitFor(() => expect(open).toBeEnabled());

    await user.click(open);

    expect(
      screen.getByRole("heading", { name: "No saved itinerary yet" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Plan a trip" })).toHaveAttribute(
      "href",
      "/trips/new",
    );
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(push).not.toHaveBeenCalled();
  });

  it("TC-087: Open latest opens the newest saved itinerary", async () => {
    latest = { trip_id: TRIP.id };
    const user = renderDashboard();
    const open = await screen.findByRole("button", { name: "Open latest" });
    await vi.waitFor(() => expect(open).toBeEnabled());

    await user.click(open);

    expect(push).toHaveBeenCalledWith(`/trips/${TRIP.id}/itinerary`);
  });

  it("TC-086: a draft shows a Draft badge and Continue draft opens the wizard on it", async () => {
    renderDashboard();

    const card = (await screen.findByText("Weekend in Sampleton")).closest(
      "li",
    ) as HTMLElement;
    expect(within(card).getByText("Draft")).toBeInTheDocument();
    expect(
      within(card).getByRole("link", { name: /continue draft/i }),
    ).toHaveAttribute("href", `/trips/new?draft=${TRIP.id}`);
  });

  it("no trips at all shows the empty state with Create a trip", async () => {
    trips = [];
    renderDashboard();

    expect(
      await screen.findByRole("heading", { name: "No trips yet" }),
    ).toBeInTheDocument();
  });
});
