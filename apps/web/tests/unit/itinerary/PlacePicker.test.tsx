import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { PlacePicker } from "@/components/itinerary/PlacePicker";
import { Toaster } from "@/components/ui/sonner";
import { CURRENT_VERSION, queryKeys } from "@/lib/api/queries";
import { ITEM, planWith, TRIP_ID } from "./fixtures";

vi.mock("@/lib/auth/supabase", () => ({
  getSupabase: () => ({
    auth: {
      getSession: async () => ({ data: { session: { access_token: "t" } } }),
    },
  }),
}));
vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test/api/v1");
const json = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
const place = {
  ...ITEM.place,
  tags: [],
  typical_duration_min: 90,
  price: null,
  price_label: "unavailable",
  hours_label: "curated",
  verification_status: "curated_checked",
  suitability: { step_free: true, child_friendly: true, indoor: true },
};
function setup(stale = false) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const original = planWith([[]], 7);
  client.setQueryData(queryKeys.itinerary(TRIP_ID, CURRENT_VERSION), original);
  const requests: { method: string; body: unknown }[] = [];
  vi.stubGlobal("fetch", async (request: Request) => {
    if (request.method === "GET")
      return json({ items: [place], total: 1, limit: 20, offset: 0 });
    requests.push({
      method: request.method,
      body:
        request.method === "POST"
          ? await request.json()
          : new URL(request.url).searchParams.get("plan_revision"),
    });
    if (stale)
      return json(
        {
          error: {
            code: "STALE_PLAN",
            message: "Stale",
            details: [],
            request_id: "request",
          },
        },
        409,
      );
    return json({
      plan_revision: 8,
      changed_days: [{ ...original.days[0], day_number: 2, items: [ITEM] }],
      totals: { ...original.totals, planning_total: "987.65" },
      findings: [],
    });
  });
  render(
    <QueryClientProvider client={client}>
      <PlacePicker
        tripId={TRIP_ID}
        destinationId="destination"
        planRevision={7}
        dayNumbers={[1, 2]}
      />
      <Toaster />
    </QueryClientProvider>,
  );
  return { client, requests, user: userEvent.setup() };
}
afterEach(() => vi.unstubAllGlobals());
it("searches API-16, adds with revision, renders server totals and a new day, and undoes via API-27", async () => {
  const { client, requests, user } = setup();
  await user.click(screen.getByRole("button", { name: "Add a place" }));
  await user.selectOptions(screen.getByRole("combobox", { name: "Day" }), "2");
  await user.type(
    screen.getByRole("textbox", { name: "Search places" }),
    "Mill",
  );
  await user.click(
    await screen.findByRole("button", { name: `Add ${place.name}` }),
  );
  expect(requests[0]).toEqual({
    method: "POST",
    body: { plan_revision: 7, day_number: 2, place_id: place.id },
  });
  const cached = client.getQueryData<ReturnType<typeof planWith>>(
    queryKeys.itinerary(TRIP_ID, CURRENT_VERSION),
  );
  expect(cached?.totals.planning_total).toBe("987.65");
  expect(cached?.days.map((d) => d.day_number)).toEqual([1, 2]);
  fireEvent.click(await screen.findByRole("button", { name: "Undo" }));
  await waitFor(() =>
    expect(requests[1]).toEqual({ method: "DELETE", body: "8" }),
  );
});
it("a stale edit refetches the shared plan and offers the exact message and Reload action", async () => {
  const { client, user } = setup(true);
  const invalidate = vi.spyOn(client, "invalidateQueries");
  await user.click(screen.getByRole("button", { name: "Add a place" }));
  await user.type(
    screen.getByRole("textbox", { name: "Search places" }),
    "Mill",
  );
  await user.click(
    await screen.findByRole("button", { name: `Add ${place.name}` }),
  );
  expect(
    await screen.findByText("This plan changed since you opened it"),
  ).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Reload" })).toBeInTheDocument();
  expect(invalidate).toHaveBeenCalledWith({
    queryKey: queryKeys.itinerary(TRIP_ID),
  });
  expect(
    client.getQueryData<ReturnType<typeof planWith>>(
      queryKeys.itinerary(TRIP_ID, CURRENT_VERSION),
    )?.plan_revision,
  ).toBe(7);
});
