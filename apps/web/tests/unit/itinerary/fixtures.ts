import type { components } from "@/lib/api/schema";

type Item = components["schemas"]["Item"];

/** A SAMPLE API-24 item with every field set, including those the read-only view must not show. */
export const ITEM: Item = {
  id: "00000000-0000-4000-8000-0000000000c1",
  position: 1,
  place: {
    id: "00000000-0000-4000-8000-000000000003",
    name: "Old Mill Museum (sample)",
    category: "museum",
    hours_label: "curated",
    lat: 12.97,
    lon: 77.59,
  },
  slot_type: "activity",
  start_time: "09:30",
  end_time: "11:00",
  duration_min: 90,
  is_locked: false,
  must_visit: false,
  origin: "model",
  note: "Arrive early for the quiet gallery.",
  note_origin: "ai",
  cost: { min: "0.00", max: "0.00", currency: "INR", label: "estimate" },
  travel_from_previous: {
    minutes: 12,
    distance_m: 900,
    mode: "walking",
    source: "fallback_estimate",
  },
  sources: [],
};
