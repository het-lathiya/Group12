import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";

import ItineraryPage from "@/app/(app)/trips/[tripId]/itinerary/page";
import { CURRENT_VERSION, queryKeys } from "@/lib/api/queries";
import type { components } from "@/lib/api/schema";
import { ITEM, planWith, TRIP_ID } from "./fixtures";

vi.mock("@/lib/auth/supabase", () => ({
  getSupabase: () => ({
    auth: {
      getSession: async () => ({ data: { session: { access_token: "t" } } }),
    },
  }),
}));
const router = { push: vi.fn() };
vi.mock("next/navigation", () => ({
  useParams: () => ({ tripId: TRIP_ID }),
  useRouter: () => router,
}));
const flags = vi.hoisted(() => ({ regeneration: true }));
vi.mock("@/lib/flags", () => ({
  isEnabled: (name: string) => name !== "regeneration" || flags.regeneration,
}));
vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test/api/v1");

function setup() {
  const posts: { path: string; body: unknown }[] = [];
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  let plan = planWith([[ITEM]], 7);
  client.setQueryData(queryKeys.itinerary(TRIP_ID, CURRENT_VERSION), plan);
  const genId = "00000000-0000-4000-8000-0000000000e1";
  const generation = (status: "queued" | "completed") => ({
    id: genId,
    trip_id: TRIP_ID,
    status,
    outcome: status === "completed" ? "fallback_rule_based" : null,
    scope: "full",
    day_number: null,
    repair_attempts: 0,
  });
  vi.stubGlobal("matchMedia", () => ({
    matches: true,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
  }));
  vi.stubGlobal("fetch", async (request: Request) => {
    const path = new URL(request.url).pathname;
    if (request.method === "POST") {
      posts.push({ path, body: await request.json() });
      return Response.json(generation("queued"), { status: 202 });
    }
    if (path.includes("/generations/")) {
      plan = {
        ...planWith([[ITEM]], 8),
        source: {
          generation_id: genId,
          provider: "MOCK",
          outcome: "fallback_rule_based",
        },
      };
      return Response.json(generation("completed"));
    }
    if (path.endsWith("/itinerary")) return Response.json(plan);
    if (path.endsWith("/preferences"))
      return Response.json({ must_visit_places: [] });
    return Response.json({ id: TRIP_ID });
  });
  const invalidate = vi.spyOn(client, "invalidateQueries");
  render(
    <QueryClientProvider client={client}>
      <ItineraryPage />
    </QueryClientProvider>,
  );
  return { posts, client, invalidate, user: userEvent.setup() };
}

afterEach(() => {
  vi.unstubAllGlobals();
  flags.regeneration = true;
});

it("IMP-607: confirms the whole plan, polls progress and invalidates all derived views", async () => {
  const { posts, client, invalidate, user } = setup();
  await user.click(
    await screen.findByRole("button", { name: "Regenerate all" }),
  );
  await user.click(
    within(screen.getByRole("dialog")).getByRole("button", { name: "Cancel" }),
  );
  expect(posts).toEqual([]);
  await user.click(screen.getByRole("button", { name: "Regenerate all" }));
  within(screen.getByRole("dialog"))
    .getByRole("button", { name: "Regenerate all" })
    .focus();
  await user.keyboard("{Enter}");
  await waitFor(() => expect(posts).toHaveLength(1));
  expect(posts[0]).toEqual({
    path: `/api/v1/trips/${TRIP_ID}/itinerary/regenerate`,
    body: { plan_revision: 7, mode: "ai" },
  });
  expect(
    await screen.findByRole("region", { name: "Progress" }),
  ).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Regenerate all" })).toBeDisabled();
  expect(
    await screen.findByText("Regeneration complete.", {}, { timeout: 6000 }),
  ).toBeInTheDocument();
  expect(
    client.getQueryData<components["schemas"]["ItineraryOut"]>(
      queryKeys.itinerary(TRIP_ID, CURRENT_VERSION),
    )?.plan_revision,
  ).toBe(8);
  for (const key of [
    ["itinerary", TRIP_ID],
    ["costs", TRIP_ID],
    ["warnings", TRIP_ID],
    ["versions", TRIP_ID],
  ]) {
    expect(invalidate).toHaveBeenCalledWith({ queryKey: key });
  }
  expect(await screen.findByText(/rule-based plan/i)).toBeInTheDocument();
  client.clear();
});

it("IMP-607: day control posts its day and current revision", async () => {
  const { posts, user, client } = setup();
  screen.getByRole("button", { name: "Regenerate day 1" }).focus();
  await user.keyboard("{Enter}");
  await waitFor(() => expect(posts).toHaveLength(1));
  expect(posts[0]).toEqual({
    path: `/api/v1/trips/${TRIP_ID}/itinerary/days/1/regenerate`,
    body: { plan_revision: 7, mode: "ai" },
  });
  client.clear();
});

it("IMP-607 TC-372: hides both entry points when switched off", () => {
  flags.regeneration = false;
  const { client } = setup();
  expect(
    screen.queryByRole("button", { name: /Regenerate/ }),
  ).not.toBeInTheDocument();
  client.clear();
});
