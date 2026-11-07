import { ItineraryItemCard } from "@/components/itinerary/ItineraryItemCard";
import { AiBadge } from "@/components/labels/AiBadge";
import type { components } from "@/lib/api/schema";
import { formatDayDate } from "@/lib/format";

type Day = components["schemas"]["Day"];

export type DayColumnProps = {
  day: Day;
  /** Set where the day index links to the card, which then takes focus. */
  id?: string;
};

/**
 * One day of the itinerary (§7.5.7; guide §14): the day number, its date, its theme and its items
 * in the order API-24 returns them. Edits arrive with IMP-408 and later.
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
      {day.theme && (
        <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          <span className="min-w-0">{day.theme}</span>
          {day.theme_origin === "ai" && <AiBadge />}
        </p>
      )}
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
