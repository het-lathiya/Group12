import { Info } from "lucide-react";
import { useId } from "react";
import { SourceBadge } from "@/components/labels/SourceBadge";
import { useLiveTier } from "@/components/labels/liveTier";
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

const BUDGET_STATUS: Record<Costs["budget"]["status"], string> = {
  none: "within your budget",
  near: "near your budget",
  exceeded: "over your budget",
};

/**
 * Amendment A2 §6.6, §9.2: a live plan's prices are unknown, so the totals cover known costs only.
 * N counts the items API-33 lists as incomplete (the items behind COST_INCOMPLETE).
 */
function KnownCostsNote({ costs }: { costs: Costs }) {
  const missing = costs.incomplete_items.length;
  return (
    <div className="flex items-start gap-2 rounded-xl bg-info-soft px-4 py-3 text-sm text-info">
      <Info aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
      <div className="flex min-w-0 flex-col gap-1">
        {missing > 0 && (
          <p>
            Known costs only: {missing}{" "}
            {missing === 1 ? "stop has" : "stops have"} no price
          </p>
        )}
        {costs.budget.amount && (
          <p>
            Budget status: {BUDGET_STATUS[costs.budget.status]}, covers known
            costs only
          </p>
        )}
      </div>
    </div>
  );
}

/** Both breakdowns are API-33 values; the browser never sums rows (IMD-172). */
export function CostBreakdown({
  costs,
  live: liveProp,
}: {
  costs: Costs;
  /** A live destination (Amendment A2 §9.2); defaults to the page's LiveTierProvider. */
  live?: boolean;
}) {
  const liveContext = useLiveTier();
  const live = liveProp ?? liveContext;
  const money = (value: string) => `${costs.currency} ${value}`;
  const dailyId = useId();
  const categoryId = useId();
  return (
    <div className="flex flex-col gap-6">
      {live && (costs.incomplete_items.length > 0 || costs.budget.amount) && (
        <KnownCostsNote costs={costs} />
      )}
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
