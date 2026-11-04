"use client";

import { useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Check,
  CheckCircle2,
  Circle,
  Loader2,
  OctagonX,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ErrorState } from "@/components/states/ErrorState";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";
import { queryKeys, useGeneration } from "@/lib/api/queries";
import type { components } from "@/lib/api/schema";

type Status = components["schemas"]["GenerationOut"]["status"];

/** IMD-12: the browser stops waiting 160 s after it started watching. */
export const GIVE_UP_AFTER_S = 160;

const STEP_LABELS: Partial<Record<Status, string>> = {
  queued: "Queued",
  running: "Running",
  validating: "Validating",
  repairing: "Repairing",
};

function formatElapsed(seconds: number): string {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

export type GenerationProgressProps = {
  generationId: string;
  /** Starts a new generation after a failure. */
  onRetry: () => void;
  retrying?: boolean;
};

/**
 * Generation status (§7.5.6, §7.6): polls API-23 with the §7.4 back-off, shows the steps and the
 * elapsed time, and announces each status change. On `completed` it opens the itinerary; on
 * `failed` it shows API-23's `failure_message` with "Try again"; after 160 s without an end it
 * offers a reload (IMD-12). Other `next_action` choices arrive with IMP-403.
 */
export function GenerationProgress({
  generationId,
  onRetry,
  retrying = false,
}: GenerationProgressProps) {
  const [elapsed, setElapsed] = useState(0);
  const gaveUp = elapsed >= GIVE_UP_AFTER_S;
  const generation = useGeneration(generationId, !gaveUp);
  const data = generation.data;
  const status = data?.status;
  const ended = status === "completed" || status === "failed";
  const timedOut = gaveUp && !ended;
  const tripId = data?.trip_id;
  const router = useRouter();
  const queryClient = useQueryClient();

  // Counted from when this page started watching, so the browser's clock never meets the server's.
  useEffect(() => {
    if (ended || gaveUp) return;
    const start = Date.now();
    const timer = setInterval(
      () => setElapsed(Math.floor((Date.now() - start) / 1000)),
      1000,
    );
    return () => clearInterval(timer);
  }, [ended, gaveUp]);

  useEffect(() => {
    if (status !== "completed" || !tripId) return;
    // §7.4: a new plan changes the trip, its itinerary, its estimate and the trip list.
    for (const queryKey of [
      queryKeys.trip(tripId),
      queryKeys.itinerary(tripId),
      queryKeys.costs(tripId),
      queryKeys.trips(),
    ]) {
      void queryClient.invalidateQueries({ queryKey });
    }
    router.push(`/trips/${tripId}/itinerary`);
  }, [status, tripId, queryClient, router]);

  if (generation.isError && !data) {
    const { error } = generation;
    return (
      <ErrorState
        title="The generation status could not be read"
        error={
          error instanceof ApiError
            ? error
            : {
                message:
                  "The server could not be reached. Check your connection and try again.",
              }
        }
        onRetry={() => void generation.refetch()}
      />
    );
  }

  const repaired =
    status === "repairing" || (data !== undefined && data.repair_attempts > 0);
  const steps: Status[] = ["queued", "running", "validating"];
  if (repaired) steps.push("repairing");
  const current =
    status === "completed" ? steps.length : status ? steps.indexOf(status) : -1;
  const stepState = (step: Status, index: number) =>
    index < current || (step === "repairing" && status === "validating")
      ? "done"
      : index === current
        ? "current"
        : "upcoming";

  return (
    <section
      aria-labelledby="generation-progress-title"
      className="rounded-xl border bg-card p-4 text-card-foreground shadow-xs sm:p-6"
    >
      <div className="flex items-baseline justify-between gap-4">
        <h2 id="generation-progress-title" className="text-base font-semibold">
          Progress
        </h2>
        <p className="text-sm text-muted-foreground tabular-nums">
          Elapsed {formatElapsed(elapsed)}
        </p>
      </div>

      {status !== "failed" && (
        <ol className="mt-4 flex flex-col gap-3">
          {steps.map((step, index) => {
            const state = stepState(step, index);
            return (
              <li
                key={step}
                aria-current={state === "current" ? "step" : undefined}
                className={
                  state === "upcoming"
                    ? "flex items-center gap-3 text-sm text-muted-foreground"
                    : state === "current"
                      ? "flex items-center gap-3 text-sm font-semibold text-primary"
                      : "flex items-center gap-3 text-sm text-foreground"
                }
              >
                {state === "done" && (
                  <Check aria-hidden="true" className="size-4 text-primary" />
                )}
                {state === "current" && (
                  <Loader2
                    aria-hidden="true"
                    className="size-4 motion-safe:animate-spin"
                  />
                )}
                {state === "upcoming" && (
                  <Circle aria-hidden="true" className="size-4" />
                )}
                {STEP_LABELS[step]}
                <span className="sr-only">
                  {state === "done"
                    ? "(done)"
                    : state === "current"
                      ? "(in progress)"
                      : "(not started)"}
                </span>
              </li>
            );
          })}
        </ol>
      )}

      {/* Announces status changes only, never the ticking counter (guide §16). */}
      <p aria-live="polite" className="sr-only">
        {status && !ended && !timedOut ? STEP_LABELS[status] : ""}
      </p>

      {status === "completed" && (
        <div
          role="status"
          className="mt-4 flex items-center gap-2 rounded-lg bg-success-soft px-3 py-2 text-sm font-medium text-success-foreground"
        >
          <CheckCircle2 aria-hidden="true" className="size-4 shrink-0" />
          Plan ready. Opening your itinerary.
        </div>
      )}

      {status === "failed" && (
        <div
          role="alert"
          className="mt-4 flex flex-col gap-3 rounded-lg bg-destructive/10 px-3 py-3 text-sm text-destructive sm:flex-row sm:items-center sm:justify-between"
        >
          <p className="flex items-center gap-2 font-medium">
            <OctagonX aria-hidden="true" className="size-4 shrink-0" />
            {data?.failure_message ?? "The plan could not be built."}
          </p>
          <Button
            variant="outline"
            onClick={onRetry}
            disabled={retrying}
            aria-busy={retrying}
          >
            {retrying && (
              <Loader2
                aria-hidden="true"
                className="motion-safe:animate-spin"
              />
            )}
            Try again
          </Button>
        </div>
      )}

      {timedOut && (
        <div
          role="alert"
          className="mt-4 flex flex-col gap-3 rounded-lg bg-warning-soft px-3 py-3 text-sm text-warning-foreground sm:flex-row sm:items-center sm:justify-between"
        >
          <p className="flex items-center gap-2 font-medium">
            <AlertTriangle aria-hidden="true" className="size-4 shrink-0" />
            Connection problem. Reload the page.
          </p>
          <Button variant="outline" onClick={() => window.location.reload()}>
            Reload
          </Button>
        </div>
      )}
    </section>
  );
}
