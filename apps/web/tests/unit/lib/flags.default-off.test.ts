import { afterEach, describe, expect, it, vi } from "vitest";

// TC-460 (web side), TC-482: `any_city_mode` is a default-off switch (Amendment A2 §3.1). It is ON
// only when NEXT_PUBLIC_FEATURES_DISABLED holds "!any_city_mode" and not "any_city_mode".

const CUT_LIST =
  "versions,trip_management,contingency,budget_alerts,wishlist,alternatives,regeneration,locks,meal_slots";

const FEATURE_NAMES_EXT = [
  "ranking_explain",
  "nl_intake",
  "day_explain",
  "optimise_order",
  "rain_swap",
  "today_view",
  "budget_fit",
  "context_cards",
  "packing",
];

async function flagsWith(value: string | undefined) {
  vi.resetModules();
  if (value !== undefined) vi.stubEnv("NEXT_PUBLIC_FEATURES_DISABLED", value);
  return import("@/lib/flags");
}

describe("default-off switch any_city_mode (Amendment A2 §3.1)", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it("is OFF when the variable is empty", async () => {
    const { isEnabled, FEATURE_NAMES } = await flagsWith("");
    expect(isEnabled("any_city_mode")).toBe(false);
    expect(FEATURE_NAMES.every((name) => isEnabled(name))).toBe(true);
  });

  it("is OFF with the nine cut-list names and no token", async () => {
    const { isEnabled } = await flagsWith(CUT_LIST);
    expect(isEnabled("any_city_mode")).toBe(false);
    expect(isEnabled("versions")).toBe(false);
    expect(isEnabled("packing")).toBe(true);
  });

  it("is OFF with the nine extension names and no token", async () => {
    const { isEnabled, FEATURE_NAMES } = await flagsWith(
      FEATURE_NAMES_EXT.join(","),
    );
    expect(isEnabled("any_city_mode")).toBe(false);
    expect(FEATURE_NAMES.slice(9).every((name) => !isEnabled(name))).toBe(true);
  });

  it('is ON with "!any_city_mode"', async () => {
    const { isEnabled, FEATURE_NAMES } = await flagsWith("!any_city_mode");
    expect(isEnabled("any_city_mode")).toBe(true);
    expect(FEATURE_NAMES.every((name) => isEnabled(name))).toBe(true);
  });

  it('is ON with "versions,!any_city_mode", and versions stays OFF', async () => {
    const { isEnabled } = await flagsWith("versions,!any_city_mode");
    expect(isEnabled("any_city_mode")).toBe(true);
    expect(isEnabled("versions")).toBe(false);
    expect(isEnabled("locks")).toBe(true);
  });

  it("an explicit any_city_mode wins over the token", async () => {
    const { isEnabled } = await flagsWith("!any_city_mode any_city_mode");
    expect(isEnabled("any_city_mode")).toBe(false);
  });

  it("keeps any_city_mode out of FEATURE_NAMES, which is unchanged", async () => {
    const { FEATURE_NAMES, DEFAULT_OFF_FEATURES } = await flagsWith("");
    expect(DEFAULT_OFF_FEATURES).toEqual(["any_city_mode"]);
    expect(FEATURE_NAMES).not.toContain("any_city_mode");
    expect([...FEATURE_NAMES]).toEqual([
      "versions",
      "trip_management",
      "contingency",
      "budget_alerts",
      "wishlist",
      "alternatives",
      "regeneration",
      "locks",
      "meal_slots",
      ...FEATURE_NAMES_EXT,
    ]);
  });
});
