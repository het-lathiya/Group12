import { Bookmark, BookmarkCheck } from "lucide-react";

import { formatDuration } from "@/components/itinerary/ItineraryItemCard";
import { SourceBadge } from "@/components/labels/SourceBadge";
import type { components } from "@/lib/api/schema";

type Schemas = components["schemas"];
// `source_name` is added to PlaceSummary by IMP-509; the intersection keeps this compiling until
// the generated types are refreshed, and is a no-op afterwards.
export type Place = Schemas["PlaceSummary"] & { source_name?: string | null };

const CATEGORY_LABELS: Record<Schemas["Category"], string> = {
  sight: "Sight",
  museum: "Museum",
  nature: "Nature",
  food: "Food",
  shopping: "Shopping",
  entertainment: "Entertainment",
  religious: "Religious site",
  activity: "Activity",
  stay: "Stay",
};

const VERIFICATION_LABELS: Record<Schemas["VerificationStatus"], string> = {
  unverified: "Not verified",
  curated_checked: "Curated and checked",
  imported_osm: "Imported from OpenStreetMap",
  estimated: "Estimated",
};

function Price({ price }: { price: Place["price"] }) {
  // §7.8: an unavailable price is never shown as a value.
  if (!price || price.label === "unavailable") {
    return <SourceBadge label="unavailable" />;
  }
  const amount =
    price.max === null || price.max === price.min
      ? price.min
      : `${price.min}–${price.max}`;
  return (
    <span className="flex flex-wrap items-center gap-2">
      <span className="tabular-nums">
        {price.currency} {amount}
      </span>
      <SourceBadge label={price.label} />
    </span>
  );
}

export type PlaceCardProps = {
  place: Place;
  /** With `onToggleSave` (wishlist on, IMP-605): whether the place is saved for the trip. */
  saved?: boolean;
  onToggleSave?: () => void;
  saveDisabled?: boolean;
};

/** One place of the explore list (§7.5.5; FR-016 AC2): facts as API-16 sent them, each labelled. */
export function PlaceCard({
  place,
  saved = false,
  onToggleSave,
  saveDisabled = false,
}: PlaceCardProps) {
  const SaveIcon = saved ? BookmarkCheck : Bookmark;
  return (
    <article className="flex flex-col gap-3 rounded-xl border bg-card p-4 text-card-foreground shadow-xs">
      <header className="flex items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h3 className="font-heading text-base font-semibold">{place.name}</h3>
          <p className="text-sm text-muted-foreground">
            {CATEGORY_LABELS[place.category] ?? place.category} ·{" "}
            {formatDuration(place.typical_duration_min)}
          </p>
        </div>
        {onToggleSave && (
          <button
            type="button"
            aria-pressed={saved}
            aria-label={`Save ${place.name}`}
            disabled={saveDisabled}
            onClick={onToggleSave}
            className={`inline-flex min-h-touch shrink-0 items-center gap-2 rounded-full border px-3 text-sm font-medium transition-colors outline-none focus-visible:ring-3 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50 ${
              saved
                ? "border-primary bg-primary text-primary-foreground hover:bg-primary-hover"
                : "border-input bg-background text-foreground hover:bg-muted"
            }`}
          >
            <SaveIcon aria-hidden="true" className="size-4" />
            {saved ? "Saved" : "Save"}
          </button>
        )}
      </header>
      {place.tags.length > 0 && (
        <ul aria-label="Tags" className="flex flex-wrap gap-1">
          {place.tags.map((tag) => (
            <li
              key={tag}
              className="rounded-xl bg-muted px-2 py-0.5 text-xs text-muted-foreground"
            >
              {tag.replaceAll("_", " ")}
            </li>
          ))}
        </ul>
      )}
      <dl className="grid grid-cols-[auto_1fr] items-center gap-x-3 gap-y-2 text-sm">
        <dt className="text-muted-foreground">Price</dt>
        <dd>
          <Price price={place.price} />
        </dd>
        <dt className="text-muted-foreground">Hours</dt>
        <dd>
          <SourceBadge label={place.hours_label} kind="hours" />
        </dd>
        <dt className="text-muted-foreground">Verification</dt>
        <dd>
          {VERIFICATION_LABELS[place.verification_status] ??
            VERIFICATION_LABELS.unverified}
        </dd>
        <dt className="text-muted-foreground">Source</dt>
        <dd className="break-words">{place.source_name ?? "Not stated"}</dd>
      </dl>
    </article>
  );
}
