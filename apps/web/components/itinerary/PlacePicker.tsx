"use client";

import { useIsMutating, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";

import { PlaceCard } from "@/components/places/PlaceCard";
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
import { Input } from "@/components/ui/input";
import {
  editKey,
  CURRENT_VERSION,
  queryKeys,
  useAddItem,
  usePlaceSearch,
  useRemoveItem,
} from "@/lib/api/queries";
import type { components } from "@/lib/api/schema";

export function PlacePicker({
  tripId,
  destinationId,
  planRevision,
  dayNumbers,
}: {
  tripId: string;
  destinationId: string;
  planRevision: number;
  dayNumbers: number[];
}) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [day, setDay] = useState(dayNumbers[0] ?? 1);
  const places = usePlaceSearch(open ? destinationId : undefined, q);
  const add = useAddItem(tripId);
  const undo = useRemoveItem(tripId);
  const cache = useQueryClient();
  const busy = useIsMutating({ mutationKey: editKey(tripId) }) > 0;

  async function choose(place: components["schemas"]["PlaceSummary"]) {
    const previous = cache.getQueryData<components["schemas"]["ItineraryOut"]>(
      queryKeys.itinerary(tripId, CURRENT_VERSION),
    );
    const ids = new Set(
      previous?.days.flatMap((d) => d.items.map((item) => item.id)),
    );
    try {
      const result = await add.mutateAsync({
        plan_revision: planRevision,
        day_number: day,
        place_id: place.id,
      });
      const added = result.changed_days
        .flatMap((d) => d.items)
        .find((item) => item.place.id === place.id && !ids.has(item.id));
      setOpen(false);
      toast.success(`Added ${place.name}`, {
        action: added
          ? {
              label: "Undo",
              onClick: () => {
                undo.mutate({
                  itemId: added.id,
                  planRevision: result.plan_revision,
                });
              },
            }
          : undefined,
      });
    } catch {
      // The shared mutation reports stale edits; the dialog keeps other errors visible.
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline">Add a place</Button>
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Add a place</DialogTitle>
          <DialogDescription>
            Search this destination and choose a day. The plan is checked after
            adding.
          </DialogDescription>
        </DialogHeader>
        <label className="flex flex-col gap-2">
          Day
          <select
            aria-label="Day"
            value={day}
            onChange={(e) => setDay(Number(e.target.value))}
            className="min-h-10 rounded-lg border border-input bg-background px-3 text-base"
          >
            {dayNumbers.map((number) => (
              <option key={number} value={number}>
                Day {number}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-2">
          Search places
          <Input
            value={q}
            maxLength={80}
            onChange={(e) => setQ(e.target.value)}
          />
        </label>
        {q === "" ? (
          <p>Search by place name.</p>
        ) : places.isFetching ? (
          <p role="status">Searching places…</p>
        ) : places.error ? (
          <ErrorState
            error={places.error}
            onRetry={() => void places.refetch()}
          />
        ) : places.data?.items.length === 0 ? (
          <p>No places match this search. Try another name.</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {places.data?.items.map((place) => (
              <li key={place.id}>
                <PlaceCard place={place} />
                <Button
                  className="mt-2"
                  disabled={busy || places.isPlaceholderData}
                  onClick={() => void choose(place)}
                >
                  Add {place.name}
                </Button>
              </li>
            ))}
          </ul>
        )}
        {add.error && <ErrorState error={add.error} inline />}
      </DialogContent>
    </Dialog>
  );
}
