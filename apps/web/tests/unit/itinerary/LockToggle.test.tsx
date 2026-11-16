import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { ItineraryItemCard } from "@/components/itinerary/ItineraryItemCard";
import { useItinerary } from "@/lib/api/queries";
import { ITEM, planWith, TRIP_ID } from "./fixtures";

vi.mock("@/lib/auth/supabase", () => ({
  getSupabase: () => ({
    auth: {
      getSession: async () => ({ data: { session: { access_token: "t" } } }),
    },
  }),
}));
const flags = vi.hoisted(() => ({ locks: true }));
vi.mock("@/lib/flags", () => ({
  isEnabled: (name: string) => name !== "locks" || flags.locks,
}));
vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test/api/v1");
const json = (data: unknown) =>
  new Response(JSON.stringify(data), {
    headers: { "Content-Type": "application/json" },
  });
function Harness() {
  const plan = useItinerary(TRIP_ID).data;
  return (
    plan && (
      <ItineraryItemCard
        item={plan.days[0].items[0]}
        edit={{
          tripId: TRIP_ID,
          planRevision: plan.plan_revision,
          dayNumber: 1,
          dayNumbers: [1],
          itemCount: 1,
        }}
      />
    )
  );
}
function setup(locked = false) {
  let plan = planWith([[{ ...ITEM, is_locked: locked }]], 7);
  const writes: unknown[] = [];
  vi.stubGlobal("fetch", async (request: Request) => {
    if (request.method === "GET") return json(plan);
    const body = await request.json();
    writes.push(body);
    plan = planWith(
      [[{ ...ITEM, is_locked: body.is_locked }]],
      plan.plan_revision + 1,
    );
    return json({
      plan_revision: plan.plan_revision,
      changed_days: plan.days,
      totals: plan.totals,
      findings: [],
    });
  });
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <Harness />
    </QueryClientProvider>,
  );
  return { writes, user: userEvent.setup() };
}
afterEach(() => {
  vi.unstubAllGlobals();
  flags.locks = true;
});
it("locks with Space and unlocks with Enter, announces the server state and sends current revisions", async () => {
  const { writes, user } = setup();
  const button = await screen.findByRole("button", {
    name: `Lock ${ITEM.place.name}`,
  });
  expect(button).toHaveAttribute("aria-pressed", "false");
  button.focus();
  await user.keyboard(" ");
  const locked = await screen.findByRole("button", {
    name: `Locked ${ITEM.place.name}`,
  });
  expect(locked).toHaveAttribute("aria-pressed", "true");
  expect(locked).toHaveTextContent("Locked");
  locked.focus();
  await user.keyboard("{Enter}");
  expect(
    await screen.findByRole("button", { name: `Lock ${ITEM.place.name}` }),
  ).toHaveAttribute("aria-pressed", "false");
  expect(writes).toEqual([
    { plan_revision: 7, is_locked: true },
    { plan_revision: 8, is_locked: false },
  ]);
});
it("hides the lock control and indicator when locks are disabled", async () => {
  flags.locks = false;
  setup(true);
  await screen.findByRole("heading", { name: ITEM.place.name });
  expect(
    screen.queryByRole("button", { name: /^(Lock|Locked) / }),
  ).not.toBeInTheDocument();
  expect(screen.queryByText("Locked")).not.toBeInTheDocument();
});
