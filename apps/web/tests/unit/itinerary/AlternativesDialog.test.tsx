import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { AlternativesDialog } from "@/components/itinerary/AlternativesDialog";
import { CURRENT_VERSION, queryKeys } from "@/lib/api/queries";
import { ITEM, ITEM_B, planWith, TRIP_ID } from "./fixtures";

vi.mock("@/lib/auth/supabase", () => ({
  getSupabase: () => ({
    auth: {
      getSession: async () => ({ data: { session: { access_token: "t" } } }),
    },
  }),
}));
const flags = vi.hoisted(() => ({ enabled: true }));
vi.mock("@/lib/flags", () => ({ isEnabled: () => flags.enabled }));
vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test/api/v1");
const json = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
function setup(empty = false) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const plan = planWith([[ITEM]], 7);
  client.setQueryData(queryKeys.itinerary(TRIP_ID, CURRENT_VERSION), plan);
  const post = vi.fn();
  vi.stubGlobal("fetch", async (request: Request) => {
    if (request.method === "GET")
      return json({
        item_id: ITEM.id,
        alternatives: empty
          ? []
          : [
              {
                place: {
                  ...ITEM_B.place,
                  price_label: "estimate",
                  price: {
                    min: "12.00",
                    max: "15.00",
                    currency: "INR",
                    label: "estimate",
                  },
                },
                cost_delta: { min: "-2.00", max: "3.00" },
                time_delta_min: -15,
                reason: "Matches your interests",
              },
            ],
      });
    post(await request.json());
    return json({
      plan_revision: 8,
      changed_days: planWith([[ITEM_B]], 8).days,
      totals: { ...plan.totals, planning_total: "456.78" },
      findings: [],
    });
  });
  render(
    <QueryClientProvider client={client}>
      <AlternativesDialog item={ITEM} tripId={TRIP_ID} planRevision={7} />
    </QueryClientProvider>,
  );
  return { client, post, user: userEvent.setup() };
}
afterEach(() => {
  vi.unstubAllGlobals();
  flags.enabled = true;
});
it("shows ranked facts and deltas, then applies with revision and uses the server result", async () => {
  const { client, post, user } = setup();
  await user.click(
    screen.getByRole("button", { name: `Replace ${ITEM.place.name}` }),
  );
  expect(
    await screen.findByText("Cost change: INR -2.00–3.00"),
  ).toBeInTheDocument();
  expect(screen.getByText("Time change: -15 min")).toBeInTheDocument();
  expect(screen.getByText("Estimate")).toBeInTheDocument();
  await user.click(
    screen.getByRole("button", { name: `Apply ${ITEM_B.place.name}` }),
  );
  await waitFor(() =>
    expect(post).toHaveBeenCalledWith({
      place_id: ITEM_B.place.id,
      plan_revision: 7,
    }),
  );
  expect(
    client.getQueryData<ReturnType<typeof planWith>>(
      queryKeys.itinerary(TRIP_ID, CURRENT_VERSION),
    )?.totals.planning_total,
  ).toBe("456.78");
});
it("shows the exact empty state", async () => {
  const { user } = setup(true);
  await user.click(
    screen.getByRole("button", { name: `Replace ${ITEM.place.name}` }),
  );
  expect(
    await screen.findByText("No alternative fits this slot"),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: /^Apply/ }),
  ).not.toBeInTheDocument();
});
it("hides Replace when alternatives are disabled", () => {
  flags.enabled = false;
  setup();
  expect(
    screen.queryByRole("button", { name: /^Replace/ }),
  ).not.toBeInTheDocument();
});
