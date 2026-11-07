import { Info } from "lucide-react";

import type { components } from "@/lib/api/schema";

type Outcome = components["schemas"]["ItinerarySource"]["outcome"];

const NOTICES: Partial<Record<Outcome, string>> = {
  fallback_rule_based:
    "Built by rules because the AI service was unavailable or its answer failed checks",
  model_repaired: "Some details were adjusted",
};

/** What the latest generation's outcome means for the plan (§6.4 Complete, §7.8). */
export function FallbackNotice({ outcome }: { outcome: Outcome }) {
  const notice = NOTICES[outcome];
  if (!notice) return null;
  return (
    <p className="flex items-start gap-2 rounded-xl bg-info-soft p-4 text-sm text-info">
      <Info aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
      {notice}
    </p>
  );
}
