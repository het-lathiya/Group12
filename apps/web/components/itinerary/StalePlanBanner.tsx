import Link from "next/link";
import { Button } from "@/components/ui/button";
import { isEnabled } from "@/lib/flags";

/** The API's stale flag is authoritative (FR-011, IMD-175). */
export function StalePlanBanner({
  tripId,
  planStale,
}: {
  tripId: string;
  planStale: boolean;
}) {
  if (!planStale) return null;
  return (
    <section
      role="status"
      aria-label="Out-of-date plan"
      className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-warning bg-warning-soft p-4 text-warning"
    >
      <p>
        Trip settings changed after this plan was built. This plan is out of
        date.
      </p>
      {isEnabled("regeneration") && (
        <Button variant="outline" asChild>
          <Link href={`/trips/${tripId}/generate`}>Regenerate</Link>
        </Button>
      )}
    </section>
  );
}
