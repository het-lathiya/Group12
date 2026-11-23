"use client";

import { ExternalLink } from "lucide-react";
import { useId } from "react";

import { type Attribution, type DataTier } from "@/components/labels/TierBadge";
import { isEnabled } from "@/lib/flags";

export const CC_BY_SA_URL = "https://creativecommons.org/licenses/by-sa/4.0/";

const LINK =
  "inline-flex min-h-touch items-center gap-1 rounded-sm font-medium text-primary underline underline-offset-4 outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 sm:min-h-0";

/** Only an https URL becomes a link; anything else is left out. */
function safeUrl(url: string | null): string | null {
  if (!url) return null;
  try {
    return new URL(url).protocol === "https:" ? url : null;
  } catch {
    return null;
  }
}

const isCcBySa = (licence: string) => /cc[\s-]?by[\s-]?sa/i.test(licence);

function OutLink({ href, children }: { href: string; children: string }) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className={LINK}>
      {children}
      <ExternalLink aria-hidden="true" className="size-3.5 shrink-0" />
      <span className="sr-only">(opens in a new tab)</span>
    </a>
  );
}

export type LiveAttributionProps = {
  tier: DataTier | undefined;
  attribution: Attribution[];
};

/**
 * The footer of explore, itinerary and costs for a live destination (Amendment A2 §9.2, §9.3, §10):
 * each attribution text of API-79 verbatim, with its source link and, for CC BY-SA text, the
 * licence link. Renders nothing with `any_city_mode` OFF or for a curated or SAMPLE destination.
 */
export function LiveAttribution({ tier, attribution }: LiveAttributionProps) {
  const headingId = useId();
  if (!isEnabled("any_city_mode") || tier !== "live") return null;
  if (attribution.length === 0) return null;
  return (
    <footer
      aria-labelledby={headingId}
      className="flex flex-col gap-2 border-t pt-4 text-sm text-muted-foreground"
    >
      <h2 id={headingId} className="text-sm font-semibold text-foreground">
        Data sources
      </h2>
      <ul className="flex flex-col gap-2">
        {attribution.map((row, index) => {
          const url = safeUrl(row.url);
          return (
            <li
              key={`${row.source_name}-${index}`}
              className="flex flex-col gap-1 break-words"
            >
              <span>
                {row.attribution_text ?? `${row.source_name} (${row.licence})`}
              </span>
              {(url || isCcBySa(row.licence)) && (
                <span className="flex flex-wrap gap-x-4 gap-y-1">
                  {url && (
                    <OutLink href={url}>{`${row.source_name} source`}</OutLink>
                  )}
                  {isCcBySa(row.licence) && (
                    <OutLink href={CC_BY_SA_URL}>CC BY-SA 4.0 licence</OutLink>
                  )}
                </span>
              )}
            </li>
          );
        })}
      </ul>
    </footer>
  );
}
