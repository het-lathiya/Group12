import { MapPinOff } from "lucide-react";

import type { components } from "@/lib/api/schema";

type Item = components["schemas"]["Item"];

export type MapListFallbackProps = {
  /** The day's items in visit order; numbered as the map markers are. */
  items: Item[];
  onSelectItem: (itemId: string) => void;
};

/**
 * FR-080 AC3: the map's stand-in when tiles, the style or WebGL fail. The same stops with the same
 * numbers and the times API-24 sent; each one goes to its item card, so no task needs the map.
 */
export function MapListFallback({ items, onSelectItem }: MapListFallbackProps) {
  return (
    <div className="flex flex-col gap-3">
      <p
        role="status"
        className="flex items-start gap-2 rounded-xl bg-info-soft p-4 text-sm text-info"
      >
        <MapPinOff aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
        Map unavailable; list view shown
      </p>
      <ol aria-label="Stops" className="flex flex-col gap-1">
        {items.map((item, index) => (
          <li key={item.id}>
            <button
              type="button"
              onClick={() => onSelectItem(item.id)}
              className="flex min-h-11 w-full items-center gap-3 rounded-lg px-2 text-left text-sm transition-colors outline-none hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            >
              {/* The visible text forms the name ("Stop 1 <place> <times>"), so WCAG 2.5.3 holds. */}
              <span className="sr-only">Stop </span>
              <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground tabular-nums">
                {index + 1}
              </span>
              <span className="min-w-0 flex-1 font-medium">
                {item.place.name}
              </span>
              <span className="text-muted-foreground tabular-nums">
                {item.start_time}–{item.end_time}
              </span>
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
}
