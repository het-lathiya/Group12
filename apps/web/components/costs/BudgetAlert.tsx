import { AlertTriangle, Info } from "lucide-react";

import type { components } from "@/lib/api/schema";
import { isEnabled } from "@/lib/flags";

type Finding = components["schemas"]["Finding"];

// Guide §2, §12: a text title and an icon with the colour, never colour alone.
const BANNERS = {
  BUDGET_EXCEEDED: {
    title: "Over budget",
    icon: AlertTriangle,
    className: "border-warning bg-warning-soft text-warning-foreground",
  },
  BUDGET_NEAR: {
    title: "Near budget",
    icon: Info,
    className: "border-info bg-info-soft text-info",
  },
} as const;

/**
 * BudgetAlert (§7.5; FR-074, IMP-608): one banner per budget alert of API-33. The message, ratio
 * and excess come from the API; the browser computes nothing. Hidden by the 'budget_alerts'
 * switch, which leaves the validator's budget finding in the warnings panel.
 */
export function BudgetAlert({ alerts }: { alerts: Finding[] }) {
  if (!isEnabled("budget_alerts")) return null;
  return alerts.map((alert) => {
    if (alert.code !== "BUDGET_EXCEEDED" && alert.code !== "BUDGET_NEAR") {
      return null;
    }
    const { title, icon: Icon, className } = BANNERS[alert.code];
    return (
      <section
        key={alert.id}
        role="status"
        aria-label={title}
        className={`flex items-start gap-2 rounded-xl border p-4 ${className}`}
      >
        <Icon aria-hidden className="mt-0.5 size-4 shrink-0" />
        <p>
          <strong className="font-semibold">{title}.</strong> {alert.message}
        </p>
      </section>
    );
  });
}
