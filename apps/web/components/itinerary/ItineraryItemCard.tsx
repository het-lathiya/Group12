"use client";

import { useIsMutating } from "@tanstack/react-query";
import { Lock, Unlock, Utensils } from "lucide-react";

import { AlternativesDialog } from "@/components/itinerary/AlternativesDialog";
import { ItemEditor } from "@/components/itinerary/ItemEditor";
import { ItemSources } from "@/components/itinerary/ItemSources";
import { MoveControls } from "@/components/itinerary/MoveControls";
import { AiBadge } from "@/components/labels/AiBadge";
import { SourceBadge } from "@/components/labels/SourceBadge";
import { Button } from "@/components/ui/button";
import { describeError } from "@/lib/api/errors";
import { editKey, useLockItem } from "@/lib/api/queries";
import { isEnabled } from "@/lib/flags";
import type { components } from "@/lib/api/schema";

type Item = components["schemas"]["Item"];
type Leg = NonNullable<Item["travel_from_previous"]>;

const SLOT_LABELS: Record<Item["slot_type"], string> = {
  activity: "Activity",
  meal: "Meal",
  rest: "Rest",
};

const MODE_LABELS: Record<Leg["mode"], string> = {
  walking: "Walking",
  local_transport: "Local transport",
  car: "Car",
};

// §7.8
const TRAVEL_LABELS: Record<Leg["source"], string> = {
  routing_api: "Estimated travel time from a routing service",
  fallback_estimate: "Estimated travel time (distance based)",
};

/** A duration in minutes as the guide writes it (§17): "45 min", "1 h", "1 h 30 min". */
export function formatDuration(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (hours === 0) return `${rest} min`;
  return rest === 0 ? `${hours} h` : `${hours} h ${rest} min`;
}

function Cost({ cost }: { cost: Item["cost"] }) {
  // §7.8: an unavailable price is never shown as a value.
  if (!cost || cost.label === "unavailable") {
    return (
      <div className="ml-auto">
        <SourceBadge label="unavailable" />
      </div>
    );
  }
  const amount = cost.min === cost.max ? cost.min : `${cost.min}–${cost.max}`;
  return (
    <p className="ml-auto flex flex-wrap items-center justify-end gap-2 text-right text-sm text-card-foreground">
      <span className="tabular-nums">
        {cost.currency} {amount}
      </span>
      <SourceBadge label={cost.label} />
    </p>
  );
}

/** The id of an item's card, which "Go to item" scrolls to and focuses. */
export const itemCardId = (itemId: string) => `item-${itemId}`;

/** What a card needs to offer edits; without it the card is read-only. */
export type ItemEditContext = {
  tripId: string;
  planRevision: number;
  dayNumber: number;
  /** For MoveControls (IMP-409): the day's item count and the trip's day numbers. */
  itemCount: number;
  dayNumbers: number[];
};

/**
 * One stop of a day's timeline (§7.5.7; guide §14): the leg from the previous stop, then the place
 * with its times, cost and note exactly as API-24 returns them. No time or amount is computed here.
 * With `edit`, the card also offers ItemEditor (IMP-408) and MoveControls (IMP-409).
 */
export function ItineraryItemCard({
  item,
  edit,
}: {
  item: Item;
  edit?: ItemEditContext;
}) {
  const leg = item.travel_from_previous;
  return (
    <div className="grid grid-cols-[56px_minmax(0,1fr)]">
      {leg && (
        <p className="col-start-2 flex flex-wrap items-center gap-x-2 border-l border-border pb-3 pl-4 text-sm text-muted-foreground">
          <span className="tabular-nums">{formatDuration(leg.minutes)}</span>
          <span aria-hidden="true">·</span>
          <span>{MODE_LABELS[leg.mode]}</span>
          <span aria-hidden="true">·</span>
          <span>{TRAVEL_LABELS[leg.source]}</span>
        </p>
      )}
      <time
        dateTime={item.start_time}
        className="pt-3 text-sm font-medium text-muted-foreground tabular-nums"
      >
        {item.start_time}
      </time>
      <div className="border-l border-border pb-3 pl-4">
        {/* The focus target of WarningsPanel's "Go to item" (IMP-405). */}
        <div
          id={itemCardId(item.id)}
          tabIndex={-1}
          className="scroll-mt-24 rounded-xl border bg-card p-3 shadow-xs outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 sm:p-4"
        >
          <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1">
            <h3 className="min-w-0 text-base font-semibold text-card-foreground">
              {item.place.name}
            </h3>
            <Cost cost={item.cost} />
          </div>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <span className="tabular-nums">
              {item.start_time}–{item.end_time}
            </span>
            <span aria-hidden="true">·</span>
            <span className="tabular-nums">
              {formatDuration(item.duration_min)}
            </span>
            <span aria-hidden="true">·</span>
            <span className="inline-flex h-6 items-center gap-1 rounded-full border border-border px-2 text-xs font-medium text-foreground">
              {/* IMP-606: a meal stop is a food place; no rating is ever shown (FR-083 AC2). */}
              {item.slot_type === "meal" && (
                <Utensils aria-hidden="true" className="size-3.5" />
              )}
              {SLOT_LABELS[item.slot_type]}
            </span>
          </p>
          <p className="mt-2 flex items-center gap-2 text-sm text-muted-foreground">
            Hours <SourceBadge label={item.place.hours_label} kind="hours" />
          </p>
          {item.note && (
            <p className="mt-2 flex flex-wrap items-center gap-2 text-sm text-card-foreground">
              {/* FR-035: the label comes first, so the reader knows before reading the text. */}
              {item.note_origin === "ai" && <AiBadge />}
              <span className="min-w-0">{item.note}</span>
            </p>
          )}
          {item.note_origin === "ai" && <ItemSources sources={item.sources} />}
          {isEnabled("locks") &&
            (edit ? (
              <LockToggle item={item} edit={edit} />
            ) : (
              item.is_locked && (
                <span className="mt-2 inline-flex items-center gap-1 text-sm">
                  <Lock aria-hidden="true" className="size-4" />
                  Locked
                </span>
              )
            ))}
          {edit && (
            <>
              <ItemEditor
                item={item}
                tripId={edit.tripId}
                planRevision={edit.planRevision}
                dayNumber={edit.dayNumber}
              />
              <MoveControls item={item} {...edit} />
              <AlternativesDialog
                item={item}
                tripId={edit.tripId}
                planRevision={edit.planRevision}
              />
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function LockToggle({ item, edit }: { item: Item; edit: ItemEditContext }) {
  const lock = useLockItem(edit.tripId);
  const busy = useIsMutating({ mutationKey: editKey(edit.tripId) }) > 0;
  const Icon = item.is_locked ? Lock : Unlock;
  return (
    <div className="mt-3">
      <Button
        variant="outline"
        aria-pressed={item.is_locked}
        aria-label={`${item.is_locked ? "Locked" : "Lock"} ${item.place.name}`}
        disabled={busy}
        onClick={() =>
          lock.mutate({
            itemId: item.id,
            plan_revision: edit.planRevision,
            is_locked: !item.is_locked,
          })
        }
      >
        <Icon aria-hidden="true" />
        {item.is_locked ? "Locked" : "Lock"}
      </Button>
      {lock.error && (
        <p role="alert" className="mt-2 text-sm text-destructive">
          {describeError(lock.error).what}. {describeError(lock.error).next}
        </p>
      )}
    </div>
  );
}
