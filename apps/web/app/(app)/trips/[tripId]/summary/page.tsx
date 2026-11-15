"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { LoadingSkeleton } from "@/components/states/LoadingSkeleton";
import { Button } from "@/components/ui/button";
import { PrintLayout } from "@/components/versions/PrintLayout";
import { ApiError } from "@/lib/api/client";
import { useSummary } from "@/lib/api/queries";

/** /trips/[tripId]/summary (§7.5, IMP-609): API-35 as a printable page; Print uses the browser. */
export default function SummaryPage() {
  const { tripId } = useParams<{ tripId: string }>();
  const summary = useSummary(tripId);
  const noPlan =
    summary.error instanceof ApiError && summary.error.status === 404;
  return (
    <div className="mx-auto flex w-full max-w-[1120px] flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3 print:hidden">
        <Link
          className="text-primary underline"
          href={`/trips/${tripId}/itinerary`}
        >
          Back to itinerary
        </Link>
        {summary.data && (
          <Button className="min-h-touch" onClick={() => window.print()}>
            Print
          </Button>
        )}
      </div>
      {noPlan ? (
        <EmptyState
          title="No itinerary yet"
          description="The summary appears once a plan has been generated."
          action={
            <Button asChild className="min-h-touch">
              <Link href={`/trips/${tripId}/generate`}>Generate a plan</Link>
            </Button>
          }
        />
      ) : summary.isPending ? (
        <LoadingSkeleton shape="text" count={6} label="Loading the summary" />
      ) : summary.error ? (
        <ErrorState
          error={summary.error}
          onRetry={() => void summary.refetch()}
        />
      ) : (
        <PrintLayout summary={summary.data} />
      )}
    </div>
  );
}
