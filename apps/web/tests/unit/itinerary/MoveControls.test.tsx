import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ItineraryPage from "@/app/(app)/trips/[tripId]/itinerary/page";
import { dropMove } from "@/components/itinerary/MoveControls";
import { Toaster } from "@/components/ui/sonner";
import type { components } from "@/lib/api/schema";

import { ITEM, ITEM_B, planWith, TRIP_ID } from "./fixtures";

// FR-060 web side (IMP-409): drag and the keyboard move controls both call API-26; the page shows
// the server's order and findings, with no reordering before the answer.
vi.mock("@/lib/auth/supabase", () => ({
  getSupabase: () => ({
    auth: {
      getSession: async () => ({ data: { session: { access_token: "t" } } }),
    },
  }),
}));
vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test/api/v1");
vi.mock("next/navigation", () => ({ useParams: () => ({ tripId: TRIP_ID }) }));

type Itinerary = components["schemas"]["ItineraryOut"];
type Item = Itinerary["days"][number]["items"][number];

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

const ITEM_C: Item = {
  ...ITEM_B,
  id: "00000000-0000-4000-8000-0000000000c3",
  position: 1,
  place: {
    ...ITEM_B.place,
    id: "00000000-0000-4000-8000-000000000005",
    name: "Hill Fort (sample)",
  },
};

const OVERLAP = {
  id: "00000000-0000-4000-8000-0000000000f1",
  code: "OVERLAP",
  severity: "error",
  day_number: 1,
  item_id: ITEM.id,
  place_id: null,
  message: "Old Mill Museum (sample) starts before River Walk (sample) ends.",
  suggested_fix: "Move one of them.",
} as const;

let current: Itinerary;
let patches: { itemId: string; body: Record<string, unknown> }[];
let release: (() => void) | null;
let hold: boolean;

/** The fake API-26: applies the move as the server would and answers with the changed days. */
async function serverMove(itemId: string, body: Record<string, unknown>) {
  const days = current.days.map((d) => [...d.items]);
  const from = days.findIndex((items) => items.some((i) => i.id === itemId));
  const item = days[from].find((i) => i.id === itemId)!;
  days[from] = days[from].filter((i) => i.id !== itemId);
  const to = (body.day_number as number | undefined) ?? from + 1;
  const target = days[to - 1];
  const position = (body.position as number | undefined) ?? target.length + 1;
  target.splice(position - 1, 0, item);
  const next = planWith(
    days.map((items) => items.map((i, n) => ({ ...i, position: n + 1 }))),
    current.plan_revision + 1,
  );
  next.findings = [OVERLAP]; // a conflict the move created (FR-060 AC3)
  current = next;
  return {
    plan_revision: next.plan_revision,
    changed_days: next.days.filter(
      (d) => d.day_number === from + 1 || d.day_number === to,
    ),
    totals: next.totals,
    findings: next.findings,
  };
}

function renderPage() {
  vi.stubGlobal("matchMedia", () => ({
    matches: true,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
  }));
  vi.stubGlobal("fetch", async (request: Request) => {
    const path = new URL(request.url).pathname;
    if (request.method === "PATCH") {
      const itemId = path.split("/").pop()!;
      const body = (await request.json()) as Record<string, unknown>;
      patches.push({ itemId, body });
      if (hold) await new Promise<void>((resolve) => (release = resolve));
      return json(await serverMove(itemId, body));
    }
    if (path.endsWith("/itinerary")) return json(current);
    return json({ must_visit_places: [] }); // API-15, for the warnings' place names
  });
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <ItineraryPage />
      <Toaster />
    </QueryClientProvider>,
  );
  return userEvent.setup();
}

const dayItems = (dayNumber: number) =>
  within(screen.getByRole("region", { name: `Day ${dayNumber}` }))
    .getAllByRole("heading", { level: 3 })
    .map((h) => h.textContent);

beforeEach(() => {
  current = planWith([[ITEM, ITEM_B], [ITEM_C]], 3);
  patches = [];
  release = null;
  hold = false;
});

afterEach(() => vi.unstubAllGlobals());

describe("MoveControls", () => {
  it("names the place on every control and disables the edges", async () => {
    renderPage();
    const first = await screen.findByRole("group", {
      name: "Move Old Mill Museum (sample)",
    });
    expect(
      within(first).getByRole("button", {
        name: "Drag Old Mill Museum (sample) to reorder",
      }),
    ).toBeInTheDocument();
    expect(
      within(first).getByRole("button", {
        name: "Move Old Mill Museum (sample) up",
      }),
    ).toBeDisabled();
    expect(
      within(first).getByRole("button", {
        name: "Move Old Mill Museum (sample) down",
      }),
    ).toBeEnabled();
    expect(
      within(first).getByRole("button", {
        name: "Move Old Mill Museum (sample) to day 2",
      }),
    ).toBeEnabled();
    const last = screen.getByRole("group", {
      name: "Move River Walk (sample)",
    });
    expect(
      within(last).getByRole("button", {
        name: "Move River Walk (sample) down",
      }),
    ).toBeDisabled();
  });

  it("moves down with the keyboard only, announces it and keeps focus on the controls (TC-198)", async () => {
    const user = renderPage();
    await screen.findByRole("group", { name: "Move Old Mill Museum (sample)" });
    const down = screen.getByRole("button", {
      name: "Move Old Mill Museum (sample) down",
    });
    down.focus();
    await user.keyboard("{Enter}");

    await waitFor(() => expect(patches).toHaveLength(1));
    expect(patches[0]).toEqual({
      itemId: ITEM.id,
      body: { plan_revision: 3, day_number: 1, position: 2 },
    });
    expect(
      await screen.findByText(
        "Moved Old Mill Museum (sample) to day 1 position 2",
      ),
    ).toHaveAttribute("aria-live", "polite");
    await waitFor(() =>
      expect(dayItems(1)).toEqual([
        "River Walk (sample)",
        "Old Mill Museum (sample)",
      ]),
    );
    // Down is now at the edge, so focus moves to another control of the same item.
    await waitFor(() =>
      expect(
        screen.getByRole("group", { name: "Move Old Mill Museum (sample)" }),
      ).toContainElement(document.activeElement as HTMLElement),
    );
  });

  it("moves to another day with the select, sending the next revision on the following move", async () => {
    const user = renderPage();
    await screen.findByRole("group", { name: "Move River Walk (sample)" });
    await user.click(
      screen.getByRole("button", { name: "Move River Walk (sample) to day 2" }),
    );

    await waitFor(() =>
      expect(dayItems(2)).toEqual([
        "Hill Fort (sample)",
        "River Walk (sample)",
      ]),
    );
    expect(patches[0].body).toEqual({ plan_revision: 3, day_number: 2 });
    expect(
      await screen.findByText("Moved River Walk (sample) to day 2 position 2"),
    ).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: "Move River Walk (sample) up" }),
    );
    await waitFor(() => expect(patches).toHaveLength(2));
    expect(patches[1].body).toEqual({
      plan_revision: 4,
      day_number: 2,
      position: 1,
    });
  });

  it("does not reorder before the server answers, then shows the conflict in WarningsPanel (FR-060 AC3)", async () => {
    hold = true;
    const user = renderPage();
    await screen.findByRole("group", { name: "Move Old Mill Museum (sample)" });
    await user.click(
      screen.getByRole("button", {
        name: "Move Old Mill Museum (sample) down",
      }),
    );

    await waitFor(() => expect(patches).toHaveLength(1));
    expect(dayItems(1)).toEqual([
      "Old Mill Museum (sample)",
      "River Walk (sample)",
    ]);
    expect(
      screen.getByRole("button", { name: "Move River Walk (sample) up" }),
    ).toBeDisabled(); // one edit at a time

    release?.();
    expect(await screen.findByText(OVERLAP.message)).toBeInTheDocument();
    expect(dayItems(1)).toEqual([
      "River Walk (sample)",
      "Old Mill Museum (sample)",
    ]); // kept, not reverted
  });

  it("shows a refused move through the error catalogue and leaves the order as it was", async () => {
    const user = renderPage();
    await screen.findByRole("group", { name: "Move Old Mill Museum (sample)" });
    vi.stubGlobal("fetch", async (request: Request) =>
      request.method === "PATCH"
        ? json(
            {
              error: {
                code: "STALE_PLAN",
                message: "Changed.",
                request_id: "r-2",
              },
            },
            409,
          )
        : json(
            new URL(request.url).pathname.endsWith("/itinerary")
              ? current
              : { must_visit_places: [] },
          ),
    );
    await user.click(
      screen.getByRole("button", {
        name: "Move Old Mill Museum (sample) down",
      }),
    );

    expect(
      await screen.findByText("This plan changed somewhere else"),
    ).toBeInTheDocument();
    expect(dayItems(1)).toEqual([
      "Old Mill Museum (sample)",
      "River Walk (sample)",
    ]);
  });
});

// TC-197: what a drop sends (dnd-kit's pointer geometry does not run in jsdom).
describe("dropMove", () => {
  const from = { item: ITEM, dayNumber: 1, position: 1 };

  it("takes the slot of the item it is dropped on, in the same day or another", () => {
    expect(dropMove(from, { item: ITEM_B, dayNumber: 1, position: 2 })).toEqual(
      { day_number: 1, position: 2 },
    );
    expect(dropMove(from, { item: ITEM_C, dayNumber: 2, position: 1 })).toEqual(
      { day_number: 2, position: 1 },
    );
  });

  it("goes to the end of another day dropped on the day itself", () => {
    expect(dropMove(from, { dayNumber: 2 })).toEqual({ day_number: 2 });
  });

  it("sends nothing for a drop where it started", () => {
    expect(
      dropMove(from, { item: ITEM, dayNumber: 1, position: 1 }),
    ).toBeNull();
    expect(dropMove(from, { dayNumber: 1 })).toBeNull();
  });
});
