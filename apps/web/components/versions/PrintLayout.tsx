import { formatDuration } from "@/components/itinerary/ItineraryItemCard";
import { AiBadge } from "@/components/labels/AiBadge";
import { SourceBadge } from "@/components/labels/SourceBadge";
import type { components } from "@/lib/api/schema";
import { formatDayDate, formatFullDate } from "@/lib/format";

type Summary = components["schemas"]["TripSummaryOut"];
type Item = Summary["days"][number]["items"][number];
type Leg = NonNullable<Item["travel_from_previous"]>;

export const ESTIMATE_STATEMENT =
  "Prices and hours are estimates unless marked Curated.";

// §7.8, as on the itinerary cards.
const TRAVEL_LABELS: Record<Leg["source"], string> = {
  routing_api: "Estimated travel time from a routing service",
  fallback_estimate: "Estimated travel time (distance based)",
};
const MODES: Record<Leg["mode"], string> = {
  walking: "walking",
  local_transport: "local transport",
  car: "car",
};

// In print only the summary is shown (no app navigation); each day after the first starts a page.
const PRINT_CSS = `@media print {
  body * { visibility: hidden; }
  [data-print-root], [data-print-root] * { visibility: visible; }
  [data-print-root] { position: absolute; inset: 0; }
}`;

function Cost({ cost }: { cost: Item["cost"] }) {
  // §7.8: an unavailable price is never shown as a value.
  if (!cost || cost.label === "unavailable")
    return <SourceBadge label="unavailable" />;
  const amount = cost.min === cost.max ? cost.min : `${cost.min}–${cost.max}`;
  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      <span className="tabular-nums">
        {cost.currency} {amount}
      </span>
      <SourceBadge label={cost.label} />
    </span>
  );
}

/** The printable trip summary (FR-094): every value comes from API-35, nothing is computed here. */
export function PrintLayout({ summary }: { summary: Summary }) {
  const { trip, days, unresolved_findings: findings, costs } = summary;
  return (
    <article data-print-root className="flex flex-col gap-6">
      <style>{PRINT_CSS}</style>
      <header>
        <h1 className="text-2xl font-semibold">{trip.title}</h1>
        <p className="text-muted-foreground">
          {trip.destination.name} · {formatFullDate(trip.start_date)} to{" "}
          {formatFullDate(trip.end_date)}
        </p>
      </header>
      {days.map((day, index) => (
        <section
          key={day.day_number}
          aria-labelledby={`summary-day-${day.day_number}`}
          className={`rounded-xl border bg-card p-4 shadow-xs print:border-0 print:shadow-none ${index > 0 ? "print:break-before-page" : ""}`}
        >
          <h2
            id={`summary-day-${day.day_number}`}
            className="text-xl font-semibold"
          >
            Day {day.day_number} · {formatDayDate(day.date)}
          </h2>
          {day.theme && (
            <p className="mt-1 flex flex-wrap items-center gap-2">
              {day.theme}
              {day.theme_origin === "ai" && <AiBadge />}
            </p>
          )}
          <ol className="mt-3 flex flex-col gap-3">
            {day.items.map((item) => (
              <li key={item.id} className="flex flex-col gap-1">
                {item.travel_from_previous && (
                  <p className="text-sm text-muted-foreground">
                    {formatDuration(item.travel_from_previous.minutes)}{" "}
                    {MODES[item.travel_from_previous.mode]} ·{" "}
                    {TRAVEL_LABELS[item.travel_from_previous.source]}
                  </p>
                )}
                <p className="flex flex-wrap items-center gap-2">
                  <span className="font-medium tabular-nums">
                    {item.start_time}–{item.end_time}
                  </span>
                  <span>{item.place.name}</span>
                  <span className="text-sm text-muted-foreground">Hours:</span>
                  <SourceBadge label={item.place.hours_label} kind="hours" />
                  <Cost cost={item.cost} />
                </p>
                {item.note && (
                  <p className="flex flex-wrap items-center gap-2 text-sm">
                    {item.note}
                    {item.note_origin === "ai" && <AiBadge />}
                  </p>
                )}
              </li>
            ))}
          </ol>
          <p className="mt-3 text-sm">
            Day estimate: {day.day_cost.currency} {day.day_cost.min}–
            {day.day_cost.max} <SourceBadge label="estimate" />
            {!day.day_cost.complete && " (some prices unavailable)"}
          </p>
        </section>
      ))}
      <section
        aria-labelledby="summary-totals"
        className="rounded-xl border bg-card p-4 shadow-xs print:break-before-page"
      >
        <h2 id="summary-totals" className="text-xl font-semibold">
          Trip total
        </h2>
        <p className="flex flex-wrap items-center gap-2">
          Planning total: {costs.currency} {costs.planning_total}
          <SourceBadge label="estimate" />
        </p>
        <p className="flex flex-wrap items-center gap-2">
          Estimate range: {costs.currency} {costs.estimate.min}–
          {costs.estimate.max}
          <SourceBadge label="estimate" />
        </p>
        {!costs.complete && (
          <p>Some costs are unavailable; treat the total as incomplete.</p>
        )}
      </section>
      <section aria-labelledby="summary-warnings">
        <h2 id="summary-warnings" className="text-xl font-semibold">
          Unresolved warnings
        </h2>
        {findings.length === 0 ? (
          <p>No unresolved warnings.</p>
        ) : (
          <ul className="mt-2 flex list-disc flex-col gap-1 pl-5">
            {findings.map((finding) => (
              <li key={finding.id}>
                {finding.day_number !== null && `Day ${finding.day_number}: `}
                {finding.message}
                {finding.suggested_fix && ` ${finding.suggested_fix}`}
              </li>
            ))}
          </ul>
        )}
      </section>
      <p className="text-sm text-muted-foreground">{ESTIMATE_STATEMENT}</p>
    </article>
  );
}
