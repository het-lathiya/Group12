"use client";

import { Info } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { LiveAttribution } from "@/components/labels/LiveAttribution";
import { LiveTierProvider } from "@/components/labels/liveTier";
import { TierBadge, useDestinationTier } from "@/components/labels/TierBadge";
import { PlaceCard, type Place } from "@/components/places/PlaceCard";
import { PlaceDetailDrawer } from "@/components/places/PlaceDetailDrawer";
import {
  activeFilterNames,
  filtersFromParams,
  filtersToParams,
  filtersToQuery,
  NO_FILTERS,
  PlaceFilterBar,
  type PlaceFilters,
} from "@/components/places/PlaceFilterBar";
import { SavedPlacesPanel } from "@/components/places/SavedPlacesPanel";
import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { LoadingSkeleton } from "@/components/states/LoadingSkeleton";
import { Button } from "@/components/ui/button";
import { ApiError, OFFLINE_MESSAGE } from "@/lib/api/client";
import {
  EXPLORE_PAGE_SIZE,
  useFilteredPlacesPage,
  useSavedPlaces,
  useToggleSavedPlace,
  useTrip,
} from "@/lib/api/queries";
import { isEnabled } from "@/lib/flags";

const SAMPLE_NOTICE =
  "Sample data; prices and hours are estimates unless marked Curated.";
const ESTIMATE_NOTICE = "Prices and hours are estimates unless marked Curated.";

const shown = (error: unknown) =>
  error instanceof ApiError ? error : { message: OFFLINE_MESSAGE };

const usesEstimates = (places: Place[]) =>
  places.some(
    (p) =>
      p.price_label === "estimate" ||
      p.hours_label === "estimate" ||
      p.verification_status === "estimated",
  );

/**
 * /trips/[tripId]/explore (§7.5.5; FR-016): the active places of the trip's destination from
 * API-16, a page at a time, each with its source and verification status, and a notice when the
 * destination is the SAMPLE fixture or the listed facts are estimates (FR-016 AC3). PlaceFilterBar
 * narrows the list, with the filters in the URL; no match explains which to relax (FR-017); Details
 * opens PlaceDetailDrawer (API-17, FR-018). With the
 * `wishlist` switch on, each place has a Save toggle and the saved list is shown (FR-020, IMP-605).
 */
export default function ExplorePage() {
  const { tripId } = useParams<{ tripId: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const [offset, setOffset] = useState(0);
  const [detailId, setDetailId] = useState<string | null>(null);
  const filters = filtersFromParams(
    new URLSearchParams(searchParams.toString()),
  );
  const filterKey = filtersToParams(filters).toString();
  const trip = useTrip(tripId, true);
  const places = useFilteredPlacesPage(
    trip.data?.destination_id,
    filtersToQuery(filters),
    offset,
  );
  const relax = activeFilterNames(filters);
  // Amendment A2 §9.2: API-79 runs only with `any_city_mode` ON.
  const tier = useDestinationTier(trip.data?.destination_id);
  // IMP-604: the applied filters live in the URL, so a reload keeps them.
  function applyFilters(next: PlaceFilters) {
    const query = filtersToParams(next).toString();
    setOffset(0);
    router.replace(`/trips/${tripId}/explore${query ? `?${query}` : ""}`, {
      scroll: false,
    });
  }
  const wishlist = isEnabled("wishlist");
  const savedPlaces = useSavedPlaces(
    tripId,
    wishlist && trip.data !== undefined,
  );
  const toggleSaved = useToggleSavedPlace(tripId);
  const savedIds = new Set((savedPlaces.data ?? []).map((p) => p.id));
  const tripNotFound =
    trip.error instanceof ApiError && trip.error.status === 404;
  const page = places.data;
  const items: Place[] = page?.items ?? [];
  const notice = trip.data?.destination.is_sample
    ? SAMPLE_NOTICE
    : usesEstimates(items)
      ? ESTIMATE_NOTICE
      : null;
  const pageNumber = Math.floor(offset / EXPLORE_PAGE_SIZE) + 1;
  const pageCount = page
    ? Math.max(1, Math.ceil(page.total / EXPLORE_PAGE_SIZE))
    : 1;

  return (
    <LiveTierProvider value={tier.live}>
      <div className="mx-auto flex w-full max-w-[1120px] flex-col gap-6 lg:gap-8">
        <header className="flex flex-col gap-1">
          <h1 className="font-heading text-2xl font-semibold tracking-[-0.01em] sm:text-3xl">
            Explore places
          </h1>
          {trip.data && (
            <p className="text-sm text-muted-foreground">
              {trip.data.destination.name}
            </p>
          )}
          <TierBadge tier={tier.tier} isSample={tier.isSample} />
        </header>
        {notice && (
          <p className="flex items-start gap-2 rounded-xl bg-info-soft px-4 py-3 text-sm text-info">
            <Info aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
            {notice}
          </p>
        )}
        {trip.data && (
          <PlaceFilterBar
            key={filterKey}
            value={filters}
            currency={trip.data.destination.currency}
            onChange={applyFilters}
          />
        )}
        {tripNotFound ? (
          <EmptyState
            title="Trip not found"
            description="This trip does not exist or is not available to you."
            action={
              <Button asChild>
                <Link href="/dashboard">Back to dashboard</Link>
              </Button>
            }
          />
        ) : trip.error ? (
          <ErrorState
            title="This trip could not be loaded"
            error={shown(trip.error)}
            onRetry={() => void trip.refetch()}
          />
        ) : places.error ? (
          <ErrorState
            title="Places could not be loaded"
            error={shown(places.error)}
            onRetry={() => void places.refetch()}
          />
        ) : !page ? (
          <LoadingSkeleton shape="cards" count={6} label="Loading places" />
        ) : page.total === 0 && relax.length > 0 ? (
          <EmptyState
            title="No places match these filters"
            description={`Try relaxing these filters: ${relax.join(", ")}.`}
            action={
              <Button onClick={() => applyFilters(NO_FILTERS)}>
                Clear filters
              </Button>
            }
          />
        ) : page.total === 0 ? (
          <EmptyState
            title="No places yet"
            description="This destination has no places to show yet."
          />
        ) : (
          <>
            {wishlist && (
              <SavedPlacesPanel
                places={savedPlaces.data}
                failed={savedPlaces.isError}
                removing={toggleSaved.isPending}
                onRemove={(placeId) =>
                  toggleSaved.mutate({ placeId, save: false })
                }
              />
            )}
            <ul className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {items.map((place) => (
                <li key={place.id} className="flex flex-col gap-2">
                  {wishlist ? (
                    <PlaceCard
                      place={place}
                      saved={savedIds.has(place.id)}
                      saveDisabled={toggleSaved.isPending || !savedPlaces.data}
                      onToggleSave={() =>
                        toggleSaved.mutate({
                          placeId: place.id,
                          save: !savedIds.has(place.id),
                        })
                      }
                    />
                  ) : (
                    <PlaceCard place={place} />
                  )}
                  <Button
                    variant="outline"
                    className="min-h-touch"
                    aria-label={`Details of ${place.name}`}
                    onClick={() => setDetailId(place.id)}
                  >
                    Details
                  </Button>
                </li>
              ))}
            </ul>
            <nav
              aria-label="Pages"
              className="flex flex-wrap items-center justify-between gap-3"
            >
              <Button
                variant="outline"
                className="min-h-touch"
                disabled={offset === 0 || places.isFetching}
                onClick={() => setOffset(offset - EXPLORE_PAGE_SIZE)}
              >
                Previous
              </Button>
              <p
                aria-live="polite"
                className="text-sm text-muted-foreground tabular-nums"
              >
                Page {pageNumber} of {pageCount} · {page.total} places
              </p>
              <Button
                variant="outline"
                className="min-h-touch"
                disabled={
                  offset + EXPLORE_PAGE_SIZE >= page.total || places.isFetching
                }
                onClick={() => setOffset(offset + EXPLORE_PAGE_SIZE)}
              >
                Next
              </Button>
            </nav>
          </>
        )}
        <PlaceDetailDrawer
          placeId={detailId}
          onClose={() => setDetailId(null)}
        />
        <LiveAttribution tier={tier.tier} attribution={tier.attribution} />
      </div>
    </LiveTierProvider>
  );
}
