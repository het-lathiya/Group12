import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import CostsPage from "@/app/(app)/trips/[tripId]/costs/page";
import { CostBreakdown } from "@/components/costs/CostBreakdown";
import { LiveTierProvider } from "@/components/labels/liveTier";
import type { AnyCitySchemas } from "@/lib/api/anyCityClient";
import type { components } from "@/lib/api/schema";

import { axeViolations } from "../../axe";

// TC-485 (Amendment A2 §6.6, §9.2, IMP-729): on a live plan the costs page says "Known costs only:
// N stops have no price" (N = the items API-33 lists as incomplete) and the budget status carries
// "covers known costs only". Curated plans and the switch OFF are unchanged.
vi.mock("@/lib/auth/supabase", () => ({
  getSupabase: () => ({
    auth: {
      getSession: async () => ({ data: { session: { access_token: "t" } } }),
    },
  }),
}));
const TRIP_ID = "00000000-0000-4000-8000-000000000002";
const DESTINATION_ID = "00000000-0000-4000-8000-0000000000d1";
vi.mock("next/navigation", () => ({ useParams: () => ({ tripId: TRIP_ID }) }));
const flag = vi.hoisted(() => ({ anyCity: true }));
vi.mock("@/lib/flags", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/flags")>();
  return {
    ...actual,
    isEnabled: (name: Parameters<typeof actual.isEnabled>[0]) =>
      name === "any_city_mode" ? flag.anyCity : actual.isEnabled(name),
  };
});
vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test/api/v1");

type Costs = components["schemas"]["CostSummaryOut"];

const KNOWN = "Known costs only: 3 stops have no price";
const BUDGET_NOTE = "Budget status: near your budget, covers known costs only";

const costs: Costs = {
  currency: "INR",
  estimate: { min: "200.00", max: "400.00" },
  contingency: { pct: 10, amount: "40.00" },
  planning_total: "440.00",
  per_traveller: { travellers: 2, largest_share: "220.00", label: "average" },
  budget: { amount: "500.00", status: "near", ratio_pct: 88, excess: null },
  by_day: [
    { day_number: 1, min: "200.00", max: "400.00", contingency_share: "40.00" },
  ],
  by_category: [
    { category: "activities", min: "0.00", max: "0.00", label: "unavailable" },
    { category: "transport", min: "200.00", max: "400.00", label: "estimate" },
  ],
  alerts: [],
  complete: false,
  incomplete_items: [
    "00000000-0000-4000-8000-0000000000c1",
    "00000000-0000-4000-8000-0000000000c2",
    "00000000-0000-4000-8000-0000000000c3",
  ],
  settings: {
    transport_allowance_per_day: null,
    stay_budget_per_night: null,
    contingency_pct: 10,
  },
};

function detail(
  tier: "live" | "curated",
): AnyCitySchemas["DestinationDetailOut"] {
  return {
    id: DESTINATION_ID,
    slug: tier === "live" ? "live-udaipur-r1234567" : "jaipur",
    name: tier === "live" ? "Udaipur" : "Jaipur",
    region: "Rajasthan",
    country_code: "IN",
    timezone: "Asia/Kolkata",
    currency: "INR",
    is_sample: false,
    center: { lat: 24.58, lon: 73.71 },
    bbox: { min_lat: 24.3, min_lon: 73.4, max_lat: 24.8, max_lon: 74 },
    data_tier: tier,
    imported_at: null,
    attribution:
      tier === "live"
        ? [
            {
              source_name: "OpenStreetMap",
              licence: "ODbL-1.0",
              attribution_text:
                "Place data © OpenStreetMap contributors, available under the Open Database Licence (ODbL)",
              url: "https://www.openstreetmap.org/copyright",
            },
          ]
        : [],
    import: null,
  };
}

const json = (body: unknown) =>
  new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
  });

function fakeApi(tier: "live" | "curated") {
  const paths: string[] = [];
  vi.stubGlobal("fetch", async (request: Request) => {
    const url = new URL(request.url);
    paths.push(url.pathname);
    if (url.pathname.endsWith("/costs")) return json(costs);
    if (url.pathname === `/api/v1/destinations/${DESTINATION_ID}`) {
      return json(detail(tier));
    }
    if (url.pathname === `/api/v1/trips/${TRIP_ID}`) {
      return json({
        id: TRIP_ID,
        destination_id: DESTINATION_ID,
        destination: {
          id: DESTINATION_ID,
          name: "Udaipur",
          currency: "INR",
          timezone: "Asia/Kolkata",
          is_sample: false,
        },
      });
    }
    return json({});
  });
  return paths;
}

function renderPage() {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <CostsPage />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  flag.anyCity = true;
});
afterEach(() => vi.unstubAllGlobals());

describe("CostBreakdown on a live plan (TC-485)", () => {
  it("states known costs only, with N from the incomplete items, and the budget note", async () => {
    const { container } = render(
      <LiveTierProvider value>
        <CostBreakdown costs={costs} />
      </LiveTierProvider>,
    );
    expect(screen.getByText(KNOWN)).toBeInTheDocument();
    expect(screen.getByText(BUDGET_NOTE)).toBeInTheDocument();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("names one stop in the singular", () => {
    render(
      <CostBreakdown
        live
        costs={{ ...costs, incomplete_items: [costs.incomplete_items[0]] }}
      />,
    );
    expect(
      screen.getByText("Known costs only: 1 stop has no price"),
    ).toBeInTheDocument();
  });

  it("shows no budget note when no budget is set", () => {
    render(
      <CostBreakdown
        live
        costs={{
          ...costs,
          budget: {
            amount: null,
            status: "none",
            ratio_pct: null,
            excess: null,
          },
        }}
      />,
    );
    expect(screen.getByText(KNOWN)).toBeInTheDocument();
    expect(
      screen.queryByText(/covers known costs only/),
    ).not.toBeInTheDocument();
  });

  it("leaves a curated plan unchanged", () => {
    render(<CostBreakdown costs={costs} />);
    expect(screen.queryByText(/Known costs only/)).not.toBeInTheDocument();
    expect(
      screen.queryByText(/covers known costs only/),
    ).not.toBeInTheDocument();
    const category = screen.getByRole("table", { name: "Costs by category" });
    expect(
      within(category).getByRole("row", { name: /Activities/ }),
    ).toHaveTextContent("Unavailable");
  });
});

describe("costs page (TC-485)", () => {
  it("a live plan shows the tier badge, the known-costs note and the attribution", async () => {
    fakeApi("live");
    const { container } = renderPage();
    expect(await screen.findByText(KNOWN)).toBeInTheDocument();
    expect(screen.getByText(BUDGET_NOTE)).toBeInTheDocument();
    expect(await screen.findByText("Live data")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /OpenStreetMap source/ }),
    ).toHaveAttribute("href", "https://www.openstreetmap.org/copyright");
    expect(await axeViolations(container)).toEqual([]);
  });

  it("a curated plan shows Curated and no known-costs note", async () => {
    fakeApi("curated");
    renderPage();
    expect(await screen.findByText("Curated")).toBeInTheDocument();
    expect(
      await screen.findByRole("table", { name: "Daily cost estimates" }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Known costs only/)).not.toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Data sources" }),
    ).not.toBeInTheDocument();
  });

  it("the switch OFF renders nothing new and reads neither the trip nor API-79", async () => {
    flag.anyCity = false;
    const paths = fakeApi("live");
    renderPage();
    expect(
      await screen.findByRole("table", { name: "Daily cost estimates" }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Known costs only/)).not.toBeInTheDocument();
    expect(screen.queryByText("Live data")).not.toBeInTheDocument();
    // Only API-33 is read (the costs view and the allowance form share it).
    expect(new Set(paths)).toEqual(new Set([`/api/v1/trips/${TRIP_ID}/costs`]));
  });
});
