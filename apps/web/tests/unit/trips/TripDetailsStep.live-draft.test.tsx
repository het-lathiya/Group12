import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TripDetailsStep } from "@/components/trips/TripDetailsStep";
import type { AnyCitySchemas } from "@/lib/api/anyCityClient";
import type { TripDetailsValues } from "@/lib/validation/trip";

import { axeViolations } from "../../axe";

// IMP-728 (Amendment A2 §9.1): a resumed draft whose destination is live shows that destination
// in the details select (read from API-79), with the tier as text. Switch OFF, or a curated
// draft: unchanged, and no API-79 request. No Supabase and no network.
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

const DETAIL: AnyCitySchemas["DestinationDetailOut"] = {
  id: LIVE_ID,
  slug: "live-udaipur-r1234567",
  name: "Udaipur",
  region: "Rajasthan",
  country_code: "IN",
  timezone: "Asia/Kolkata",
  currency: "INR",
  is_sample: false,
  center: { lat: 24.58, lon: 73.71 },
  bbox: { min_lat: 24.3, min_lon: 73.4, max_lat: 24.8, max_lon: 74 },
  data_tier: "live",
  imported_at: null,
  attribution: [],
  import: {
    status: "completed",
    failure_reason: null,
    places_found: 120,
    places_usable: 64,
    nearby_city: null,
    started_at: null,
    imported_at: null,
    expires_at: null,
  },
};

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

function fakeApi(detail: () => Response = () => json(DETAIL)) {
  const paths: string[] = [];
  vi.stubGlobal("fetch", async (request: Request) => {
    const url = new URL(request.url);
    paths.push(`${request.method} ${url.pathname}`);
    if (url.pathname === "/api/v1/destinations") {
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
    if (url.pathname === `/api/v1/destinations/${LIVE_ID}`) return detail();
    return json(
      {
        error: {
          code: "NOT_FOUND",
          message: "Not found.",
          request_id: "req-1",
          details: [],
          retry_after_s: null,
        },
      },
      404,
    );
  });
  const anyCityCalls = () =>
    paths.filter((path) => path !== "GET /api/v1/destinations");
  return { paths, anyCityCalls };
}

function draft(destinationId: string, currency: string): TripDetailsValues {
  return {
    destination_id: destinationId,
    title: "Resumed trip",
    start_date: "2026-12-01",
    end_date: "2026-12-03",
    adults: 2,
    children: 0,
    group_needs: [],
    budget: { amount: "", currency },
  };
}

function renderDraft(initial: TripDetailsValues) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <TripDetailsStep
        formId="trip-details"
        locked={false}
        initial={initial}
        onSave={vi.fn()}
      />
    </QueryClientProvider>,
  );
}

const select = () =>
  screen.findByRole<HTMLSelectElement>("combobox", { name: "Destination" });
const selectedText = (element: HTMLSelectElement) =>
  element.selectedOptions[0]?.textContent;
const settle = () => new Promise((resolve) => setTimeout(resolve, 30));

let server: ReturnType<typeof fakeApi>;

beforeEach(() => {
  flag.anyCity = true;
  server = fakeApi();
});

describe("switch ON: resumed live draft", () => {
  it("shows the live destination selected with its tier as text", async () => {
    const { container } = renderDraft(draft(LIVE_ID, "INR"));
    const destination = await select();
    await waitFor(() =>
      expect(selectedText(destination)).toBe("Udaipur (Live data)"),
    );
    expect(destination).toHaveValue(LIVE_ID);
    expect(destination).toHaveAccessibleName("Destination");
    expect(screen.getByLabelText("Currency")).toHaveValue("INR");
    expect(server.anyCityCalls()).toEqual([
      `GET /api/v1/destinations/${LIVE_ID}`,
    ]);
    expect(await axeViolations(container)).toEqual([]);
  });

  it("keeps the current output when API-79 fails", async () => {
    server = fakeApi(() =>
      json(
        {
          error: {
            code: "INTERNAL",
            message: "Something went wrong.",
            request_id: "req-2",
            details: [],
            retry_after_s: null,
          },
        },
        500,
      ),
    );
    renderDraft(draft(LIVE_ID, "INR"));
    const destination = await select();
    await waitFor(() =>
      expect(server.anyCityCalls()).toContain(
        `GET /api/v1/destinations/${LIVE_ID}`,
      ),
    );
    await settle();
    expect(destination.value).toBe("");
    expect(screen.queryByRole("option", { name: /Live data/ })).toBeNull();
    expect(destination).toHaveAccessibleName("Destination");
  });

  it("a curated draft is unchanged and makes no API-79 request", async () => {
    renderDraft(draft(SAMPLE_ID, "GBP"));
    const destination = await select();
    await waitFor(() =>
      expect(selectedText(destination)).toBe("Sampleton (sample)"),
    );
    await settle();
    expect(screen.getByLabelText("Currency")).toHaveValue("GBP");
    expect(screen.queryByRole("option", { name: /Live data/ })).toBeNull();
    expect(server.anyCityCalls()).toEqual([]);
  });
});

describe("switch OFF", () => {
  beforeEach(() => {
    flag.anyCity = false;
  });

  it("an unknown draft id is unchanged and makes no any-city request", async () => {
    const { container } = renderDraft(draft(LIVE_ID, "INR"));
    const destination = await select();
    await settle();
    expect(destination.value).toBe("");
    expect(screen.queryByRole("option", { name: /Live data/ })).toBeNull();
    expect(screen.queryByLabelText("Any city (live data)")).toBeNull();
    expect(server.anyCityCalls()).toEqual([]);
    expect(await axeViolations(container)).toEqual([]);
  });
});
