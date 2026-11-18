"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { FullPageSpinner } from "@/components/states";
import { useTrip } from "@/components/shell";

export default function TripIndex() {
  const { tripId } = useTrip();
  const router = useRouter();
  useEffect(() => { if (tripId) router.replace(`/trips/${tripId}/itinerary/`); }, [tripId, router]);
  return <FullPageSpinner text="Opening itinerary…" />;
}
