import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SourceBadge } from "@/components/labels/SourceBadge";

// §7.8, FR-076 (TC-231): the label is text as well as colour, and only three labels exist.
describe("SourceBadge", () => {
  it.each([
    ["estimate", "Estimate", "text-warning"],
    ["unavailable", "Unavailable", "text-muted-foreground"],
    ["curated", "Curated", "text-primary"],
  ] as const)(
    "shows %s as the text %s with its colour",
    (label, text, colour) => {
      render(<SourceBadge label={label} />);
      const badge = screen.getByText(text);
      expect(badge).toHaveClass(colour);
      expect(badge.className).not.toMatch(/#[0-9a-f]{3,6}/i); // tokens only
    },
  );

  it("names the date curated opening hours were checked", () => {
    render(<SourceBadge label="curated" kind="hours" checkedOn="2026-11-14" />);
    expect(
      screen.getByText("Curated, checked on Sat 14 Nov"),
    ).toBeInTheDocument();
  });

  it("IMD-130: a curated price shows no date", () => {
    render(<SourceBadge label="curated" checkedOn="2026-11-14" />);
    expect(screen.getByText("Curated")).toBeInTheDocument();
    expect(screen.queryByText(/checked on/)).not.toBeInTheDocument();
  });

  it.each(["live", "verified", "Live", "Verified"])(
    "TC-231: a label %s outside the contract never renders as Live or Verified",
    (value) => {
      const { container } = render(<SourceBadge label={value as never} />);
      expect(container).toHaveTextContent("Unavailable");
      expect(container.textContent).not.toMatch(/live|verified/i);
    },
  );
});
