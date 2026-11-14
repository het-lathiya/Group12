import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  formatDuration,
  ItineraryItemCard,
} from "@/components/itinerary/ItineraryItemCard";

import { ITEM } from "./fixtures";

// FR-059, §7.8: the card shows API-24's values as sent, each fact with its label.
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

  it("shows the time range as sent, not worked out from the duration", () => {
    render(
      <ItineraryItemCard
        item={{ ...ITEM, start_time: "09:30", end_time: "23:59" }}
      />,
    );
    expect(screen.getByText("09:30–23:59")).toBeInTheDocument();
  });

  it("shows a cost range with its label, and one amount when both ends match", () => {
    const cost = { min: "10.00", max: "25.50", currency: "GBP" } as const;
    const { rerender } = render(
      <ItineraryItemCard
        item={{ ...ITEM, cost: { ...cost, label: "curated" } }}
      />,
    );
    expect(screen.getByText("GBP 10.00–25.50")).toBeInTheDocument();
    expect(screen.getAllByText("Curated")).toHaveLength(2);

    rerender(
      <ItineraryItemCard
        item={{ ...ITEM, cost: { ...cost, max: "10.00", label: "estimate" } }}
      />,
    );
    expect(screen.getByText("GBP 10.00")).toBeInTheDocument();
    expect(screen.getByText("Estimate")).toBeInTheDocument();
  });

  it("says Unavailable and shows no amount when there is no price", () => {
    const { container, rerender } = render(
      <ItineraryItemCard item={{ ...ITEM, cost: null }} />,
    );
    expect(screen.getByText("Unavailable")).toBeInTheDocument();

    rerender(
      <ItineraryItemCard
        item={{
          ...ITEM,
          cost: {
            min: "0.00",
            max: "0.00",
            currency: "INR",
            label: "unavailable",
          },
        }}
      />,
    );
    expect(screen.getByText("Unavailable")).toBeInTheDocument();
    expect(container).not.toHaveTextContent("0.00");
  });

  it("labels travel by its source and shows none for the first stop", () => {
    const leg = ITEM.travel_from_previous!;
    const { container, rerender } = render(<ItineraryItemCard item={ITEM} />);
    expect(screen.getByText("12 min")).toBeInTheDocument();
    expect(screen.getByText("Walking")).toBeInTheDocument();
    expect(
      screen.getByText("Estimated travel time (distance based)"),
    ).toBeInTheDocument();

    rerender(
      <ItineraryItemCard
        item={{
          ...ITEM,
          travel_from_previous: { ...leg, source: "routing_api" },
        }}
      />,
    );
    expect(
      screen.getByText("Estimated travel time from a routing service"),
    ).toBeInTheDocument();

    rerender(
      <ItineraryItemCard item={{ ...ITEM, travel_from_previous: null }} />,
    );
    expect(container).not.toHaveTextContent("Estimated travel time");
  });

  it("marks only an AI-written note", () => {
    const { container, rerender } = render(<ItineraryItemCard item={ITEM} />);
    expect(
      screen.getByText("Arrive early for the quiet gallery."),
    ).toBeInTheDocument();
    expect(screen.getByText("AI-written")).toBeInTheDocument();

    rerender(<ItineraryItemCard item={{ ...ITEM, note_origin: "user" }} />);
    expect(
      screen.getByText("Arrive early for the quiet gallery."),
    ).toBeInTheDocument();
    expect(container).not.toHaveTextContent("AI-written");
  });

  it("writes durations the way the guide does", () => {
    expect(formatDuration(45)).toBe("45 min");
    expect(formatDuration(60)).toBe("1 h");
    expect(formatDuration(90)).toBe("1 h 30 min");
    expect(formatDuration(125)).toBe("2 h 5 min");
  });
});
