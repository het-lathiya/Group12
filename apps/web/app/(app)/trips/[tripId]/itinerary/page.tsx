"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useSyncExternalStore } from "react";

import { FallbackNotice } from "@/components/generation/FallbackNotice";
import { DayColumn } from "@/components/itinerary/DayColumn";
import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ApiError } from "@/lib/api/client";
import { useItinerary, useTrip } from "@/lib/api/queries";
import type { components } from "@/lib/api/schema";
import { formatDayDate } from "@/lib/format";

const MapPanel = dynamic(
  () => import("@/components/map/MapPanel").then((module) => module.MapPanel),
  { ssr: false, loading: () => <div role="status" className="h-[420px] rounded-xl border bg-muted">Loading map…</div> },
);

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

function Days({ days }: { days: Day[] }) {
  const tabletUp = useTabletUp();
  const [activeDayNumber, setActiveDayNumber] = useState(days[0].day_number);
  const [mobileView, setMobileView] = useState<"list" | "map">("list");
  const activeDay =
    days.find((day) => day.day_number === activeDayNumber) ?? days[0];

  if (!tabletUp) {
    return (
      <div className="flex flex-col gap-4">
        <div className="flex gap-2" aria-label="Itinerary view">
          <Button type="button" size="sm" variant={mobileView === "list" ? "default" : "outline"} aria-pressed={mobileView === "list"} onClick={() => setMobileView("list")}>List</Button>
          <Button type="button" size="sm" variant={mobileView === "map" ? "default" : "outline"} aria-pressed={mobileView === "map"} onClick={() => setMobileView("map")}>Map</Button>
        </div>
        {mobileView === "map" ? (
          <>
            <Tabs value={dayId(activeDay)} onValueChange={(value) => {
              const selected = days.find((day) => dayId(day) === value);
              if (selected) setActiveDayNumber(selected.day_number);
            }}>
              <TabsList aria-label="Map day">
                {days.map((day) => <TabsTrigger key={day.day_number} value={dayId(day)}>Day {day.day_number}</TabsTrigger>)}
              </TabsList>
            </Tabs>
            <MapPanel items={activeDay.items} />
          </>
        ) : (
          <Tabs value={dayId(activeDay)} onValueChange={(value) => {
            const selected = days.find((day) => dayId(day) === value);
            if (selected) setActiveDayNumber(selected.day_number);
          }}>
            <TabsList aria-label="Days">
              {days.map((day) => <TabsTrigger key={day.day_number} value={dayId(day)}>Day {day.day_number}</TabsTrigger>)}
            </TabsList>
            {days.map((day) => <TabsContent key={day.day_number} value={dayId(day)}><DayColumn day={day} /></TabsContent>)}
          </Tabs>
        )}
      </div>
    );
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[200px_minmax(0,1fr)_minmax(320px,420px)] lg:gap-6">
      <nav aria-label="Days" className="hidden lg:block">
        <ul className="sticky top-24 flex flex-col gap-1">
          {days.map((day) => (
            <li key={day.day_number}>
              <button type="button" aria-current={activeDayNumber === day.day_number ? "date" : undefined} onClick={() => {
                setActiveDayNumber(day.day_number);
                document.getElementById(dayId(day))?.focus();
              }} className="flex min-h-10 w-full items-center rounded-lg px-3 text-left text-sm font-medium text-foreground tabular-nums transition-colors outline-none hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2">
                {dayLabel(day)}
              </button>
            </li>
          ))}
        </ul>
      </nav>
      <div className="flex flex-col gap-6">
        {days.map((day) => (
          <div key={day.day_number} onFocusCapture={() => setActiveDayNumber(day.day_number)}>
            <DayColumn day={day} id={dayId(day)} />
          </div>
        ))}
      </div>
      <aside className="hidden lg:block">
        <div className="sticky top-24">
          <h2 className="mb-3 text-lg font-semibold">Day {activeDay.day_number} map</h2>
          <MapPanel items={activeDay.items} />
        </div>
      </aside>
    </div>
  );
}

/**
 * /trips/[tripId]/itinerary (§7.5.7), read-only until IMP-408: the saved days and items of API-24,
 * shown as the server sent them. API-24 answers 404 for a trip with no plan and for a foreign or
 * missing trip alike, so API-10 tells the two apart (§7.5: not-found screen for the second).
 */
export default function ItineraryPage() {
  const { tripId } = useParams<{ tripId: string }>();
  const itinerary = useItinerary(tripId);
  const noPlan =
    itinerary.error instanceof ApiError && itinerary.error.status === 404;
  const trip = useTrip(tripId, noPlan);
  const failed = noPlan ? trip : itinerary;
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
            <Days days={itinerary.data.days} />
          </>
        )
      )}
    </div>
  );
}
