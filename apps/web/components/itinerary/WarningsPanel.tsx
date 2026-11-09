import Link from "next/link";
import { AlertCircle, AlertTriangle, Info } from "lucide-react";

import type { components } from "@/lib/api/schema";

type Finding = components["schemas"]["Finding"];

const SEVERITIES = [
  { value: "error", label: "Errors", Icon: AlertCircle, className: "text-destructive" },
  { value: "warning", label: "Warnings", Icon: AlertTriangle, className: "text-warning" },
  { value: "info", label: "Information", Icon: Info, className: "text-info" },
] as const;

/** Findings returned with API-24, grouped by severity and then itinerary day. */
export function WarningsPanel({ findings }: { findings: Finding[] }) {
  if (findings.length === 0) return null;

  return (
    <section
      aria-labelledby="itinerary-findings-title"
      aria-live="polite"
      aria-atomic="false"
      className="rounded-xl border bg-card p-4 sm:p-5"
    >
      <h2 id="itinerary-findings-title" className="text-lg font-semibold">
        Plan checks
      </h2>
      <div className="mt-3 flex flex-col gap-5">
        {SEVERITIES.map(({ value, label, Icon, className }) => {
          const group = findings.filter((finding) => finding.severity === value);
          if (group.length === 0) return null;

          const byDay = new Map<number | null, Finding[]>();
          for (const finding of group) {
            const day = finding.day_number;
            byDay.set(day, [...(byDay.get(day) ?? []), finding]);
          }

          return (
            <section key={value} aria-label={label}>
              <h3 className="flex items-center gap-2 text-sm font-semibold">
                <Icon aria-hidden="true" className={`size-4 ${className}`} />
                {label} <span className="text-muted-foreground">({group.length})</span>
              </h3>
              <div className="mt-2 flex flex-col gap-3">
                {[...byDay.entries()]
                  .sort(([a], [b]) => (a ?? Number.MAX_SAFE_INTEGER) - (b ?? Number.MAX_SAFE_INTEGER))
                  .map(([day, dayFindings]) => (
                    <div key={day ?? "trip"}>
                      <h4 className="text-xs font-medium text-muted-foreground">
                        {day === null ? "Trip-wide" : `Day ${day}`}
                      </h4>
                      <ul className="mt-1 flex flex-col gap-2">
                        {dayFindings.map((finding) => (
                          <li key={finding.id} className="rounded-lg bg-muted/50 p-3">
                            <p className="text-sm font-medium">{finding.message}</p>
                            {finding.suggested_fix && (
                              <p className="mt-1 text-sm text-muted-foreground">
                                Suggested fix: {finding.suggested_fix}
                              </p>
                            )}
                            {finding.item_id && (
                              <Link
                                href={`#item-${finding.item_id}`}
                                className="mt-2 inline-flex min-h-touch items-center text-sm font-medium text-primary underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                              >
                                Go to item
                              </Link>
                            )}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
              </div>
            </section>
          );
        })}
      </div>
    </section>
  );
}
