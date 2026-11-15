import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { BudgetAlert } from "@/components/costs/BudgetAlert";
import { BudgetSettingsForm } from "@/components/costs/BudgetSettingsForm";
import type { components } from "@/lib/api/schema";

// FR-074 and FR-075 web side (IMP-608): banners and the buffer line show only what API-33 returns.
const flags = { budget_alerts: true, contingency: true };
vi.mock("@/lib/flags", () => ({
  isEnabled: (name: string) => flags[name as keyof typeof flags] ?? true,
}));
vi.mock("@/lib/auth/supabase", () => ({
  getSupabase: () => ({
    auth: {
      getSession: async () => ({ data: { session: { access_token: "t" } } }),
    },
  }),
}));
vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test/api/v1");

type Finding = components["schemas"]["Finding"];
const TRIP_ID = "00000000-0000-4000-8000-000000000003";

function finding(code: Finding["code"], message: string): Finding {
  return {
    id: `00000000-0000-4000-8000-${code === "BUDGET_NEAR" ? "000000000010" : "000000000011"}`,
    code,
    severity: code === "BUDGET_EXCEEDED" ? "warning" : "info",
    message,
    day_number: null,
    item_id: null,
    place_id: null,
    suggested_fix: null,
  };
}
const NEAR = finding("BUDGET_NEAR", "The plan uses 92% of your budget.");
const OVER = finding(
  "BUDGET_EXCEEDED",
  "The plan is over your budget by 250.00 GBP.",
);

function costs(pct: number, amount: string) {
  return {
    currency: "GBP",
    estimate: { min: "100.00", max: "120.00" },
    contingency: { pct, amount },
    planning_total: "132.00",
    per_traveller: { travellers: 1, largest_share: "132.00", label: "average" },
    budget: { amount: null, status: "none", ratio_pct: null, excess: null },
    by_day: [],
    by_category: [],
    alerts: [],
    complete: true,
    incomplete_items: [],
    settings: {
      transport_allowance_per_day: null,
      stay_budget_per_night: null,
      contingency_pct: pct,
    },
  };
}

let patches: unknown[];
const json = (body: unknown) =>
  new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
  });

beforeEach(() => {
  flags.budget_alerts = true;
  flags.contingency = true;
  patches = [];
  vi.stubGlobal("fetch", async (request: Request) => {
    if (request.method === "PATCH") {
      patches.push(await request.json());
      return json(costs(25, "30.00")); // the server's figure, never computed here
    }
    return json(costs(10, "12.00"));
  });
});

function renderForm() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <BudgetSettingsForm tripId={TRIP_ID} currency="GBP" />
    </QueryClientProvider>,
  );
  return userEvent.setup();
}

describe("BudgetAlert (FR-074)", () => {
  it("TC-227: shows the near-budget banner as a status with a text title", () => {
    render(<BudgetAlert alerts={[NEAR]} />);

    const banner = screen.getByRole("status", { name: "Near budget" });
    expect(banner).toHaveTextContent(
      "Near budget. The plan uses 92% of your budget.",
    );
  });

  it("TC-228: shows the over-budget banner with the excess from the API", () => {
    render(<BudgetAlert alerts={[OVER]} />);

    expect(
      screen.getByRole("status", { name: "Over budget" }),
    ).toHaveTextContent(
      "Over budget. The plan is over your budget by 250.00 GBP.",
    );
  });

  it("shows nothing without alerts or for other finding codes", () => {
    render(
      <BudgetAlert
        alerts={[finding("COST_INCOMPLETE", "2 items have no price.")]}
      />,
    );
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("is hidden when the budget_alerts switch is off", () => {
    flags.budget_alerts = false;
    render(<BudgetAlert alerts={[NEAR, OVER]} />);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});

describe("BudgetSettingsForm contingency (FR-075)", () => {
  it("TC-229: shows the stored percentage and the API's buffer line", async () => {
    renderForm();

    expect(await screen.findByLabelText("Contingency buffer (%)")).toHaveValue(
      "10",
    );
    expect(
      screen.getByText("In costs: GBP 12.00, Estimate"),
    ).toBeInTheDocument();
  });

  it("saves a new percentage through API-34 and shows the returned line", async () => {
    const user = renderForm();
    const input = await screen.findByLabelText("Contingency buffer (%)");
    await user.clear(input);
    await user.type(input, "25");
    await user.click(
      screen.getByRole("button", { name: "Save budget inputs" }),
    );

    expect(
      await screen.findByText("In costs: GBP 30.00, Estimate"),
    ).toBeInTheDocument();
    expect(patches).toEqual([
      {
        transport_allowance_per_day: null,
        stay_budget_per_night: null,
        contingency_pct: 25,
      },
    ]);
  });

  it("refuses a percentage above 50 and sends nothing", async () => {
    const user = renderForm();
    const input = await screen.findByLabelText("Contingency buffer (%)");
    await user.clear(input);
    await user.type(input, "51");
    await user.click(
      screen.getByRole("button", { name: "Save budget inputs" }),
    );

    expect(
      await screen.findByText("Enter a whole number from 0 to 50."),
    ).toBeInTheDocument();
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(patches).toEqual([]);
  });

  it("TC-230: with the contingency switch off, states that no buffer is included", async () => {
    flags.contingency = false;
    const user = renderForm();

    expect(
      await screen.findByText(
        "No contingency buffer is included in this estimate.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByLabelText("Contingency buffer (%)"),
    ).not.toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "Save budget inputs" }),
    );
    await vi.waitFor(() => expect(patches).toHaveLength(1));
    expect(patches[0]).not.toHaveProperty("contingency_pct");
  });
});
