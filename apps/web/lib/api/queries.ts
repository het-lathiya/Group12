import {
  useMutation,
  useQuery,
  useQueryClient,
  keepPreviousData,
} from "@tanstack/react-query";

import { toast } from "sonner";

import { ApiError, api, unwrap, STALE_PLAN_MESSAGE } from "@/lib/api/client";
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

// IMP-504
/** API-25 is available, enabling removal undo (IMD-157). */
export const EDIT_UNDO_ENABLED = true;

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
  after?: (result: EditResult, variables: V) => void,
) {
  const queryClient = useQueryClient();
  const refresh = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.itinerary(tripId) }),
      queryClient.invalidateQueries({ queryKey: queryKeys.costs(tripId) }),
      queryClient.invalidateQueries({ queryKey: ["summary", tripId] }),
      queryClient.invalidateQueries({ queryKey: ["versions", tripId] }),
    ]);
  return useMutation({
    mutationKey: editKey(tripId),
    mutationFn: request,
    onSuccess: async (result, variables) => {
      queryClient.setQueryData<Schemas["ItineraryOut"]>(
        queryKeys.itinerary(tripId, CURRENT_VERSION),
        (current) =>
          current && {
            ...current,
            plan_revision: result.plan_revision,
            totals: result.totals,
            findings: result.findings,
            days: [
              ...current.days.filter(
                (day) =>
                  !result.changed_days.some(
                    (changed) => changed.day_number === day.day_number,
                  ),
              ),
              ...result.changed_days,
            ].sort((a, b) => a.day_number - b.day_number),
          },
      );
      after?.(result, variables);
      await refresh();
    },
    onError: async (error) => {
      if (error instanceof ApiError && error.code === "STALE_PLAN") {
        await refresh();
        toast.error(STALE_PLAN_MESSAGE, {
          action: {
            label: "Reload",
            onClick: () => {
              void refresh();
            },
          },
        });
      }
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

/**
 * API-27 remove (FR-061); plan_revision travels as a query parameter (IMD-26). `onRemoved` runs
 * from the hook's own success path: the removed card, which calls `mutate`, unmounts when the
 * changed day is written, and TanStack Query skips a per-call `onSuccess` after that.
 */
export function useRemoveItem(tripId: string) {
  return useItemEdit(
    tripId,
    async ({
      itemId,
      planRevision,
    }: {
      itemId: string;
      planRevision: number;
      onRemoved?: (result: EditResult) => void;
    }) =>
      unwrap(
        await api().DELETE("/api/v1/itinerary/items/{item_id}", {
          params: {
            path: { item_id: itemId },
            query: { plan_revision: planRevision },
          },
        }),
      ),
    (result, { onRemoved }) => onRemoved?.(result),
  );
}

// IMP-504
/** API-25 add and removal undo, with the shared server-result and stale-edit handling. */
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

/** API-26 move: to `day_number` (default its own day) at `position` (default the end) (FR-060). */
export function useMoveItem(tripId: string) {
  return useItemEdit(
    tripId,
    async ({
      itemId,
      ...body
    }: {
      itemId: string;
      plan_revision: number;
      day_number?: number;
      position?: number;
    }) =>
      unwrap(
        await api().PATCH("/api/v1/itinerary/items/{item_id}", {
          params: { path: { item_id: itemId } },
          body,
        }),
      ),
  );
}

// IMP-509

/** Places per explore page; API-16 allows at most 50. */
export const EXPLORE_PAGE_SIZE = 20;

/** API-16 for the explore page: one page of the destination's places, by name. */
export function usePlacesPage(
  destinationId: string | undefined,
  offset: number,
) {
  return useQuery({
    queryKey: queryKeys.places(destinationId ?? "", {
      limit: EXPLORE_PAGE_SIZE,
      offset,
    }),
    queryFn: async () =>
      unwrap(
        await api().GET("/api/v1/places", {
          params: {
            query: {
              destination_id: destinationId ?? "",
              limit: EXPLORE_PAGE_SIZE,
              offset,
            },
          },
        }),
      ),
    enabled: destinationId !== undefined,
    placeholderData: keepPreviousData,
  });
}

// IMP-505
/** API-28: the current ranked alternatives for an open dialog. */
export function useAlternatives(itemId: string, enabled: boolean) {
  return useQuery({
    queryKey: ["alternatives", itemId],
    enabled,
    queryFn: async () =>
      unwrap(
        await api().GET("/api/v1/itinerary/items/{item_id}/alternatives", {
          params: { path: { item_id: itemId } },
        }),
      ),
  });
}
/** API-29 uses the same cache replacement and stale handling as every item edit. */
export function useReplaceItem(tripId: string) {
  return useItemEdit(
    tripId,
    async ({
      itemId,
      ...body
    }: {
      itemId: string;
      place_id: string;
      plan_revision: number;
    }) =>
      unwrap(
        await api().POST("/api/v1/itinerary/items/{item_id}/replace", {
          params: { path: { item_id: itemId } },
          body,
        }),
      ),
  );
}

// IMP-506
/** API-26 lock state, with revision checks and the shared edit invalidation. */
export function useLockItem(tripId: string) {
  return useItemEdit(
    tripId,
    async ({
      itemId,
      ...body
    }: {
      itemId: string;
      plan_revision: number;
      is_locked: boolean;
    }) =>
      unwrap(
        await api().PATCH("/api/v1/itinerary/items/{item_id}", {
          params: { path: { item_id: itemId } },
          body,
        }),
      ),
  );
}

// IMP-510
/** API-11 saves trip settings; plan_stale comes only from the backend. */
export function useUpdateTrip(tripId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: Schemas["TripPatch"]) =>
      unwrap(
        await api().PATCH("/api/v1/trips/{trip_id}", {
          params: { path: { trip_id: tripId } },
          body,
        }),
      ),
    onSuccess: async (trip) => {
      queryClient.setQueryData(queryKeys.trip(tripId), trip);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.trips() }),
        queryClient.invalidateQueries({
          queryKey: queryKeys.itinerary(tripId),
        }),
        queryClient.invalidateQueries({ queryKey: queryKeys.costs(tripId) }),
        queryClient.invalidateQueries({ queryKey: ["summary", tripId] }),
      ]);
    },
  });
}

// IMP-605 saved places
/** §7.4 key of API-21; saving or unsaving invalidates it. */
export const savedPlacesKey = (tripId: string) =>
  ["savedPlaces", tripId] as const;

/** API-21 the trip's saved places; off when the `wishlist` switch is (IMD-11). */
export function useSavedPlaces(tripId: string, enabled: boolean) {
  return useQuery({
    queryKey: savedPlacesKey(tripId),
    queryFn: async () =>
      unwrap(
        await api().GET("/api/v1/trips/{trip_id}/saved-places", {
          params: { path: { trip_id: tripId } },
        }),
      ),
    enabled,
  });
}

/** API-19 saves (`save: true`) or API-20 unsaves a place; both are idempotent. */
export function useToggleSavedPlace(tripId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      placeId,
      save,
    }: {
      placeId: string;
      save: boolean;
    }) => {
      const params = { path: { trip_id: tripId, place_id: placeId } };
      const path = "/api/v1/trips/{trip_id}/saved-places/{place_id}";
      unwrap(
        save
          ? await api().PUT(path, { params })
          : await api().DELETE(path, { params }),
      );
    },
    onSettled: () =>
      queryClient.invalidateQueries({ queryKey: savedPlacesKey(tripId) }),
  });
}

// IMP-610 versions
/** API-36: the trip's versions, newest first (404 while the `versions` switch is off). */
export function useVersions(tripId: string) {
  return useQuery({
    queryKey: ["versions", tripId],
    queryFn: async () =>
      unwrap(
        await api().GET("/api/v1/trips/{trip_id}/versions", {
          params: { path: { trip_id: tripId } },
        }),
      ),
    retry: retryUnless404,
  });
}

/** API-37: save the current plan as a named version (§7.4: invalidate `versions`). */
export function useSaveVersion(tripId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: Schemas["VersionCreateIn"]) =>
      unwrap(
        await api().POST("/api/v1/trips/{trip_id}/versions", {
          params: { path: { trip_id: tripId } },
          body,
        }),
      ),
    onSettled: () =>
      queryClient.invalidateQueries({ queryKey: ["versions", tripId] }),
  });
}

/** API-38: restore a version (§7.4: invalidate `versions`, `itinerary`, `costs`, `summary`, `trip`). */
export function useRestoreVersion(tripId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      versionId,
      ...body
    }: {
      versionId: string;
      plan_revision: number;
    }) =>
      unwrap(
        await api().POST(
          "/api/v1/trips/{trip_id}/versions/{version_id}/restore",
          {
            params: { path: { trip_id: tripId, version_id: versionId } },
            body,
          },
        ),
      ),
    onSettled: () =>
      Promise.all(
        [
          ["versions", tripId],
          queryKeys.itinerary(tripId),
          queryKeys.costs(tripId),
          ["summary", tripId],
          queryKeys.trip(tripId),
        ].map((queryKey) => queryClient.invalidateQueries({ queryKey })),
      ),
  });
}

// IMP-602 trip actions
/** API-12: soft delete one trip (§7.4: invalidate `trips` and `latestItinerary`). */
export function useDeleteTrip(tripId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () =>
      unwrap(
        await api().DELETE("/api/v1/trips/{trip_id}", {
          params: { path: { trip_id: tripId } },
        }),
      ),
    onSuccess: async () => {
      queryClient.removeQueries({ queryKey: queryKeys.trip(tripId) });
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.trips() }),
        queryClient.invalidateQueries({
          queryKey: queryKeys.latestItinerary(),
        }),
      ]);
    },
  });
}

/** API-13: copy one trip with its plan (§7.4: invalidate `trips` and `latestItinerary`). */
export function useDuplicateTrip(tripId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () =>
      unwrap(
        await api().POST("/api/v1/trips/{trip_id}/duplicate", {
          params: { path: { trip_id: tripId } },
        }),
      ),
    onSuccess: async (trip) => {
      queryClient.setQueryData(queryKeys.trip(trip.id), trip);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.trips() }),
        queryClient.invalidateQueries({
          queryKey: queryKeys.latestItinerary(),
        }),
      ]);
    },
  });
}

// IMP-602 dashboard
/** API-08 for the dashboard: one page of trips, archived ones only when asked (FR-012 AC3). */
export function useTripList(includeArchived: boolean, limit = 20) {
  return useQuery({
    queryKey: queryKeys.trips({ limit, include_archived: includeArchived }),
    queryFn: async () =>
      unwrap(
        await api().GET("/api/v1/trips", {
          params: { query: { limit, include_archived: includeArchived } },
        }),
      ),
    placeholderData: keepPreviousData, // the filter toggle keeps the list on screen
  });
}

// IMP-601 profile
/** API-04: save the caller's profile fields (FR-004; §7.4: set `me`). */
export function useUpdateProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: Schemas["ProfilePatch"]) =>
      unwrap(await api().PATCH("/api/v1/me", { body })),
    onSuccess: (profile) => queryClient.setQueryData(queryKeys.me(), profile),
  });
}

// IMP-604 filter bar
/** The API-16 filters of IMP-604; unset filters are left out of the request. */
export type PlaceSearchQuery = Readonly<{
  q?: string;
  category?: string[];
  interest?: string[];
  price_max?: string;
  duration_max_min?: number;
  step_free?: boolean;
}>;
// The cast below is replaced by generated types after make openapi (the new filters are not in them).
type PlacesQuery =
  import("@/lib/api/schema").operations["search_places_api_v1_places_get"]["parameters"]["query"];

/** API-16 with the explore filters, a page at a time (key `['places', destinationId, filters]`). */
export function useFilteredPlacesPage(
  destinationId: string | undefined,
  filters: PlaceSearchQuery,
  offset: number,
) {
  return useQuery({
    queryKey: queryKeys.places(destinationId ?? "", {
      filters: JSON.stringify(filters),
      limit: EXPLORE_PAGE_SIZE,
      offset,
    }),
    queryFn: async () =>
      unwrap(
        await api().GET("/api/v1/places", {
          params: {
            query: {
              destination_id: destinationId ?? "",
              limit: EXPLORE_PAGE_SIZE,
              offset,
              ...filters,
            } as PlacesQuery,
          },
        }),
      ),
    enabled: destinationId !== undefined,
    placeholderData: keepPreviousData,
  });
}
