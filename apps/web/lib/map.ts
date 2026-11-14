/** OpenFreeMap's public vector style (§9); no key. Terms and attribution: docs/decisions/map-tiles.md. */
export const OPENFREEMAP_STYLE_URL =
  "https://tiles.openfreemap.org/styles/liberty";

/**
 * The MapLibre worker as a bundled asset. MapLibre 6 derives its worker URL from its own
 * `import.meta.url`, which the production bundle turns into a `file:` URL, so the worker would
 * not load; the map is given this served URL instead (`setWorkerUrl`). Bundling it from the
 * installed package keeps the worker on the same version as the library.
 */
export const MAPLIBRE_WORKER_URL = new URL(
  "../node_modules/maplibre-gl/dist/maplibre-gl-worker.mjs",
  import.meta.url,
).href;
