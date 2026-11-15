"use client";

import { Loader2, RotateCw } from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useRef, useState, useSyncExternalStore } from "react";

import { GenerationProgress } from "@/components/generation/GenerationProgress";
import { PrivacyNotice } from "@/components/generation/PrivacyNotice";
import { ConfirmDialog } from "@/components/states/ConfirmDialog";
import { FallbackNotice } from "@/components/generation/FallbackNotice";
import { DayColumn } from "@/components/itinerary/DayColumn";
import { itemCardId } from "@/components/itinerary/ItineraryItemCard";
import { MoveDndContext } from "@/components/itinerary/MoveControls";
import { PlacePicker } from "@/components/itinerary/PlacePicker";
import { StalePlanBanner } from "@/components/itinerary/StalePlanBanner";
import { WarningsPanel } from "@/components/itinerary/WarningsPanel";
import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ApiError, OFFLINE_MESSAGE } from "@/lib/api/client";
import {
  useItinerary,
  usePreferences,
  useRegenerate,
  useTrip,
} from "@/lib/api/queries";
import type { components } from "@/lib/api/schema";
import { formatDayDate } from "@/lib/format";
import { isEnabled } from "@/lib/flags";

type Day = components["schemas"]["Day"];

// MapLibre needs the browser (WebGL), so the map loads on the client only (IMP-508).
const MapPanel = dynamic(
  () => import("@/components/map/MapPanel").then((m) => m.MapPanel),
  { ssr: false, loading: () => <Skeleton className="h-80 w-full xl:h-96" /> },
);

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
  edit: { tripId: string; planRevision: number; dayNumbers: number[] };
  /** The open day tab below 768 px; null opens the first day. */
  tab: string | null;
  onTab: (tab: string) => void;
  regeneration?: {
    onRegenerate: (dayNumber: number) => void;
    disabled: boolean;
  };
};

function Days(props: DaysProps) {
  return (
    <MoveDndContext
      tripId={props.edit.tripId}
      planRevision={props.edit.planRevision}
    >
      <DayLayout {...props} />
    </MoveDndContext>
  );
}

function DayLayout({ days, edit, tab, onTab, regeneration }: DaysProps) {
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
            <DayColumn
              day={day}
              edit={regeneration?.disabled ? undefined : edit}
              regeneration={regeneration}
            />
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
                  onTab(dayId(day)); // the map shows this day
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
            edit={regeneration?.disabled ? undefined : edit}
            regeneration={regeneration}
          />
        ))}
      </div>
    </div>
  );
}

/**
 * /trips/[tripId]/itinerary (§7.5.7): the saved days and items of API-24, shown as the server sent
 * them, with retime, remove and move on each item (IMP-408, IMP-409), with the plan checks (WarningsPanel, IMP-405) beside or above. API-24 answers 404 for a trip with no plan and for a foreign or
 * missing trip alike, so API-10 tells the two apart (§7.5: not-found screen for the second).
 */
export default function ItineraryPage() {
  const { tripId } = useParams<{ tripId: string }>();
  const itinerary = useItinerary(tripId);
  const regenerate = useRegenerate(tripId);
  const [generationId, setGenerationId] = useState<string | null>(null);
  const [targetDay, setTargetDay] = useState<number | undefined>();
  const [confirmAll, setConfirmAll] = useState(false);
  const [startError, setStartError] = useState<Error | null>(null);
  const [needsNotice, setNeedsNotice] = useState(false);
  const [regenerated, setRegenerated] = useState(false);
  const inFlight = useRef(false);
  const regenerationEnabled = isEnabled("regeneration");
  const regenerationBusy = regenerate.isPending || generationId !== null;
  const completed = useCallback(() => {
    setGenerationId(null);
    setRegenerated(true);
  }, []);

  async function startRegeneration(
    dayNumber?: number,
    mode: "ai" | "rule_based" = "ai",
  ) {
    if (inFlight.current || !itinerary.data) return;
    inFlight.current = true;
    setTargetDay(dayNumber);
    setStartError(null);
    setRegenerated(false);
    try {
      const generation = await regenerate.mutateAsync({
        dayNumber,
        plan_revision: itinerary.data.plan_revision,
        mode,
      });
      setGenerationId(generation.id);
    } catch (error) {
      if (
        error instanceof ApiError &&
        error.code === "GENERATION_IN_PROGRESS"
      ) {
        const active = error.details.find(
          (detail) => detail.field === "generation_id",
        );
        if (active) setGenerationId(active.message);
        else setStartError(error);
      } else if (
        error instanceof ApiError &&
        error.details.some((d) => d.field === "ai_notice")
      ) {
        setNeedsNotice(true);
      } else {
        setStartError(
          error instanceof Error ? error : new Error(OFFLINE_MESSAGE),
        );
      }
    } finally {
      inFlight.current = false;
    }
  }
  const noPlan =
    itinerary.error instanceof ApiError && itinerary.error.status === 404;
  const trip = useTrip(tripId, true);
  const failed = noPlan ? trip : itinerary;
  const preferences = usePreferences(itinerary.data ? tripId : undefined);
  const placeNames = Object.fromEntries(
    (preferences.data?.must_visit_places ?? []).map((p) => [p.id, p.name]),
  );
  const [tab, setTab] = useState<string | null>(null);
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  // Below 768 px the map sits behind a "Map" tab (§7.5.7 Map or List toggle).
  const [view, setView] = useState("list");
  const tabletUp = useTabletUp();
  const days = itinerary.data?.days ?? [];
  const mapDay = days.find((d) => dayId(d) === tab) ?? days[0];

  const dayOf = (itemId: string) =>
    days.find((d) => d.items.some((item) => item.id === itemId));

  /** A card was focused or clicked: its day goes on the map and its marker is highlighted. */
  function selectCard(target: EventTarget) {
    const card = (target as Element).closest?.('[id^="item-"]');
    const itemId = card?.id.slice("item-".length);
    const day = itemId ? dayOf(itemId) : undefined;
    if (!itemId || !day) return;
    setSelectedItemId(itemId);
    setTab(dayId(day));
  }

  function goToItem(itemId: string) {
    const day = dayOf(itemId);
    setView("list");
    if (day) setTab(dayId(day)); // below 768 px the item may sit in a closed tab
    // After the tab has rendered: bring the card into view and move focus to it.
    requestAnimationFrame(() => {
      const card = document.getElementById(itemCardId(itemId));
      card?.scrollIntoView?.({ block: "center" });
      card?.focus({ preventScroll: true });
    });
  }
  const { error } = failed;
  const map = mapDay && (
    <MapPanel
      items={mapDay.items}
      selectedItemId={selectedItemId}
      onSelectItem={goToItem}
    />
  );
  const daysView = itinerary.data && (
    <Days
      days={itinerary.data.days}
      edit={{
        tripId,
        planRevision: itinerary.data.plan_revision,
        dayNumbers: itinerary.data.days.map((d) => d.day_number),
      }}
      tab={tab}
      onTab={setTab}
      regeneration={
        regenerationEnabled
          ? {
              onRegenerate: (dayNumber) => void startRegeneration(dayNumber),
              disabled: regenerationBusy,
            }
          : undefined
      }
    />
  );
  const tripNotFound = error instanceof ApiError && error.status === 404;

  return (
    <div className="mx-auto flex w-full max-w-[1120px] flex-col gap-6 lg:gap-8">
      <h1 className="font-heading text-2xl font-semibold tracking-[-0.01em] sm:text-3xl">
        Your itinerary
      </h1>
      {regenerationEnabled && itinerary.data && (
        <>
          <Button
            variant="outline"
            className="min-h-touch self-start"
            disabled={regenerationBusy}
            aria-busy={regenerationBusy}
            onClick={() => setConfirmAll(true)}
          >
            {regenerationBusy ? (
              <Loader2
                aria-hidden="true"
                className="motion-safe:animate-spin"
              />
            ) : (
              <RotateCw aria-hidden="true" />
            )}
            Regenerate all
          </Button>
          <ConfirmDialog
            open={confirmAll}
            onOpenChange={setConfirmAll}
            title="Regenerate the whole itinerary?"
            description={
              isEnabled("versions")
                ? "Unlocked items will be rebuilt around your locked items. Your current plan is kept in Versions."
                : "Unlocked items will be rebuilt around your locked items. A backup of your current plan is kept."
            }
            confirmLabel="Regenerate all"
            onConfirm={() => void startRegeneration()}
          />
        </>
      )}
      {needsNotice && (
        <PrivacyNotice
          onAcknowledge={() => {
            setNeedsNotice(false);
            void startRegeneration(targetDay);
          }}
        />
      )}
      {startError && (
        <ErrorState
          title="Regeneration could not start"
          error={
            startError instanceof ApiError
              ? startError
              : { message: OFFLINE_MESSAGE }
          }
          onRetry={() => void startRegeneration(targetDay)}
        />
      )}
      {startError instanceof ApiError &&
        startError.code === "AI_QUOTA_REACHED" && (
          <Button
            variant="outline"
            disabled={regenerationBusy}
            onClick={() => void startRegeneration(targetDay, "rule_based")}
          >
            Build a rule-based plan
          </Button>
        )}
      {generationId && (
        <GenerationProgress
          key={generationId}
          generationId={generationId}
          onRetry={() => void startRegeneration(targetDay)}
          onRuleBased={() => void startRegeneration(targetDay, "rule_based")}
          retrying={regenerate.isPending}
          onComplete={completed}
        />
      )}
      {regenerated && (
        <p role="status" aria-live="polite">
          Regeneration complete.
        </p>
      )}
      {itinerary.data && (
        <StalePlanBanner
          tripId={tripId}
          planStale={itinerary.data.plan_stale}
        />
      )}
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
            <div className="flex flex-wrap gap-3">
              <Button asChild>
                <Link href={`/trips/${tripId}/generate`}>Generate</Link>
              </Button>
              {itinerary.data && trip.data && (
                <PlacePicker
                  tripId={tripId}
                  destinationId={trip.data.destination_id}
                  planRevision={itinerary.data.plan_revision}
                  dayNumbers={Array.from(
                    { length: trip.data.num_days },
                    (_, i) => i + 1,
                  )}
                />
              )}
            </div>
          }
        />
      ) : (
        itinerary.data && (
          <>
            {itinerary.data.source && (
              <FallbackNotice outcome={itinerary.data.source.outcome} />
            )}
            {trip.data && !regenerationBusy && (
              <PlacePicker
                tripId={tripId}
                destinationId={trip.data.destination_id}
                planRevision={itinerary.data.plan_revision}
                dayNumbers={Array.from(
                  { length: trip.data.num_days },
                  (_, i) => i + 1,
                )}
              />
            )}
            <div className="flex flex-col gap-6 xl:grid xl:grid-cols-[minmax(0,1fr)_320px] xl:items-start xl:gap-8">
              <div className="flex flex-col gap-6 xl:sticky xl:top-24 xl:order-2">
                {tabletUp && mapDay && (
                  <section aria-labelledby="map-heading">
                    <h2
                      id="map-heading"
                      className="mb-3 text-base font-semibold"
                    >
                      Map · Day {mapDay.day_number}
                    </h2>
                    {map}
                  </section>
                )}
                <WarningsPanel
                  findings={itinerary.data.findings}
                  placeNames={placeNames}
                  onGoToItem={goToItem}
                />
              </div>
              <div
                className="min-w-0 xl:order-1"
                onFocus={(event) => selectCard(event.target)}
                onClick={(event) => selectCard(event.target)}
              >
                {tabletUp ? (
                  daysView
                ) : (
                  <Tabs value={view} onValueChange={setView}>
                    <TabsList aria-label="Itinerary view">
                      <TabsTrigger value="list">List</TabsTrigger>
                      <TabsTrigger value="map">Map</TabsTrigger>
                    </TabsList>
                    <TabsContent value="list">{daysView}</TabsContent>
                    <TabsContent value="map">
                      {mapDay && (
                        <>
                          <h2 className="mb-3 text-base font-semibold">
                            Map · Day {mapDay.day_number}
                          </h2>
                          {map}
                        </>
                      )}
                    </TabsContent>
                  </Tabs>
                )}
              </div>
            </div>
          </>
        )
      )}
    </div>
  );
}
