"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState, useSyncExternalStore } from "react";

import { FallbackNotice } from "@/components/generation/FallbackNotice";
import { DayColumn } from "@/components/itinerary/DayColumn";
import { itemCardId } from "@/components/itinerary/ItineraryItemCard";
import { WarningsPanel } from "@/components/itinerary/WarningsPanel";
import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ApiError } from "@/lib/api/client";
import { useItinerary, usePreferences, useTrip } from "@/lib/api/queries";
import type { components } from "@/lib/api/schema";
import { formatDayDate } from "@/lib/format";

type Day = components["schemas"]["Day"];

// §7.5.7: day tabs below 768 px; one layout is rendered, so ids and headings stay unique.
const TABLET = "(min-width: 768px)";

function useTabletUp(): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const query = window.matchMedia(TABLET);
      query.addEventListener("change", onChange);
      return () => query.removeEventListener("change", onChange);
    },
    () => window.matchMedia(TABLET).matches,
    () => true,
  );
}

const dayLabel = (day: Day) =>
  `Day ${day.day_number} · ${formatDayDate(day.date)}`;
const dayId = (day: Day) => `day-${day.day_number}`;

function DaySkeleton() {
  return (
    <div role="status" aria-busy="true" className="flex flex-col gap-6">
      <span className="sr-only">Loading your itinerary</span>
      {[0, 1].map((day) => (
        <div
          key={day}
          aria-hidden="true"
          className="rounded-xl border bg-card p-4 shadow-xs sm:p-6"
        >
          <Skeleton className="h-3 w-12" />
          <Skeleton className="mt-2 h-7 w-32" />
          <div className="mt-4 flex flex-col gap-3">
            {[0, 1, 2].map((item) => (
              <div key={item} className="grid grid-cols-[56px_1fr]">
                <Skeleton className="mt-3 h-4 w-10" />
                <Skeleton className="h-16 w-full" />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

type DaysProps = {
  days: Day[];
  edit: { tripId: string; planRevision: number };
  /** The open day tab below 768 px; null opens the first day. */
  tab: string | null;
  onTab: (tab: string) => void;
};

function Days({ days, edit, tab, onTab }: DaysProps) {
  const tabletUp = useTabletUp();

  if (!tabletUp) {
    return (
      <Tabs value={tab ?? dayId(days[0])} onValueChange={onTab}>
        <TabsList aria-label="Days">
          {days.map((day) => (
            <TabsTrigger key={day.day_number} value={dayId(day)}>
              Day {day.day_number}
            </TabsTrigger>
          ))}
        </TabsList>
        {days.map((day) => (
          <TabsContent key={day.day_number} value={dayId(day)}>
            <DayColumn day={day} edit={edit} />
          </TabsContent>
        ))}
      </Tabs>
    );
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[240px_1fr] lg:gap-8">
      <nav aria-label="Days" className="hidden lg:block">
        <ul className="sticky top-24 flex flex-col gap-1">
          {days.map((day) => (
            <li key={day.day_number}>
              <a
                href={`#${dayId(day)}`}
                onClick={(event) => {
                  event.preventDefault();
                  document.getElementById(dayId(day))?.focus();
                }}
                className="flex min-h-10 items-center rounded-lg px-3 text-sm font-medium text-foreground tabular-nums transition-colors outline-none hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              >
                {dayLabel(day)}
              </a>
            </li>
          ))}
        </ul>
      </nav>
      <div className="flex flex-col gap-6">
        {days.map((day) => (
          <DayColumn
            key={day.day_number}
            day={day}
            id={dayId(day)}
            edit={edit}
          />
        ))}
      </div>
    </div>
  );
}

/**
 * /trips/[tripId]/itinerary (§7.5.7): the saved days and items of API-24, shown as the server sent
 * them, with retime and remove on each item (IMP-408), with the plan checks (WarningsPanel, IMP-405) beside or above. API-24 answers 404 for a trip with no plan and for a foreign or
 * missing trip alike, so API-10 tells the two apart (§7.5: not-found screen for the second).
 */
export default function ItineraryPage() {
  const { tripId } = useParams<{ tripId: string }>();
  const itinerary = useItinerary(tripId);
  const noPlan =
    itinerary.error instanceof ApiError && itinerary.error.status === 404;
  const trip = useTrip(tripId, noPlan);
  const failed = noPlan ? trip : itinerary;
  const preferences = usePreferences(itinerary.data ? tripId : undefined);
  const placeNames = Object.fromEntries(
    (preferences.data?.must_visit_places ?? []).map((p) => [p.id, p.name]),
  );
  const [tab, setTab] = useState<string | null>(null);

  function goToItem(itemId: string) {
    const day = itinerary.data?.days.find((d) =>
      d.items.some((item) => item.id === itemId),
    );
    if (day) setTab(dayId(day)); // below 768 px the item may sit in a closed tab
    // After the tab has rendered: bring the card into view and move focus to it.
    requestAnimationFrame(() => {
      const card = document.getElementById(itemCardId(itemId));
      card?.scrollIntoView?.({ block: "center" });
      card?.focus({ preventScroll: true });
    });
  }
  const { error } = failed;
  const tripNotFound = error instanceof ApiError && error.status === 404;

  return (
    <div className="mx-auto flex w-full max-w-[1120px] flex-col gap-6 lg:gap-8">
      <h1 className="font-heading text-2xl font-semibold tracking-[-0.01em] sm:text-3xl">
        Your itinerary
      </h1>
      {itinerary.isPending || (noPlan && trip.isPending) ? (
        <DaySkeleton />
      ) : tripNotFound ? (
        <EmptyState
          title="Trip not found"
          description="This trip does not exist or is not available to you."
          action={
            <Button asChild>
              <Link href="/dashboard">Back to dashboard</Link>
            </Button>
          }
        />
      ) : error ? (
        <ErrorState
          title="Your itinerary could not be loaded"
          error={
            error instanceof ApiError
              ? error
              : {
                  message:
                    "The server could not be reached. Check your connection and try again.",
                }
          }
          onRetry={() => void failed.refetch()}
        />
      ) : noPlan || itinerary.data?.days.every((d) => !d.items.length) ? (
        <EmptyState
          title="Nothing planned yet"
          description="Generate a day-by-day plan for this trip."
          action={
            <Button asChild>
              <Link href={`/trips/${tripId}/generate`}>Generate</Link>
            </Button>
          }
        />
      ) : (
        itinerary.data && (
          <>
            {itinerary.data.source && (
              <FallbackNotice outcome={itinerary.data.source.outcome} />
            )}
            <div className="flex flex-col gap-6 xl:grid xl:grid-cols-[minmax(0,1fr)_320px] xl:items-start xl:gap-8">
              <div className="xl:sticky xl:top-24 xl:order-2">
                <WarningsPanel
                  findings={itinerary.data.findings}
                  placeNames={placeNames}
                  onGoToItem={goToItem}
                />
              </div>
              <div className="min-w-0 xl:order-1">
                <Days
                  days={itinerary.data.days}
                  edit={{
                    tripId,
                    planRevision: itinerary.data.plan_revision,
                  }}
                  tab={tab}
                  onTab={setTab}
                />
              </div>
            </div>
          </>
        )
      )}
    </div>
  );
}
