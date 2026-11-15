import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import ExplorePage from "@/app/(app)/trips/[tripId]/explore/page";
import {
  filtersFromParams,
  filtersToParams,
  NO_FILTERS,
  PlaceFilterBar,
} from "@/components/places/PlaceFilterBar";

// FR-017 (IMP-604 filter-bar part; TC-096 UI half): filters live in the URL, are keyboard
// operable native controls, and an empty result names the filters to relax.
const TRIP_ID = "00000000-0000-4000-8000-000000000002";
const nav = vi.hoisted(() => ({ search: "", replace: vi.fn() }));
vi.mock("next/navigation", () => ({
  useParams: () => ({ tripId: TRIP_ID }),
  useRouter: () => ({ replace: nav.replace }),
  useSearchParams: () => new URLSearchParams(nav.search),
}));
vi.mock("@/lib/auth/supabase", () => ({
  getSupabase: () => ({
    auth: {
      getSession: async () => ({ data: { session: { access_token: "t" } } }),
    },
  }),
}));
vi.mock("@/lib/flags", () => ({ isEnabled: () => false }));
vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test/api/v1");

afterEach(() => {
  vi.unstubAllGlobals();
  nav.search = "";
  nav.replace.mockReset();
});

describe("filter URL state", () => {
  it("round-trips the filters and drops values the API would refuse", () => {
    const params = new URLSearchParams(
      "q=tower&category=food&category=stay&interest=lunch&price_max=7.50&duration_max_min=60&step_free=true&sort=x",
    );
    const filters = filtersFromParams(params);
    expect(filters).toEqual({
      q: "tower",
      category: ["food"],
      interest: ["lunch"],
      price_max: "7.50",
      duration_max_min: "60",
      step_free: true,
    });
    expect(filtersToParams(filters).toString()).toBe(
      "q=tower&category=food&interest=lunch&price_max=7.50&duration_max_min=60&step_free=true",
    );
    expect(filtersFromParams(new URLSearchParams("price_max=1.234"))).toEqual(
      NO_FILTERS,
    );
  });
});

describe("PlaceFilterBar", () => {
  it("applies the draft with Enter and clears every filter", () => {
    const onChange = vi.fn();
    render(
      <PlaceFilterBar value={NO_FILTERS} currency="GBP" onChange={onChange} />,
    );

    fireEvent.change(screen.getByLabelText("Search by name or tag"), {
      target: { value: "tower" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Food" }));
    expect(screen.getByRole("button", { name: "Food" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    fireEvent.click(screen.getByLabelText(/Step-free only/));
    fireEvent.submit(screen.getByRole("search", { name: "Filter places" }));

    expect(onChange).toHaveBeenLastCalledWith({
      ...NO_FILTERS,
      q: "tower",
      category: ["food"],
      step_free: true,
    });

    fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(onChange).toHaveBeenLastCalledWith(NO_FILTERS);
  });

  it("refuses a malformed price instead of sending it", () => {
    const onChange = vi.fn();
    render(
      <PlaceFilterBar value={NO_FILTERS} currency="GBP" onChange={onChange} />,
    );

    fireEvent.change(screen.getByLabelText("Maximum price (GBP)"), {
      target: { value: "7.555" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply filters" }));

    expect(onChange).not.toHaveBeenCalled();
    expect(
      screen.getByText("Enter an amount such as 10 or 7.50."),
    ).toBeVisible();
  });
});

const json = (body: unknown) =>
  new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });

describe("ExplorePage filters", () => {
  it("sends the URL filters to API-16 and explains which to relax (TC-096)", async () => {
    nav.search = "category=museum&step_free=true&price_max=1.00";
    const requests: URL[] = [];
    vi.stubGlobal("fetch", async (request: Request) => {
      const url = new URL(request.url);
      if (url.pathname.endsWith("/places")) {
        requests.push(url);
        return json({ items: [], total: 0, limit: 20, offset: 0 });
      }
      return json({
        id: TRIP_ID,
        destination_id: "d1",
        destination: {
          id: "d1",
          name: "Sampleton (sample)",
          currency: "GBP",
          is_sample: true,
        },
      });
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

    expect(
      await screen.findByText("No places match these filters"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Try relaxing these filters: category, maximum price, step-free only.",
      ),
    ).toBeInTheDocument();
    const sent = requests[0].searchParams;
    expect(sent.getAll("category")).toEqual(["museum"]);
    expect(sent.get("step_free")).toBe("true");
    expect(sent.get("price_max")).toBe("1.00");

    const clear = screen.getAllByRole("button", { name: "Clear filters" });
    fireEvent.click(clear[clear.length - 1]);
    expect(nav.replace).toHaveBeenCalledWith(`/trips/${TRIP_ID}/explore`, {
      scroll: false,
    });
  });
});
