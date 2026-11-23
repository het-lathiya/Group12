import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CitySearch } from "@/components/trips/CitySearch";
import { PlacesStep } from "@/components/trips/PlacesStep";
import { TripDetailsStep } from "@/components/trips/TripDetailsStep";
import type { AnyCitySchemas } from "@/lib/api/anyCityClient";

import { axeViolations } from "../../axe";

// TC-482, TC-483 (Amendment A2 §9.1, IMP-728): the any-city search against a fake API. With the
// switch OFF nothing renders and no any-city request is made; with it ON, API-76 runs only on
// submit, results render, choosing resolves (API-77), and a completed import sets the trip form's
// destination and currency. No Supabase and no network.
vi.mock("@/lib/auth/supabase", () => ({
  getSupabase: () => ({
    auth: {
      getSession: async () => ({ data: { session: { access_token: "t" } } }),
    },
  }),
}));
const flag = vi.hoisted(() => ({ anyCity: false }));
vi.mock("@/lib/flags", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/flags")>();
  return {
    ...actual,
    isEnabled: (name: Parameters<typeof actual.isEnabled>[0]) =>
      name === "any_city_mode" ? flag.anyCity : actual.isEnabled(name),
  };
});
vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test/api/v1");

const SAMPLE_ID = "00000000-0000-4000-8000-000000000001";
const LIVE_ID = "00000000-0000-4000-8000-0000000000d1";
const HINT =
  "Live data comes from OpenStreetMap and Wikivoyage. It is not checked by our team: opening hours and prices are unknown.";

const UDAIPUR: AnyCitySchemas["CityCandidate"] = {
  osm_ref: "R1234567",
  name: "Udaipur",
  display_name: "Udaipur, Udaipur Tehsil, Rajasthan, 313001, India",
  region: "Rajasthan",
  country_code: "IN",
  lat: 24.58,
  lon: 73.71,
  kind: "city",
  destination_id: null,
  data_tier: null,
};

function liveOut(
  status: AnyCitySchemas["ImportState"]["status"],
): AnyCitySchemas["LiveDestinationOut"] {
  return {
    destination_id: LIVE_ID,
    slug: "live-udaipur-r1234567",
    name: "Udaipur",
    region: "Rajasthan",
    country_code: "IN",
    timezone: "Asia/Kolkata",
    currency: "INR",
    data_tier: "live",
    import: {
      status,
      failure_reason: null,
      places_found: status === "completed" ? 120 : null,
      places_usable: status === "completed" ? 64 : null,
      nearby_city: null,
      started_at: null,
      imported_at: null,
      expires_at: null,
    },
  };
}

function detailOut(
  status: AnyCitySchemas["ImportState"]["status"],
): AnyCitySchemas["DestinationDetailOut"] {
  const out = liveOut(status);
  return {
    id: LIVE_ID,
    slug: out.slug,
    name: out.name,
    region: out.region,
    country_code: out.country_code,
    timezone: out.timezone,
    currency: out.currency,
    is_sample: false,
    center: { lat: 24.58, lon: 73.71 },
    bbox: { min_lat: 24.3, min_lon: 73.4, max_lat: 24.8, max_lon: 74 },
    data_tier: "live",
    imported_at: null,
    attribution: [],
    import: out.import,
  };
}

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
const envelope = (code: string, message: string) => ({
  error: {
    code,
    message,
    request_id: "req-1",
    details: [],
    retry_after_s: null,
  },
});

type Call = { method: string; path: string; q: string | null; body: unknown };

function fakeApi() {
  const calls: Call[] = [];
  const answer: {
    search: () => Response;
    resolve: () => Response;
    importStatus: () => Response;
    detail: () => Response;
  } = {
    search: () => json({ results: [UDAIPUR] }),
    resolve: () => json(liveOut("completed")),
    importStatus: () => json(liveOut("completed")),
    detail: () => json(detailOut("completed")),
  };
  vi.stubGlobal("fetch", async (request: Request) => {
    const url = new URL(request.url);
    const body = request.method === "GET" ? null : await request.json();
    calls.push({
      method: request.method,
      path: url.pathname,
      q: url.searchParams.get("q"),
      body,
    });
    const key = `${request.method} ${url.pathname}`;
    if (key === "GET /api/v1/destinations") {
      return json([
        {
          id: SAMPLE_ID,
          slug: "sampleton",
          name: "Sampleton (sample)",
          region: null,
          country_code: "GB",
          timezone: "Europe/London",
          currency: "GBP",
          is_sample: true,
          center: { lat: 51.5, lon: -0.1 },
          bbox: { min_lat: 51, min_lon: -1, max_lat: 52, max_lon: 1 },
        },
      ]);
    }
    if (key === "GET /api/v1/destinations/search") return answer.search();
    if (key === "POST /api/v1/destinations/resolve") return answer.resolve();
    if (key === `GET /api/v1/destinations/${LIVE_ID}/import`) {
      return answer.importStatus();
    }
    if (key === `GET /api/v1/destinations/${LIVE_ID}`) return answer.detail();
    if (key === "GET /api/v1/places") {
      return json({ items: [], total: 0, limit: 20, offset: 0 });
    }
    return json(envelope("NOT_FOUND", "Not found."), 404);
  });
  const anyCityCalls = () =>
    calls.filter((call) => call.path !== "/api/v1/destinations");
  return { calls, answer, anyCityCalls };
}

let server: ReturnType<typeof fakeApi>;

beforeEach(() => {
  flag.anyCity = true;
  server = fakeApi();
});

function wrap(ui: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

function renderSearch(onReady = vi.fn(), onPickCurated = vi.fn()) {
  const view = wrap(
    <CitySearch onReady={onReady} onPickCurated={onPickCurated} />,
  );
  return { ...view, user: userEvent.setup(), onReady, onPickCurated };
}

function renderDetails() {
  const view = wrap(
    <TripDetailsStep formId="trip-details" locked={false} onSave={vi.fn()} />,
  );
  return { ...view, user: userEvent.setup() };
}

const searchField = () => screen.getByLabelText("Any city (live data)");
const searchButton = () => screen.getByRole("button", { name: "Search" });

describe("switch OFF (TC-482)", () => {
  beforeEach(() => {
    flag.anyCity = false;
  });

  it("CitySearch renders nothing and makes no request", async () => {
    const { container } = renderSearch();
    expect(container).toBeEmptyDOMElement();
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(server.calls).toEqual([]);
  });

  it("the trip details step shows no any-city control and calls only API-06", async () => {
    const { user } = renderDetails();
    await user.selectOptions(
      await screen.findByLabelText("Destination"),
      "Sampleton (sample)",
    );
    expect(screen.queryByLabelText("Any city (live data)")).toBeNull();
    expect(screen.queryByText(HINT)).toBeNull();
    expect(screen.getByLabelText("Currency")).toHaveValue("GBP");
    expect(server.anyCityCalls()).toEqual([]);
  });
});

describe("switch ON: search on submit only (TC-483)", () => {
  it("shows the label, the Search button and the exact hint", () => {
    renderSearch();
    expect(searchField()).toHaveAccessibleDescription(HINT);
    expect(searchButton()).toBeVisible();
  });

  it("typing alone sends no request; the Search button sends one", async () => {
    const { user } = renderSearch();
    await user.type(searchField(), "Udaipur");
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(server.anyCityCalls()).toEqual([]);

    await user.click(searchButton());
    const result = await screen.findByRole("button", {
      name: "Udaipur, Rajasthan, India · city",
    });
    expect(result).toBeVisible();
    expect(server.anyCityCalls()).toEqual([
      {
        method: "GET",
        path: "/api/v1/destinations/search",
        q: "Udaipur",
        body: null,
      },
    ]);
    expect(
      screen.getByText("Search by Nominatim · © OpenStreetMap contributors"),
    ).toBeVisible();
  });

  it("Enter searches and does not submit the surrounding form", async () => {
    const onSubmit = vi.fn((event: React.FormEvent) => event.preventDefault());
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <form onSubmit={onSubmit}>
          <CitySearch onReady={vi.fn()} />
        </form>
      </QueryClientProvider>,
    );
    const user = userEvent.setup();
    await user.type(searchField(), "Udaipur{Enter}");
    await screen.findByRole("button", {
      name: "Udaipur, Rajasthan, India · city",
    });
    expect(onSubmit).not.toHaveBeenCalled();
    expect(server.anyCityCalls()).toHaveLength(1);
  });

  it("a term shorter than 2 characters is not sent", async () => {
    const { user } = renderSearch();
    await user.type(searchField(), " U ");
    await user.click(searchButton());
    expect(
      await screen.findByText("Enter at least 2 characters."),
    ).toBeVisible();
    expect(server.anyCityCalls()).toEqual([]);
  });

  it("shows the 422 message from the error envelope", async () => {
    server.answer.search = () =>
      json(
        envelope("VALIDATION_ERROR", "Search terms are 2 to 100 characters."),
        422,
      );
    const { user } = renderSearch();
    await user.type(searchField(), "Udaipur");
    await user.click(searchButton());
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Search terms are 2 to 100 characters.",
    );
  });

  it("shows the 503 message from the error envelope", async () => {
    server.answer.search = () =>
      json(
        envelope(
          "SERVICE_UNAVAILABLE",
          "City search is unavailable right now.",
        ),
        503,
      );
    const { user } = renderSearch();
    await user.type(searchField(), "Udaipur");
    await user.click(searchButton());
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "City search is unavailable right now.",
    );
  });
});

describe("switch ON: choosing a result (TC-483)", () => {
  it("resolves the result and shows the import progress", async () => {
    server.answer.resolve = () => json(liveOut("queued"), 202);
    const { user, onReady } = renderSearch();
    await user.type(searchField(), "Udaipur");
    await user.click(searchButton());
    await user.click(
      await screen.findByRole("button", {
        name: "Udaipur, Rajasthan, India · city",
      }),
    );
    expect(
      await screen.findByText("Building your city: finding places…"),
    ).toBeVisible();
    const resolves = server.calls.filter((call) => call.method === "POST");
    expect(resolves).toEqual([
      {
        method: "POST",
        path: "/api/v1/destinations/resolve",
        q: null,
        body: { osm_ref: "R1234567" },
      },
    ]);
    expect(onReady).not.toHaveBeenCalled();
  });

  it("shows a resolve error from the error envelope", async () => {
    server.answer.resolve = () =>
      json(
        envelope("VALIDATION_ERROR", "This country is not supported yet"),
        422,
      );
    const { user } = renderSearch();
    await user.type(searchField(), "Udaipur");
    await user.click(searchButton());
    await user.click(
      await screen.findByRole("button", {
        name: "Udaipur, Rajasthan, India · city",
      }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "This country is not supported yet",
    );
  });

  it("a curated result is chosen in the list above without a resolve", async () => {
    server.answer.search = () =>
      json({
        results: [
          { ...UDAIPUR, destination_id: SAMPLE_ID, data_tier: "curated" },
        ],
      });
    const { user, onPickCurated } = renderSearch();
    await user.type(searchField(), "Udaipur");
    await user.click(searchButton());
    await user.click(
      await screen.findByRole("button", {
        name: "Udaipur, Rajasthan, India · city",
      }),
    );
    expect(onPickCurated).toHaveBeenCalledWith(SAMPLE_ID);
    expect(server.calls.some((call) => call.method === "POST")).toBe(false);
  });

  it("the not-enough-data button searches the nearby city", async () => {
    server.answer.resolve = () =>
      json({
        ...liveOut("insufficient_data"),
        name: "Nathdwara",
        import: {
          ...liveOut("insufficient_data").import,
          nearby_city: "Udaipur",
        },
      });
    const { user } = renderSearch();
    await user.type(searchField(), "Nathdwara");
    await user.click(searchButton());
    await user.click(
      await screen.findByRole("button", {
        name: "Udaipur, Rajasthan, India · city",
      }),
    );
    await user.click(
      await screen.findByRole("button", { name: "Search Udaipur" }),
    );
    await waitFor(() =>
      expect(
        server.calls
          .filter((call) => call.path === "/api/v1/destinations/search")
          .map((call) => call.q),
      ).toEqual(["Nathdwara", "Udaipur"]),
    );
    expect(searchField()).toHaveValue("Udaipur");
  });

  it("a completed import sets the trip form's destination and currency", async () => {
    const { user } = renderDetails();
    await screen.findByLabelText("Destination");
    await user.type(searchField(), "Udaipur");
    await user.click(searchButton());
    await user.click(
      await screen.findByRole("button", {
        name: "Udaipur, Rajasthan, India · city",
      }),
    );
    expect(
      await screen.findByText("Ready: 64 places from OpenStreetMap"),
    ).toBeVisible();
    await waitFor(() =>
      expect(screen.getByLabelText("Destination")).toHaveValue(LIVE_ID),
    );
    expect(
      within(screen.getByLabelText("Destination")).getByRole("option", {
        name: "Udaipur (Live data)",
      }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Currency")).toHaveValue("INR");
  });
});

describe("switch ON: keyboard and axe (TC-483)", () => {
  it("the field, the Search button and the results work by keyboard", async () => {
    server.answer.resolve = () => json(liveOut("queued"), 202);
    const { user } = renderSearch();
    await user.tab();
    expect(searchField()).toHaveFocus();
    await user.keyboard("Udaipur");
    await user.tab();
    expect(searchButton()).toHaveFocus();
    await user.keyboard("{Enter}");
    const result = await screen.findByRole("button", {
      name: "Udaipur, Rajasthan, India · city",
    });
    await user.tab();
    expect(result).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(
      await screen.findByText("Building your city: finding places…"),
    ).toBeVisible();
    expect(server.calls.filter((call) => call.method === "POST")).toHaveLength(
      1,
    );
  });

  it("has no axe violation before and after a search", async () => {
    const { container, user } = renderSearch();
    expect(await axeViolations(container)).toEqual([]);
    await user.type(searchField(), "Udaipur");
    await user.click(searchButton());
    await screen.findByRole("button", {
      name: "Udaipur, Rajasthan, India · city",
    });
    expect(await axeViolations(container)).toEqual([]);
  });
});

describe("places step lock (IMP-728 step 5)", () => {
  function renderPlaces() {
    return wrap(
      <PlacesStep
        formId="trip-places"
        destinationId={LIVE_ID}
        initial={[]}
        effect={undefined}
        onSave={vi.fn(async () => [])}
      />,
    );
  }

  it("is disabled with a reason while the live import is not completed", async () => {
    server.answer.detail = () => json(detailOut("running"));
    renderPlaces();
    expect(
      await screen.findByText(/Places can be chosen once your city is ready/),
    ).toBeVisible();
    expect(screen.queryByLabelText("Search places")).toBeNull();
  });

  it("opens once the import is completed", async () => {
    renderPlaces();
    await waitFor(() =>
      expect(
        server.calls.some(
          (call) => call.path === `/api/v1/destinations/${LIVE_ID}`,
        ),
      ).toBe(true),
    );
    expect(screen.getByLabelText("Search places")).toBeVisible();
    expect(screen.queryByText(/Places can be chosen once/)).toBeNull();
  });

  it("with the switch OFF it makes no any-city request", async () => {
    flag.anyCity = false;
    renderPlaces();
    expect(screen.getByLabelText("Search places")).toBeVisible();
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(server.anyCityCalls()).toEqual([]);
  });
});
