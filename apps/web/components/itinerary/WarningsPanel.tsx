"use client";

import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  Info,
  MapPin,
  OctagonX,
  type LucideIcon,
} from "lucide-react";
import { useState } from "react";

import { useLiveTier } from "@/components/labels/liveTier";
import { Button } from "@/components/ui/button";
import type { components } from "@/lib/api/schema";

type Finding = components["schemas"]["Finding"];
type Severity = Finding["severity"];

const SEVERITIES: Severity[] = ["error", "warning", "info"];

// Guide §2, §12: text, icon and colour together, never colour alone.
const BADGES: Record<
  Severity,
  { label: string; icon: LucideIcon; className: string }
> = {
  error: {
    label: "Error",
    icon: OctagonX,
    className: "bg-destructive/10 text-destructive",
  },
  warning: {
    label: "Warning",
    icon: AlertTriangle,
    className: "bg-warning-soft text-warning-foreground",
  },
  info: { label: "Info", icon: Info, className: "bg-info-soft text-info" },
};

const HEADINGS: Record<Severity, string> = {
  error: "Errors",
  warning: "Warnings",
  info: "Infos",
};

const NOUNS: Record<Severity, [string, string]> = {
  error: ["error", "errors"],
  warning: ["warning", "warnings"],
  info: ["info", "info"],
};

/** "2 errors · 3 warnings": the non-zero counts, in severity order. */
export function countLabel(findings: Finding[]): string {
  return SEVERITIES.map((severity) => {
    const count = findings.filter((f) => f.severity === severity).length;
    return count ? `${count} ${NOUNS[severity][count === 1 ? 0 : 1]}` : "";
  })
    .filter(Boolean)
    .join(" · ");
}

/**
 * Amendment A2 §6.6, §9.2: on a live destination every stop carries HOURS_UNVERIFIED, so those rows
 * become one whole-trip line, "Opening hours unknown for N stops". The severity stays info.
 */
export function groupLiveHours(findings: Finding[]): Finding[] {
  const hours = findings.filter((f) => f.code === "HOURS_UNVERIFIED");
  if (hours.length === 0) return findings;
  const grouped: Finding = {
    id: "hours-unverified-group",
    code: "HOURS_UNVERIFIED",
    severity: "info",
    day_number: null,
    item_id: null,
    place_id: null,
    message: `Opening hours unknown for ${hours.length} ${hours.length === 1 ? "stop" : "stops"}`,
    suggested_fix: null,
  };
  return [...findings.filter((f) => f.code !== "HOURS_UNVERIFIED"), grouped];
}

function byDay(findings: Finding[]): [number | null, Finding[]][] {
  const groups = new Map<number | null, Finding[]>();
  for (const finding of findings) {
    groups.set(finding.day_number, [
      ...(groups.get(finding.day_number) ?? []),
      finding,
    ]);
  }
  // Findings of the whole trip (no day) first, then the days in order.
  return [...groups].sort(([a], [b]) => (a ?? 0) - (b ?? 0));
}

function SeverityBadge({ severity }: { severity: Severity }) {
  const { label, icon: Icon, className } = BADGES[severity];
  return (
    <span
      className={`inline-flex h-6 shrink-0 items-center gap-1 rounded-full px-2 text-xs font-medium ${className}`}
    >
      <Icon aria-hidden="true" className="size-3" />
      {label}
    </span>
  );
}

export type WarningsPanelProps = {
  findings: Finding[];
  /** Names of places that are not in the plan (MUST_VISIT_MISSING), by place id. */
  placeNames?: Record<string, string>;
  /** Scrolls to the item's card and moves focus to it. */
  onGoToItem: (itemId: string) => void;
};

/**
 * "Plan checks" (§7, FR-056; IMP-405): API-24's findings grouped by severity, then by day, each
 * with its cause and suggested fix. A finding about an item links to its card; MUST_VISIT_MISSING
 * has no item, so it names the place instead. Beside the days from 1280 px; above them, and
 * collapsible, on smaller screens (collapsed when only info rows remain). Changes are announced in
 * a polite live region.
 */
export function WarningsPanel({
  findings: allFindings,
  placeNames = {},
  onGoToItem,
}: WarningsPanelProps) {
  const live = useLiveTier();
  const findings = live ? groupLiveHours(allFindings) : allFindings;
  const onlyInfo = findings.every((f) => f.severity === "info");
  const [open, setOpen] = useState(!onlyInfo);
  const counts = countLabel(findings);
  const summary = counts || "No issues found";

  return (
    <section
      aria-labelledby="plan-checks-title"
      className="rounded-xl border bg-card p-4 text-card-foreground shadow-xs sm:p-6"
    >
      <div className="flex items-center justify-between gap-3">
        <h2 id="plan-checks-title" className="flex flex-col">
          <span className="text-base font-semibold">Plan checks</span>
          <span className="text-sm font-normal text-muted-foreground">
            {summary}
          </span>
        </h2>
        <Button
          variant="ghost"
          size="sm"
          className="xl:hidden"
          aria-expanded={open}
          aria-controls="plan-checks-list"
          onClick={() => setOpen(!open)}
        >
          <ChevronDown
            aria-hidden="true"
            className={`transition-transform duration-200 motion-reduce:transition-none ${open ? "rotate-180" : ""}`}
          />
          {open ? "Hide" : "Show"}
        </Button>
      </div>

      <p aria-live="polite" className="sr-only">
        Plan checks: {summary}
      </p>

      <div
        id="plan-checks-list"
        className={open ? "mt-4" : "mt-4 hidden xl:block"}
      >
        {findings.length === 0 ? (
          <p className="flex items-center gap-2 text-sm text-success-foreground">
            <CheckCircle2 aria-hidden="true" className="size-4 shrink-0" />
            No issues found
          </p>
        ) : (
          <div className="flex flex-col gap-5">
            {SEVERITIES.map((severity) => {
              const group = findings.filter((f) => f.severity === severity);
              if (!group.length) return null;
              return (
                <section
                  key={severity}
                  aria-labelledby={`plan-checks-${severity}`}
                >
                  <h3
                    id={`plan-checks-${severity}`}
                    className="text-sm font-semibold"
                  >
                    {HEADINGS[severity]}
                  </h3>
                  {byDay(group).map(([day, rows]) => (
                    <div key={day ?? "trip"} className="mt-3 first:mt-0">
                      <h4 className="text-xs font-medium tracking-wider text-muted-foreground uppercase">
                        {day === null ? "Whole trip" : `Day ${day}`}
                      </h4>
                      <ul className="mt-2 flex flex-col gap-3">
                        {rows.map((finding) => (
                          <li
                            key={finding.id}
                            className="flex flex-col gap-1 border-l-2 border-border pl-3 text-sm"
                          >
                            <div className="flex flex-wrap items-start gap-2">
                              <SeverityBadge severity={finding.severity} />
                              <span className="min-w-0 flex-1">
                                {finding.message}
                              </span>
                            </div>
                            {finding.place_id &&
                              placeNames[finding.place_id] && (
                                <p className="flex items-center gap-1 font-medium">
                                  <MapPin
                                    aria-hidden="true"
                                    className="size-4 shrink-0 text-muted-foreground"
                                  />
                                  {placeNames[finding.place_id]}
                                </p>
                              )}
                            {finding.suggested_fix && (
                              <p className="text-muted-foreground">
                                <span className="font-medium text-foreground">
                                  Suggested fix:
                                </span>{" "}
                                {finding.suggested_fix}
                              </p>
                            )}
                            {finding.item_id && (
                              <Button
                                variant="link"
                                size="sm"
                                className="h-auto self-start px-0"
                                onClick={() =>
                                  finding.item_id && onGoToItem(finding.item_id)
                                }
                              >
                                Go to item
                              </Button>
                            )}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </section>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}
