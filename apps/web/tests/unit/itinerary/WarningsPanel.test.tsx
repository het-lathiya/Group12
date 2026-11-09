import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { WarningsPanel } from "@/components/itinerary/WarningsPanel";
import type { components } from "@/lib/api/schema";

type Finding = components["schemas"]["Finding"];

const finding = (overrides: Partial<Finding> = {}): Finding => ({
  id: "finding-1",
  code: "OVERLAP",
  severity: "warning",
  message: "Two activities overlap.",
  suggested_fix: "Move the later activity.",
  day_number: 2,
  item_id: "item-1",
  place_id: null,
  ...overrides,
});

describe("WarningsPanel", () => {
  it("renders nothing when there are no findings", () => {
    const { container } = render(<WarningsPanel findings={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("groups findings by severity and day and links to the item", () => {
    render(
      <WarningsPanel
        findings={[
          finding(),
          finding({
            id: "finding-2",
            severity: "error",
            message: "A required place is missing.",
            item_id: null,
            day_number: null,
          }),
        ]}
      />,
    );

    expect(screen.getByRole("region", { name: "Errors" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Warnings" })).toBeInTheDocument();
    expect(screen.getByText("Trip-wide")).toBeInTheDocument();
    expect(screen.getByText("Day 2")).toBeInTheDocument();
    expect(screen.getByText("Suggested fix: Move the later activity.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Go to item" })).toHaveAttribute(
      "href",
      "#item-item-1",
    );
  });

  it("announces changes politely", () => {
    render(<WarningsPanel findings={[finding()]} />);
    expect(screen.getByRole("region", { name: "Plan checks" })).toHaveAttribute(
      "aria-live",
      "polite",
    );
  });
});
