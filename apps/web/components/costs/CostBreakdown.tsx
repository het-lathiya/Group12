import { useId } from "react";
import { SourceBadge } from "@/components/labels/SourceBadge";
import type { components } from "@/lib/api/schema";

type Costs = components["schemas"]["CostSummaryOut"];
const categories: Record<Costs["by_category"][number]["category"], string> = {
  activities: "Activities",
  food: "Food",
  transport: "Transport",
  accommodation: "Accommodation",
  other: "Other",
  contingency: "Contingency",
};
const cell = "border-b px-3 py-3 text-left tabular-nums";
// Scroll regions take keyboard focus so narrow screens can scroll them (axe scrollable-region-focusable).
const region =
  "overflow-x-auto rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2";

/** Both breakdowns are API-33 values; the browser never sums rows (IMD-172). */
export function CostBreakdown({ costs }: { costs: Costs }) {
  const money = (value: string) => `${costs.currency} ${value}`;
  const dailyId = useId();
  const categoryId = useId();
  return (
    <div className="flex flex-col gap-6">
      <div
        className={region}
        tabIndex={0}
        role="region"
        aria-labelledby={dailyId}
      >
        <table className="w-full text-sm">
          <caption
            id={dailyId}
            className="mb-2 text-left text-lg font-semibold"
          >
            Daily cost estimates
          </caption>
          <thead>
            <tr>
              {["Day", "Low", "High", "Contingency share", "Label"].map(
                (heading) => (
                  <th key={heading} scope="col" className={cell}>
                    {heading}
                  </th>
                ),
              )}
            </tr>
          </thead>
          <tbody>
            {costs.by_day.map((day) => (
              <tr key={day.day_number}>
                <th scope="row" className={cell}>
                  Day {day.day_number}
                </th>
                <td className={cell}>{money(day.min)}</td>
                <td className={cell}>{money(day.max)}</td>
                <td className={cell}>{money(day.contingency_share)}</td>
                <td className={cell}>
                  <SourceBadge label="estimate" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-2 text-sm text-muted-foreground">
          Daily high estimates plus their contingency shares make up the
          planning total.
        </p>
      </div>
      <div
        className={region}
        tabIndex={0}
        role="region"
        aria-labelledby={categoryId}
      >
        <table className="w-full text-sm">
          <caption
            id={categoryId}
            className="mb-2 text-left text-lg font-semibold"
          >
            Costs by category
          </caption>
          <thead>
            <tr>
              {["Category", "Low", "High", "Label"].map((heading) => (
                <th key={heading} scope="col" className={cell}>
                  {heading}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {costs.by_category.map((line) => (
              <tr key={line.category}>
                <th scope="row" className={cell}>
                  {categories[line.category]}
                </th>
                <td className={cell}>
                  {line.label === "unavailable" ? "—" : money(line.min)}
                </td>
                <td className={cell}>
                  {line.label === "unavailable" ? "—" : money(line.max)}
                </td>
                <td className={cell}>
                  <SourceBadge label={line.label} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
