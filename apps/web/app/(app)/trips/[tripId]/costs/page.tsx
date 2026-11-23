"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { BudgetAlert } from "@/components/costs/BudgetAlert";
import { BudgetSettingsForm } from "@/components/costs/BudgetSettingsForm";
import { CostBreakdown } from "@/components/costs/CostBreakdown";
import { LiveAttribution } from "@/components/labels/LiveAttribution";
import { LiveTierProvider } from "@/components/labels/liveTier";
import { SourceBadge } from "@/components/labels/SourceBadge";
import { TierBadge, useDestinationTier } from "@/components/labels/TierBadge";
import { ErrorState } from "@/components/states/ErrorState";
import { LoadingSkeleton } from "@/components/states/LoadingSkeleton";
import { useCosts, useTrip } from "@/lib/api/queries";
import { isEnabled } from "@/lib/flags";

export default function CostsPage() {
  const { tripId } = useParams<{ tripId: string }>();
  const costs = useCosts(tripId);
  const data = costs.data;
  // Amendment A2 §9.2: the trip and API-79 are read only with `any_city_mode` ON.
  const trip = useTrip(tripId, isEnabled("any_city_mode"));
  const tier = useDestinationTier(trip.data?.destination_id);
  return (
    <LiveTierProvider value={tier.live}>
      <div className="mx-auto flex w-full max-w-[1120px] flex-col gap-6">
        <header>
          <h1 className="text-2xl font-semibold">Trip costs</h1>
          <TierBadge tier={tier.tier} isSample={tier.isSample} />
          <Link
            className="text-primary underline"
            href={`/trips/${tripId}/itinerary`}
          >
            Back to itinerary
          </Link>
        </header>
        {costs.isPending ? (
          <LoadingSkeleton shape="text" count={6} label="Loading costs" />
        ) : costs.error ? (
          <ErrorState
            error={costs.error}
            onRetry={() => void costs.refetch()}
          />
        ) : (
          data && (
            <>
              <section
                aria-labelledby="cost-summary"
                className="rounded-xl border bg-card p-4 shadow-xs sm:p-6"
              >
                <h2 id="cost-summary" className="text-xl font-semibold">
                  Planning total
                </h2>
                <p className="my-2 flex flex-wrap items-center gap-2 text-xl tabular-nums">
                  {!data.complete && data.planning_total === "0.00"
                    ? "Cost not available yet"
                    : `${data.currency} ${data.planning_total}`}
                  <SourceBadge label="estimate" />
                </p>
                <p>
                  Estimate range: {data.currency} {data.estimate.min}–
                  {data.estimate.max} <SourceBadge label="estimate" />
                </p>
                <p>
                  About per traveller: {data.currency}{" "}
                  {data.per_traveller.largest_share}{" "}
                  <SourceBadge label="estimate" />
                </p>
                {isEnabled("contingency") && (
                  <p>
                    Contingency ({data.contingency.pct}%): {data.currency}{" "}
                    {data.contingency.amount} <SourceBadge label="estimate" />
                  </p>
                )}
                {!data.complete && (
                  <p role="status" className="mt-2 text-warning">
                    Some costs are unavailable or estimated. Treat this total as
                    incomplete.
                  </p>
                )}
                {data.incomplete_items.length > 0 && (
                  <p className="text-sm">
                    {data.incomplete_items.length} items have unavailable costs.
                  </p>
                )}
                {data.budget.amount ? (
                  <p>
                    Your budget: {data.currency} {data.budget.amount}{" "}
                    <SourceBadge label="traveller_input" />
                  </p>
                ) : (
                  <p>Set an allowance to see the remaining budget.</p>
                )}
                <BudgetAlert alerts={data.alerts} />
              </section>
              <CostBreakdown costs={data} />
              <section aria-labelledby="budget-settings">
                <h2 id="budget-settings" className="mb-3 text-xl font-semibold">
                  Your allowances
                </h2>
                <BudgetSettingsForm tripId={tripId} currency={data.currency} />
              </section>
            </>
          )
        )}
        <LiveAttribution tier={tier.tier} attribution={tier.attribution} />
      </div>
    </LiveTierProvider>
  );
}
