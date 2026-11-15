"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { LoadingSkeleton } from "@/components/states/LoadingSkeleton";
import { TripCard } from "@/components/trips/TripCard";
import { Button } from "@/components/ui/button";
import type { ApiError } from "@/lib/api/client";
import { useLatestItinerary, useTripList } from "@/lib/api/queries";

/**
 * /dashboard (§7.5.3; FR-012 to FR-015): New trip, Open latest (API-09) and the traveller's trips
 * (API-08) as TripCards with their actions; archived trips only behind Show archived (FR-012 AC3).
 */
export default function DashboardPage() {
  const router = useRouter();
  const latest = useLatestItinerary();
  const [showArchived, setShowArchived] = useState(false);
  const trips = useTripList(showArchived);
  const [noLatest, setNoLatest] = useState(false);
  const latestTripId = latest.data?.trip_id ?? null;

  function openLatest() {
    if (latestTripId) router.push(`/trips/${latestTripId}/itinerary`);
    else setNoLatest(true); // FR-014 AC2: offer generation, not an error
  }

  const drafts =
    trips.data?.items.filter((trip) => trip.status === "draft") ?? [];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-heading text-2xl font-semibold text-foreground">
          Your trips
        </h1>
        <div className="flex flex-wrap gap-3">
          <Button asChild>
            <Link href="/trips/new">New trip</Link>
          </Button>
          <Button
            variant={latestTripId ? "default" : "outline"}
            onClick={openLatest}
            disabled={latest.isPending}
            // Not transition-all: the opacity fade after re-enabling left the label below 4.5:1 for a frame.
            className="transition-colors"
          >
            Open latest
          </Button>
        </div>
      </div>
      {!!trips.data?.total && drafts.length === 0 && (
        <p className="text-sm text-muted-foreground">
          No drafts in progress. Open latest shows your newest itinerary.
        </p>
      )}

      {latest.isError && (
        <ErrorState
          inline
          title="Your latest itinerary could not be found"
          error={latest.error as ApiError}
          onRetry={() => void latest.refetch()}
        />
      )}
      {noLatest && !latestTripId && (
        <EmptyState
          title="No saved itinerary yet"
          description="Plan a trip and generate its itinerary; it will open from here."
          action={
            <Button asChild>
              <Link href="/trips/new">Plan a trip</Link>
            </Button>
          }
        />
      )}

      {trips.isPending && (
        <LoadingSkeleton shape="cards" count={3} label="Loading your trips" />
      )}
      {trips.isError && (
        <ErrorState
          title="Your trips could not be loaded"
          error={trips.error as ApiError}
          onRetry={() => void trips.refetch()}
        />
      )}
      {trips.data && (
        <section
          aria-labelledby="trips-heading"
          className="flex flex-col gap-3"
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 id="trips-heading" className="text-lg font-semibold">
              All trips
            </h2>
            <label className="flex min-h-touch items-center gap-2 text-sm">
              <input
                type="checkbox"
                className="size-4 accent-primary"
                checked={showArchived}
                onChange={(event) => setShowArchived(event.target.checked)}
              />
              Show archived
            </label>
          </div>
          {trips.data.total > 0 ? (
            <ul className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              {trips.data.items.map((trip) => (
                <TripCard key={trip.id} trip={trip} />
              ))}
            </ul>
          ) : showArchived ? (
            <p className="text-sm text-muted-foreground">
              No trips yet, archived or not.
            </p>
          ) : (
            <EmptyState
              headingLevel={3}
              title="No trips yet"
              description="Start with a destination, your dates and a budget. Archived trips appear with Show archived."
              action={
                <Button asChild>
                  <Link href="/trips/new">Create your first trip</Link>
                </Button>
              }
            />
          )}
        </section>
      )}
    </div>
  );
}
