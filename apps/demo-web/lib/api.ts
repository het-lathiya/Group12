"use client";

// Typed client for the Group12 API (contracts/openapi.v1.json). Every call carries the Supabase
// access token. The browser only ever calls same-origin /api/v1 (proxied to staging).
import { createClient, type SupabaseClient } from "@supabase/supabase-js";

/* ---------------- Supabase ---------------- */
let sb: SupabaseClient | undefined;
export function supabase(): SupabaseClient {
  sb ??= createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!, {
    auth: { persistSession: true, autoRefreshToken: true, storageKey: "tripbook-demo-auth" },
  });
  return sb;
}

/* ---------------- Types (subset of the contract) ---------------- */
export type Money = { amount: string; currency: string };
export type TripStatus = "draft" | "ready" | "archived";
export type Trip = {
  id: string; title: string; destination_id: string;
  destination: { id: string; name: string; currency: string; timezone: string; is_sample: boolean };
  start_date: string; end_date: string; num_days: number; adults: number; children: number;
  budget: Money | null; status: TripStatus; has_itinerary: boolean; plan_revision: number; plan_stale: boolean;
  group_needs: string[]; created_at: string; updated_at: string;
};
export type Destination = { id: string; name: string; slug: string; region: string | null; country_code: string; currency: string; timezone: string; is_sample: boolean; center: { lat: number; lon: number } };
export type Category = "sight" | "museum" | "nature" | "food" | "shopping" | "entertainment" | "religious" | "activity" | "stay";
export type SourceLabel = "curated" | "estimate" | "unavailable";
export type TravelLeg = { distance_m: number; minutes: number; mode: "walking" | "local_transport" | "car"; source: string };
export type SourceRef = { title: string; source_name: string; url: string | null; kind: "place" | "guide" };
export type Item = {
  id: string; position: number; start_time: string; end_time: string; duration_min: number;
  slot_type: "activity" | "meal" | "rest"; is_locked: boolean; must_visit: boolean;
  note: string | null; note_origin: string; origin: string;
  place: { id: string; name: string; category: Category; lat: number; lon: number; hours_label: SourceLabel };
  cost: { currency: string; min: string; max: string; label: SourceLabel } | null;
  travel_from_previous: TravelLeg | null; sources: SourceRef[];
};
export type Day = { day_number: number; date: string; theme: string | null; items: Item[]; day_cost: { currency: string; min: string; max: string; complete: boolean } };
export type Finding = { id: string; code: string; severity: "error" | "warning" | "info"; message: string; day_number: number | null; item_id: string | null; suggested_fix: string | null };
export type Totals = { currency: string; planning_total: string; estimate: { min: string; max: string }; complete: boolean; incomplete_count: number };
export type Itinerary = { trip_id: string; version_id: string | null; plan_revision: number; plan_stale: boolean; is_current: boolean; days: Day[]; findings: Finding[]; totals: Totals; source: { outcome: string; provider: string } | null };
export type EditResult = { changed_days: Day[]; findings: Finding[]; plan_revision: number; totals: Totals };
export type Generation = {
  id: string; trip_id: string; status: "queued" | "running" | "validating" | "repairing" | "completed" | "failed";
  mode: "ai" | "rule_based"; outcome: string | null; failure_message: string | null; next_action: string | null;
  plan_revision: number | null; validation_summary: { errors: number; warnings: number; infos: number };
};
export type CostSummary = {
  currency: string; planning_total: string; estimate: { min: string; max: string }; complete: boolean;
  budget: { amount: string | null; excess: string | null; ratio_pct: number | null; status: "none" | "near" | "exceeded" };
  by_category: { category: string; label: string; min: string; max: string }[];
  by_day: { day_number: number; min: string; max: string; contingency_share: string }[];
  contingency: { amount: string; pct: number }; per_traveller: { label: string; largest_share: string; travellers: number };
  alerts: Finding[]; incomplete_items: string[]; settings: { contingency_pct: number; stay_budget_per_night: string | null; transport_allowance_per_day: string | null };
};
export type Version = { id: string; version_no: number; kind: string; name: string | null; reason: string; created_at: string; plan_revision: number; generation_id: string | null; validation_summary: { errors: number; warnings: number; infos: number } };
export type Place = {
  id: string; name: string; category: Category; lat: number; lon: number; typical_duration_min: number;
  price: { currency: string; min: string; max: string | null; label: SourceLabel } | null; price_label: SourceLabel;
  tags: string[]; verification_status: string; suitability: { step_free: boolean | null; child_friendly: boolean | null; indoor: boolean | null };
};
export type Profile = { id: string; email: string | null; display_name: string | null; home_country: string | null; preferred_currency: string | null; ai_notice_ack_at: string | null; default_preferences: Record<string, unknown> };
export type Summary = { trip: Trip; days: Day[]; costs: CostSummary; unresolved_findings: Finding[]; generated_at: string };
type Page<T> = { items: T[]; total: number; limit: number; offset: number };

/* ---------------- Errors ---------------- */
export class ApiError extends Error {
  constructor(readonly status: number, readonly code: string, message: string, readonly details: { field?: string; message: string }[] = []) { super(message); }
}

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/v1";

async function token(): Promise<string | null> {
  const { data } = await supabase().auth.getSession();
  return data.session?.access_token ?? null;
}

async function call<T>(method: string, path: string, body?: unknown): Promise<T> {
  const doFetch = async (t: string | null) => fetch(BASE + path, {
    method,
    headers: { "Content-Type": "application/json", "X-Request-ID": crypto.randomUUID(), ...(t ? { Authorization: `Bearer ${t}` } : {}) },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  let res: Response;
  try { res = await doFetch(await token()); } catch { throw new ApiError(0, "OFFLINE", "The server could not be reached. Check your connection and try again."); }
  if (res.status === 401) {
    const { data } = await supabase().auth.refreshSession();
    if (data.session) res = await doFetch(data.session.access_token);
    if (res.status === 401) {
      await supabase().auth.signOut({ scope: "local" });
      if (typeof window !== "undefined") window.location.assign(`/sign-in/?next=${encodeURIComponent(location.pathname)}`);
      throw new ApiError(401, "UNAUTHENTICATED", "Please sign in again.");
    }
  }
  if (res.status === 204) return undefined as T;
  const json = await res.json().catch(() => undefined);
  if (!res.ok) {
    const e = json?.error;
    throw new ApiError(res.status, e?.code ?? "INTERNAL", e?.message ?? "Something went wrong. Please try again.", e?.details ?? []);
  }
  return json as T;
}

/* ---------------- Endpoints ---------------- */
const q = (o: Record<string, string | number | boolean | undefined>) => {
  const s = new URLSearchParams();
  Object.entries(o).forEach(([k, v]) => v !== undefined && v !== "" && s.set(k, String(v)));
  const str = s.toString(); return str ? "?" + str : "";
};

export const api = {
  me: () => call<Profile>("GET", "/me"),
  updateMe: (b: Partial<{ display_name: string; home_country: string; preferred_currency: string; ai_notice_acknowledged: boolean }>) => call<Profile>("PATCH", "/me", b),

  destinations: () => call<Destination[]>("GET", "/destinations"),
  places: (p: { destination_id: string; q?: string; category?: string; limit?: number }) => call<Page<Place>>("GET", "/places" + q({ limit: 30, ...p })),

  trips: () => call<Page<Trip>>("GET", "/trips" + q({ limit: 50 })),
  trip: (id: string) => call<Trip>("GET", `/trips/${id}`),
  createTrip: (b: { title: string; destination_id: string; start_date: string; end_date: string; adults: number; children: number; budget?: { amount: string; currency: string } | null; group_needs?: string[] }) => call<Trip>("POST", "/trips", b),
  deleteTrip: (id: string) => call<void>("DELETE", `/trips/${id}`),
  savePreferences: (id: string, b: { interests: string[]; pace: string; budget_priority: string; transport_pref?: string; notes?: string | null }) => call<unknown>("PUT", `/trips/${id}/preferences`, b),

  startGeneration: (id: string, mode: "ai" | "rule_based" = "ai") => call<Generation>("POST", `/trips/${id}/generations`, { mode }),
  generation: (gid: string) => call<Generation>("GET", `/generations/${gid}`),
  regenerateDay: (id: string, day: number, plan_revision: number) => call<Generation>("POST", `/trips/${id}/itinerary/days/${day}/regenerate`, { plan_revision, mode: "ai" }),

  itinerary: (id: string) => call<Itinerary>("GET", `/trips/${id}/itinerary`),
  moveItem: (itemId: string, b: { plan_revision: number; position?: number; day_number?: number; start_time?: string; is_locked?: boolean; duration_min?: number }) => call<EditResult>("PATCH", `/itinerary/items/${itemId}`, b),
  deleteItem: (itemId: string, plan_revision: number) => call<EditResult>("DELETE", `/itinerary/items/${itemId}?plan_revision=${plan_revision}`),
  addItem: (id: string, b: { day_number: number; place_id: string; plan_revision: number }) => call<EditResult>("POST", `/trips/${id}/itinerary/items`, b),
  validate: (id: string) => call<unknown>("POST", `/trips/${id}/itinerary/validate`),

  costs: (id: string) => call<CostSummary>("GET", `/trips/${id}/costs`),
  updateBudget: (id: string, b: { contingency_pct?: number; stay_budget_per_night?: string | null; transport_allowance_per_day?: string | null }) => call<unknown>("PATCH", `/trips/${id}/budget-settings`, b),
  versions: (id: string) => call<Version[]>("GET", `/trips/${id}/versions`),
  saveVersion: (id: string, name: string, plan_revision: number) => call<Version>("POST", `/trips/${id}/versions`, { name, plan_revision }),
  restoreVersion: (id: string, vid: string, plan_revision: number) => call<Itinerary>("POST", `/trips/${id}/versions/${vid}/restore`, { plan_revision }),
  summary: (id: string) => call<Summary>("GET", `/trips/${id}/summary`),
  duplicate: (id: string) => call<Trip>("POST", `/trips/${id}/duplicate`),

  savedPlaces: (id: string) => call<Place[]>("GET", `/trips/${id}/saved-places`),
  savePlace: (id: string, pid: string) => call<void>("PUT", `/trips/${id}/saved-places/${pid}`),
  unsavePlace: (id: string, pid: string) => call<void>("DELETE", `/trips/${id}/saved-places/${pid}`),
};

/* ---------------- Helpers ---------------- */
export function money(v: string | number | null | undefined, currency = "INR") {
  if (v === null || v === undefined) return "—";
  const n = typeof v === "string" ? parseFloat(v) : v;
  const sym: Record<string, string> = { INR: "₹", USD: "$", EUR: "€", GBP: "£" };
  return (sym[currency] ?? currency + " ") + Math.round(n).toLocaleString("en-IN");
}
export function range(min: string, max: string, currency: string) {
  return min === max ? money(min, currency) : `${money(min, currency)}–${money(max, currency).replace(/^\D+/, "")}`;
}
export function fmtTime(hhmm: string) {
  const [h, m] = hhmm.split(":").map(Number);
  return `${((h + 11) % 12) + 1}:${String(m).padStart(2, "0")} ${h < 12 ? "AM" : "PM"}`;
}
export function fmtDate(iso: string, opts: Intl.DateTimeFormatOptions = { weekday: "long", month: "short", day: "numeric" }) {
  return new Date(iso + "T00:00:00").toLocaleDateString("en-IN", opts);
}

const photo = (id: string) => `https://images.unsplash.com/${id}?auto=format&fit=crop&w=800&q=70`;
const destPhotos: [RegExp, string][] = [
  [/jaipur/i, "photo-1477587458883-47145ed94245"], [/goa/i, "photo-1512343879784-a960bf40e7f2"], [/udaipur/i, "photo-1568495248636-6432b97bd949"],
  [/kerala|kochi|alleppey/i, "photo-1602216056096-3b40cc0c9944"], [/manali|himachal/i, "photo-1626621341517-bbf3d9990a23"], [/varanasi/i, "photo-1561361513-2d000a50f0dc"],
  [/mumbai/i, "photo-1529253355930-ddbe423a2ac7"], [/delhi/i, "photo-1587474260584-136574528ed5"],
];
export function destinationPhoto(name: string) {
  return photo(destPhotos.find(([r]) => r.test(name))?.[1] ?? "photo-1500530855697-b586d89ba3ee");
}
const catPhotos: Record<Category, string[]> = {
  sight: ["photo-1599661046289-e31897846e41", "photo-1524492412937-b28074a5d7da"],
  museum: ["photo-1566127444979-b3d2b654e3d7", "photo-1554907984-15263bfd63bd"],
  nature: ["photo-1500530855697-b586d89ba3ee", "photo-1506461883276-594a12b11cf3"],
  food: ["photo-1585937421612-70a008356fbe", "photo-1504674900247-0877df9cc836", "photo-1517244683847-7456b63c5969"],
  shopping: ["photo-1555529669-e69e7aa0ba9a", "photo-1528360983277-13d401cdc186"],
  entertainment: ["photo-1514525253161-7a46d19cd819"],
  religious: ["photo-1561361513-2d000a50f0dc", "photo-1524492412937-b28074a5d7da"],
  activity: ["photo-1565193566173-7a0ee3dbe261", "photo-1474487548417-781cb71495f3"],
  stay: ["photo-1566073771259-6a8506099945"],
};
export function placePhoto(category: Category, seed: string) {
  const list = catPhotos[category] ?? catPhotos.sight;
  let h = 0; for (const c of seed) h = (h * 31 + c.charCodeAt(0)) | 0;
  return photo(list[Math.abs(h) % list.length]);
}
export const categoryIcon: Record<string, string> = {
  sight: "photo_camera", museum: "museum", nature: "park", food: "restaurant", shopping: "shopping_bag",
  entertainment: "theater_comedy", religious: "temple_hindu", activity: "local_activity", stay: "hotel",
  activities: "local_activity", transport: "train", accommodation: "hotel", other: "category", contingency: "savings",
};
export const legIcon = { walking: "directions_walk", local_transport: "directions_bus", car: "local_taxi" } as const;
