"use client";

import { useParams } from "next/navigation";
import { TripWizard } from "@/components/trips/TripWizard";

export default function EditTripPage() {
  const { tripId } = useParams<{ tripId: string }>();
  return <TripWizard editId={tripId} />;
}
