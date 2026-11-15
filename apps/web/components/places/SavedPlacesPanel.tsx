import { X } from "lucide-react";

import type { Place } from "@/components/places/PlaceCard";
import { Button } from "@/components/ui/button";

export type SavedPlacesPanelProps = {
  /** API-21; undefined while loading. */
  places: Place[] | undefined;
  failed: boolean;
  onRemove: (placeId: string) => void;
  removing: boolean;
};

/**
 * The trip's saved places on the explore page (§7.5.5; FR-020, IMP-605). Saving is a wish, not a
 * must-visit choice: generation treats it only as a ranking signal, and the panel says so.
 */
export function SavedPlacesPanel({
  places,
  failed,
  onRemove,
  removing,
}: SavedPlacesPanelProps) {
  return (
    <section
      aria-labelledby="saved-places-heading"
      className="flex flex-col gap-3 rounded-xl border bg-card p-4 text-card-foreground shadow-xs"
    >
      <header className="flex flex-col gap-1">
        <h2
          id="saved-places-heading"
          className="font-heading text-lg font-semibold"
        >
          Saved places
        </h2>
        <p className="text-sm text-muted-foreground">
          Saved places are preferred when a plan is made, but they are not
          must-visit places.
        </p>
      </header>
      {failed ? (
        <p role="alert" className="text-sm text-destructive">
          Saved places could not be loaded.
        </p>
      ) : !places ? (
        <p className="text-sm text-muted-foreground">Loading saved places…</p>
      ) : places.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No saved places yet. Use Save on a place to keep it here.
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {places.map((place) => (
            <li
              key={place.id}
              className="flex items-center justify-between gap-3 text-sm"
            >
              <span className="break-words">{place.name}</span>
              <Button
                variant="ghost"
                size="icon"
                aria-label={`Remove ${place.name} from saved places`}
                disabled={removing}
                onClick={() => onRemove(place.id)}
              >
                <X aria-hidden="true" />
              </Button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
