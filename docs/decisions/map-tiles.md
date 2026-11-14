# Map tiles

Recorded for IMP-508 (FR-080). The itinerary map uses MapLibre GL JS with OpenFreeMap vector tiles (§9, "OpenFreeMap tiles + MapLibre GL JS").

| Item                   | Value                                                                                                                                                                                           |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Provider               | OpenFreeMap                                                                                                                                                                                     |
| Style URL              | `https://tiles.openfreemap.org/styles/liberty` (constant `OPENFREEMAP_STYLE_URL` in `apps/web/lib/map.ts`)                                                                                      |
| Key                    | None                                                                                                                                                                                            |
| Terms, as stated in §9 | No stated limit; no uptime guarantee; attribution required                                                                                                                                      |
| Attribution text       | The attribution carried by the style (expected to credit OpenFreeMap, OpenMapTiles and OpenStreetMap contributors), shown by MapLibre's attribution control, always expanded (`compact: false`) |
| Checked on             | Not checked                                                                                                                                                                                     |
| Status                 | **Unverified**                                                                                                                                                                                  |

## To verify

A team member opens the OpenFreeMap site and terms and the OpenStreetMap copyright page, confirms the usage terms, the exact attribution wording and that the style's attribution shows on the rendered map, then records the date, their name and the result here and sets the status to Verified. Until then nothing in the app or the documents claims the terms were checked.

## Behaviour that does not depend on the provider

- Markers and the straight segments between consecutive stops use the place coordinates from API-24 only; there is no geocoding and no routing geometry. The segments show visit order, not a route.
- A style or tile load error, or a browser without WebGL, replaces the map with the numbered list (MapListFallback) and the notice "Map unavailable; list view shown". No task needs the map.
