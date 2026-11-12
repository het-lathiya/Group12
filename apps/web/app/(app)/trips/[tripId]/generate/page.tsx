"use client";

import { Loader2, Sparkles } from "lucide-react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useRef, useState } from "react";

import { GenerationProgress } from "@/components/generation/GenerationProgress";
import { PrivacyNotice } from "@/components/generation/PrivacyNotice";
import {
  ErrorState,
  type ErrorStateError,
} from "@/components/states/ErrorState";
import { Button } from "@/components/ui/button";
import { ApiError, OFFLINE_MESSAGE } from "@/lib/api/client";
import { useProfile, useStartGeneration } from "@/lib/api/queries";

type StartError = { error: ErrorStateError; reload: boolean };

const OFFLINE: ErrorStateError = { message: OFFLINE_MESSAGE };

/**
 * /trips/[tripId]/generate (§7.5.6; FR-024, FR-025): starts one generation (API-22, mode `ai`),
 * keeps its id in `?generation=` so a reload resumes polling, and hands it to GenerationProgress.
 * A 409 GENERATION_IN_PROGRESS names the running job (IMD-119), which is then polled instead.
 * PrivacyNotice replaces the start button until the account has acknowledged it (IMD-24): API-03
 * says so, and a 422 on field `ai_notice` says so when that read has not answered. Acknowledging
 * starts the generation. A failed generation offers what API-23's next_action names, and a
 * provider quota pause offers "Build a rule-based plan" (mode rule_based, IMP-403).
 */
export default function GeneratePage() {
  const { tripId } = useParams<{ tripId: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const [generationId, setGenerationId] = useState(
    searchParams.get("generation"),
  );
  const [startError, setStartError] = useState<StartError | null>(null);
  const [noticeRefused, setNoticeRefused] = useState(false);
  const profile = useProfile();
  const start = useStartGeneration(tripId);
  // A second click lands before React re-renders the disabled button; the ref stops it.
  const inFlight = useRef(false);

  function watch(id: string) {
    setGenerationId(id);
    router.replace(`/trips/${tripId}/generate?generation=${id}`, {
      scroll: false,
    });
  }

  async function generate(mode: "ai" | "rule_based" = "ai") {
    if (inFlight.current) return;
    inFlight.current = true;
    setStartError(null);
    try {
      watch((await start.mutateAsync(mode)).id);
    } catch (error) {
      if (!(error instanceof ApiError)) {
        setStartError({ error: OFFLINE, reload: false });
      } else if (error.details.some((d) => d.field === "ai_notice")) {
        setNoticeRefused(true);
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
  const showNotice =
    generationId === null &&
    (noticeRefused || profile.data?.ai_notice_ack_at === null);

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

      {showNotice ? (
        <PrivacyNotice
          onAcknowledge={() => {
            setNoticeRefused(false);
            void generate();
          }}
        />
      ) : (
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
              <Loader2
                aria-hidden="true"
                className="motion-safe:animate-spin"
              />
            ) : (
              <Sparkles aria-hidden="true" />
            )}
            Generate with AI
          </Button>
        </section>
      )}

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
          onRuleBased={() => void generate("rule_based")}
          retrying={running}
        />
      )}
    </div>
  );
}
