import { ItineraryItemCard } from "@/components/itinerary/ItineraryItemCard";
import { SortableDay, SortableItem } from "@/components/itinerary/MoveControls";
import { AiBadge } from "@/components/labels/AiBadge";
import type { components } from "@/lib/api/schema";
import { formatDayDate } from "@/lib/format";

type Day = components["schemas"]["Day"];

const EMPTY = "Nothing planned for this day.";

export type DayColumnProps = {
  day: Day;
  /** Set where the day index links to the card, which then takes focus. */
  id?: string;
  /** Set where the plan can be edited (IMP-408, IMP-409); without it the day is read-only. */
  edit?: { tripId: string; planRevision: number; dayNumbers: number[] };
};

/**
 * One day of the itinerary (§7.5.7; guide §14): the day number, its date, its theme and its items
 * in the order API-24 returns them, with each item's edit controls when `edit` is set.
 */
export function DayColumn({ day, id, edit }: DayColumnProps) {
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
      {edit ? (
        // Editable: the list is a drop area even when empty (IMP-409).
        <SortableDay
          dayNumber={day.day_number}
          itemIds={day.items.map(({ id }) => id)}
        >
          {day.items.length === 0 && (
            <li className="text-sm text-muted-foreground">{EMPTY}</li>
          )}
          {day.items.map((item) => (
            <SortableItem key={item.id} item={item} dayNumber={day.day_number}>
              <ItineraryItemCard
                item={item}
                edit={{
                  ...edit,
                  dayNumber: day.day_number,
                  itemCount: day.items.length,
                }}
              />
            </SortableItem>
          ))}
        </SortableDay>
      ) : day.items.length === 0 ? (
        <p className="mt-4 text-sm text-muted-foreground">{EMPTY}</p>
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
