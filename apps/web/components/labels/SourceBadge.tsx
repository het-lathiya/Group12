import type { components } from "@/lib/api/schema";
import { formatDayDate } from "@/lib/format";

type SourceLabel = components["schemas"]["SourceLabel"];

// FR-076: exactly these three; nothing in the MVP is live or verified.
const LOOK: Record<SourceLabel, { text: string; className: string }> = {
  curated: { text: "Curated", className: "bg-primary/10 text-primary" },
  estimate: { text: "Estimate", className: "bg-warning-soft text-warning" },
  unavailable: {
    text: "Unavailable",
    className: "bg-muted text-muted-foreground",
  },
};

export type SourceBadgeProps = {
  label: SourceLabel;
  /** `price` (default) or `hours`: only curated opening hours carry a date (IMD-130). */
  kind?: "price" | "hours";
  /** The date curated opening hours were checked (`hours_checked_on`). */
  checkedOn?: string | null;
};

/** The source of a price or an opening time, in words as well as colour (§7.8; guide §12). */
export function SourceBadge({
  label,
  kind = "price",
  checkedOn,
}: SourceBadgeProps) {
  // A value outside the contract (never expected) is shown as Unavailable, never as itself.
  const safe: SourceLabel = Object.hasOwn(LOOK, label) ? label : "unavailable";
  const { text, className } = LOOK[safe];
  const dated = safe === "curated" && kind === "hours" && checkedOn;
  return (
    <span
      className={`inline-flex h-6 shrink-0 items-center rounded-xl px-2 text-xs font-medium ${className}`}
    >
      {dated ? `${text}, checked on ${formatDayDate(checkedOn)}` : text}
    </span>
  );
}
