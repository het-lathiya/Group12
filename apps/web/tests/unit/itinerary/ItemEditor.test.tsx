import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DayColumn } from "@/components/itinerary/DayColumn";
import { itemTimesSchema } from "@/components/itinerary/ItemEditor";
import { ItineraryItemCard } from "@/components/itinerary/ItineraryItemCard";
import { MoveDndContext } from "@/components/itinerary/MoveControls";
import { Toaster } from "@/components/ui/sonner";
import { CURRENT_VERSION, queryKeys, useItinerary } from "@/lib/api/queries";
import type { components } from "@/lib/api/schema";

import { ITEM, ITEM_B, planWith, TRIP_ID } from "./fixtures";

// FR-061, FR-063 web side (IMP-408): retime and remove go to API-26 and API-27, and the page shows
// the server's answer, never a value worked out in the browser.
vi.mock("@/lib/auth/supabase", () => ({
  getSupabase: () => ({
    auth: {
      getSession: async () => ({ data: { session: { access_token: "t" } } }),
    },
  }),
}));
vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test/api/v1");

type Itinerary = components["schemas"]["ItineraryOut"];

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

// What the fake server answers after the edit: totals no browser could compute from the card.
const SERVER_TOTALS = {
  currency: "INR",
  estimate: { min: "123.45", max: "678.90" },
  planning_total: "746.79",
  complete: false,
  incomplete_count: 1,
};

let requests: { method: string; url: URL; body: unknown }[];
let answer: (() => Response) | null;
let resolveEdit: (() => void) | null;
// Network time of the refetch after an edit; in a browser the card unmounts during it.
let getDelayMs: number;

function editResult(items: Itinerary["days"][number]["items"]) {
  const day = planWith([items], 8).days[0];
  return {
    plan_revision: 8,
    changed_days: [day],
    totals: SERVER_TOTALS,
    findings: [],
  };
}

function setup(item = ITEM) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const plan = planWith([[item, ITEM_B]], 7);
  client.setQueryData(queryKeys.itinerary(TRIP_ID, CURRENT_VERSION), plan);
  const user = userEvent.setup();
  render(
    <QueryClientProvider client={client}>
      <ol>
        {plan.days[0].items.map((i) => (
          <li key={i.id}>
            <ItineraryItemCard
              item={i}
              edit={{
                tripId: TRIP_ID,
                planRevision: 7,
                dayNumber: 1,
                itemCount: 2,
                dayNumbers: [1],
              }}
            />
          </li>
        ))}
      </ol>
      <Toaster />
    </QueryClientProvider>,
  );
  const cached = () =>
    client.getQueryData<Itinerary>(
      queryKeys.itinerary(TRIP_ID, CURRENT_VERSION),
    );
  return { user, cached };
}

beforeEach(() => {
  requests = [];
  answer = null;
  resolveEdit = null;
  getDelayMs = 0;
  vi.stubGlobal("fetch", async (request: Request) => {
    const url = new URL(request.url);
    const body = request.method === "PATCH" ? await request.json() : undefined;
    requests.push({ method: request.method, url, body });
    if (request.method === "GET") {
      await new Promise((resolve) => setTimeout(resolve, getDelayMs));
      return json(planWith([[ITEM_B]], 8));
    }
    if (answer) return answer();
    if (request.method === "DELETE") {
      await new Promise<void>((resolve) => (resolveEdit = resolve));
      return json(editResult([{ ...ITEM_B, position: 1 }]));
    }
    return json(editResult([{ ...ITEM, duration_min: 120 }, ITEM_B]));
  });
});

afterEach(() => vi.unstubAllGlobals());

const edits = () => requests.filter(({ method }) => method !== "GET");

describe("ItemEditor", () => {
  it("opens labelled start time and duration fields inside the card", async () => {
    const { user } = setup();
    await user.click(
      screen.getByRole("button", {
        name: "Edit time of Old Mill Museum (sample)",
      }),
    );

    const form = screen.getByRole("form", {
      name: "Edit time of Old Mill Museum (sample)",
    });
    expect(within(form).getByLabelText("Start time")).toHaveValue("09:30");
    expect(within(form).getByLabelText("Duration (minutes)")).toHaveValue("90");
    expect(
      within(form).getByRole("button", { name: "Save" }),
    ).toBeInTheDocument();
    expect(
      within(form).getByRole("button", { name: "Cancel" }),
    ).toBeInTheDocument();
  });

  it("refuses a duration outside 15 to 480 under the field and sends nothing (FR-063 AC2)", async () => {
    const { user } = setup();
    await user.click(
      screen.getByRole("button", { name: /Edit time of Old Mill/ }),
    );
    const duration = screen.getByLabelText("Duration (minutes)");
    await user.clear(duration);
    await user.type(duration, "481");
    await user.click(screen.getByRole("button", { name: "Save" }));

    const message = await screen.findByText(
      "Enter whole minutes from 15 to 480.",
    );
    expect(duration).toHaveAttribute("aria-invalid", "true");
    expect(duration.getAttribute("aria-describedby")).toContain(message.id);
    expect(edits()).toEqual([]);
  });

  it("mirrors the server's rules", () => {
    const ok = { start_time: "09:30", duration_min: "15" };
    expect(itemTimesSchema.safeParse(ok).success).toBe(true);
    expect(
      itemTimesSchema.safeParse({ ...ok, duration_min: "480" }).success,
    ).toBe(true);
    expect(
      itemTimesSchema.safeParse({ ...ok, duration_min: "14" }).success,
    ).toBe(false);
    expect(
      itemTimesSchema.safeParse({ ...ok, duration_min: "60.5" }).success,
    ).toBe(false);
    expect(
      itemTimesSchema.safeParse({ ...ok, start_time: "24:00" }).success,
    ).toBe(false);
    expect(
      itemTimesSchema.safeParse({ ...ok, start_time: "9:30" }).success,
    ).toBe(false);
  });

  it("saves a retime through API-26 and shows the server's totals, then returns focus to the card", async () => {
    const { user, cached } = setup();
    await user.click(
      screen.getByRole("button", { name: /Edit time of Old Mill/ }),
    );
    const duration = screen.getByLabelText("Duration (minutes)");
    await user.clear(duration);
    await user.type(duration, "120");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(edits()).toHaveLength(1));
    const [patch] = edits();
    expect(patch.method).toBe("PATCH");
    expect(patch.url.pathname).toBe(`/api/v1/itinerary/items/${ITEM.id}`);
    expect(patch.body).toEqual({ plan_revision: 7, duration_min: 120 }); // only what changed
    await waitFor(() =>
      expect(document.activeElement).toHaveAttribute("id", `item-${ITEM.id}`),
    );
    // The page's totals are the response's, as sent (IMP-408 acceptance).
    await waitFor(() => expect(cached()?.plan_revision).toBe(8));
    expect(cached()?.totals).toEqual(SERVER_TOTALS);
    expect(screen.queryByRole("form")).not.toBeInTheDocument();
  });

  it("shows a server refusal through the error catalogue and keeps the editor open", async () => {
    const { user } = setup();
    answer = () =>
      json(
        {
          error: {
            code: "STALE_PLAN",
            message: "This plan changed since you opened it.",
            request_id: "r-1",
          },
        },
        409,
      );
    await user.click(
      screen.getByRole("button", { name: /Edit time of Old Mill/ }),
    );
    await user.clear(screen.getByLabelText("Start time"));
    await user.type(screen.getByLabelText("Start time"), "10:00");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "This plan changed somewhere else. Reload to see the latest version",
    );
    expect(screen.getByRole("form")).toBeInTheDocument();
  });

  it("cancels without a request and returns focus to the card", async () => {
    const { user } = setup();
    await user.click(
      screen.getByRole("button", { name: /Edit time of Old Mill/ }),
    );
    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(screen.queryByRole("form")).not.toBeInTheDocument();
    await waitFor(() =>
      expect(document.activeElement).toHaveAttribute("id", `item-${ITEM.id}`),
    );
    expect(edits()).toEqual([]);
  });

  it("removes only after confirmation, keeps the item until the server answers, then says so (FR-061)", async () => {
    const { user, cached } = setup();
    await user.click(
      screen.getByRole("button", { name: "Remove Old Mill Museum (sample)" }),
    );
    const dialog = screen.getByRole("dialog", {
      name: "Remove Old Mill Museum (sample) from day 1?",
    });
    expect(edits()).toEqual([]);
    await user.click(within(dialog).getByRole("button", { name: "Remove" }));

    await waitFor(() => expect(edits()).toHaveLength(1));
    const [removal] = edits();
    expect(removal.method).toBe("DELETE");
    expect(removal.url.pathname).toBe(`/api/v1/itinerary/items/${ITEM.id}`);
    expect(removal.url.searchParams.get("plan_revision")).toBe("7");
    // Still shown, marked as saving, while the server works.
    expect(
      screen.getByRole("heading", { name: "Old Mill Museum (sample)" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Removing…")).toBeInTheDocument();

    resolveEdit?.();
    expect(
      await screen.findByText("Removed Old Mill Museum (sample)"),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Undo" }),
    ).not.toBeInTheDocument(); // PD-IMP-408-1
    await waitFor(() => expect(cached()?.totals).toEqual(SERVER_TOTALS));
  });

  it("sends nothing when the removal is cancelled", async () => {
    const { user } = setup();
    await user.click(screen.getByRole("button", { name: /Remove Old Mill/ }));
    await user.click(
      within(screen.getByRole("dialog")).getByRole("button", {
        name: "Cancel",
      }),
    );

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(edits()).toEqual([]);
  });

  // RUN-063b: the day is drawn from the itinerary query, as on the page, so the removed card and
  // its ItemEditor unmount as soon as the server's day is written. The toast and focus must still
  // follow.
  it("after a removal unmounts the card, says so and moves focus to the next card (FR-061)", async () => {
    getDelayMs = 100;
    toast.dismiss(); // sonner keeps toasts of earlier tests in its store
    // No refetch on mount: the fake GET already answers with the plan after the removal.
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false, staleTime: Infinity } },
    });
    client.setQueryData(
      queryKeys.itinerary(TRIP_ID, CURRENT_VERSION),
      planWith([[ITEM, ITEM_B]], 7),
    );
    function Day() {
      const { data } = useItinerary(TRIP_ID);
      if (!data) return null;
      return (
        <MoveDndContext tripId={TRIP_ID} planRevision={data.plan_revision}>
          <DayColumn
            day={data.days[0]}
            edit={{
              tripId: TRIP_ID,
              planRevision: data.plan_revision,
              dayNumbers: [1],
            }}
          />
        </MoveDndContext>
      );
    }
    const user = userEvent.setup();
    render(
      <QueryClientProvider client={client}>
        <Day />
        <Toaster />
      </QueryClientProvider>,
    );

    await user.click(
      screen.getByRole("button", { name: "Remove Old Mill Museum (sample)" }),
    );
    await user.click(
      within(await screen.findByRole("dialog")).getByRole("button", {
        name: "Remove",
      }),
    );
    await waitFor(() => expect(resolveEdit).not.toBeNull());
    resolveEdit?.();

    await waitFor(() =>
      expect(
        screen.queryByRole("heading", { name: "Old Mill Museum (sample)" }),
      ).not.toBeInTheDocument(),
    );
    expect(
      await screen.findByText("Removed Old Mill Museum (sample)"),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Undo" }),
    ).not.toBeInTheDocument(); // IMD-157
    await waitFor(() =>
      expect(document.getElementById(`item-${ITEM_B.id}`)).toHaveFocus(),
    );
  });
});
