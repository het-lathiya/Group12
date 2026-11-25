import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SummaryPage from "@/app/(app)/trips/[tripId]/summary/page";
import { TripWizard } from "@/components/trips/TripWizard";
import type { AnyCitySchemas } from "@/lib/api/anyCityClient";
import type { components } from "@/lib/api/schema";

import { axeViolations } from "../../axe";
import { ITEM, TRIP_ID } from "../itinerary/fixtures";

// Amendment A2 §10 (IMP-729): every screen that shows live places carries the §9.3 attribution.
// The summary page (inside its printed part) and the trip form's places and review steps, against
// a fake API. Curated and SAMPLE screens, and the switch OFF, are unchanged. No network.
vi.mock("next/navigation", () => ({
  useParams: () => ({ tripId: TRIP_ID }),
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
}));
vi.mock("@/lib/auth/supabase", () => ({
  getSupabase: () => ({
    auth: {
      getSession: async () => ({ data: { session: { access_token: "t" } } }),
    },
  }),
}));
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

type Schemas = components["schemas"];
type Detail = AnyCitySchemas["DestinationDetailOut"];

const DESTINATION_ID = "00000000-0000-4000-8000-0000000000d1";
const OSM_TEXT =
  "Place data © OpenStreetMap contributors, available under the Open Database Licence (ODbL)";
const WIKI_TEXT =
  "Guide text from Wikivoyage (Liveton (SAMPLE)), by its contributors, under CC BY-SA 4.0; excerpts, some sections left out";
const MUST_VISIT = {
  id: "00000000-0000-4000-8000-0000000000e1",
  name: "Hill Fort (SAMPLE)",
};

const TRIP: Schemas["TripOut"] = {
  id: TRIP_ID,
  title: "Weekend in Liveton (SAMPLE)",
  destination_id: DESTINATION_ID,
  destination: {
    id: DESTINATION_ID,
    name: "Liveton (SAMPLE)",
    currency: "INR",
    timezone: "Asia/Kolkata",
    is_sample: false,
  },
  start_date: "2026-12-04",
  end_date: "2026-12-04",
  num_days: 1,
  adults: 2,
  children: 0,
  budget: null,
  group_needs: [],
  status: "ready",
  plan_revision: 1,
  plan_stale: false,
  has_itinerary: true,
  created_at: "2026-11-15T10:00:00Z",
  updated_at: "2026-11-15T10:00:00Z",
};

const COSTS: Schemas["TripSummaryOut"]["costs"] = {
  currency: "INR",
  estimate: { min: "0.00", max: "0.00" },
  contingency: { pct: 10, amount: "0.00" },
  planning_total: "0.00",
  per_traveller: { travellers: 2, largest_share: "0.00", label: "average" },
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
};

const SUMMARY: Schemas["TripSummaryOut"] = {
  trip: TRIP,
  days: [
    {
      day_number: 1,
      date: "2026-12-04",
      theme: null,
      theme_origin: "none",
      day_cost: { min: "0.00", max: "0.00", currency: "INR", complete: false },
      items: [{ ...ITEM, cost: null }],
    },
  ],
  unresolved_findings: [],
  costs: COSTS,
  generated_at: "2026-11-15T10:00:00Z",
};

const PREFERENCES: Schemas["PreferencesOut"] = {
  interests: [],
  pace: "balanced",
  budget_priority: "balanced",
  transport_pref: "walking",
  accommodation_type: "any",
  step_free_required: false,
  notes: null,
  must_visit_place_ids: [MUST_VISIT.id],
  must_visit_places: [MUST_VISIT],
  effects: [],
  saved: true,
};

function detail(tier: Detail["data_tier"], isSample = false): Detail {
  return {
    id: DESTINATION_ID,
    slug: "live-liveton-r9000001",
    name: "Liveton (SAMPLE)",
    region: null,
    country_code: "IN",
    timezone: "Asia/Kolkata",
    currency: "INR",
    is_sample: isSample,
    center: { lat: 23.5, lon: 77.5 },
    bbox: { min_lat: 23.4, min_lon: 77.4, max_lat: 23.6, max_lon: 77.6 },
    data_tier: tier,
    imported_at: null,
    attribution: [
      {
        source_name: "OpenStreetMap",
        licence: "ODbL 1.0",
        attribution_text: OSM_TEXT,
        url: "https://www.openstreetmap.org/copyright",
      },
      {
        source_name: "Wikivoyage",
        licence: "CC BY-SA 4.0",
        attribution_text: WIKI_TEXT,
        url: "https://en.wikivoyage.org/wiki/Liveton_(SAMPLE)",
      },
    ],
    import:
      tier === "live"
        ? {
            status: "completed",
            failure_reason: null,
            places_found: 48,
            places_usable: 44,
            nearby_city: null,
            started_at: null,
            imported_at: null,
            expires_at: null,
          }
        : null,
  };
}

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

/** Answers by path and returns the requested paths. */
function fakeApi(destination: Detail): string[] {
  const paths: string[] = [];
  const answers: Record<string, unknown> = {
    [`/api/v1/trips/${TRIP_ID}`]: TRIP,
    [`/api/v1/trips/${TRIP_ID}/summary`]: SUMMARY,
    [`/api/v1/trips/${TRIP_ID}/preferences`]: PREFERENCES,
    [`/api/v1/trips/${TRIP_ID}/costs`]: COSTS,
    [`/api/v1/destinations/${DESTINATION_ID}`]: destination,
    "/api/v1/destinations": [],
    "/api/v1/me": {
      id: "u",
      display_name: null,
      default_preferences: {},
      created_at: "2026-11-01T00:00:00Z",
    },
  };
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: Request | string | URL) => {
      const url = new URL(input instanceof Request ? input.url : String(input));
      paths.push(url.pathname);
      const body = answers[url.pathname];
      return body === undefined
        ? json(
            { error: { code: "NOT_FOUND", message: "x", request_id: null } },
            404,
          )
        : json(body);
    }),
  );
  return paths;
}

const withClient = (node: React.ReactNode) => (
  <QueryClientProvider
    client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
  >
    {node}
  </QueryClientProvider>
);
const DETAIL_PATH = `/api/v1/destinations/${DESTINATION_ID}`;
const sources = () => screen.queryByRole("heading", { name: "Data sources" });

async function expectSources(root: HTMLElement) {
  const heading = await screen.findByRole("heading", { name: "Data sources" });
  const footer = heading.closest("footer") as HTMLElement;
  expect(root).toContainElement(footer);
  expect(within(footer).getByText(OSM_TEXT)).toBeInTheDocument();
  expect(within(footer).getByText(WIKI_TEXT)).toBeInTheDocument();
  const links = within(footer).getAllByRole("link");
  expect(links.map((a) => a.getAttribute("href"))).toEqual([
    "https://www.openstreetmap.org/copyright",
    "https://en.wikivoyage.org/wiki/Liveton_(SAMPLE)",
    "https://creativecommons.org/licenses/by-sa/4.0/",
  ]);
  return links;
}

/** Tab reaches the links one after another, in order. */
async function expectKeyboard(links: HTMLElement[]) {
  const user = userEvent.setup();
  links[0].focus();
  for (const link of links) {
    expect(link).toHaveFocus();
    await user.tab();
  }
}

beforeEach(() => {
  flag.anyCity = true;
  // jsdom has no scrollTo.
  vi.stubGlobal("scrollTo", vi.fn());
});

describe("summary page (A2 §10)", () => {
  it("a live trip's summary carries the attribution inside the printed part", async () => {
    fakeApi(detail("live"));
    const { container } = render(withClient(<SummaryPage />));
    await screen.findByText(ITEM.place.name);
    const printed = container.querySelector("[data-print-root]") as HTMLElement;
    const links = await expectSources(printed);
    expect(await axeViolations(container)).toEqual([]);
    await expectKeyboard(links);
  });

  it.each([
    ["curated", detail("curated")],
    ["SAMPLE", detail("curated", true)],
  ])("a %s summary is unchanged", async (_label, destination) => {
    const paths = fakeApi(destination);
    render(withClient(<SummaryPage />));
    await screen.findByText(ITEM.place.name);
    await vi.waitFor(() => expect(paths).toContain(DETAIL_PATH));
    expect(sources()).not.toBeInTheDocument();
  });

  it("the switch OFF renders nothing new and never calls API-79", async () => {
    flag.anyCity = false;
    const paths = fakeApi(detail("live"));
    render(withClient(<SummaryPage />));
    await screen.findByText(ITEM.place.name);
    expect(sources()).not.toBeInTheDocument();
    expect(paths).not.toContain(DETAIL_PATH);
  });
});

describe("trip form (A2 §10)", () => {
  it("the review and places steps carry the attribution; earlier steps do not", async () => {
    fakeApi(detail("live"));
    const user = userEvent.setup();
    const { container } = render(withClient(<TripWizard draftId={TRIP_ID} />));
    await screen.findByRole("heading", { level: 2, name: "Review your trip" });
    expect(
      (await screen.findAllByText(MUST_VISIT.name)).length,
    ).toBeGreaterThan(0);
    const links = await expectSources(container);
    expect(await axeViolations(container)).toEqual([]);
    await expectKeyboard(links);

    await user.click(screen.getByRole("button", { name: "Back" }));
    await screen.findByRole("heading", { level: 2, name: "Must-visit places" });
    await expectSources(container);
    expect(await axeViolations(container)).toEqual([]);

    await user.click(screen.getByRole("button", { name: "Back" }));
    await screen.findByRole("heading", { level: 2, name: "Your preferences" });
    expect(sources()).not.toBeInTheDocument();
  });

  it.each([
    ["curated", detail("curated")],
    ["SAMPLE", detail("curated", true)],
  ])("a %s trip form is unchanged", async (_label, destination) => {
    const paths = fakeApi(destination);
    render(withClient(<TripWizard draftId={TRIP_ID} />));
    await screen.findByRole("heading", { level: 2, name: "Review your trip" });
    await vi.waitFor(() => expect(paths).toContain(DETAIL_PATH));
    expect(sources()).not.toBeInTheDocument();
  });

  it("the switch OFF renders nothing new and never calls API-79", async () => {
    flag.anyCity = false;
    const paths = fakeApi(detail("live"));
    render(withClient(<TripWizard draftId={TRIP_ID} />));
    await screen.findByRole("heading", { level: 2, name: "Review your trip" });
    expect(sources()).not.toBeInTheDocument();
    expect(paths).not.toContain(DETAIL_PATH);
  });
});
