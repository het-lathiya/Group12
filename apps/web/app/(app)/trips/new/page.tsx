import type { Metadata } from "next";

import { TripWizard } from "@/components/trips/TripWizard";

export const metadata: Metadata = {
  title: "Plan a new trip · AI Travel Planner",
};

// Trip wizard (§7.5.4). Thin server component (§7.1); the wizard loads its data in the browser.
// ?draft=<trip id> reopens a saved draft (FR-013, IMP-410).
export default async function NewTripPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { draft } = await searchParams;
  return <TripWizard draftId={typeof draft === "string" ? draft : undefined} />;
}
