import { Info, Loader2, PauseCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ERROR_CATALOGUE } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";

type Outcome = components["schemas"]["ItinerarySource"]["outcome"];

// IMP-403 card step 4 (wording of the card and the run; §7.5.6 words it slightly differently,
// see PD-IMP-403-1). An info notice: the plan is usable, nothing failed for the traveller.
export const FALLBACK_TEXT =
  "Built by rules because the AI service was unavailable or failed checks";

const NOTICES: Partial<Record<Outcome, string>> = {
  fallback_rule_based: FALLBACK_TEXT,
  model_repaired: "Some details were adjusted",
};

/**
 * What the latest generation's outcome means for the plan (§6.4 Complete, §7.8). It sits above
 * the plan and never hides it, and it never carries an AI badge: a rule-based plan has no
 * AI-written text.
 */
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

const PAUSED = ERROR_CATALOGUE.AI_QUOTA_REACHED;

export type PausedAiNoticeProps = {
  /** Starts a rule-based generation (API-22, mode rule_based). */
  onBuildRuleBased: () => void;
  building?: boolean;
};

/**
 * FR-037 AC2: AI generation is paused (provider quota, IMD-44), with the one-click rule-based
 * option. The text is the error catalogue's (IMP-412).
 */
export function PausedAiNotice({
  onBuildRuleBased,
  building = false,
}: PausedAiNoticeProps) {
  return (
    <div
      role="status"
      className="mt-4 flex flex-col gap-3 rounded-lg bg-info-soft px-3 py-3 text-sm text-info sm:flex-row sm:items-center sm:justify-between"
    >
      <div className="flex items-start gap-2">
        <PauseCircle aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
        <div>
          <p className="font-medium">{PAUSED.what}</p>
          <p>{PAUSED.next}</p>
        </div>
      </div>
      <Button
        onClick={onBuildRuleBased}
        disabled={building}
        aria-busy={building}
      >
        {building && (
          <Loader2 aria-hidden="true" className="motion-safe:animate-spin" />
        )}
        Build a rule-based plan
      </Button>
    </div>
  );
}
