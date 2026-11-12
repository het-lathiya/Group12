import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import ItineraryPage from "@/app/(app)/trips/[tripId]/itinerary/page";
import type { components } from "@/lib/api/schema";

import { ITEM } from "./fixtures";

// §7.5, §7.5.7, §7.8: which state the page shows for each answer of API-24 and API-10.
vi.mock("@/lib/auth/supabase", () => ({
  getSupabase: () => ({
    auth: {
      getSession: async () => ({ data: { session: { access_token: "t" } } }),
    },
  }),
}));
vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test/api/v1");

const TRIP_ID = "00000000-0000-4000-8000-000000000002";
vi.mock("next/navigation", () => ({ useParams: () => ({ tripId: TRIP_ID }) }));

type Itinerary = components["schemas"]["ItineraryOut"];

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
const notFound = () =>
  json(
    { error: { code: "NOT_FOUND", message: "Not found.", request_id: null } },
    404,
  );

const plan = (
  items: Itinerary["days"][number]["items"],
  outcome: NonNullable<Itinerary["source"]>["outcome"] = "model",
): Itinerary => ({
  trip_id: TRIP_ID,
  plan_revision: 1,
  version_id: null,
  is_current: true,
  plan_stale: false,
  source: {
    generation_id: "00000000-0000-4000-8000-0000000000a1",
    provider: "MOCK",
    outcome,
  },
  days: [
    {
      day_number: 1,
      date: "2026-11-14",
      theme: null,
      theme_origin: "none",
      day_cost: { min: "0.00", max: "0.00", currency: "INR", complete: true },
      items,
    },
  ],
  findings: [],
  totals: {
    currency: "INR",
    estimate: { min: "0.00", max: "0.00" },
    planning_total: "0.00",
    complete: true,
    incomplete_count: 0,
  },
});

function renderPage(itinerary: () => Response, trip: () => Response) {
  vi.stubGlobal("matchMedia", () => ({
    matches: true,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
  }));
  vi.stubGlobal("fetch", async (request: Request) =>
    new URL(request.url).pathname.endsWith("/itinerary") ? itinerary() : trip(),
  );
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ItineraryPage />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("ItineraryPage", () => {
  it("shows the not-found screen for a foreign or missing trip", async () => {
    renderPage(notFound, notFound);

    expect(await screen.findByText("Trip not found")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Back to dashboard" }),
    ).toHaveAttribute("href", "/dashboard");
    expect(screen.queryByText("Nothing planned yet")).not.toBeInTheDocument();
  });

  it("offers to generate for the caller's trip with no plan", async () => {
    renderPage(notFound, () => json({ id: TRIP_ID }));

    expect(await screen.findByText("Nothing planned yet")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Generate" })).toHaveAttribute(
      "href",
      `/trips/${TRIP_ID}/generate`,
    );
  });

  it("treats a plan with no items as nothing planned", async () => {
    renderPage(
      () => json(plan([])),
      () => json({ id: TRIP_ID }),
    );

    expect(await screen.findByText("Nothing planned yet")).toBeInTheDocument();
  });

  it("shows ErrorState when the trip cannot be checked", async () => {
    renderPage(notFound, () =>
      json(
        { error: { code: "INTERNAL", message: "Boom.", request_id: "r1" } },
        500,
      ),
    );

    expect(
      await screen.findByText("Your itinerary could not be loaded", undefined, {
        timeout: 4000,
      }),
    ).toBeInTheDocument();
  });

  it("shows FallbackNotice on a rule-based plan only", async () => {
    renderPage(
      () => json(plan([ITEM], "fallback_rule_based")),
      () => json({ id: TRIP_ID }),
    );

    expect(
      await screen.findByText(
        "Built by rules because the AI service was unavailable or failed checks",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: ITEM.place.name }),
    ).toBeInTheDocument();
  });

  it("says when a model plan was repaired", async () => {
    renderPage(
      () => json(plan([ITEM], "model_repaired")),
      () => json({ id: TRIP_ID }),
    );

    expect(
      await screen.findByText("Some details were adjusted"),
    ).toBeInTheDocument();
  });

  it("shows no notice on a model plan", async () => {
    renderPage(
      () => json(plan([ITEM])),
      () => json({ id: TRIP_ID }),
    );

    await screen.findByRole("heading", { name: ITEM.place.name });
    expect(screen.queryByText(/Built by rules/)).not.toBeInTheDocument();
  });

  it("IMP-405: shows the plan checks, and Go to item moves focus to the item's card", async () => {
    const withFinding: Itinerary = {
      ...plan([ITEM]),
      findings: [
        {
          id: "00000000-0000-4000-8000-0000000000f1",
          code: "HOURS_UNVERIFIED",
          severity: "info",
          message: "Opening hours unavailable.",
          day_number: 1,
          item_id: ITEM.id,
          place_id: null,
          suggested_fix: "Check opening times before the visit.",
        },
      ],
    };
    renderPage(
      () => json(withFinding),
      () => json({ id: TRIP_ID }),
    );

    fireEvent.click(await screen.findByRole("button", { name: "Go to item" }));

    await waitFor(() =>
      expect(document.getElementById(`item-${ITEM.id}`)).toHaveFocus(),
    );
    expect(
      screen.getByRole("region", { name: /Plan checks/ }),
    ).toBeInTheDocument();
  });
});
