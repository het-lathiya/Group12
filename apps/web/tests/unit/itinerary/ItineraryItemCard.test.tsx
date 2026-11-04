import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  formatDuration,
  ItineraryItemCard,
} from "@/components/itinerary/ItineraryItemCard";

import { ITEM } from "./fixtures";

// IMP-213 (FR-059 view part, §7 rule): the card shows only start time, place name, duration and slot
// type from API-24. Cost, end time, travel and the note are in the fixture and must not appear.
describe("ItineraryItemCard", () => {
  it("shows the start time, place name, duration and slot type as sent", () => {
    render(<ItineraryItemCard item={ITEM} />);

    expect(screen.getByText("09:30")).toHaveAttribute("datetime", "09:30");
    expect(
      screen.getByRole("heading", {
        level: 3,
        name: "Old Mill Museum (sample)",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("1 h 30 min")).toBeInTheDocument();
    expect(screen.getByText("Activity")).toBeInTheDocument();
  });

  it("never shows a cost, end time, travel time or note", () => {
    const { container } = render(<ItineraryItemCard item={ITEM} />);
    const text = container.textContent ?? "";

    for (const absent of [
      "0.00",
      "INR",
      "11:00",
      "12",
      "900",
      "Arrive early",
    ]) {
      expect(text).not.toContain(absent);
    }
    expect(text).not.toMatch(/cost|price|total|travel/i);
  });

  it("writes durations the way the guide does", () => {
    expect(formatDuration(45)).toBe("45 min");
    expect(formatDuration(60)).toBe("1 h");
    expect(formatDuration(90)).toBe("1 h 30 min");
    expect(formatDuration(125)).toBe("2 h 5 min");
  });
});
