import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TripActionsMenu } from "@/components/trips/TripActionsMenu";
import type { components } from "@/lib/api/schema";

// FR-015 (TC-089 to TC-091) web side: the menu calls API-11, API-12 and API-13; IMD-11 hides it.
vi.mock("@/lib/auth/supabase", () => ({
  getSupabase: () => ({
    auth: {
      getSession: async () => ({ data: { session: { access_token: "t" } } }),
    },
  }),
}));
const flags = { enabled: true };
vi.mock("@/lib/flags", () => ({ isEnabled: () => flags.enabled }));
const toast = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn() }));
vi.mock("sonner", () => ({ toast }));
vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test/api/v1");

const TRIP: components["schemas"]["TripOut"] = {
  id: "00000000-0000-4000-8000-000000000002",
  title: "Weekend in Sampleton",
  destination_id: "00000000-0000-4000-8000-000000000001",
  start_date: "2026-12-04",
  end_date: "2026-12-06",
  num_days: 3,
  adults: 2,
  children: 0,
  group_needs: [],
  budget: null,
  status: "ready",
  plan_revision: 1,
  plan_stale: false,
  has_itinerary: true,
  destination: {
    id: "00000000-0000-4000-8000-000000000001",
    name: "Sampleton",
    timezone: "Europe/London",
    currency: "GBP",
    is_sample: true,
  },
  created_at: "2026-11-03T10:00:00Z",
  updated_at: "2026-11-03T10:00:00Z",
};

type Call = { method: string; path: string; body: unknown };
let calls: Call[];
let reply: (call: Call) => Response;

const json = (body: unknown, status = 200) =>
  new Response(status === 204 ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

beforeEach(() => {
  flags.enabled = true;
  toast.success.mockReset();
  toast.error.mockReset();
  calls = [];
  reply = ({ method, body }) => {
    if (method === "DELETE") return json(null, 204);
    if (method === "POST")
      return json({ ...TRIP, id: "copy", title: `${TRIP.title} (copy)` }, 201);
    return json({ ...TRIP, ...(body as object) });
  };
  vi.stubGlobal("fetch", async (request: Request) => {
    const text = await request.text();
    const call = {
      method: request.method,
      path: new URL(request.url).pathname,
      body: text ? JSON.parse(text) : null,
    };
    calls.push(call);
    return reply(call);
  });
});

function renderMenu(trip = TRIP) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <TripActionsMenu trip={trip} />
    </QueryClientProvider>,
  );
  return userEvent.setup();
}

async function choose(user: ReturnType<typeof userEvent.setup>, name: string) {
  await user.click(
    screen.getByRole("button", { name: `Actions for ${TRIP.title}` }),
  );
  await user.click(await screen.findByRole("menuitem", { name }));
}

const PATH = `/api/v1/trips/${TRIP.id}`;

describe("TripActionsMenu (FR-015)", () => {
  it("renames with API-11 and validates the name length first", async () => {
    const user = renderMenu();
    await choose(user, "Rename");
    const field = await screen.findByLabelText("Trip name (required)");
    await user.clear(field);
    await user.click(screen.getByRole("button", { name: "Save name" }));
    expect(
      screen.getByText("Enter a trip name of 1 to 120 characters."),
    ).toBeInTheDocument();
    expect(calls).toEqual([]);

    await user.type(field, "  Long weekend  ");
    await user.click(screen.getByRole("button", { name: "Save name" }));

    await waitFor(() =>
      expect(toast.success).toHaveBeenCalledWith("Trip renamed"),
    );
    expect(calls).toEqual([
      { method: "PATCH", path: PATH, body: { title: "Long weekend" } },
    ]);
  });

  it("shows the API's field message when the rename is refused", async () => {
    reply = () =>
      json(
        {
          error: {
            code: "CONFLICT",
            message: "This trip is archived. Restore it before changing it.",
            request_id: "r",
            details: [],
            retry_after_s: null,
          },
        },
        409,
      );
    const user = renderMenu();
    await choose(user, "Rename");
    await user.click(await screen.findByRole("button", { name: "Save name" }));

    expect(
      await screen.findByText(
        "This trip is archived. Restore it before changing it.",
      ),
    ).toBeInTheDocument();
  });

  it("TC-089: duplicates with API-13 and names the copy", async () => {
    const user = renderMenu();
    await choose(user, "Duplicate");

    await waitFor(() =>
      expect(toast.success).toHaveBeenCalledWith(
        "Copied as Weekend in Sampleton (copy)",
      ),
    );
    expect(calls).toEqual([
      { method: "POST", path: `${PATH}/duplicate`, body: null },
    ]);
  });

  it("TC-091: archives only after confirmation", async () => {
    const user = renderMenu();
    await choose(user, "Archive");
    const dialog = await screen.findByRole("dialog", {
      name: `Archive ${TRIP.title}?`,
    });
    expect(dialog).toHaveTextContent("read-only until you restore it");
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(calls).toEqual([]);

    await choose(user, "Archive");
    await user.click(
      await screen.findByRole("button", { name: "Archive trip" }),
    );

    await waitFor(() =>
      expect(calls).toEqual([
        { method: "PATCH", path: PATH, body: { status: "archived" } },
      ]),
    );
  });

  it("restores an archived trip and offers no rename", async () => {
    const user = renderMenu({ ...TRIP, status: "archived" });
    await user.click(
      screen.getByRole("button", { name: `Actions for ${TRIP.title}` }),
    );
    expect(screen.queryByRole("menuitem", { name: "Rename" })).toBeNull();
    await user.click(await screen.findByRole("menuitem", { name: "Restore" }));

    await waitFor(() =>
      expect(toast.success).toHaveBeenCalledWith("Trip restored"),
    );
    expect(calls).toEqual([
      { method: "PATCH", path: PATH, body: { status: "ready" } },
    ]);
  });

  it("TC-090: deletes with API-12 after a destructive confirmation", async () => {
    const user = renderMenu();
    await choose(user, "Delete");
    const dialog = await screen.findByRole("dialog", {
      name: `Delete ${TRIP.title}?`,
    });
    expect(dialog).toHaveTextContent("kept for 30 days");
    await user.click(screen.getByRole("button", { name: "Delete trip" }));

    await waitFor(() =>
      expect(toast.success).toHaveBeenCalledWith("Trip deleted"),
    );
    expect(calls).toEqual([{ method: "DELETE", path: PATH, body: null }]);
  });

  it("TC-372: renders nothing when trip_management is switched off", () => {
    flags.enabled = false;
    renderMenu();
    expect(screen.queryByRole("button")).toBeNull();
  });
});
