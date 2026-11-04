import type { components } from "@/lib/api/schema";

type Item = components["schemas"]["Item"];

const SLOT_LABELS: Record<Item["slot_type"], string> = {
  activity: "Activity",
  meal: "Meal",
  rest: "Rest",
};

/** A duration in minutes as the guide writes it (§17): "45 min", "1 h", "1 h 30 min". */
export function formatDuration(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (hours === 0) return `${rest} min`;
  return rest === 0 ? `${hours} h` : `${hours} h ${rest} min`;
}

/**
 * One stop of a day's timeline (§7.6; guide §14), read-only in Sprint 2: the start time, place name,
 * duration and slot type exactly as API-24 returns them. Money amounts, travel and notes arrive
 * with IMP-308 and IMP-309; nothing here is computed from other values.
 */
export function ItineraryItemCard({ item }: { item: Item }) {
  return (
    <div className="grid grid-cols-[56px_1fr]">
      <time
        dateTime={item.start_time}
        className="pt-3 text-sm font-medium text-muted-foreground tabular-nums"
      >
        {item.start_time}
      </time>
      <div className="border-l border-border pb-3 pl-4">
        <div className="rounded-lg border bg-card p-3 shadow-xs sm:p-4">
          <h3 className="text-base font-semibold text-card-foreground">
            {item.place.name}
          </h3>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <span className="tabular-nums">
              {formatDuration(item.duration_min)}
            </span>
            <span aria-hidden="true">·</span>
            <span className="inline-flex h-6 items-center rounded-full border border-border px-2 text-xs font-medium text-foreground">
              {SLOT_LABELS[item.slot_type]}
            </span>
          </p>
        </div>
      </div>
    </div>
  );
}
