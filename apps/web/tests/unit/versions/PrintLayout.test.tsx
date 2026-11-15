import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import SummaryPage from "@/app/(app)/trips/[tripId]/summary/page";
import {
  ESTIMATE_STATEMENT,
  PrintLayout,
} from "@/components/versions/PrintLayout";
import type { components } from "@/lib/api/schema";

import { ITEM, TRIP_ID } from "../itinerary/fixtures";

vi.mock("next/navigation", () => ({ useParams: () => ({ tripId: TRIP_ID }) }));
vi.mock("@/lib/auth/supabase", () => ({
  getSupabase: () => ({
    auth: {
      getSession: async () => ({ data: { session: { access_token: "t" } } }),
    },
  }),
}));
vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test/api/v1");
afterEach(() => vi.unstubAllGlobals());

type Summary = components["schemas"]["TripSummaryOut"];

// A SAMPLE API-35 answer: two days, one priced item and one unavailable price, one warning.
const SUMMARY: Summary = {
  trip: {
    id: TRIP_ID,
    title: "Weekend in Sampleton",
    destination_id: "00000000-0000-4000-8000-000000000001",
    destination: {
      id: "00000000-0000-4000-8000-000000000001",
      name: "Sampleton",
      currency: "INR",
      timezone: "Asia/Kolkata",
      is_sample: true,
    },
    start_date: "2026-12-04",
    end_date: "2026-12-05",
    num_days: 2,
    adults: 2,
    children: 0,
    budget: null,
    group_needs: [],
    status: "ready",
    plan_revision: 3,
    plan_stale: false,
    has_itinerary: true,
    created_at: "2026-11-15T10:00:00Z",
    updated_at: "2026-11-15T10:00:00Z",
  },
  days: [
    {
      day_number: 1,
      date: "2026-12-04",
      theme: "Museums and markets",
      theme_origin: "ai",
      day_cost: {
        min: "120.00",
        max: "150.00",
        currency: "INR",
        complete: true,
      },
      items: [
        {
          ...ITEM,
          cost: {
            min: "120.00",
            max: "150.00",
            currency: "INR",
            label: "curated",
          },
        },
      ],
    },
    {
      day_number: 2,
      date: "2026-12-05",
      theme: null,
      theme_origin: "none",
      day_cost: { min: "0.00", max: "0.00", currency: "INR", complete: false },
      items: [
        {
          ...ITEM,
          id: "00000000-0000-4000-8000-0000000000c2",
          place: {
            ...ITEM.place,
            name: "River Walk (sample)",
            hours_label: "estimate",
          },
          note: null,
          note_origin: "none",
          cost: null,
          travel_from_previous: null,
        },
      ],
    },
  ],
  unresolved_findings: [
    {
      id: "00000000-0000-4000-8000-0000000000f1",
      code: "HOURS_UNVERIFIED",
      severity: "info",
      message: "Opening hours unavailable.",
      day_number: 2,
      item_id: null,
      place_id: null,
      suggested_fix: "Check opening times before the visit.",
    },
  ],
  costs: {
    currency: "INR",
    estimate: { min: "120.00", max: "150.00" },
    contingency: { pct: 10, amount: "15.00" },
    planning_total: "165.00",
    per_traveller: { travellers: 2, largest_share: "82.50", label: "average" },
    budget: { amount: null, status: "none", ratio_pct: null, excess: null },
    by_day: [],
    by_category: [],
    alerts: [],
    complete: false,
    incomplete_items: [],
    settings: {
      transport_allowance_per_day: null,
      stay_budget_per_night: null,
      contingency_pct: 10,
    },
  },
  generated_at: "2026-11-15T10:00:00Z",
};

it("TC-254: every day lists times, places, travel and labelled costs from the API", () => {
  render(<PrintLayout summary={SUMMARY} />);
  const day1 = screen.getByRole("region", { name: /Day 1/ });
  expect(day1).toHaveTextContent("09:30–11:00");
  expect(day1).toHaveTextContent("Old Mill Museum (sample)");
  expect(day1).toHaveTextContent("INR 120.00–150.00");
  expect(day1).toHaveTextContent("Curated");
  expect(day1).toHaveTextContent(
    "12 min walking · Estimated travel time (distance based)",
  );
  // AI-written theme and note carry the badge.
  expect(within(day1).getAllByText("AI-written")).toHaveLength(2);
  const day2 = screen.getByRole("region", { name: /Day 2/ });
  expect(day2).toHaveTextContent("Unavailable"); // never shown as a value
  expect(day2).toHaveTextContent("Estimate"); // estimated hours
  expect(day2).toHaveTextContent("some prices unavailable");
  expect(within(day2).queryByText("AI-written")).not.toBeInTheDocument();
  expect(screen.getByRole("region", { name: "Trip total" })).toHaveTextContent(
    "Planning total: INR 165.00",
  );
  expect(screen.getByText(ESTIMATE_STATEMENT)).toBeInTheDocument();
});

it("TC-255: unresolved warnings appear in their own section", () => {
  render(<PrintLayout summary={SUMMARY} />);
  expect(
    screen.getByRole("region", { name: "Unresolved warnings" }),
  ).toHaveTextContent(
    "Day 2: Opening hours unavailable. Check opening times before the visit.",
  );
});

it("starts each day after the first on a new printed page", () => {
  render(<PrintLayout summary={SUMMARY} />);
  expect(screen.getByRole("region", { name: /Day 1/ })).not.toHaveClass(
    "print:break-before-page",
  );
  expect(screen.getByRole("region", { name: /Day 2/ })).toHaveClass(
    "print:break-before-page",
  );
});

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

function renderPage(response: Response) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => response),
  );
  render(
    <QueryClientProvider client={new QueryClient()}>
      <SummaryPage />
    </QueryClientProvider>,
  );
}

it("the Print button opens the browser's print dialog", async () => {
  const print = vi.fn();
  vi.stubGlobal("print", print);
  renderPage(json(SUMMARY));
  fireEvent.click(await screen.findByRole("button", { name: "Print" }));
  expect(print).toHaveBeenCalledOnce();
});

it("without an itinerary the page offers to generate one", async () => {
  renderPage(
    json(
      {
        error: {
          code: "NOT_FOUND",
          message: "No itinerary yet.",
          request_id: null,
        },
      },
      404,
    ),
  );
  expect(
    await screen.findByRole("link", { name: "Generate a plan" }),
  ).toHaveAttribute("href", `/trips/${TRIP_ID}/generate`);
});
