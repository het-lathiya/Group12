import { ApiError, type ErrorCode } from "@/lib/api/client";

/**
 * The error catalogue (FR-116, IMP-412): one entry per §6.3 error code plus "network error", each
 * saying what happened and what to do next. docs/guides/error-catalogue.md holds the same text.
 */
export type CatalogueKey = ErrorCode | "NETWORK";

export type CatalogueEntry = { what: string; next: string };

export const ERROR_CATALOGUE: Record<CatalogueKey, CatalogueEntry> = {
  UNAUTHENTICATED: {
    what: "You are signed out",
    next: "Sign in again to continue. Your saved trips are kept.",
  },
  NOT_FOUND: {
    what: "We could not find that",
    next: "It may have been deleted or belong to another account. Go back to your trips.",
  },
  STALE_PLAN: {
    what: "This plan changed somewhere else",
    next: "Reload to see the latest version, then make your change again.",
  },
  GENERATION_IN_PROGRESS: {
    what: "An itinerary is still being generated",
    next: "Wait for it to finish, then try again.",
  },
  CONFLICT: {
    what: "This change conflicts with the trip's current state",
    next: "Reload the page to see the current state, then try again.",
  },
  VALIDATION_ERROR: {
    what: "Some details need attention",
    next: "Check the highlighted fields and try again.",
  },
  INVALID_EDIT: {
    what: "That change cannot be made",
    next: "Choose another day, position or place, or unlock the item first.",
  },
  RATE_LIMITED: {
    what: "Too many requests",
    next: "Wait a moment, then try again.",
  },
  AI_QUOTA_REACHED: {
    what: "Today's AI planning limit is reached",
    next: "Try again tomorrow, or use the rule-based plan now.",
  },
  INTERNAL: {
    what: "Something went wrong on our side",
    next: "Try again. If it keeps happening, share the reference below with the team.",
  },
  NOT_IMPLEMENTED: {
    what: "This feature is not available yet",
    next: "Go back and continue with the rest of your trip.",
  },
  SERVICE_UNAVAILABLE: {
    what: "The service is temporarily unavailable",
    next: "Try again in a few minutes. Your saved work is kept.",
  },
  NETWORK: {
    what: "The server could not be reached",
    next: "Check your connection and try again; your input is kept.",
  },
};

export type DescribedError = CatalogueEntry & {
  code: CatalogueKey;
  /** The API's own message (§6.3: safe to show), or a caller's plain text; never a stack or JSON. */
  message: string | null;
  requestId: string | null;
  retryAfterS: number | null;
};

/** Plain text only: a JSON body or a multi-line dump is never shown. */
function safeText(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const text = value.trim();
  if (!text || /^[[{]/.test(text) || text.includes("\n")) return null;
  return text;
}

/**
 * What ErrorState shows for any thrown value: an ApiError by its code; a caller's
 * `{ message, requestId? }`; anything else (a fetch TypeError, an unknown object) as a network
 * error, without its own message or stack.
 */
export function describeError(error: unknown): DescribedError {
  if (error instanceof ApiError) {
    const code = error.code in ERROR_CATALOGUE ? error.code : "INTERNAL";
    return {
      ...ERROR_CATALOGUE[code],
      code,
      message: safeText(error.message),
      requestId: error.requestId,
      retryAfterS: error.retryAfterS,
    };
  }
  const plain =
    typeof error === "object" && error !== null && !(error instanceof Error)
      ? (error as { message?: unknown; requestId?: unknown })
      : null;
  const message = plain ? safeText(plain.message) : null;
  return {
    ...ERROR_CATALOGUE.NETWORK,
    // A caller's own text already says what to do (the offline messages); no second hint.
    ...(message ? { next: "" } : {}),
    code: "NETWORK",
    message,
    requestId: plain ? safeText(plain.requestId) : null,
    retryAfterS: null,
  };
}
