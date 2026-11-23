"use client";

import { useLiveTier } from "@/components/labels/liveTier";
import { SourceBadge } from "@/components/labels/SourceBadge";
import { ErrorState } from "@/components/states/ErrorState";
import { LoadingSkeleton } from "@/components/states/LoadingSkeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ApiError, OFFLINE_MESSAGE } from "@/lib/api/client";
import { usePlace } from "@/lib/api/queries";
import type { components } from "@/lib/api/schema";
import { formatDayDate } from "@/lib/format";

type PlaceOut = components["schemas"]["PlaceOut"];

const WEEKDAYS = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

const VERIFICATION: Record<PlaceOut["verification_status"], string> = {
  unverified: "Not verified",
  curated_checked: "Curated and checked",
  imported_osm: "Imported from OpenStreetMap",
  estimated: "Estimated",
};

function Hours({ place }: { place: PlaceOut }) {
  const live = useLiveTier();
  // FR-018 AC2: without hours nothing is guessed: no time is shown.
  if (place.hours_label === "unavailable" || place.hours.length === 0) {
    // Amendment A2 §9.2: a live place's missing hours read "Hours unknown".
    return live ? (
      <SourceBadge label="unavailable" kind="hours" live />
    ) : (
      <p>Hours unavailable</p>
    );
  }
  return (
    <div className="flex flex-col gap-2">
      <SourceBadge
        label={place.hours_label}
        kind="hours"
        checkedOn={place.hours_checked_on}
      />
      <ul className="flex flex-col gap-1">
        {place.hours.map((h, index) => (
          <li
            key={`${h.weekday}-${index}`}
            className="flex justify-between gap-3 tabular-nums"
          >
            <span>{WEEKDAYS[h.weekday - 1]}</span>
            <span>
              {h.is_closed
                ? "Closed"
                : `${h.open_time}–${h.close_time}${h.closes_next_day ? " (next day)" : ""}`}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Price({ price }: { price: PlaceOut["price"] }) {
  const live = useLiveTier();
  // A missing price is "Unavailable" ("Price unknown" on a live place), never 0.
  if (!price || price.label === "unavailable") {
    return <SourceBadge label="unavailable" live={live} />;
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

function Facts({ place }: { place: PlaceOut }) {
  const { source } = place;
  return (
    <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-3">
      <dt className="text-muted-foreground">Hours</dt>
      <dd>
        <Hours place={place} />
      </dd>
      <dt className="text-muted-foreground">Price</dt>
      <dd>
        <Price price={place.price} />
      </dd>
      <dt className="text-muted-foreground">Verification</dt>
      <dd>
        {VERIFICATION[place.verification_status] ?? VERIFICATION.unverified}
      </dd>
      <dt className="text-muted-foreground">Location</dt>
      <dd className="tabular-nums">
        {place.address && <span className="block">{place.address}</span>}
        {place.lat}, {place.lon}
      </dd>
      <dt className="text-muted-foreground">Source</dt>
      <dd className="flex flex-col gap-1 break-words">
        {source.url ? (
          <a
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary underline"
          >
            {source.name}
          </a>
        ) : (
          <span>{source.name}</span>
        )}
        <span className="text-muted-foreground">
          {source.retrieved_on
            ? `Retrieved ${formatDayDate(source.retrieved_on)}`
            : "Retrieval date unavailable"}
          {` · ${source.licence}`}
        </span>
        {source.attribution_text && (
          <span className="text-muted-foreground">
            {source.attribution_text}
          </span>
        )}
      </dd>
    </dl>
  );
}

export type PlaceDetailDrawerProps = {
  /** The place to show (API-17); null keeps the drawer closed. */
  placeId: string | null;
  onClose: () => void;
};

/**
 * Place detail (§7.5.5; FR-018, IMP-604): description, hours, price, verification, location and
 * source, each fact as API-17 sent it and labelled with SourceBadge: curated hours read "Curated,
 * checked on <date>", missing hours "Hours unavailable", an estimated price "Estimate". Nothing is
 * filled in here.
 */
export function PlaceDetailDrawer({
  placeId,
  onClose,
}: PlaceDetailDrawerProps) {
  const place = usePlace(placeId);
  return (
    <Dialog open={placeId !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="top-0 right-0 left-auto h-full max-h-none w-full max-w-md translate-x-0 translate-y-0 content-start overflow-y-auto rounded-none sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{place.data?.name ?? "Place details"}</DialogTitle>
          <DialogDescription>
            {place.data?.description ?? "Facts are labelled with their source."}
          </DialogDescription>
        </DialogHeader>
        {place.error ? (
          <ErrorState
            title="This place could not be loaded"
            error={
              place.error instanceof ApiError
                ? place.error
                : { message: OFFLINE_MESSAGE }
            }
            onRetry={() => void place.refetch()}
          />
        ) : !place.data ? (
          <LoadingSkeleton shape="cards" count={1} label="Loading place" />
        ) : (
          <Facts place={place.data} />
        )}
      </DialogContent>
    </Dialog>
  );
}
