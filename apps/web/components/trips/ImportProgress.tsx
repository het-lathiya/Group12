"use client";

import { CircleAlert, CircleCheck, Loader2 } from "lucide-react";
import { useEffect, useRef } from "react";

import { Button } from "@/components/ui/button";
import type { LiveDestination } from "@/lib/api/anyCityClient";
import { ApiError, OFFLINE_MESSAGE } from "@/lib/api/client";
import { useImportStatus } from "@/lib/api/queries";

export const BUILDING_TEXT = "Building your city: finding places…";
export const FAILED_TEXT =
  "We could not reach the map data service. Try again in a few minutes.";
export const BUSY_TEXT = "The service is busy.";

export function readyText(placesUsable: number | null): string {
  return `Ready: ${placesUsable ?? 0} places from OpenStreetMap`;
}

export function notEnoughText(name: string, nearbyCity: string | null): string {
  const first = `We could not find enough places for ${name} yet.`;
  return nearbyCity
    ? `${first} Try ${nearbyCity}, a larger city nearby.`
    : first;
}

/**
 * The import of a live destination (Amendment A2 §9.1): polls API-78 from the resolve answer until
 * it ends, says where it is in words, and hands a completed destination to the trip form.
 */
export function ImportProgress({
  live,
  onReady,
  onSearchNearby,
  onRetry,
}: {
  /** The API-77 answer: the first state, shown until the first poll answers. */
  live: LiveDestination;
  onReady: (live: LiveDestination) => void;
  onSearchNearby: (city: string) => void;
  onRetry?: () => void;
}) {
  const status = useImportStatus(live.destination_id);
  const current = status.data ?? live;
  const { import: state } = current;

  const reported = useRef<string | null>(null);
  useEffect(() => {
    if (
      state.status === "completed" &&
      reported.current !== current.destination_id
    ) {
      reported.current = current.destination_id;
      onReady(current);
    }
  }, [state.status, current, onReady]);

  const pollFailed = status.isError && !status.data;
  const pollMessage =
    status.error instanceof ApiError ? status.error.message : OFFLINE_MESSAGE;

  const running = state.status === "queued" || state.status === "running";
  const Icon = running
    ? Loader2
    : state.status === "completed"
      ? CircleCheck
      : CircleAlert;

  return (
    <div className="grid gap-3 rounded-lg border bg-background p-4">
      <p
        role="status"
        aria-live="polite"
        className="flex items-start gap-2 text-sm font-medium"
      >
        <Icon
          aria-hidden="true"
          className={
            running
              ? "mt-0.5 size-4 shrink-0 motion-safe:animate-spin"
              : "mt-0.5 size-4 shrink-0"
          }
        />
        <span>
          {pollFailed
            ? pollMessage
            : running
              ? BUILDING_TEXT
              : state.status === "completed"
                ? readyText(state.places_usable)
                : state.status === "insufficient_data"
                  ? notEnoughText(current.name, state.nearby_city)
                  : state.failure_reason === "rate_limited"
                    ? `${FAILED_TEXT} ${BUSY_TEXT}`
                    : FAILED_TEXT}
        </span>
      </p>
      {!pollFailed &&
        state.status === "insufficient_data" &&
        state.nearby_city && (
          <div>
            <Button
              type="button"
              variant="outline"
              onClick={() => onSearchNearby(state.nearby_city ?? "")}
            >
              Search {state.nearby_city}
            </Button>
          </div>
        )}
      {!pollFailed && state.status === "failed" && onRetry && (
        <div>
          <Button type="button" variant="outline" onClick={onRetry}>
            Try again
          </Button>
        </div>
      )}
    </div>
  );
}
