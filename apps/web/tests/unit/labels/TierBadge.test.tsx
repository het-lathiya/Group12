import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ExplorePage from "@/app/(app)/trips/[tripId]/explore/page";
import { ItineraryItemCard } from "@/components/itinerary/ItineraryItemCard";
import { WarningsPanel } from "@/components/itinerary/WarningsPanel";
import { LiveTierProvider } from "@/components/labels/liveTier";
import { SourceBadge } from "@/components/labels/SourceBadge";
import {
  LIVE_HINT,
  TierBadge,
  useDestinationTier,
} from "@/components/labels/TierBadge";
import { PlaceCard, type Place } from "@/components/places/PlaceCard";
import { PreferenceForm } from "@/components/trips/PreferenceForm";
import type { AnyCitySchemas } from "@/lib/api/anyCityClient";
import type { components } from "@/lib/api/schema";

import { axeViolations } from "../../axe";
import { ITEM } from "../itinerary/fixtures";

// TC-484 (Amendment A2 §9.2, IMP-729): the tier badge, the OpenStreetMap source badge, the
// "Price unknown" and "Hours unknown" chips and the grouped hours warning render on live data
// only. Curated and SAMPLE destinations keep today's labels, and with `any_city_mode` OFF nothing
// new renders and API-79 is never called. No Supabase and no network.
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
const TRIP_ID = "00000000-0000-4000-8000-000000000002";
const LIVE_ID = "00000000-0000-4000-8000-0000000000d1";
vi.mock("next/navigation", () => ({
  useParams: () => ({ tripId: TRIP_ID }),
  useRouter: () => ({ replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));
vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test/api/v1");

type Finding = components["schemas"]["Finding"];

const OSM_TEXT =
  "Place data © OpenStreetMap contributors, available under the Open Database Licence (ODbL)";

const livePlace = (overrides: Partial<Place> = {}): Place => ({
  id: "00000000-0000-4000-8000-0000000000e1",
  name: "City Palace",
  category: "sight",
  tags: [],
  lat: 24.576,
  lon: 73.683,
  typical_duration_min: 90,
  price: null,
  price_label: "unavailable",
  hours_label: "unavailable",
  verification_status: "imported_osm",
  suitability: { step_free: null, child_friendly: null, indoor: null },
  source_name: "OpenStreetMap",
  ...overrides,
});

function detail(
  tier: "live" | "curated",
  isSample = false,
): AnyCitySchemas["DestinationDetailOut"] {
  return {
    id: LIVE_ID,
    slug: tier === "live" ? "live-udaipur-r1234567" : "jaipur",
    name: tier === "live" ? "Udaipur" : "Jaipur",
    region: "Rajasthan",
    country_code: "IN",
    timezone: "Asia/Kolkata",
    currency: "INR",
    is_sample: isSample,
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
              attribution_text: OSM_TEXT,
              url: "https://www.openstreetmap.org/copyright",
            },
          ]
        : [],
    import: null,
  };
}

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

function fakeApi(destination: AnyCitySchemas["DestinationDetailOut"]) {
  const paths: string[] = [];
  vi.stubGlobal("fetch", async (request: Request) => {
    const url = new URL(request.url);
    paths.push(url.pathname);
    if (url.pathname === `/api/v1/destinations/${LIVE_ID}`) {
      return json(destination);
    }
    if (url.pathname === "/api/v1/places") {
      return json({
        items: [livePlace()],
        total: 1,
        limit: 24,
        offset: 0,
      });
    }
    if (url.pathname === `/api/v1/trips/${TRIP_ID}`) {
      return json({
        id: TRIP_ID,
        destination_id: LIVE_ID,
        destination: {
          id: LIVE_ID,
          name: destination.name,
          currency: "INR",
          timezone: "Asia/Kolkata",
          is_sample: destination.is_sample,
        },
      });
    }
    return json([]);
  });
  return paths;
}

function withClient(ui: ReactNode) {
  return (
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      {ui}
    </QueryClientProvider>
  );
}

beforeEach(() => {
  flag.anyCity = true;
});
afterEach(() => {
  vi.unstubAllGlobals();
});

describe("TierBadge (TC-484)", () => {
  it("shows Live data with the §9.1 hint for a live destination", async () => {
    const { container } = render(<TierBadge tier="live" />);
    expect(screen.getByText("Live data")).toBeInTheDocument();
    expect(screen.getByText(LIVE_HINT)).toBeInTheDocument();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("shows Curated, without the live hint, for a curated destination", () => {
    render(<TierBadge tier="curated" />);
    expect(screen.getByText("Curated")).toBeInTheDocument();
    expect(screen.queryByText(LIVE_HINT)).not.toBeInTheDocument();
  });

  it("leaves the SAMPLE destination with its own label only", () => {
    const { container } = render(<TierBadge tier="curated" isSample />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing while the tier is unknown", () => {
    const { container } = render(<TierBadge tier={undefined} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing with the switch OFF", () => {
    flag.anyCity = false;
    const { container } = render(<TierBadge tier="live" />);
    expect(container).toBeEmptyDOMElement();
  });

  it("makes no API-79 request with the switch OFF", async () => {
    flag.anyCity = false;
    const paths = fakeApi(detail("live"));
    function Probe() {
      const { tier } = useDestinationTier(LIVE_ID);
      return <p>{tier ?? "no tier"}</p>;
    }
    render(withClient(<Probe />));
    expect(await screen.findByText("no tier")).toBeInTheDocument();
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(paths).toEqual([]);
  });
});

describe("unknown chips and the OpenStreetMap badge (TC-484)", () => {
  it("SourceBadge reads Price unknown and Hours unknown only when live", () => {
    render(
      <>
        <SourceBadge label="unavailable" live />
        <SourceBadge label="unavailable" kind="hours" live />
        <SourceBadge label="unavailable" />
        <SourceBadge label="openstreetmap" />
      </>,
    );
    expect(screen.getByText("Price unknown")).toBeInTheDocument();
    expect(screen.getByText("Hours unknown")).toBeInTheDocument();
    expect(screen.getByText("Unavailable")).toBeInTheDocument();
    expect(screen.getByText("OpenStreetMap")).toHaveClass("text-info");
  });

  it("a live PlaceCard shows the chips and the OpenStreetMap source", async () => {
    const { container } = render(
      <LiveTierProvider value>
        <PlaceCard place={livePlace()} />
      </LiveTierProvider>,
    );
    expect(screen.getByText("Price unknown")).toBeInTheDocument();
    expect(screen.getByText("Hours unknown")).toBeInTheDocument();
    expect(screen.getByText("OpenStreetMap")).toBeInTheDocument();
    expect(screen.queryByText("Unavailable")).not.toBeInTheDocument();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("a curated PlaceCard keeps Unavailable", () => {
    render(
      <PlaceCard
        place={livePlace({
          verification_status: "curated_checked",
          source_name: "Team survey",
        })}
      />,
    );
    expect(screen.getAllByText("Unavailable")).toHaveLength(2);
    expect(screen.queryByText(/unknown/)).not.toBeInTheDocument();
    expect(screen.getByText("Team survey")).toBeInTheDocument();
  });

  it("a live itinerary item shows the chips and the OpenStreetMap source", () => {
    const item = {
      ...ITEM,
      note: null,
      note_origin: "none" as const,
      cost: null,
      place: {
        ...ITEM.place,
        name: "City Palace",
        hours_label: "unavailable" as const,
      },
    };
    render(
      withClient(
        <LiveTierProvider value>
          <ItineraryItemCard item={item} />
        </LiveTierProvider>,
      ),
    );
    expect(screen.getByText("Price unknown")).toBeInTheDocument();
    expect(screen.getByText("Hours unknown")).toBeInTheDocument();
    expect(screen.getByText("OpenStreetMap")).toBeInTheDocument();
  });

  it("a curated itinerary item keeps Unavailable", () => {
    const item = {
      ...ITEM,
      cost: null,
      place: { ...ITEM.place, hours_label: "unavailable" as const },
    };
    render(withClient(<ItineraryItemCard item={item} />));
    expect(screen.getAllByText("Unavailable")).toHaveLength(2);
    expect(screen.queryByText("OpenStreetMap")).not.toBeInTheDocument();
  });
});

describe("grouped hours warning (TC-484)", () => {
  const hours = (day: number, item: string): Finding => ({
    id: crypto.randomUUID(),
    code: "HOURS_UNVERIFIED",
    severity: "info",
    message: "Opening hours unavailable for this stop.",
    day_number: day,
    item_id: item,
    place_id: null,
    suggested_fix: "Check opening times before the visit.",
  });
  const findings = [
    hours(1, "00000000-0000-4000-8000-0000000000c1"),
    hours(1, "00000000-0000-4000-8000-0000000000c2"),
    hours(2, "00000000-0000-4000-8000-0000000000c3"),
  ];

  it("groups HOURS_UNVERIFIED into one info line on the live tier", async () => {
    const { container } = render(
      <LiveTierProvider value>
        <WarningsPanel findings={findings} onGoToItem={() => {}} />
      </LiveTierProvider>,
    );
    const line = screen.getByText("Opening hours unknown for 3 stops");
    expect(line.closest("li")).toHaveTextContent("Info");
    expect(
      screen.queryByText("Opening hours unavailable for this stop."),
    ).not.toBeInTheDocument();
    expect(screen.getAllByText("1 info").length).toBeGreaterThan(0);
    expect(await axeViolations(container)).toEqual([]);
  });

  it("keeps one row per stop on a curated destination", () => {
    render(<WarningsPanel findings={findings} onGoToItem={() => {}} />);
    expect(
      screen.getAllByText("Opening hours unavailable for this stop."),
    ).toHaveLength(3);
    expect(
      screen.queryByText(/Opening hours unknown for/),
    ).not.toBeInTheDocument();
  });
});

describe("step-free warning on the live tier (Amendment A2 §9.2)", () => {
  const WARNING =
    "Few live places have step-free information; your list may be short";
  const preferences: components["schemas"]["PreferencesOut"] = {
    interests: [],
    pace: "balanced",
    budget_priority: "balanced",
    transport_pref: "walking",
    accommodation_type: "any",
    step_free_required: false,
    notes: null,
    must_visit_place_ids: [],
    must_visit_places: [],
    saved: false,
    effects: [],
  };

  it("shows the warning once step-free is ticked for a live destination", async () => {
    fakeApi(detail("live"));
    const user = userEvent.setup();
    render(
      withClient(
        <PreferenceForm
          formId="prefs"
          preferences={preferences}
          onSave={async () => []}
          destinationId={LIVE_ID}
        />,
      ),
    );
    expect(screen.queryByText(WARNING)).not.toBeInTheDocument();
    await user.click(screen.getByLabelText("I need step-free access"));
    expect(await screen.findByText(WARNING)).toBeInTheDocument();
  });

  it("never shows it with the switch OFF", async () => {
    flag.anyCity = false;
    const paths = fakeApi(detail("live"));
    const user = userEvent.setup();
    render(
      withClient(
        <PreferenceForm
          formId="prefs"
          preferences={preferences}
          onSave={async () => []}
          destinationId={LIVE_ID}
        />,
      ),
    );
    await user.click(screen.getByLabelText("I need step-free access"));
    expect(screen.queryByText(WARNING)).not.toBeInTheDocument();
    expect(paths).toEqual([]);
  });
});

describe("explore page (TC-484)", () => {
  it("a live destination shows the tier badge, chips and attribution footer", async () => {
    fakeApi(detail("live"));
    const { container } = render(withClient(<ExplorePage />));
    expect(await screen.findByText("Live data")).toBeInTheDocument();
    expect(await screen.findByText("Price unknown")).toBeInTheDocument();
    expect(screen.getByText("Hours unknown")).toBeInTheDocument();
    const footer = screen.getByRole("heading", { name: "Data sources" })
      .parentElement as HTMLElement;
    expect(within(footer).getByText(OSM_TEXT)).toBeInTheDocument();
    expect(await axeViolations(container)).toEqual([]);
  });

  it("a curated destination shows Curated and keeps Unavailable, with no footer", async () => {
    fakeApi(detail("curated"));
    render(withClient(<ExplorePage />));
    expect(await screen.findByText("Curated")).toBeInTheDocument();
    expect(await screen.findAllByText("Unavailable")).toHaveLength(2);
    expect(screen.queryByText("Live data")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Data sources" }),
    ).not.toBeInTheDocument();
  });

  it("the switch OFF renders nothing new and never calls API-79", async () => {
    flag.anyCity = false;
    const paths = fakeApi(detail("live"));
    render(withClient(<ExplorePage />));
    expect(await screen.findAllByText("Unavailable")).toHaveLength(2);
    expect(screen.queryByText("Live data")).not.toBeInTheDocument();
    expect(screen.queryByText("Curated")).not.toBeInTheDocument();
    expect(screen.queryByText(OSM_TEXT)).not.toBeInTheDocument();
    expect(paths).not.toContain(`/api/v1/destinations/${LIVE_ID}`);
  });
});
