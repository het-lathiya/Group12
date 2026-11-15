import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Button } from "@/components/ui/button";

const VARIANTS = [
  "default",
  "outline",
  "secondary",
  "ghost",
  "destructive",
  "link",
] as const;

describe("Button", () => {
  // IMP-513 (TC-383): a disabled Button that becomes enabled must not fade its opacity, or a
  // contrast scan during the fade reads a half-transparent label (below 4.5:1).
  it.each(VARIANTS)("%s animates colours only, never opacity", (variant) => {
    render(<Button variant={variant}>Go</Button>);
    const button = screen.getByRole("button", { name: "Go" });

    expect(button).toHaveClass("transition-colors");
    expect(button).not.toHaveClass("transition-all");
    expect(button).not.toHaveClass("transition-opacity");
    expect(button).not.toHaveClass("transition");
  });

  it("keeps the disabled look and the colour-only transition when disabled", () => {
    render(<Button disabled>Go</Button>);
    const button = screen.getByRole("button", { name: "Go" });

    expect(button).toBeDisabled();
    expect(button).toHaveClass("disabled:opacity-50", "transition-colors");
    expect(button).not.toHaveClass("transition-all");
  });

  // RUN-075, PD-RUN-071b-1 (IMD-183): solid tokens, so the hover keeps #B91C1C at 5.30:1.
  it("destructive uses the solid soft tokens, with no opacity-mixed background", () => {
    render(<Button variant="destructive">Delete</Button>);
    const button = screen.getByRole("button", { name: "Delete" });

    expect(button).toHaveClass(
      "bg-destructive-soft",
      "hover:bg-destructive-soft-hover",
      "text-destructive",
    );
    expect(button.className).not.toMatch(
      /(^|\s)(dark:)?(hover:)?bg-destructive\//,
    );
  });
});
