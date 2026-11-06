"use client";

import { Loader2 } from "lucide-react";
import { useEffect, useRef } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, OFFLINE_MESSAGE } from "@/lib/api/client";
import { useAcknowledgeAiNotice } from "@/lib/api/queries";

/** The approved wording (OD-11): a later decision changes it here and nowhere else. */
export const PRIVACY_NOTICE = {
  heading: "Before your first AI-written plan",
  bodyBeforeTerms:
    "To write your itinerary, this app sends your trip details, preferences and notes to Google's Gemini API. They are also used to find relevant places and guide passages. Your name and email address are not sent. Google handles this data under the ",
  termsLabel: "Gemini API terms",
  termsUrl: "https://ai.google.dev/gemini-api/terms",
  bodyAfterTerms: ". Do not enter personal details in your notes.",
  button: "I understand, continue",
} as const;

export type PrivacyNoticeProps = {
  /** Called once API-04 has stored the acknowledgement. */
  onAcknowledge: () => void;
};

/**
 * The AI-provider notice before an account's first generation (§7.5.6, IMD-24, NFR-021). The button
 * sends API-04; if that fails the error shows here and the same button tries again.
 */
export function PrivacyNotice({ onAcknowledge }: PrivacyNoticeProps) {
  const heading = useRef<HTMLHeadingElement>(null);
  const acknowledge = useAcknowledgeAiNotice();

  useEffect(() => heading.current?.focus(), []);

  async function accept() {
    try {
      // Not mutate's own onSuccess: updating `me` can unmount this notice, which would drop it.
      await acknowledge.mutateAsync();
    } catch {
      return; // shown below from the mutation's error
    }
    onAcknowledge();
  }

  const { error } = acknowledge;

  return (
    <section
      aria-labelledby="privacy-notice-title"
      className="flex flex-col items-start gap-4 rounded-xl border bg-card p-4 text-card-foreground shadow-xs sm:p-6"
    >
      <h2
        id="privacy-notice-title"
        ref={heading}
        tabIndex={-1}
        className="text-base font-semibold outline-none"
      >
        {PRIVACY_NOTICE.heading}
      </h2>
      <p className="text-sm">
        {PRIVACY_NOTICE.bodyBeforeTerms}
        <a
          href={PRIVACY_NOTICE.termsUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="rounded-sm font-medium text-primary underline underline-offset-4 outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        >
          {PRIVACY_NOTICE.termsLabel}
        </a>
        {PRIVACY_NOTICE.bodyAfterTerms}
      </p>
      {error && (
        <p
          role="alert"
          className="w-full rounded-lg bg-destructive/10 px-3 py-2 text-sm font-medium text-destructive"
        >
          {error instanceof ApiError ? error.message : OFFLINE_MESSAGE}
        </p>
      )}
      <Button
        onClick={() => void accept()}
        disabled={acknowledge.isPending}
        aria-busy={acknowledge.isPending}
      >
        {acknowledge.isPending && (
          <Loader2 aria-hidden="true" className="motion-safe:animate-spin" />
        )}
        {PRIVACY_NOTICE.button}
      </Button>
    </section>
  );
}
