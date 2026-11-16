import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import VersionsPage from "@/app/(app)/trips/[tripId]/versions/page";

vi.mock("@/lib/auth/supabase", () => ({
  getSupabase: () => ({
    auth: {
      getSession: async () => ({ data: { session: { access_token: "t" } } }),
    },
  }),
}));
vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test/api/v1");

const TRIP_ID = "00000000-0000-4000-8000-000000000002";
vi.mock("next/navigation", () => ({ useParams: () => ({ tripId: TRIP_ID }) }));

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
const notFound = () =>
  json(
    { error: { code: "NOT_FOUND", message: "Not found.", request_id: null } },
    404,
  );

function renderPage(versions: () => Response, trip: () => Response) {
  vi.stubGlobal("fetch", async (request: Request) => {
    const path = new URL(request.url).pathname;
    if (path.endsWith("/versions")) return versions();
    if (path.endsWith("/itinerary")) return notFound();
    return trip();
  });
  render(
    <QueryClientProvider client={new QueryClient()}>
      <VersionsPage />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

it("shows the not-found state when API-36 returns 404 for a foreign trip", async () => {
  renderPage(notFound, notFound);

  expect(await screen.findByText("Trip not found")).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: "Back to dashboard" }),
  ).toHaveAttribute("href", "/dashboard");
  expect(screen.queryByText("No itinerary yet")).not.toBeInTheDocument();
  expect(
    screen.queryByRole("link", { name: "Generate a plan" }),
  ).not.toBeInTheDocument();
});

it("keeps the no-itinerary state for the owner's empty versions list", async () => {
  renderPage(
    () => json([]),
    () => json({ id: TRIP_ID }),
  );

  expect(await screen.findByText("No itinerary yet")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Generate a plan" })).toHaveAttribute(
    "href",
    `/trips/${TRIP_ID}/generate`,
  );
  expect(screen.queryByText("Trip not found")).not.toBeInTheDocument();
});
