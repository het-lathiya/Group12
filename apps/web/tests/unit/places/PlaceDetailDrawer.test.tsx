import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PlaceDetailDrawer } from "@/components/places/PlaceDetailDrawer";
import type { components } from "@/lib/api/schema";

// FR-018 (IMP-604 detail-drawer part; TC-098 UI, TC-099, TC-100): every fact as API-17 sent it,
// labelled with SourceBadge; missing hours or prices are never guessed.
vi.mock("@/lib/auth/supabase", () => ({
  getSupabase: () => ({
    auth: {
      getSession: async () => ({ data: { session: { access_token: "t" } } }),
    },
  }),
}));
vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test/api/v1");

type PlaceOut = components["schemas"]["PlaceOut"];
const PLACE_ID = "00000000-0000-4000-8000-0000000000a1";

const placeOut = (overrides: Partial<PlaceOut> = {}): PlaceOut => ({
  id: PLACE_ID,
  name: "Curated Test Hall",
  category: "museum",
  tags: ["history"],
  lat: 53.9,
  lon: 2.2,
  typical_duration_min: 60,
  price: { min: "4.50", max: "6.00", currency: "GBP", label: "curated" },
  price_label: "curated",
  hours_label: "curated",
  verification_status: "curated_checked",
  suitability: { step_free: true, child_friendly: null, indoor: null },
  source_name: "SAMPLE fixture (synthetic)",
  description: "A hall used by the detail test.",
  address: "1 Test Row",
  website_url: null,
  booking_url: null,
  hours: [
    {
      weekday: 1,
      is_closed: true,
      open_time: null,
      close_time: null,
      closes_next_day: false,
    },
    {
      weekday: 2,
      is_closed: false,
      open_time: "09:00",
      close_time: "17:00",
      closes_next_day: false,
    },
  ],
  hours_checked_on: "2026-10-01",
  source: {
    name: "SAMPLE fixture (synthetic)",
    source_type: "other",
    licence: "synthetic test data",
    attribution_text: null,
    url: null,
    retrieved_on: "2026-10-31",
  },
  ...overrides,
});

function renderDrawer(body: PlaceOut) {
  const requests: string[] = [];
  vi.stubGlobal("fetch", async (request: Request) => {
    requests.push(new URL(request.url).pathname);
    return new Response(JSON.stringify(body), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  });
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <PlaceDetailDrawer placeId={PLACE_ID} onClose={() => undefined} />
    </QueryClientProvider>,
  );
  return requests;
}

const fact = (term: string) => {
  const dt = screen.getByText(term, { selector: "dt" });
  const dd = dt.nextElementSibling;
  if (!(dd instanceof HTMLElement)) throw new Error(`no value for ${term}`);
  return dd;
};

afterEach(() => vi.unstubAllGlobals());

describe("PlaceDetailDrawer", () => {
  it("shows curated hours as 'Curated, checked on <date>' with each day (TC-098)", async () => {
    const requests = renderDrawer(placeOut());

    expect(
      await screen.findByRole("dialog", { name: "Curated Test Hall" }),
    ).toBeInTheDocument();
    expect(requests).toEqual([`/api/v1/places/${PLACE_ID}`]);
    const hours = fact("Hours");
    expect(
      within(hours).getByText("Curated, checked on Thu 1 Oct"),
    ).toBeInTheDocument();
    expect(hours).toHaveTextContent("MondayClosed");
    expect(hours).toHaveTextContent("Tuesday09:00–17:00");
    expect(fact("Source")).toHaveTextContent("Retrieved Sat 31 Oct");
    expect(fact("Verification")).toHaveTextContent("Curated and checked");
  });

  it("shows 'Hours unavailable' and no time when the place has no hours (TC-099)", async () => {
    renderDrawer(
      placeOut({
        hours_label: "unavailable",
        hours: [],
        hours_checked_on: null,
      }),
    );

    await screen.findByRole("dialog", { name: "Curated Test Hall" });
    expect(fact("Hours")).toHaveTextContent(/^Hours unavailable$/);
    expect(fact("Hours")).not.toHaveTextContent(/\d{2}:\d{2}/);
  });

  it("labels an estimated price 'Estimate' and a missing one 'Unavailable', never 0 (TC-100)", async () => {
    renderDrawer(
      placeOut({
        price: { min: "3.00", max: "5.00", currency: "GBP", label: "estimate" },
        price_label: "estimate",
        hours_label: "estimate",
      }),
    );
    await screen.findByRole("dialog", { name: "Curated Test Hall" });
    expect(fact("Price")).toHaveTextContent("GBP 3.00–5.00Estimate");
    expect(within(fact("Hours")).getByText("Estimate")).toBeInTheDocument();
  });

  it("never shows a missing price as a value", async () => {
    renderDrawer(placeOut({ price: null, price_label: "unavailable" }));
    await screen.findByRole("dialog", { name: "Curated Test Hall" });
    expect(fact("Price")).toHaveTextContent(/^Unavailable$/);
  });
});
