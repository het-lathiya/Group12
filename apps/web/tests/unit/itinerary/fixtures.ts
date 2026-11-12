import type { components } from "@/lib/api/schema";

type Item = components["schemas"]["Item"];

/** A SAMPLE API-24 item with every field set. */
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

type Itinerary = components["schemas"]["ItineraryOut"];
export const TRIP_ID = "00000000-0000-4000-8000-000000000002";

/** A SAMPLE API-24 plan whose days hold the given items, numbered from day 1. */
export function planWith(days: Item[][], planRevision = 1): Itinerary {
  return {
    trip_id: TRIP_ID,
    plan_revision: planRevision,
    version_id: null,
    is_current: true,
    plan_stale: false,
    source: null,
    days: days.map((items, index) => ({
      day_number: index + 1,
      date: `2026-11-${String(14 + index).padStart(2, "0")}`,
      theme: null,
      theme_origin: "none",
      day_cost: { min: "0.00", max: "0.00", currency: "INR", complete: true },
      items,
    })),
    findings: [],
    totals: {
      currency: "INR",
      estimate: { min: "0.00", max: "0.00" },
      planning_total: "0.00",
      complete: true,
      incomplete_count: 0,
    },
  };
}

/** A second SAMPLE item for ordering cases. */
export const ITEM_B: Item = {
  ...ITEM,
  id: "00000000-0000-4000-8000-0000000000c2",
  position: 2,
  place: {
    ...ITEM.place,
    id: "00000000-0000-4000-8000-000000000004",
    name: "River Walk (sample)",
  },
  start_time: "11:30",
  end_time: "12:30",
  duration_min: 60,
  note: null,
  note_origin: "none",
  travel_from_previous: null,
};
