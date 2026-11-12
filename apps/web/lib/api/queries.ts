import {
  useMutation,
  useQuery,
  useQueryClient,
  keepPreviousData,
} from "@tanstack/react-query";

import { ApiError, api, unwrap } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

/**
 * Query keys of §7.4. TanStack Query is the only cache; every hook built on the API client
 * (IMP-214 and later) takes its key from this factory, so invalidation in one place reaches every
 * reader. Calling a key without its trailing arguments gives the prefix used to invalidate them all,
 * for example `queryKeys.trips()` matches every `['trips', filters]` entry.
 */

/** Filter values that are part of a list key, kept in the URL query string by the page. */
export type QueryFilters = Readonly<
  Record<string, string | number | boolean | null | undefined>
>;

export const queryKeys = {
  me: () => ["me"] as const,
  trips: (filters?: QueryFilters) =>
    filters === undefined
      ? (["trips"] as const)
      : (["trips", filters] as const),
  trip: (tripId: string) => ["trip", tripId] as const,
  destinations: () => ["destinations"] as const,
  preferences: (tripId: string) => ["preferences", tripId] as const,
  places: (destinationId: string, filters?: QueryFilters) =>
    filters === undefined
      ? (["places", destinationId] as const)
      : (["places", destinationId, filters] as const),
  itinerary: (tripId: string, versionId?: string) =>
    versionId === undefined
      ? (["itinerary", tripId] as const)
      : (["itinerary", tripId, versionId] as const),
  costs: (tripId: string) => ["costs", tripId] as const,
  latestItinerary: () => ["latestItinerary"] as const,
  generation: (generationId: string) => ["generation", generationId] as const,
} as const;

/** The version segment of the itinerary key for the plan currently in use. */
export const CURRENT_VERSION = "current";

type Schemas = components["schemas"];

/** API-03: the caller's profile, created on the first call. */
export function useProfile() {
  return useQuery({
    queryKey: queryKeys.me(),
    queryFn: async () => unwrap(await api().GET("/api/v1/me")),
  });
}

/** API-04: acknowledge the AI notice (IMD-24; §7.4: set `me`). */
export function useAcknowledgeAiNotice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () =>
      unwrap(
        await api().PATCH("/api/v1/me", {
          body: { ai_notice_acknowledged: true },
        }),
      ),
    onSuccess: (profile) => queryClient.setQueryData(queryKeys.me(), profile),
  });
}

/** API-06: the active destinations, for the wizard's destination list. */
export function useDestinations() {
  return useQuery({
    queryKey: queryKeys.destinations(),
    queryFn: async () => unwrap(await api().GET("/api/v1/destinations")),
  });
}

/** API-15: the trip's preferences, with what each field does (FR-009). */
export function usePreferences(tripId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.preferences(tripId ?? ""),
    queryFn: async () =>
      unwrap(
        await api().GET("/api/v1/trips/{trip_id}/preferences", {
          params: { path: { trip_id: tripId ?? "" } },
        }),
      ),
    enabled: tripId !== undefined,
  });
}

/** API-16 basic search: places of one destination whose name matches `q`. */
export function usePlaceSearch(destinationId: string | undefined, q: string) {
  return useQuery({
    queryKey: queryKeys.places(destinationId ?? "", { q }),
    queryFn: async () =>
      unwrap(
        await api().GET("/api/v1/places", {
          params: { query: { destination_id: destinationId ?? "", q } },
        }),
      ),
    enabled: destinationId !== undefined && q !== "",
    placeholderData: keepPreviousData,
  });
}

/** API-07: create a draft trip (§7.4: invalidate `trips`). */
export function useCreateTrip() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: Schemas["TripIn"]) =>
      unwrap(await api().POST("/api/v1/trips", { body })),
    onSuccess: async (trip) => {
      queryClient.setQueryData(queryKeys.trip(trip.id), trip);
      await queryClient.invalidateQueries({ queryKey: queryKeys.trips() });
    },
  });
}

/** API-22: start generating the whole trip (IMD-21: the body is the mode only). */
export function useStartGeneration(tripId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (mode: "ai" | "rule_based" = "ai") =>
      unwrap(
        await api().POST("/api/v1/trips/{trip_id}/generations", {
          params: { path: { trip_id: tripId } },
          body: { mode },
        }),
      ),
    // The 202 body is the first status, so the first poll waits 2 s (§7.4).
    onSuccess: (generation) =>
      queryClient.setQueryData(queryKeys.generation(generation.id), generation),
  });
}

/** §7.4 polling: 2 s after the start, then 3, 4 and 5 s, then every 5 s. */
const POLL_DELAYS_MS = [2000, 3000, 4000, 5000] as const;

/**
 * API-23: the generation's status, polled until `completed` or `failed`, or until `poll` is false
 * (the 160 s limit of IMD-12). Polling pauses while the tab is hidden (TanStack Query's default).
 */
export function useGeneration(generationId: string, poll: boolean) {
  return useQuery({
    queryKey: queryKeys.generation(generationId),
    queryFn: async () =>
      unwrap(
        await api().GET("/api/v1/generations/{generation_id}", {
          params: { path: { generation_id: generationId } },
        }),
      ),
    // Only the interval refetches, so a status seeded from the 202 waits the first 2 s.
    staleTime: Infinity,
    refetchInterval: (query) => {
      const { data, status, dataUpdateCount } = query.state;
      if (!poll || data?.status === "completed" || data?.status === "failed")
        return false;
      if (status === "error" && !data) return false; // the page shows the error and a retry
      const step = Math.min(dataUpdateCount, POLL_DELAYS_MS.length) - 1;
      return POLL_DELAYS_MS[Math.max(step, 0)];
    },
  });
}

// A 404 is an answer, not a fault worth repeating.
const retryUnless404 = (failures: number, error: Error) =>
  !(error instanceof ApiError && error.status === 404) && failures < 1;

/** API-10: one trip; a 404 means it is missing or not the caller's. */
export function useTrip(tripId: string, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.trip(tripId),
    queryFn: async () =>
      unwrap(
        await api().GET("/api/v1/trips/{trip_id}", {
          params: { path: { trip_id: tripId } },
        }),
      ),
    enabled,
    retry: retryUnless404,
  });
}

/** API-08: one page of the caller's trips, newest first. */
export function useTrips(limit = 20) {
  return useQuery({
    queryKey: queryKeys.trips({ limit }),
    queryFn: async () =>
      unwrap(
        await api().GET("/api/v1/trips", { params: { query: { limit } } }),
      ),
  });
}

/** API-09: the trip whose itinerary changed last; `trip_id` is null when there is none. */
export function useLatestItinerary() {
  return useQuery({
    queryKey: queryKeys.latestItinerary(),
    queryFn: async () => unwrap(await api().GET("/api/v1/itineraries/latest")),
  });
}

/** API-24: the trip's current itinerary; a 404 means none has been saved or the trip is not found. */
export function useItinerary(tripId: string) {
  return useQuery({
    queryKey: queryKeys.itinerary(tripId, CURRENT_VERSION),
    queryFn: async () =>
      unwrap(
        await api().GET("/api/v1/trips/{trip_id}/itinerary", {
          params: { path: { trip_id: tripId } },
        }),
      ),
    retry: retryUnless404,
  });
}

/** API-33: the trip's costs, computed by the API (the browser never totals, CLAUDE.md §4). */
export function useCosts(tripId: string) {
  return useQuery({
    queryKey: queryKeys.costs(tripId),
    queryFn: async () =>
      unwrap(
        await api().GET("/api/v1/trips/{trip_id}/costs", {
          params: { path: { trip_id: tripId } },
        }),
      ),
    retry: retryUnless404,
  });
}

/** API-34: save the allowances; the answer is the recalculated costs (§7.4: invalidate `costs`, `itinerary`). */
export function useUpdateBudgetSettings(tripId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: Schemas["BudgetSettingsPatch"]) =>
      unwrap(
        await api().PATCH("/api/v1/trips/{trip_id}/budget-settings", {
          params: { path: { trip_id: tripId } },
          body,
        }),
      ),
    onSuccess: async (costs) => {
      queryClient.setQueryData(queryKeys.costs(tripId), costs);
      await queryClient.invalidateQueries({
        queryKey: queryKeys.itinerary(tripId),
      });
    },
  });
}

/** API-14: replace the trip's preferences (§7.4: invalidate `preferences` and `trip`). */
export function useSavePreferences(tripId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: Schemas["PreferencesIn"]) =>
      unwrap(
        await api().PUT("/api/v1/trips/{trip_id}/preferences", {
          params: { path: { trip_id: tripId } },
          body,
        }),
      ),
    onSuccess: async (saved) => {
      queryClient.setQueryData(queryKeys.preferences(tripId), saved);
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: queryKeys.preferences(tripId),
        }),
        queryClient.invalidateQueries({ queryKey: queryKeys.trip(tripId) }),
      ]);
    },
  });
}

/**
 * API-25 undo of a removal (PD-IMP-408-1). Stays false until IMP-504 builds API-25; while false
 * the "Removed" toast offers no Undo.
 */
export const EDIT_UNDO_ENABLED = false;

/** The mutation key every itinerary edit shares, so all edit controls wait while one is saving. */
export const editKey = (tripId: string) => ["edit", tripId] as const;

type EditResult = Schemas["EditResultOut"];

/**
 * §7.4 "Edit item": the server's answer replaces the changed days, totals, findings and revision
 * in `itinerary`, then `itinerary` and `costs` are refetched together. Nothing is worked out here.
 * On 409 STALE_PLAN the plan is refetched.
 */
function useItemEdit<V>(
  tripId: string,
  request: (variables: V) => Promise<EditResult>,
) {
  const queryClient = useQueryClient();
  const refresh = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.itinerary(tripId) }),
      queryClient.invalidateQueries({ queryKey: queryKeys.costs(tripId) }),
    ]);
  return useMutation({
    mutationKey: editKey(tripId),
    mutationFn: request,
    onSuccess: async (result) => {
      queryClient.setQueryData<Schemas["ItineraryOut"]>(
        queryKeys.itinerary(tripId, CURRENT_VERSION),
        (current) =>
          current && {
            ...current,
            plan_revision: result.plan_revision,
            totals: result.totals,
            findings: result.findings,
            days: current.days.map(
              (day) =>
                result.changed_days.find(
                  (changed) => changed.day_number === day.day_number,
                ) ?? day,
            ),
          },
      );
      await refresh();
    },
    onError: async (error) => {
      if (error instanceof ApiError && error.code === "STALE_PLAN")
        await refresh();
    },
  });
}

/** API-26 retime: a new start time and/or duration (FR-063). */
export function useRetimeItem(tripId: string) {
  return useItemEdit(
    tripId,
    async ({
      itemId,
      ...body
    }: {
      itemId: string;
      plan_revision: number;
      start_time?: string;
      duration_min?: number;
    }) =>
      unwrap(
        await api().PATCH("/api/v1/itinerary/items/{item_id}", {
          params: { path: { item_id: itemId } },
          body,
        }),
      ),
  );
}

/** API-27 remove (FR-061); plan_revision travels as a query parameter (IMD-26). */
export function useRemoveItem(tripId: string) {
  return useItemEdit(
    tripId,
    async ({
      itemId,
      planRevision,
    }: {
      itemId: string;
      planRevision: number;
    }) =>
      unwrap(
        await api().DELETE("/api/v1/itinerary/items/{item_id}", {
          params: {
            path: { item_id: itemId },
            query: { plan_revision: planRevision },
          },
        }),
      ),
  );
}

/** API-25 add, used only by the removal undo while EDIT_UNDO_ENABLED is false (IMP-504). */
export function useAddItem(tripId: string) {
  return useItemEdit(tripId, async (body: Schemas["ItemAddIn"]) =>
    unwrap(
      await api().POST("/api/v1/trips/{trip_id}/itinerary/items", {
        params: { path: { trip_id: tripId } },
        body,
      }),
    ),
  );
}
