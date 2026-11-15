"use client";

import { useState } from "react";

import { ConfirmDialog } from "@/components/states/ConfirmDialog";
import { Button } from "@/components/ui/button";
import type { components } from "@/lib/api/schema";

type Version = components["schemas"]["VersionOut"];

const REASONS: Record<Version["reason"], string> = {
  generation: "Generated plan",
  fallback: "Rule-based plan",
  regeneration: "Before regeneration",
  edit: "After an edit",
  restore: "Restore",
  manual: "Saved version",
};

export type VersionListProps = {
  versions: Version[];
  /** The plan_revision currently in use; that row cannot be restored. */
  currentRevision: number;
  onRestore: (version: Version) => void;
  restoring?: boolean;
};

const TAG = "rounded-full border px-2 py-0.5 text-xs font-normal";

const savedAt = (iso: string) =>
  new Date(iso).toLocaleString("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  });

const counts = ({ errors, warnings, infos }: Version["validation_summary"]) =>
  `${errors} errors, ${warnings} warnings, ${infos} notes`;

/** API-36 rows newest first; Restore asks first (FR-095 AC2). */
export function VersionList({
  versions,
  currentRevision,
  onRestore,
  restoring = false,
}: VersionListProps) {
  const [chosen, setChosen] = useState<Version | null>(null);
  return (
    <>
      <ol className="flex flex-col gap-3" aria-label="Saved versions">
        {versions.map((version) => {
          const title = version.name ?? REASONS[version.reason];
          const current = version.plan_revision === currentRevision;
          return (
            <li
              key={version.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border bg-card p-4 shadow-xs"
            >
              <div className="flex min-w-0 flex-col gap-1">
                <p className="flex flex-wrap items-center gap-2 font-medium">
                  <span className="break-words">
                    Version {version.version_no}: {title}
                  </span>
                  <span className={TAG}>
                    {version.kind === "named" ? "Named" : "Automatic"}
                  </span>
                  {current && <span className={TAG}>Current plan</span>}
                </p>
                <p className="text-sm text-muted-foreground">
                  {savedAt(version.created_at)} · plan revision{" "}
                  {version.plan_revision} · {counts(version.validation_summary)}
                </p>
              </div>
              {!current && (
                <Button
                  variant="outline"
                  className="min-h-touch"
                  disabled={restoring}
                  onClick={() => setChosen(version)}
                  aria-label={`Restore version ${version.version_no}`}
                >
                  Restore
                </Button>
              )}
            </li>
          );
        })}
      </ol>
      <ConfirmDialog
        open={chosen !== null}
        onOpenChange={(open) => !open && setChosen(null)}
        title={`Restore version ${chosen?.version_no ?? ""}?`}
        description="It becomes your current plan. Your current plan is kept in the history, and costs, travel times and warnings are worked out again."
        confirmLabel="Restore"
        onConfirm={() => chosen && onRestore(chosen)}
      />
    </>
  );
}
