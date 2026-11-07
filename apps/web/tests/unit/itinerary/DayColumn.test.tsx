import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DayColumn } from "@/components/itinerary/DayColumn";
import type { components } from "@/lib/api/schema";
import { formatDayDate } from "@/lib/format";

import { ITEM } from "./fixtures";

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
      screen.getByRole("heading", { level: 2, name: "Day 1 Sat 14 Nov" }),
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
