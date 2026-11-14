"use client";

import { useIsMutating } from "@tanstack/react-query";
import { useState } from "react";
import { SourceBadge } from "@/components/labels/SourceBadge";
import { ErrorState } from "@/components/states/ErrorState";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  editKey,
  useAlternatives,
  useReplaceItem,
  useTrip,
} from "@/lib/api/queries";
import type { components } from "@/lib/api/schema";
import { isEnabled } from "@/lib/flags";

type Props = {
  item: components["schemas"]["Item"];
  tripId: string;
  planRevision: number;
};
export function AlternativesDialog(props: Props) {
  if (!isEnabled("alternatives") || props.item.is_locked) return null;
  return <EnabledAlternatives {...props} />;
}
function EnabledAlternatives({ item, tripId, planRevision }: Props) {
  const [open, setOpen] = useState(false);
  const alternatives = useAlternatives(item.id, open);
  const replace = useReplaceItem(tripId);
  const trip = useTrip(tripId, open && !item.cost?.currency);
  const currency =
    item.cost?.currency ??
    trip.data?.budget?.currency ??
    trip.data?.destination?.currency;
  const busy = useIsMutating({ mutationKey: editKey(tripId) }) > 0;
  async function apply(placeId: string) {
    try {
      await replace.mutateAsync({
        itemId: item.id,
        place_id: placeId,
        plan_revision: planRevision,
      });
      setOpen(false);
    } catch {
      // Keep the dialog and the shared mutation's error visible.
    }
  }
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          variant="outline"
          className="mt-3"
          aria-label={`Replace ${item.place.name}`}
        >
          Replace
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Alternatives for {item.place.name}</DialogTitle>
          <DialogDescription>
            Choose a ranked alternative. The day is checked again after
            applying.
          </DialogDescription>
        </DialogHeader>
        {alternatives.isPending ? (
          <p role="status">Loading alternatives…</p>
        ) : alternatives.error ? (
          <ErrorState
            error={alternatives.error}
            onRetry={() => void alternatives.refetch()}
          />
        ) : alternatives.data?.alternatives.length === 0 ? (
          <p>No alternative fits this slot</p>
        ) : (
          <ol className="flex flex-col gap-4">
            {alternatives.data?.alternatives.map((alternative) => (
              <li key={alternative.place.id} className="rounded-lg border p-3">
                <h3 className="font-semibold">{alternative.place.name}</h3>
                <p className="flex flex-wrap gap-2">
                  Price:{" "}
                  {alternative.place.price &&
                    alternative.place.price_label !== "unavailable" && (
                      <span>
                        {alternative.place.price.currency}{" "}
                        {alternative.place.price.min}–
                        {alternative.place.price.max ??
                          alternative.place.price.min}
                      </span>
                    )}
                  <SourceBadge label={alternative.place.price_label} />
                </p>
                <p className="tabular-nums">
                  Cost change:{" "}
                  {currency
                    ? `${currency} ${alternative.cost_delta.min}–${alternative.cost_delta.max}`
                    : "Unavailable"}
                </p>
                <p className="tabular-nums">
                  Time change: {alternative.time_delta_min} min
                </p>
                <p className="text-sm text-muted-foreground">
                  {alternative.reason}
                </p>
                <Button
                  className="mt-2"
                  disabled={busy || alternatives.isFetching}
                  onClick={() => void apply(alternative.place.id)}
                  aria-label={`Apply ${alternative.place.name}`}
                >
                  Apply
                </Button>
              </li>
            ))}
          </ol>
        )}
        {replace.error && <ErrorState error={replace.error} inline />}
      </DialogContent>
    </Dialog>
  );
}
