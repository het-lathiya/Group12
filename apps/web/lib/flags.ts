/**
 * Feature switches (IMD-11). NEXT_PUBLIC_FEATURES_DISABLED lists the switched-off features,
 * separated by commas or spaces; an empty or missing value enables everything. The API reads the
 * same list from FEATURES_DISABLED, so a disabled feature is hidden here and its routes return 404.
 */

export const FEATURE_NAMES = [
  // Cut list, in cut order (IMD-11).
  "versions",
  "trip_management",
  "contingency",
  "budget_alerts",
  "wishlist",
  "alternatives",
  "regeneration",
  "locks",
  "meal_slots",
  // Extensions (EXT, §2.5).
  "ranking_explain",
  "nl_intake",
  "day_explain",
  "optimise_order",
  "rain_swap",
  "today_view",
  "budget_fit",
  "context_cards",
  "packing",
] as const;

export type FeatureName = (typeof FEATURE_NAMES)[number];

/**
 * Default-off switches (Amendment A2 §3.1), kept outside FEATURE_NAMES: such a switch is ON only
 * when the list holds its "!" token (for example "!any_city_mode") and not its plain name.
 */
export const DEFAULT_OFF_FEATURES = ["any_city_mode"] as const;

export type DefaultOffFeatureName = (typeof DEFAULT_OFF_FEATURES)[number];

const DEFAULT_OFF: ReadonlySet<string> = new Set(DEFAULT_OFF_FEATURES);

export function parseDisabledFeatures(
  raw: string | undefined,
): ReadonlySet<string> {
  return new Set(
    (raw ?? "")
      .split(/[\s,]+/)
      .map((name) => name.trim())
      .filter((name) => name.length > 0),
  );
}

// Next.js inlines NEXT_PUBLIC_* values at build time only for this literal property access.
const disabled = parseDisabledFeatures(
  process.env.NEXT_PUBLIC_FEATURES_DISABLED,
);

export function isEnabled(name: FeatureName | DefaultOffFeatureName): boolean {
  if (DEFAULT_OFF.has(name)) {
    return disabled.has(`!${name}`) && !disabled.has(name);
  }
  return !disabled.has(name);
}
