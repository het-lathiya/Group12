# OpenRouteService format fixtures

These files are format fixtures, not live recordings. No ORS key exists yet, so they were written by hand to the JSON response format of the OpenRouteService directions documentation (`POST /v2/directions/{profile}/json`: `bbox`, `routes[]` with `summary.distance` in metres and `summary.duration` in seconds, `metadata`).

Replace them with real recordings once the ORS key exists (IMP-113). No key belongs in any file here.

- `directions_foot_walking.json`: a successful `foot-walking` answer.
- `directions_driving_car.json`: a successful `driving-car` answer.
- `directions_error_no_route.json`: an error body, sent with HTTP 404.
