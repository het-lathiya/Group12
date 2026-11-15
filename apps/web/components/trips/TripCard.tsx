import Link from "next/link";

import { TripActionsMenu } from "@/components/trips/TripActionsMenu";
import { Button } from "@/components/ui/button";
import type { components } from "@/lib/api/schema";
import { formatDayDate } from "@/lib/format";
import { cn } from "@/lib/utils";

type Trip = components["schemas"]["TripOut"];

const STATUS: Record<Trip["status"], { label: string; className: string }> = {
  draft: { label: "Draft", className: "bg-muted text-muted-foreground" },
  ready: { label: "Ready", className: "bg-success-soft text-success" },
  archived: { label: "Archived", className: "bg-muted text-muted-foreground" },
};

/** The next step: finish the draft, open the plan or generate one; an archived trip without a
 * plan has none until it is restored (IMD-35). */
function primaryAction(trip: Trip): { href: string; label: string } | null {
  if (trip.has_itinerary)
    return { href: `/trips/${trip.id}/itinerary`, label: "Open itinerary" };
  if (trip.status === "draft")
    return { href: `/trips/new?draft=${trip.id}`, label: "Continue draft" };
  if (trip.status === "ready")
    return { href: `/trips/${trip.id}/generate`, label: "Generate plan" };
  return null;
}

/** One trip on the dashboard (FR-012 AC1): title, destination, dates, status and its actions. */
export function TripCard({ trip }: { trip: Trip }) {
  const status = STATUS[trip.status];
  const action = primaryAction(trip);
  return (
    <li className="flex flex-col gap-3 rounded-xl border bg-card p-4 text-card-foreground sm:p-6">
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-semibold break-words">{trip.title}</h3>
        <div className="flex shrink-0 items-center gap-1">
          <span
            className={cn(
              "inline-flex h-6 items-center rounded-full px-2 text-xs font-medium",
              status.className,
            )}
          >
            {status.label}
          </span>
          <TripActionsMenu trip={trip} />
        </div>
      </div>
      <p className="text-sm text-muted-foreground">
        {trip.destination.name} ·{" "}
        <span className="tabular-nums">
          {formatDayDate(trip.start_date)} to {formatDayDate(trip.end_date)}
        </span>
      </p>
      {action && (
        <div className="mt-auto flex flex-col gap-2 sm:flex-row">
          <Button
            asChild
            variant={trip.status === "archived" ? "outline" : "default"}
            className="w-full sm:w-auto"
          >
            <Link
              href={action.href}
              aria-label={`${action.label}: ${trip.title}`}
            >
              {action.label}
            </Link>
          </Button>
        </div>
      )}
    </li>
  );
}
