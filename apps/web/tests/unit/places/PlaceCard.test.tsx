import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import ExplorePage from "@/app/(app)/trips/[tripId]/explore/page";
import { PlaceCard, type Place } from "@/components/places/PlaceCard";

// FR-016 (IMP-509; TC-092 to TC-094): each place shows its source and verification status with
// labelled facts, the explore page pages through API-16, and states when data is sample.
vi.mock("@/lib/auth/supabase", () => ({
  getSupabase: () => ({
    auth: {
      getSession: async () => ({ data: { session: { access_token: "t" } } }),
    },
  }),
}));
vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test/api/v1");

const TRIP_ID = "00000000-0000-4000-8000-000000000002";
const DESTINATION_ID = "00000000-0000-4000-8000-0000000000d1";
vi.mock("next/navigation", () => ({ useParams: () => ({ tripId: TRIP_ID }) }));

const SAMPLE_NOTICE =
  "Sample data; prices and hours are estimates unless marked Curated.";

const place = (overrides: Partial<Place> = {}): Place => ({
  id: "00000000-0000-4000-8000-0000000000p1",
  name: "Sample Old Signal Tower (sample)",
  category: "sight",
  tags: ["views", "history"],
  lat: 53.876,
  lon: 2.12,
  typical_duration_min: 90,
  price: { min: "3.00", max: "5.00", currency: "GBP", label: "estimate" },
  price_label: "estimate",
  hours_label: "curated",
  verification_status: "estimated",
  suitability: { step_free: null, child_friendly: true, indoor: false },
  source_name: "SAMPLE fixture (synthetic)",
  ...overrides,
});

const fact = (term: string) => {
  const dt = screen.getByText(term, { selector: "dt" });
  const dd = dt.nextElementSibling;
  if (!(dd instanceof HTMLElement)) throw new Error(`no value for ${term}`);
  return dd;
};

describe("PlaceCard", () => {
  it("shows the source name and verification status (TC-093)", () => {
    render(<PlaceCard place={place()} />);

    expect(
      screen.getByRole("heading", { name: "Sample Old Signal Tower (sample)" }),
    ).toBeInTheDocument();
    expect(fact("Source")).toHaveTextContent("SAMPLE fixture (synthetic)");
    expect(fact("Verification")).toHaveTextContent("Estimated");
    expect(screen.getByText("Sight · 1 h 30 min")).toBeInTheDocument();
  });

  it("labels the price and hours with SourceBadge, as the API sent them", () => {
    render(<PlaceCard place={place()} />);

    expect(fact("Price")).toHaveTextContent("GBP 3.00–5.00");
    expect(within(fact("Price")).getByText("Estimate")).toBeInTheDocument();
    expect(within(fact("Hours")).getByText("Curated")).toBeInTheDocument();
  });

  it("never shows an unavailable price as a value", () => {
    render(
      <PlaceCard
        place={place({
          price: null,
          price_label: "unavailable",
          hours_label: "unavailable",
          verification_status: "curated_checked",
        })}
      />,
    );

    expect(fact("Price")).toHaveTextContent(/^Unavailable$/);
    expect(fact("Hours")).toHaveTextContent(/^Unavailable$/);
    expect(fact("Verification")).toHaveTextContent("Curated and checked");
  });
});

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

const trip = (isSample: boolean) => ({
  id: TRIP_ID,
  destination_id: DESTINATION_ID,
  destination: {
    id: DESTINATION_ID,
    name: "Sampleton (sample)",
    currency: "GBP",
    timezone: "Europe/London",
    is_sample: isSample,
  },
});

function renderPage(
  tripBody: () => Response,
  placesBody: (offset: number) => Response,
) {
  const placeRequests: URL[] = [];
  vi.stubGlobal("fetch", async (request: Request) => {
    const url = new URL(request.url);
    if (url.pathname.endsWith("/places")) {
      placeRequests.push(url);
      return placesBody(Number(url.searchParams.get("offset")));
    }
    return tripBody();
  });
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <ExplorePage />
    </QueryClientProvider>,
  );
  return placeRequests;
}

const pageOf = (
  offset: number,
  total: number,
  overrides: Partial<Place> = {},
) =>
  json({
    items: [
      place({ id: `p-${offset}`, name: `Place at ${offset}`, ...overrides }),
    ],
    total,
    limit: 20,
    offset,
  });

afterEach(() => vi.unstubAllGlobals());

describe("ExplorePage", () => {
  it("states that the SAMPLE destination's data is sample and estimated (TC-094)", async () => {
    renderPage(
      () => json(trip(true)),
      (offset) => pageOf(offset, 1),
    );

    expect(await screen.findByText("Place at 0")).toBeInTheDocument();
    expect(screen.getByText(SAMPLE_NOTICE)).toBeInTheDocument();
  });

  it("states estimates without calling real data sample", async () => {
    renderPage(
      () => json(trip(false)),
      (offset) => pageOf(offset, 1),
    );

    expect(await screen.findByText("Place at 0")).toBeInTheDocument();
    expect(
      screen.getByText("Prices and hours are estimates unless marked Curated."),
    ).toBeInTheDocument();
    expect(screen.queryByText(SAMPLE_NOTICE)).not.toBeInTheDocument();
  });

  it("shows no notice for curated, non-sample data", async () => {
    renderPage(
      () => json(trip(false)),
      (offset) =>
        pageOf(offset, 1, {
          price_label: "curated",
          hours_label: "curated",
          verification_status: "curated_checked",
          price: { min: "3.00", max: null, currency: "GBP", label: "curated" },
        }),
    );

    expect(await screen.findByText("Place at 0")).toBeInTheDocument();
    expect(
      screen.queryByText(/estimates unless marked/),
    ).not.toBeInTheDocument();
  });

  it("lists the trip destination's places in pages (TC-092)", async () => {
    const requests = renderPage(
      () => json(trip(true)),
      (offset) => pageOf(offset, 25),
    );

    expect(await screen.findByText("Place at 0")).toBeInTheDocument();
    expect(screen.getByText("Page 1 of 2 · 25 places")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
    expect(requests[0].searchParams.get("destination_id")).toBe(DESTINATION_ID);

    fireEvent.click(screen.getByRole("button", { name: "Next" }));

    expect(await screen.findByText("Place at 20")).toBeInTheDocument();
    expect(screen.getByText("Page 2 of 2 · 25 places")).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Next" })).toBeDisabled(),
    );
    expect(requests.at(-1)?.searchParams.get("offset")).toBe("20");
  });

  it("shows EmptyState when the destination has no places", async () => {
    renderPage(
      () => json(trip(true)),
      () => json({ items: [], total: 0, limit: 20, offset: 0 }),
    );

    expect(await screen.findByText("No places yet")).toBeInTheDocument();
  });

  it("shows ErrorState with retry when places fail to load", async () => {
    renderPage(
      () => json(trip(true)),
      () =>
        json(
          { error: { code: "INTERNAL", message: "Boom.", request_id: "r1" } },
          500,
        ),
    );

    expect(
      await screen.findByText("Places could not be loaded"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Try again" }),
    ).toBeInTheDocument();
  });

  it("shows the not-found screen for a foreign or missing trip", async () => {
    renderPage(
      () =>
        json(
          {
            error: {
              code: "NOT_FOUND",
              message: "Not found.",
              request_id: null,
            },
          },
          404,
        ),
      (offset) => pageOf(offset, 1),
    );

    expect(await screen.findByText("Trip not found")).toBeInTheDocument();
  });
});
