import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DayColumn } from "@/components/itinerary/DayColumn";
import { MoveDndContext } from "@/components/itinerary/MoveControls";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CURRENT_VERSION, queryKeys, useItinerary } from "@/lib/api/queries";
import type { components } from "@/lib/api/schema";
import { formatDayDate } from "@/lib/format";

import { ITEM, ITEM_B, planWith, TRIP_ID } from "./fixtures";

// FR-059 (TC-196): a day shows its number, its date, its theme and its items in the order API-24
// sent them, each estimated cost with its label.
type Day = components["schemas"]["Day"];

const DAY: Day = {
  day_number: 1,
  date: "2026-11-14",
  theme: "Museums and the old town",
  theme_origin: "ai",
  day_cost: { min: "0.00", max: "0.00", currency: "INR", complete: false },
  items: [
    ITEM,
    {
      ...ITEM,
      id: "00000000-0000-4000-8000-0000000000c2",
      position: 2,
      place: { ...ITEM.place, name: "River Cafe (sample)", category: "food" },
      slot_type: "meal",
      start_time: "11:15",
      duration_min: 60,
    },
  ],
};

describe("DayColumn", () => {
  it("shows the day number and date as the heading and the items in order", () => {
    render(<DayColumn day={DAY} />);

    expect(
      screen.getByRole("heading", { level: 2, name: "Day 1, Sat 14 Nov" }),
    ).toBeInTheDocument();
    const items = within(screen.getByRole("list")).getAllByRole("listitem");
    expect(items.map((item) => item.textContent)).toEqual([
      expect.stringContaining("09:30Old Mill Museum (sample)"),
      expect.stringContaining("11:15River Cafe (sample)"),
    ]);
    expect(items[1]).toHaveTextContent("1 h");
    expect(items[1]).toHaveTextContent("Meal");
  });

  it("TC-196: keeps the server's time order and labels estimated costs", () => {
    render(<DayColumn day={DAY} />);

    const items = within(screen.getByRole("list")).getAllByRole("listitem");
    expect(
      items.map(
        (item) => within(item).getAllByText(/^\d\d:\d\d$/)[0].textContent,
      ),
    ).toEqual(["09:30", "11:15"]);
    for (const item of items) {
      expect(within(item).getByText("Estimate")).toBeInTheDocument();
    }
  });

  it("marks an AI-written theme and leaves a rule-based one unmarked", () => {
    const { rerender, container } = render(<DayColumn day={DAY} />);
    const theme = screen.getByText("Museums and the old town");
    expect(theme.parentElement).toHaveTextContent("AI-written");

    rerender(
      <DayColumn
        day={{
          ...DAY,
          theme: "Day 1 around the mill",
          theme_origin: "none",
          items: [],
        }}
      />,
    );
    expect(screen.getByText("Day 1 around the mill")).toBeInTheDocument();
    expect(container).not.toHaveTextContent("AI-written");
  });

  it("does not show the day cost", () => {
    const { container } = render(<DayColumn day={{ ...DAY, items: [] }} />);
    expect(container).not.toHaveTextContent("INR");
  });

  it("takes focus from the day index only when it has an id", () => {
    const { rerender } = render(<DayColumn day={DAY} />);
    expect(screen.getByRole("region", { name: "Day 1" })).not.toHaveAttribute(
      "tabindex",
    );

    rerender(<DayColumn day={DAY} id="day-1" />);
    const region = screen.getByRole("region", { name: "Day 1" });
    expect(region).toHaveAttribute("id", "day-1");
    expect(region).toHaveAttribute("tabindex", "-1");
  });

  it("says when a day has nothing planned", () => {
    render(<DayColumn day={{ ...DAY, items: [] }} />);
    expect(
      screen.getByText("Nothing planned for this day."),
    ).toBeInTheDocument();
  });

  it("reads the date-only string without a time-zone shift", () => {
    expect(formatDayDate("2026-11-14")).toBe("Sat 14 Nov");
    expect(formatDayDate("2027-01-01")).toBe("Fri 1 Jan");
  });
});

// IMP-513 (FR-115, TC-280): focus and announcements after an edit, through the real hooks, the
// edit context and DayColumn as the itinerary page renders them (as in the RUN-063b case of
// ItemEditor.test.tsx). The fake server answers each edit after the page re-reads API-24.
vi.mock("@/lib/auth/supabase", () => ({
  getSupabase: () => ({
    auth: {
      getSession: async () => ({ data: { session: { access_token: "t" } } }),
    },
  }),
}));
vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test/api/v1");

type Itinerary = components["schemas"]["ItineraryOut"];
type Item = components["schemas"]["Item"];

describe("DayColumn focus and announcements (IMP-513)", () => {
  let after: Itinerary; // the plan the server holds after the edit
  let changed: number[]; // the day numbers the edit answer carries

  beforeEach(() => {
    vi.stubGlobal("fetch", async (request: Request) => {
      if (request.method === "GET") {
        // Network time of the re-read: in a browser the edited card unmounts meanwhile.
        await new Promise((resolve) => setTimeout(resolve, 50));
        return Response.json(after);
      }
      return Response.json({
        plan_revision: after.plan_revision,
        changed_days: after.days.filter((d) => changed.includes(d.day_number)),
        totals: after.totals,
        findings: [],
      });
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  /** The itinerary page's day list: every day, or below 768 px (`tabs`) one day tab at a time. */
  function renderPlan(before: Itinerary, tabs = false) {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false, staleTime: Infinity } },
    });
    client.setQueryData(queryKeys.itinerary(TRIP_ID, CURRENT_VERSION), before);
    function Plan() {
      const { data } = useItinerary(TRIP_ID);
      const [tab, setTab] = useState("day-1");
      if (!data) return null;
      const edit = {
        tripId: TRIP_ID,
        planRevision: data.plan_revision,
        dayNumbers: data.days.map((d) => d.day_number),
      };
      const columns = data.days.map((day) => (
        <DayColumn key={day.day_number} day={day} edit={edit} />
      ));
      return (
        <MoveDndContext tripId={TRIP_ID} planRevision={data.plan_revision}>
          {tabs ? (
            <Tabs value={tab} onValueChange={setTab}>
              <TabsList aria-label="Days">
                {data.days.map((day) => (
                  <TabsTrigger
                    key={day.day_number}
                    value={`day-${day.day_number}`}
                  >
                    Day {day.day_number}
                  </TabsTrigger>
                ))}
              </TabsList>
              {data.days.map((day, index) => (
                <TabsContent
                  key={day.day_number}
                  value={`day-${day.day_number}`}
                >
                  {columns[index]}
                </TabsContent>
              ))}
            </Tabs>
          ) : (
            columns
          )}
        </MoveDndContext>
      );
    }
    render(
      <QueryClientProvider client={client}>
        <Plan />
      </QueryClientProvider>,
    );
    return userEvent.setup();
  }

  async function removeByKeyboard(
    user: ReturnType<typeof userEvent.setup>,
    name: string,
  ) {
    screen.getByRole("button", { name: `Remove ${name}` }).focus();
    await user.keyboard("{Enter}");
    within(await screen.findByRole("dialog"))
      .getByRole("button", { name: "Remove" })
      .focus();
    await user.keyboard("{Enter}");
    await waitFor(() =>
      expect(
        screen.queryByRole("heading", { level: 3, name }),
      ).not.toBeInTheDocument(),
    );
  }

  it("after removing the last item, moves focus to the previous card (FR-061, FR-115)", async () => {
    after = planWith([[ITEM]], 8);
    changed = [1];
    const user = renderPlan(planWith([[ITEM, ITEM_B]], 7));

    await removeByKeyboard(user, ITEM_B.place.name);

    await waitFor(() =>
      expect(document.getElementById(`item-${ITEM.id}`)).toHaveFocus(),
    );
  });

  it("after removing the only item, moves focus to the day heading (FR-061, FR-115)", async () => {
    after = planWith([[]], 8);
    changed = [1];
    const user = renderPlan(planWith([[ITEM]], 7));

    await removeByKeyboard(user, ITEM.place.name);

    await waitFor(() =>
      expect(
        screen.getByRole("heading", { level: 2, name: "Day 1, Sat 14 Nov" }),
      ).toHaveFocus(),
    );
    expect(
      screen.getByText("Nothing planned for this day."),
    ).toBeInTheDocument();
  });

  const movedToDay2 = (item: Item) => {
    after = planWith([[ITEM_B], [{ ...item, position: 1 }]], 8);
    changed = [1, 2];
  };

  it("TC-280: announces a move to another day and keeps focus on the item's controls", async () => {
    movedToDay2(ITEM);
    const user = renderPlan(planWith([[ITEM, ITEM_B], []], 7));

    screen
      .getByRole("button", { name: `Move ${ITEM.place.name} to day 2` })
      .focus();
    await user.keyboard("{Enter}");

    expect(
      await screen.findByText(`Moved ${ITEM.place.name} to day 2 position 1`),
    ).toHaveAttribute("aria-live", "polite");
    const day2 = screen.getByRole("region", { name: "Day 2" });
    await waitFor(() =>
      expect(
        within(day2).getByRole("button", {
          name: `Move ${ITEM.place.name} to day 1`,
        }),
      ).toHaveFocus(),
    );
  });

  it("below 768 px, a move to another day announces it and focuses that day's tab, which opens it", async () => {
    movedToDay2(ITEM);
    const user = renderPlan(planWith([[ITEM, ITEM_B], []], 7), true);

    screen
      .getByRole("button", { name: `Move ${ITEM.place.name} to day 2` })
      .focus();
    await user.keyboard("{Enter}");

    expect(
      await screen.findByText(`Moved ${ITEM.place.name} to day 2 position 1`),
    ).toBeInTheDocument();
    const tab = screen.getByRole("tab", { name: "Day 2" });
    await waitFor(() => expect(tab).toHaveFocus());
    expect(tab).toHaveAttribute("aria-selected", "true");
    expect(
      screen.getByRole("heading", { level: 3, name: ITEM.place.name }),
    ).toBeInTheDocument();
  });
});
