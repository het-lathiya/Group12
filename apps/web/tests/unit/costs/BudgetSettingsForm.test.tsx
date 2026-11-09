import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  BudgetSettingsForm,
  budgetSettingsSchema,
} from "@/components/costs/BudgetSettingsForm";

// FR-072 web side (IMP-411): the traveller's figures go to API-34 and the lines show its answer.
vi.mock("@/lib/auth/supabase", () => ({
  getSupabase: () => ({
    auth: {
      getSession: async () => ({ data: { session: { access_token: "t" } } }),
    },
  }),
}));
vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test/api/v1");

const TRIP_ID = "00000000-0000-4000-8000-000000000002";

function costs(transport: string | null, stay: string | null) {
  const line = (category: string, perUnit: string | null, units: number) =>
    perUnit === null
      ? { category, min: "0.00", max: "0.00", label: "unavailable" }
      : {
          category,
          // The fake server answers like the API; the form never multiplies.
          min: (Number(perUnit) * units).toFixed(2),
          max: (Number(perUnit) * units).toFixed(2),
          label: "traveller_input",
        };
  return {
    currency: "GBP",
    estimate: { min: "0.00", max: "0.00" },
    contingency: { pct: 10, amount: "0.00" },
    planning_total: "0.00",
    per_traveller: { travellers: 1, largest_share: "0.00", label: "average" },
    budget: { amount: null, status: "none", ratio_pct: null, excess: null },
    by_day: [],
    by_category: [
      line("transport", transport, 3),
      line("accommodation", stay, 2),
    ],
    alerts: [],
    complete: false,
    incomplete_items: [],
    settings: {
      transport_allowance_per_day: transport,
      stay_budget_per_night: stay,
      contingency_pct: 10,
    },
  };
}

let patches: unknown[];
let patchAnswer: (() => Response) | null;
const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

beforeEach(() => {
  patches = [];
  patchAnswer = null;
  vi.stubGlobal("fetch", async (request: Request) => {
    if (request.method === "PATCH") {
      const body = (await request.json()) as {
        transport_allowance_per_day: string | null;
        stay_budget_per_night: string | null;
      };
      patches.push(body);
      if (patchAnswer) return patchAnswer();
      return json(
        costs(body.transport_allowance_per_day, body.stay_budget_per_night),
      );
    }
    return json(costs(null, null));
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

describe("BudgetSettingsForm (FR-072)", () => {
  it("shows both fields with the currency prefix, decimal input and helper text", async () => {
    renderForm();

    for (const label of ["Transport per day", "Stay per night"]) {
      const input = await screen.findByLabelText(label);
      expect(input).toHaveAttribute("inputmode", "decimal");
      expect(input).toHaveAccessibleDescription(
        "Your own figure. Shown as Traveller input in costs.",
      );
    }
    expect(screen.getAllByText("GBP")).toHaveLength(2);
    expect(screen.getAllByText("In costs: Unavailable")).toHaveLength(2);
  });

  it("TC-223: saves through API-34 and shows the returned lines as Traveller input", async () => {
    const user = renderForm();
    await user.type(await screen.findByLabelText("Transport per day"), "10");
    await user.click(
      screen.getByRole("button", { name: "Save budget inputs" }),
    );

    expect(
      await screen.findByText("In costs: GBP 30.00, Traveller input"),
    ).toBeInTheDocument();
    expect(screen.getByText("In costs: Unavailable")).toBeInTheDocument();
    expect(patches).toEqual([
      { transport_allowance_per_day: "10", stay_budget_per_night: null },
    ]);
  });

  it("a negative figure is refused on the field and nothing is sent", async () => {
    const user = renderForm();
    const input = await screen.findByLabelText("Stay per night");
    await user.type(input, "-5");
    await user.click(
      screen.getByRole("button", { name: "Save budget inputs" }),
    );

    expect(
      await screen.findByText(
        "Enter 0 or more, with at most 2 decimal places.",
      ),
    ).toBeInTheDocument();
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(patches).toEqual([]);
  });

  it("maps the server's 422 onto its field", async () => {
    patchAnswer = () =>
      json(
        {
          error: {
            code: "VALIDATION_ERROR",
            message: "Some fields need attention.",
            details: [
              { field: "transport_allowance_per_day", message: "Too large." },
            ],
            request_id: "req-1",
          },
        },
        422,
      );
    const user = renderForm();
    await user.type(await screen.findByLabelText("Transport per day"), "1");
    await user.click(
      screen.getByRole("button", { name: "Save budget inputs" }),
    );

    expect(await screen.findByText("Too large.")).toBeInTheDocument();
  });

  it("zod mirrors the server: empty or a decimal of 0 or more", () => {
    const parse = (value: string) =>
      budgetSettingsSchema.safeParse({
        transport_allowance_per_day: value,
        stay_budget_per_night: "",
      }).success;
    expect(parse("")).toBe(true);
    expect(parse("0")).toBe(true);
    expect(parse("12.50")).toBe(true);
    expect(parse("-1")).toBe(false);
    expect(parse("1.234")).toBe(false);
    expect(parse("abc")).toBe(false);
  });
});
