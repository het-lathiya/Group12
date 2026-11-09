"use client";

import { useEffect, useRef, useState } from "react";
import maplibregl, { type Map as MapLibreMap, type Marker } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

import type { components } from "@/lib/api/schema";
import { MapListFallback } from "@/components/map/MapListFallback";

type Item = components["schemas"]["Item"];

// OpenFreeMap's public style; no API key is required.
export const MAP_STYLE_URL = "https://tiles.openfreemap.org/styles/liberty";

function focusItem(itemId: string) {
  const target = document.getElementById(`item-${itemId}`);
  target?.scrollIntoView({ behavior: "smooth", block: "center" });
  target?.focus();
}

export function MapPanel({ items }: { items: Item[] }) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const markersRef = useRef<Marker[]>([]);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!container.current || items.length === 0) return;
    if (!maplibregl.supported()) {
      setFailed(true);
      return;
    }

    let disposed = false;
    let map: MapLibreMap;
    try {
      map = new maplibregl.Map({
        container: container.current,
        style: MAP_STYLE_URL,
        center: [items[0].place.lon, items[0].place.lat],
        zoom: 12,
        attributionControl: true,
      });
    } catch {
      setFailed(true);
      return;
    }
    mapRef.current = map;

    map.on("error", () => {
      if (!disposed) setFailed(true);
    });

    map.once("load", () => {
      if (disposed) return;
      const bounds = new maplibregl.LngLatBounds();
      items.forEach((item, index) => {
        const markerButton = document.createElement("button");
        markerButton.type = "button";
        markerButton.className =
          "flex size-8 items-center justify-center rounded-full border-2 border-white bg-slate-900 text-sm font-bold text-white shadow-lg";
        markerButton.textContent = String(index + 1);
        markerButton.setAttribute(
          "aria-label",
          `Stop ${index + 1}: ${item.place.name}`,
        );
        markerButton.addEventListener("click", () => focusItem(item.id));
        const marker = new maplibregl.Marker({ element: markerButton })
          .setLngLat([item.place.lon, item.place.lat])
          .addTo(map);
        markersRef.current.push(marker);
        bounds.extend([item.place.lon, item.place.lat]);
      });

      if (items.length > 1) {
        map.fitBounds(bounds, { padding: 48, maxZoom: 14 });
        // Straight segments intentionally represent visit order, not routed geometry.
        map.addSource("visit-order", {
          type: "geojson",
          data: {
            type: "Feature",
            properties: {},
            geometry: {
              type: "LineString",
              coordinates: items.map((item) => [item.place.lon, item.place.lat]),
            },
          },
        });
        map.addLayer({
          id: "visit-order-line",
          type: "line",
          source: "visit-order",
          paint: { "line-color": "#475569", "line-width": 2, "line-dasharray": [2, 2] },
        });
      }
    });

    return () => {
      disposed = true;
      markersRef.current.forEach((marker) => marker.remove());
      markersRef.current = [];
      map.remove();
      mapRef.current = null;
    };
  }, [items]);

  if (failed) return <MapListFallback items={items} />;
  if (items.length === 0) {
    return <MapListFallback items={items} reason="No places to show on the map yet." />;
  }

  return (
    <section aria-label="Itinerary map" className="flex flex-col gap-2">
      <div
        ref={container}
        aria-label="Map with numbered itinerary stops"
        className="h-[420px] min-h-[320px] w-full overflow-hidden rounded-xl border bg-muted"
      />
      <p className="text-xs text-muted-foreground">
        Map tiles © OpenStreetMap contributors · Markers follow visit order; connecting lines are illustrative, not routes.
      </p>
    </section>
  );
}
