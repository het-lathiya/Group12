import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DayColumn } from "@/components/itinerary/DayColumn";
import { ItineraryItemCard } from "@/components/itinerary/ItineraryItemCard";
import { AiBadge } from "@/components/labels/AiBadge";
import type { components } from "@/lib/api/schema";

import { ITEM } from "../itinerary/fixtures";

// FR-035 (IMP-406): AI-written text carries the AiBadge; retrieved facts keep their SourceBadge.
type Day = components["schemas"]["Day"];

const NOTE = "Arrive early for the quiet gallery.";

function noteLine(): HTMLElement {
  const line = screen.getByText(NOTE).parentElement;
  if (!line) throw new Error("the note has no line");
  return line;
}

describe("AiBadge", () => {
  it("says AI-written in text, not by colour alone, with a decorative icon", () => {
    const { container } = render(<AiBadge />);

    expect(screen.getByText("AI-written")).toBeInTheDocument();
    expect(container.querySelector("svg")).toHaveAttribute(
      "aria-hidden",
      "true",
    );
    expect(container.firstElementChild).toHaveClass("bg-ai-soft", "text-ai");
  });

  it("comes before an AI-written item note", () => {
    render(<ItineraryItemCard item={ITEM} />);

    const line = noteLine();
    const badge = within(line).getByText("AI-written");
    expect(line.firstElementChild).toBe(badge);
  });

  it("is distinct from the price's source label on the same card", () => {
    render(
      <ItineraryItemCard
        item={{
          ...ITEM,
          cost: { min: "5.00", max: "5.00", currency: "INR", label: "curated" },
        }}
      />,
    );

    expect(within(noteLine()).getByText("AI-written")).toBeInTheDocument();
    expect(within(noteLine()).queryByText("Curated")).not.toBeInTheDocument();
    expect(screen.getByText("Curated")).toBeInTheDocument();
    expect(screen.getAllByText("AI-written")).toHaveLength(1);
  });

  it("is not shown on a rule-based or sample item, which has no note", () => {
    const { container } = render(
      <ItineraryItemCard
        item={{
          ...ITEM,
          origin: "fallback_rule_based",
          note: null,
          note_origin: "none",
        }}
      />,
    );

    expect(container).not.toHaveTextContent("AI-written");
    expect(screen.getByText("Estimate")).toBeInTheDocument();
  });

  it("is not shown on a note the traveller wrote", () => {
    render(<ItineraryItemCard item={{ ...ITEM, note_origin: "user" }} />);

    expect(screen.getByText(NOTE)).toBeInTheDocument();
    expect(screen.queryByText("AI-written")).not.toBeInTheDocument();
  });

  it("follows an AI-written day theme and not a template theme", () => {
    const day: Day = {
      day_number: 1,
      date: "2026-11-14",
      theme: "Museums and the old town",
      theme_origin: "ai",
      day_cost: { min: "0.00", max: "0.00", currency: "INR", complete: true },
      items: [],
    };
    const { rerender } = render(<DayColumn day={day} />);
    const theme = screen.getByText("Museums and the old town");
    expect(theme.nextElementSibling).toHaveTextContent("AI-written");

    rerender(
      <DayColumn
        day={{ ...day, theme: "Day 1 around Old Mill", theme_origin: "none" }}
      />,
    );
    expect(screen.getByText("Day 1 around Old Mill")).toBeInTheDocument();
    expect(screen.queryByText("AI-written")).not.toBeInTheDocument();
  });
});
