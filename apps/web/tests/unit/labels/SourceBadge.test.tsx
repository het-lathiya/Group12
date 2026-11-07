import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SourceBadge } from "@/components/labels/SourceBadge";

// §7.8: the label is text as well as colour.
describe("SourceBadge", () => {
  it.each([
    ["estimate", "Estimate"],
    ["unavailable", "Unavailable"],
    ["curated", "Curated"],
  ] as const)("shows %s as %s", (label, text) => {
    render(<SourceBadge label={label} />);
    expect(screen.getByText(text)).toBeInTheDocument();
  });

  it("names the date a curated fact was checked", () => {
    render(<SourceBadge label="curated" checkedOn="2026-11-14" />);
    expect(
      screen.getByText("Curated, checked on Sat 14 Nov"),
    ).toBeInTheDocument();
  });
});
