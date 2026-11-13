"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { LoadingSkeleton } from "@/components/states/LoadingSkeleton";
import { Button } from "@/components/ui/button";
import type { ApiError } from "@/lib/api/client";
import { useLatestItinerary, useTrips } from "@/lib/api/queries";
import { formatDayDate } from "@/lib/format";

/**
 * /dashboard (§7.5.3; FR-013, FR-014): New trip, Open latest (API-09) and the traveller's drafts (API-08)
 * with Continue draft. The full trip list and its actions are IMP-602.
 */
export default function DashboardPage() {
  const router = useRouter();
  const latest = useLatestItinerary();
  const trips = useTrips();
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
      {trips.data?.total === 0 && (
        <EmptyState
          title="No trips yet"
          description="Start with a destination, your dates and a budget."
          action={
            <Button asChild>
              <Link href="/trips/new">Create a trip</Link>
            </Button>
          }
        />
      )}
      {drafts.length > 0 && (
        <section
          aria-labelledby="drafts-heading"
          className="flex flex-col gap-3"
        >
          <h2 id="drafts-heading" className="text-lg font-semibold">
            Drafts
          </h2>
          <ul className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            {drafts.map((trip) => (
              <li
                key={trip.id}
                className="flex flex-col gap-3 rounded-xl border bg-card p-4 text-card-foreground"
              >
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-semibold break-words">{trip.title}</h3>
                  <span className="inline-flex h-6 shrink-0 items-center rounded-full bg-muted px-2 text-xs font-medium text-muted-foreground">
                    Draft
                  </span>
                </div>
                <p className="text-sm text-muted-foreground">
                  {trip.destination.name} · {formatDayDate(trip.start_date)} to{" "}
                  {formatDayDate(trip.end_date)}
                </p>
                <div className="mt-auto flex flex-col gap-2 sm:flex-row">
                  <Button asChild className="w-full sm:w-auto">
                    <Link
                      href={`/trips/new?draft=${trip.id}`}
                      aria-label={`Continue draft: ${trip.title}`}
                    >
                      Continue draft
                    </Link>
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
