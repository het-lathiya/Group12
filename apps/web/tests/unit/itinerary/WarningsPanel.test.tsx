import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  countLabel,
  WarningsPanel,
} from "@/components/itinerary/WarningsPanel";
import type { components } from "@/lib/api/schema";

// FR-056 (IMP-405): each finding shows its cause and a suggested fix, grouped by severity then
// day; an item finding links to the item; a missing must-visit place names the place.
type Finding = components["schemas"]["Finding"];

const ITEM_ID = "00000000-0000-4000-8000-0000000000c1";
const PLACE_ID = "00000000-0000-4000-8000-0000000000p1";

function finding(overrides: Partial<Finding>): Finding {
  return {
    id: crypto.randomUUID(),
    code: "OVERLAP",
    severity: "error",
    message: "Museum starts before Old Fort ends.",
    day_number: 1,
    item_id: ITEM_ID,
    place_id: null,
    suggested_fix: "Move Museum to 11:45.",
    ...overrides,
  };
}

const FINDINGS: Finding[] = [
  finding({
    code: "HOURS_UNVERIFIED",
    severity: "info",
    day_number: 1,
    message: "Opening hours unavailable for Riverside Market.",
    suggested_fix: "Check opening times before the visit.",
  }),
  finding({
    code: "TRANSFER_TOO_SHORT",
    severity: "warning",
    day_number: 2,
    message: "5 min to reach the market, but the transfer needs 20 min.",
    suggested_fix: "Start the market 15 min later.",
  }),
  finding({ day_number: 2 }),
  finding({
    code: "MUST_VISIT_MISSING",
    severity: "error",
    day_number: null,
    item_id: null,
    place_id: PLACE_ID,
    message: "Must-visit place Lake Walk is not in the plan.",
    suggested_fix: "Add it to a day with room.",
  }),
];

describe("WarningsPanel", () => {
  it("titles the section Plan checks with the counts per severity", () => {
    render(<WarningsPanel findings={FINDINGS} onGoToItem={vi.fn()} />);

    const section = screen.getByRole("region", { name: /Plan checks/ });
    expect(
      within(section).getByRole("heading", { level: 2 }),
    ).toHaveTextContent("Plan checks2 errors · 1 warning · 1 info");
    expect(countLabel([])).toBe("");
  });

  it("groups by severity in the order error, warning, info, then by day", () => {
    render(<WarningsPanel findings={FINDINGS} onGoToItem={vi.fn()} />);

    const panel = screen.getByRole("region", { name: /Plan checks/ });
    expect(
      within(panel)
        .getAllByRole("heading", { level: 3 })
        .map((h) => h.textContent),
    ).toEqual(["Errors", "Warnings", "Infos"]);
    const errors = screen.getByRole("region", { name: "Errors" });
    expect(
      within(errors)
        .getAllByRole("heading", { level: 4 })
        .map((h) => h.textContent),
    ).toEqual(["Whole trip", "Day 2"]);
  });

  it("shows each cause with a text badge and the suggested fix", () => {
    render(<WarningsPanel findings={FINDINGS} onGoToItem={vi.fn()} />);

    for (const { message, suggested_fix } of FINDINGS) {
      const row = screen.getByText(message).closest("li");
      expect(row).not.toBeNull();
      expect(
        within(row as HTMLElement).getByText("Suggested fix:"),
      ).toBeVisible();
      expect(
        within(row as HTMLElement).getByText(suggested_fix as string),
      ).toBeVisible();
    }
    const warningRow = screen
      .getByText(FINDINGS[1].message)
      .closest("li") as HTMLElement;
    expect(within(warningRow).getByText("Warning")).toBeVisible();
  });

  it("Go to item is a keyboard-reachable button that hands over the item id", () => {
    const onGoToItem = vi.fn();
    render(<WarningsPanel findings={FINDINGS} onGoToItem={onGoToItem} />);

    const buttons = screen.getAllByRole("button", { name: "Go to item" });
    expect(buttons).toHaveLength(3); // every finding with an item
    buttons[0].focus();
    expect(buttons[0]).toHaveFocus();
    fireEvent.click(buttons[0]);
    expect(onGoToItem).toHaveBeenCalledWith(ITEM_ID);
  });

  it("names the missing must-visit place and offers no item link for it", () => {
    render(
      <WarningsPanel
        findings={FINDINGS}
        placeNames={{ [PLACE_ID]: "Lake Walk" }}
        onGoToItem={vi.fn()}
      />,
    );

    const row = screen
      .getByText(/Must-visit place Lake Walk/)
      .closest("li") as HTMLElement;
    expect(within(row).getByText("Lake Walk")).toBeVisible();
    expect(within(row).queryByRole("button")).toBeNull();
  });

  it("says No issues found when there is nothing to report", () => {
    render(<WarningsPanel findings={[]} onGoToItem={vi.fn()} />);

    expect(screen.getAllByText("No issues found").length).toBeGreaterThan(0);
    expect(screen.queryByRole("button", { name: "Go to item" })).toBeNull();
  });

  it("announces the counts in a polite live region", () => {
    const { container, rerender } = render(
      <WarningsPanel findings={FINDINGS} onGoToItem={vi.fn()} />,
    );
    const live = container.querySelector('[aria-live="polite"]');
    expect(live).toHaveTextContent(
      "Plan checks: 2 errors · 1 warning · 1 info",
    );

    rerender(<WarningsPanel findings={[]} onGoToItem={vi.fn()} />);
    expect(live).toHaveTextContent("Plan checks: No issues found");
  });

  it("starts collapsed on small screens when only info rows remain, and the toggle opens it", () => {
    render(<WarningsPanel findings={[FINDINGS[0]]} onGoToItem={vi.fn()} />);

    const toggle = screen.getByRole("button", { name: "Show" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(document.getElementById("plan-checks-list")).toHaveClass("hidden");
    fireEvent.click(toggle);
    expect(screen.getByRole("button", { name: "Hide" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    expect(document.getElementById("plan-checks-list")).not.toHaveClass(
      "hidden",
    );
  });

  it("starts open when it has errors or warnings", () => {
    render(<WarningsPanel findings={FINDINGS} onGoToItem={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Hide" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
  });
});
