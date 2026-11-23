"use client";

import { createContext, useContext } from "react";

const LiveTierContext = createContext(false);

/**
 * Marks a subtree as showing a live destination (Amendment A2 §9.2). Pages set it only with
 * `any_city_mode` ON and API-79 `data_tier` "live"; false (the default) keeps curated wording.
 */
export const LiveTierProvider = LiveTierContext.Provider;

/** True only inside a LiveTierProvider set for a live destination. */
export function useLiveTier(): boolean {
  return useContext(LiveTierContext);
}
