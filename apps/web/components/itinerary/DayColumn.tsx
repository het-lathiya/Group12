import { ItineraryItemCard } from "@/components/itinerary/ItineraryItemCard";
import type { components } from "@/lib/api/schema";

type Day = components["schemas"]["Day"];

/** A date-only string "2026-11-14" as "Sat 14 Nov" (guide §17), read in UTC so no zone shifts it. */
export function formatDayDate(isoDate: string): string {
  const [year, month, day] = isoDate.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day)).toLocaleDateString("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  });
}

export type DayColumnProps = {
  day: Day;
  /** Set where the day index links to the card, which then takes focus. */
  id?: string;
};

/**
 * One day of the itinerary (§7.6; guide §14), read-only in Sprint 2: the day number, its date and
 * its items in the order API-24 returns them. Theme, money amounts and edits arrive with IMP-308,
 * IMP-309 and later.
 */
export function DayColumn({ day, id }: DayColumnProps) {
  return (
    <section
      id={id}
      tabIndex={id ? -1 : undefined}
      aria-label={`Day ${day.day_number}`}
      className="scroll-mt-24 rounded-xl border bg-card p-4 text-card-foreground shadow-xs outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 sm:p-6"
    >
      <h2 className="flex flex-col">
        <span className="text-xs font-medium tracking-wider text-muted-foreground uppercase">
          Day {day.day_number}
        </span>{" "}
        <span className="text-xl font-semibold tracking-[-0.01em]">
          {formatDayDate(day.date)}
        </span>
      </h2>
      {day.items.length === 0 ? (
        <p className="mt-4 text-sm text-muted-foreground">
          Nothing planned for this day.
        </p>
      ) : (
        <ol className="mt-4">
          {day.items.map((item) => (
            <li key={item.id}>
              <ItineraryItemCard item={item} />
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
