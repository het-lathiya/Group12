"use client";

import { Loader2, Sparkles } from "lucide-react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useRef, useState } from "react";

import { GenerationProgress } from "@/components/generation/GenerationProgress";
import {
  ErrorState,
  type ErrorStateError,
} from "@/components/states/ErrorState";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";
import { useStartGeneration } from "@/lib/api/queries";

type StartError = { error: ErrorStateError; reload: boolean };

const OFFLINE: ErrorStateError = {
  message:
    "The server could not be reached. Check your connection and try again.",
};

/**
 * /trips/[tripId]/generate (§7.5.6; FR-024, FR-025): starts one generation (API-22, mode `ai`),
 * keeps its id in `?generation=` so a reload resumes polling, and hands it to GenerationProgress.
 * A 409 GENERATION_IN_PROGRESS names the running job (IMD-119), which is then polled instead.
 * The privacy notice and "Build without AI" arrive with IMP-305 and IMP-402.
 */
export default function GeneratePage() {
  const { tripId } = useParams<{ tripId: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const [generationId, setGenerationId] = useState(
    searchParams.get("generation"),
  );
  const [startError, setStartError] = useState<StartError | null>(null);
  const start = useStartGeneration(tripId);
  // A second click lands before React re-renders the disabled button; the ref stops it.
  const inFlight = useRef(false);

  function watch(id: string) {
    setGenerationId(id);
    router.replace(`/trips/${tripId}/generate?generation=${id}`, {
      scroll: false,
    });
  }

  async function generate() {
    if (inFlight.current) return;
    inFlight.current = true;
    setStartError(null);
    try {
      watch((await start.mutateAsync()).id);
    } catch (error) {
      if (!(error instanceof ApiError)) {
        setStartError({ error: OFFLINE, reload: false });
      } else if (error.code === "GENERATION_IN_PROGRESS") {
        const active = error.details.find(
          (detail) => detail.field === "generation_id",
        );
        if (active) watch(active.message);
        else setStartError({ error, reload: true });
      } else {
        setStartError({ error, reload: false });
      }
    } finally {
      inFlight.current = false;
    }
  }

  const running = start.isPending;

  return (
    <div className="mx-auto flex w-full max-w-[720px] flex-col gap-6">
      <header>
        <h1 className="font-heading text-2xl font-semibold tracking-[-0.01em] sm:text-3xl">
          Generate your itinerary
        </h1>
        <p className="mt-2 text-muted-foreground">
          We build a day-by-day plan from your trip details and preferences.
        </p>
      </header>

      <section
        aria-label="Start"
        className="rounded-xl border bg-card p-4 text-card-foreground shadow-xs sm:p-6"
      >
        <Button
          onClick={() => void generate()}
          disabled={running || generationId !== null}
          aria-busy={running}
        >
          {running ? (
            <Loader2 aria-hidden="true" className="motion-safe:animate-spin" />
          ) : (
            <Sparkles aria-hidden="true" />
          )}
          Generate with AI
        </Button>
      </section>

      {startError && (
        <ErrorState
          title="The generation could not start"
          error={startError.error}
          onRetry={
            startError.reload
              ? () => window.location.reload()
              : () => void generate()
          }
          retryLabel={startError.reload ? "Reload" : "Try again"}
        />
      )}

      {generationId && (
        <GenerationProgress
          key={generationId}
          generationId={generationId}
          onRetry={() => void generate()}
          retrying={running}
        />
      )}
    </div>
  );
}
