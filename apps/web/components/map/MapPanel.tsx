"use client";

import "maplibre-gl/dist/maplibre-gl.css";

import {
  type GeoJSONSource,
  LngLatBounds,
  Map as MapLibreMap,
  Marker,
  setWorkerUrl,
} from "maplibre-gl";
import { useEffect, useEffectEvent, useMemo, useRef, useState } from "react";

import { MapListFallback } from "@/components/map/MapListFallback";
import type { components } from "@/lib/api/schema";
import { MAPLIBRE_WORKER_URL, OPENFREEMAP_STYLE_URL } from "@/lib/map";

type Item = components["schemas"]["Item"];

export type MapPanelProps = {
  /** The selected day's items as API-24 returns them; numbered in position order. */
  items: Item[];
  /** The item whose card was selected last; its marker is highlighted. */
  selectedItemId: string | null;
  /** A marker or list entry was chosen: the page scrolls to and focuses that item's card. */
  onSelectItem: (itemId: string) => void;
};

const OSM_CREDIT =
  '<a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">© OpenStreetMap contributors</a>';
const LINE = "visit-order";
// The primary token (guide §2): map paint cannot read the CSS theme variables.
const LINE_COLOR = "#0F766E";
const MARKER_CLASS =
  "flex size-8 cursor-pointer items-center justify-center rounded-full border-2 border-card bg-primary text-sm font-semibold text-primary-foreground tabular-nums shadow-md outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 aria-[current=true]:bg-foreground aria-[current=true]:ring-2 aria-[current=true]:ring-primary";

function webglAvailable(): boolean {
  try {
    const canvas = document.createElement("canvas");
    return Boolean(canvas.getContext("webgl2") ?? canvas.getContext("webgl"));
  } catch {
    return false;
  }
}

const lineOf = (stops: Item[]): GeoJSON.Feature<GeoJSON.LineString> => ({
  type: "Feature",
  properties: {},
  geometry: {
    type: "LineString",
    coordinates: stops.map(({ place }) => [place.lon, place.lat]),
  },
});

/**
 * FR-080 (§7.5.7): the selected day on an OpenFreeMap map, one numbered marker per stop in visit
 * order with straight segments between them (no routing geometry in the MVP). Positions come from
 * API-24 only (no geocoding). A style or tile error, or no WebGL, swaps in MapListFallback.
 * Loaded with next/dynamic and ssr false: MapLibre needs the browser.
 */
export function MapPanel(props: MapPanelProps) {
  const [failed, setFailed] = useState(() => !webglAvailable());
  // TanStack Query keeps `items` identical across refetches when nothing changed, so the markers
  // (and the map's fit) are redrawn only when the day's stops really change.
  const stops = useMemo(
    () => [...props.items].sort((a, b) => a.position - b.position),
    [props.items],
  );
  if (failed) {
    return <MapListFallback items={stops} onSelectItem={props.onSelectItem} />;
  }
  return <LiveMap {...props} stops={stops} onFail={() => setFailed(true)} />;
}

function LiveMap({
  stops,
  selectedItemId,
  onSelectItem,
  onFail,
}: MapPanelProps & { stops: Item[]; onFail: () => void }) {
  const container = useRef<HTMLDivElement>(null);
  const markers = useRef(new Map<string, HTMLButtonElement>());
  const [map, setMap] = useState<MapLibreMap | null>(null);
  const fail = useEffectEvent(onFail);
  const select = useEffectEvent(onSelectItem);

  useEffect(() => {
    if (!container.current) return;
    let instance: MapLibreMap;
    try {
      setWorkerUrl(MAPLIBRE_WORKER_URL);
      instance = new MapLibreMap({
        container: container.current,
        style: OPENFREEMAP_STYLE_URL,
        // The credit is ours, not the remote style's; the style's own attributions stay.
        attributionControl: {
          compact: false,
          customAttribution: OSM_CREDIT,
        },
      });
    } catch {
      fail();
      return;
    }
    instance.on("error", () => fail());
    instance.once("load", () => {
      instance.addSource(LINE, { type: "geojson", data: lineOf([]) });
      instance.addLayer({
        id: LINE,
        type: "line",
        source: LINE,
        paint: { "line-color": LINE_COLOR, "line-width": 3 },
      });
      setMap(instance);
    });
    return () => instance.remove();
  }, []);

  useEffect(() => {
    if (!map) return;
    const added = stops.map((item, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = MARKER_CLASS;
      button.textContent = String(index + 1);
      button.setAttribute(
        "aria-label",
        `Stop ${index + 1}: ${item.place.name}`,
      );
      button.addEventListener("click", () => select(item.id));
      markers.current.set(item.id, button);
      return new Marker({ element: button })
        .setLngLat([item.place.lon, item.place.lat])
        .addTo(map);
    });
    map.getSource<GeoJSONSource>(LINE)?.setData(lineOf(stops));
    if (stops.length) {
      const bounds = new LngLatBounds();
      stops.forEach(({ place }) => bounds.extend([place.lon, place.lat]));
      map.fitBounds(bounds, { padding: 48, maxZoom: 15, duration: 0 });
    }
    const owned = markers.current;
    return () => {
      added.forEach((marker) => marker.remove());
      owned.clear();
    };
  }, [map, stops]);

  useEffect(() => {
    markers.current.forEach((button, id) =>
      button.setAttribute("aria-current", String(id === selectedItemId)),
    );
  }, [map, stops, selectedItemId]);

  return (
    <div
      ref={container}
      className="h-80 w-full overflow-hidden rounded-xl border bg-muted xl:h-96"
    />
  );
}
