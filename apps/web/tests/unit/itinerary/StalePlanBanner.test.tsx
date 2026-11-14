import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import { StalePlanBanner } from "@/components/itinerary/StalePlanBanner";

it("only shows the API's stale flag, and Regenerate links to the generate page", () => {
  const { rerender } = render(
    <StalePlanBanner tripId="trip" planStale={false} />,
  );
  expect(screen.queryByRole("status")).not.toBeInTheDocument();
  rerender(<StalePlanBanner tripId="trip" planStale />);
  expect(
    screen.getByRole("status", { name: "Out-of-date plan" }),
  ).toHaveTextContent("This plan is out of date.");
  expect(screen.getByRole("link", { name: "Regenerate" })).toHaveAttribute(
    "href",
    "/trips/trip/generate",
  );
});
