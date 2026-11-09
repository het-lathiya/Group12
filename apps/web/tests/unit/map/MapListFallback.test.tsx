import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { MapListFallback } from "@/components/map/MapListFallback";
import type { components } from "@/lib/api/schema";

type Item = components["schemas"]["Item"];

const items = [
  {
    id: "item-one",
    place: { name: "Museum" },
    start_time: "09:00",
  },
  {
    id: "item-two",
    place: { name: "Garden" },
    start_time: "11:00",
  },
] as unknown as Item[];

describe("MapListFallback", () => {
  it("shows stops in visit order with numbered accessible controls", () => {
    render(<MapListFallback items={items} />);

    expect(screen.getByRole("status")).toHaveTextContent(
      "Map unavailable; list view shown",
    );
    expect(screen.getByRole("button", { name: /Stop|Museum/ })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Museum/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Garden/ })).toBeInTheDocument();
    expect(screen.getByText("09:00")).toBeInTheDocument();
    expect(screen.getByText("11:00")).toBeInTheDocument();
  });

  it("focuses the matching itinerary card when a stop is selected", () => {
    const target = document.createElement("div");
    target.id = "item-item-two";
    target.tabIndex = -1;
    document.body.append(target);
    const scrollIntoView = vi.fn();
    target.scrollIntoView = scrollIntoView;
    render(<MapListFallback items={items} />);

    fireEvent.click(screen.getByRole("button", { name: /Garden/ }));

    expect(target).toHaveFocus();
    expect(scrollIntoView).toHaveBeenCalledWith({
      behavior: "smooth",
      block: "center",
    });
    target.remove();
  });
});
