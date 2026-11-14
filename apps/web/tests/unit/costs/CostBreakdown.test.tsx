import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import CostsPage from "@/app/(app)/trips/[tripId]/costs/page";
import { CostBreakdown } from "@/components/costs/CostBreakdown";
import { useRetimeItem } from "@/lib/api/queries";
import type { components } from "@/lib/api/schema";

vi.mock("next/navigation", () => ({ useParams: () => ({ tripId: "trip" }) }));
vi.mock("@/lib/auth/supabase", () => ({
  getSupabase: () => ({
    auth: {
      getSession: async () => ({ data: { session: { access_token: "t" } } }),
    },
  }),
}));
vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test/api/v1");
const costs: components["schemas"]["CostSummaryOut"] = {
  currency: "INR",
  estimate: { min: "7.77", max: "12.34" },
  contingency: { pct: 10, amount: "1.23" },
  planning_total: "13.57",
  per_traveller: { travellers: 1, largest_share: "13.57", label: "average" },
  budget: { amount: null, status: "none", ratio_pct: null, excess: null },
  by_day: [
    { day_number: 1, min: "7.77", max: "12.34", contingency_share: "1.23" },
  ],
  by_category: [
    { category: "activities", min: "7.77", max: "12.34", label: "curated" },
    { category: "transport", min: "0.00", max: "0.00", label: "unavailable" },
    {
      category: "accommodation",
      min: "0.00",
      max: "0.00",
      label: "traveller_input",
    },
    { category: "contingency", min: "1.23", max: "1.23", label: "estimate" },
  ],
  alerts: [],
  complete: false,
  incomplete_items: [],
  settings: {
    transport_allowance_per_day: null,
    stay_budget_per_night: "0.00",
    contingency_pct: 10,
  },
};
afterEach(() => vi.unstubAllGlobals());
it("TC-282: accessible tables show API amounts and labels, including unavailable and traveller input", () => {
  render(<CostBreakdown costs={costs} />);
  const daily = screen.getByRole("table", { name: "Daily cost estimates" });
  expect(
    within(daily).getByRole("rowheader", { name: "Day 1" }),
  ).toBeInTheDocument();
  expect(within(daily).getByText("INR 7.77")).toBeInTheDocument();
  expect(within(daily).getByText("INR 1.23")).toBeInTheDocument();
  const category = screen.getByRole("table", { name: "Costs by category" });
  const unavailable = within(category).getByRole("row", { name: /Transport/ });
  expect(unavailable).toHaveTextContent("Unavailable");
  expect(unavailable).not.toHaveTextContent("0.00");
  expect(within(category).getByText("Traveller input")).toBeInTheDocument();
});
function Edit() {
  const edit = useRetimeItem("trip");
  return (
    <button
      onClick={() =>
        edit.mutate({ itemId: "item", plan_revision: 7, duration_min: 60 })
      }
    >
      Edit item
    </button>
  );
}
it("TC-226: shared edit invalidation refetches the costs page without a manual reload", async () => {
  let current = costs;
  const json = (data: unknown) =>
    new Response(JSON.stringify(data), {
      headers: { "Content-Type": "application/json" },
    });
  vi.stubGlobal("fetch", async (request: Request) => {
    if (request.method === "GET") return json(current);
    current = {
      ...costs,
      planning_total: "23.45",
      by_day: [{ ...costs.by_day[0], max: "22.22" }],
    };
    return json({
      plan_revision: 8,
      changed_days: [],
      totals: {
        currency: "INR",
        estimate: current.estimate,
        planning_total: current.planning_total,
        complete: false,
        incomplete_count: 1,
      },
      findings: [],
    });
  });
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <CostsPage />
      <Edit />
    </QueryClientProvider>,
  );
  expect(
    await screen.findByRole("table", { name: "Daily cost estimates" }),
  ).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Edit item" }));
  expect(await screen.findByText("INR 22.22")).toBeInTheDocument();
  expect(screen.getByText("INR 23.45")).toBeInTheDocument();
  expect(
    screen.getByText(/Treat this total as incomplete/),
  ).toBeInTheDocument();
});
