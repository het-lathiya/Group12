import type { components } from "@/lib/api/schema";
import { formatDayDate } from "@/lib/format";

type SourceLabel = components["schemas"]["ItemCost"]["label"];

const LOOK: Record<SourceLabel, string> = {
  curated: "bg-success-soft text-success",
  estimate: "bg-warning-soft text-warning",
  unavailable: "bg-muted text-muted-foreground",
};

export type SourceBadgeProps = {
  label: SourceLabel;
  /** The date a curated fact was checked. API-24 does not send one yet (PD-IMP-309-1). */
  checkedOn?: string | null;
};

const badgeText = (label: SourceLabel, checkedOn?: string | null) => {
  if (label === "estimate") return "Estimate";
  if (label === "unavailable") return "Unavailable";
  return checkedOn
    ? `Curated, checked on ${formatDayDate(checkedOn)}`
    : "Curated";
};

/** The source of a price or an opening time, in words as well as colour (§7.8; guide §12). */
export function SourceBadge({ label, checkedOn }: SourceBadgeProps) {
  return (
    <span
      className={`inline-flex h-6 shrink-0 items-center rounded-full px-2 text-xs font-medium ${LOOK[label]}`}
    >
      {badgeText(label, checkedOn)}
    </span>
  );
}
