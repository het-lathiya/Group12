"use client";

import { OctagonX } from "lucide-react";
import { type ReactNode, useState } from "react";

import { Button } from "@/components/ui/button";
import { describeError } from "@/lib/api/errors";

/** A caller's own error text; an ApiError (lib/api/client.ts) or any thrown value also works. */
export type ErrorStateError = {
  message: string;
  requestId?: string | null;
};

export type ErrorStateProps = {
  /** Shown through the error catalogue (lib/api/errors.ts); never as raw text, JSON or a stack. */
  error: unknown;
  /** What happened, in the page's words; defaults to the catalogue's. */
  title?: string;
  onRetry?: () => void;
  retryLabel?: string;
  /** A navigation action used instead of Retry. */
  action?: ReactNode;
  /** True when the error sits inside a page that still shows other content (no role="alert"). */
  inline?: boolean;
};

/**
 * Shown when a request failed (§7.6; FR-116, IMP-412): what happened, what to do next, one
 * action, and the request ID as a reference with a Copy button.
 */
export function ErrorState({
  error,
  title,
  onRetry,
  retryLabel = "Try again",
  action,
  inline = false,
}: ErrorStateProps) {
  const described = describeError(error);
  const [copied, setCopied] = useState(false);

  async function copy(requestId: string) {
    try {
      await navigator.clipboard.writeText(requestId);
      setCopied(true);
    } catch {
      setCopied(false); // the reference stays selectable by hand
    }
  }

  return (
    <section
      role={inline ? undefined : "alert"}
      aria-live={inline ? "polite" : undefined}
      className="flex flex-col items-center gap-3 rounded-xl border border-destructive/40 bg-card px-4 py-10 text-center"
    >
      <OctagonX aria-hidden="true" className="size-6 text-destructive" />
      <h2 className="font-heading text-lg font-semibold text-card-foreground">
        {title ?? described.what}
      </h2>
      {described.message && (
        <p className="max-w-prose text-sm text-card-foreground">
          {described.message}
        </p>
      )}
      {described.next && (
        <p className="max-w-prose text-sm text-muted-foreground">
          {described.next}
        </p>
      )}
      {described.code === "RATE_LIMITED" && described.retryAfterS !== null && (
        <p className="text-sm font-medium text-card-foreground">
          Try again in {described.retryAfterS} s
        </p>
      )}
      {(action ?? onRetry) && (
        <div className="mt-2">
          {action ?? (
            <Button variant="outline" onClick={onRetry}>
              {retryLabel}
            </Button>
          )}
        </div>
      )}
      {described.requestId && (
        <p className="flex flex-wrap items-center justify-center gap-2 text-xs text-muted-foreground">
          <span>
            Reference:{" "}
            <span className="font-mono break-all select-all">
              {described.requestId}
            </span>
          </span>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => void copy(described.requestId as string)}
            aria-label={copied ? "Reference copied" : "Copy reference"}
          >
            {copied ? "Copied" : "Copy"}
          </Button>
        </p>
      )}
    </section>
  );
}
