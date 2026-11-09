# Map tiles and attribution

## Provider

- Provider: OpenFreeMap
- Style URL: https://tiles.openfreemap.org/styles/liberty
- API key: none required by the configured public style URL
- Status: **Unverified**
- Terms checked date: Not checked yet
- Reviewer / evidence: Pending team review

## Attribution shown in the UI

The map displays: “Map tiles © OpenStreetMap contributors”.

OpenStreetMap data attribution is included in the map panel and MapLibre's attribution control remains enabled. Before release, the team must verify the current OpenFreeMap usage terms, service availability, attribution requirements, and suitability for the intended traffic.

## Failure behaviour

If WebGL is unavailable, MapLibre cannot initialize, or the map emits a tile/style error, the UI replaces the map with the ordered MapListFallback. The itinerary list remains usable and each numbered fallback entry focuses the corresponding item card.

## Scope

The connecting line between stops is a straight visual segment in visit order. It is not a route, does not encode travel time, and must not be presented as navigation guidance.
