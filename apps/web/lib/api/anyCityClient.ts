import createClient from "openapi-fetch";

import { apiOrigin, authFetch } from "@/lib/api/client";
import type { components, paths } from "@/lib/api/any-city-schema";

/**
 * The any-city client (Amendment A2 §3.4): a second openapi-fetch client typed by
 * any-city-schema.d.ts, for API-76 to API-79. It shares the base URL, bearer token, request ID and
 * 401 handling of the main client (`authFetch`). Only hooks in queries.ts use it, and only while
 * `isEnabled("any_city_mode")`.
 */

export type AnyCitySchemas = components["schemas"];
export type CityCandidate = AnyCitySchemas["CityCandidate"];
export type LiveDestination = AnyCitySchemas["LiveDestinationOut"];
export type ImportState = AnyCitySchemas["ImportState"];

let client: ReturnType<typeof createClient<paths>> | undefined;

/** Created on first use, like `api()`, so tests and builds need no values. */
export function anyCityApi(): ReturnType<typeof createClient<paths>> {
  client ??= createClient<paths>({ baseUrl: apiOrigin(), fetch: authFetch });
  return client;
}
