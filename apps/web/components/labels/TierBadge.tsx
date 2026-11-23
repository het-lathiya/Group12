"use client";

import { BadgeCheck, Globe } from "lucide-react";

import type { AnyCitySchemas } from "@/lib/api/anyCityClient";
import { useDestinationDetail } from "@/lib/api/queries";
import { isEnabled } from "@/lib/flags";

export type DataTier = AnyCitySchemas["DestinationDetailOut"]["data_tier"];
export type Attribution = AnyCitySchemas["Attribution"];

/** The §9.1 hint, shown with the live tier badge (Amendment A2 §9.2). */
export const LIVE_HINT =
  "Live data comes from OpenStreetMap and Wikivoyage. It is not checked by our team: opening hours and prices are unknown.";

/**
 * The tier of a trip's destination from API-79 (Amendment A2 §9.2). With the switch OFF, or before
 * the destination is known, no request is made and the tier is undefined, so nothing new renders.
 */
export function useDestinationTier(destinationId: string | undefined): {
  tier: DataTier | undefined;
  isSample: boolean;
  live: boolean;
  attribution: Attribution[];
} {
  const on = isEnabled("any_city_mode");
  const detail = useDestinationDetail(on ? (destinationId ?? "") : "");
  const data = on ? detail.data : undefined;
  return {
    tier: data?.data_tier,
    isSample: data?.is_sample ?? false,
    live: data?.data_tier === "live",
    attribution: data?.attribution ?? [],
  };
}

const LOOK: Record<
  DataTier,
  { text: string; icon: typeof Globe; className: string }
> = {
  live: { text: "Live data", icon: Globe, className: "bg-info-soft text-info" },
  curated: {
    text: "Curated",
    icon: BadgeCheck,
    className: "bg-success-soft text-success",
  },
};

export type TierBadgeProps = {
  tier: DataTier | undefined;
  /** The SAMPLE fixture keeps its own label, so no tier badge is shown for it. */
  isSample?: boolean;
};

/**
 * The data tier of a destination in words, an icon and colour (Amendment A2 §9.2; guide §12):
 * "Live data" with the §9.1 hint, or "Curated". Renders nothing with `any_city_mode` OFF, for the
 * SAMPLE destination or while the tier is unknown.
 */
export function TierBadge({ tier, isSample = false }: TierBadgeProps) {
  if (!isEnabled("any_city_mode") || isSample || !tier) return null;
  const safe: DataTier = tier === "live" ? "live" : "curated";
  const { text, icon: Icon, className } = LOOK[safe];
  return (
    <div className="flex flex-col items-start gap-1">
      <span
        className={`inline-flex h-6 shrink-0 items-center gap-1 rounded-full px-2 text-xs font-medium ${className}`}
      >
        <Icon aria-hidden="true" className="size-3" />
        {text}
      </span>
      {safe === "live" && (
        <p className="text-sm break-words text-muted-foreground">{LIVE_HINT}</p>
      )}
    </div>
  );
}
