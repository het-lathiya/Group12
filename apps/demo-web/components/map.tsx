"use client";

import { motion } from "motion/react";
import { useEffect, useMemo, useRef, useState } from "react";

export type Pin = { id: string; lat: number; lon: number; label?: string; color?: string };

const project = (lat: number, lon: number, z: number) => {
  const n = 256 * 2 ** z;
  const r = (lat * Math.PI) / 180;
  return { x: ((lon + 180) / 360) * n, y: ((1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2) * n };
};

function fitZoom(pins: Pin[], w: number, h: number) {
  if (pins.length < 2) return 15;
  for (let z = 16; z >= 6; z--) {
    const ps = pins.map((p) => project(p.lat, p.lon, z));
    const dx = Math.max(...ps.map((p) => p.x)) - Math.min(...ps.map((p) => p.x));
    const dy = Math.max(...ps.map((p) => p.y)) - Math.min(...ps.map((p) => p.y));
    if (dx < w * 0.7 && dy < h * 0.65) return z;
  }
  return 6;
}

/** Lightweight pan/zoom OSM map with numbered pins and a route line. */
export function TripMap({ pins, selected, onSelect, route = true }: { pins: Pin[]; selected?: string; onSelect?: (id: string) => void; route?: boolean }) {
  const box = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 600, h: 400 });
  const [zoom, setZoom] = useState(14);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const drag = useRef<{ x: number; y: number; px: number; py: number } | null>(null);

  useEffect(() => {
    const el = box.current; if (!el) return;
    const ro = new ResizeObserver(() => setSize({ w: el.clientWidth, h: el.clientHeight }));
    ro.observe(el); return () => ro.disconnect();
  }, []);

  const key = pins.map((p) => p.id).join();
  useEffect(() => { setZoom(fitZoom(pins, size.w, size.h)); setPan({ x: 0, y: 0 }); }, [key, size.w, size.h]); // eslint-disable-line react-hooks/exhaustive-deps

  // centre on selection
  useEffect(() => {
    const s = pins.find((p) => p.id === selected); if (!s || pins.length === 0) return;
    const c = centre(pins, zoom); const sp = project(s.lat, s.lon, zoom);
    setPan({ x: c.x - sp.x, y: c.y - sp.y });
  }, [selected]); // eslint-disable-line react-hooks/exhaustive-deps

  const { tiles, pts, cx, cy } = useMemo(() => {
    const c = centre(pins, zoom);
    const cx = c.x - pan.x, cy = c.y - pan.y;
    const left = cx - size.w / 2, top = cy - size.h / 2;
    const t0x = Math.floor(left / 256), t0y = Math.floor(top / 256);
    const t1x = Math.floor((left + size.w) / 256), t1y = Math.floor((top + size.h) / 256);
    const tiles: { k: string; src: string; x: number; y: number }[] = [];
    const max = 2 ** zoom;
    for (let ty = t0y; ty <= t1y; ty++) for (let tx = t0x; tx <= t1x; tx++) {
      if (ty < 0 || ty >= max) continue;
      tiles.push({ k: `${zoom}/${tx}/${ty}`, src: `https://tile.openstreetmap.org/${zoom}/${((tx % max) + max) % max}/${ty}.png`, x: tx * 256 - left, y: ty * 256 - top });
    }
    const pts = pins.map((p) => { const q = project(p.lat, p.lon, zoom); return { ...p, x: q.x - left, y: q.y - top }; });
    return { tiles, pts, cx, cy };
  }, [pins, zoom, pan, size]);
  void cx; void cy;

  return (
    <div ref={box} className="relative h-full w-full touch-none select-none overflow-hidden bg-[#e8eef5]"
      onPointerDown={(e) => { drag.current = { x: e.clientX, y: e.clientY, px: pan.x, py: pan.y }; (e.target as HTMLElement).setPointerCapture?.(e.pointerId); }}
      onPointerMove={(e) => { const d = drag.current; if (d) setPan({ x: d.px + e.clientX - d.x, y: d.py + e.clientY - d.y }); }}
      onPointerUp={() => (drag.current = null)}
      onWheel={(e) => setZoom((z) => Math.max(6, Math.min(18, z + (e.deltaY < 0 ? 1 : -1))))}
      style={{ cursor: drag.current ? "grabbing" : "grab" }}>
      {tiles.map((t) => (
        // eslint-disable-next-line @next/next/no-img-element
        <img key={t.k} src={t.src} alt="" draggable={false} className="absolute h-64 w-64 max-w-none" style={{ left: t.x, top: t.y }} />
      ))}

      {route && pts.length > 1 && (
        <svg className="pointer-events-none absolute inset-0 h-full w-full">
          <motion.polyline key={key + zoom} points={pts.map((p) => `${p.x},${p.y}`).join(" ")} fill="none" stroke="#0f172a" strokeWidth={3} strokeDasharray="7 6" strokeLinecap="round"
            initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1.2, ease: "easeInOut" }} opacity={0.7} />
        </svg>
      )}

      {pts.map((p, i) => {
        const on = p.id === selected;
        return (
          <motion.button key={p.id} onPointerDown={(e) => e.stopPropagation()} onClick={() => onSelect?.(p.id)}
            initial={{ scale: 0, y: -20 }} animate={{ scale: on ? 1.25 : 1, y: 0 }} transition={{ type: "spring", stiffness: 400, damping: 18, delay: i * 0.06 }}
            className="absolute -translate-x-1/2 -translate-y-1/2" style={{ left: p.x, top: p.y, zIndex: on ? 20 : 10 }} aria-label={p.label ?? `Stop ${i + 1}`}>
            {on && <span className="absolute inset-0 -m-2 animate-ping rounded-full bg-coral/40" />}
            <span className={`relative grid h-8 w-8 place-items-center rounded-full border-[3px] border-white text-xs font-bold text-white shadow-lg ${on ? "bg-coral-deep" : ""}`}
              style={{ background: on ? undefined : p.color ?? "#ff5a36" }}>{p.label ?? i + 1}</span>
          </motion.button>
        );
      })}

      <div className="absolute right-3 top-3 flex flex-col overflow-hidden rounded-xl bg-white shadow-md">
        <button onPointerDown={(e) => e.stopPropagation()} onClick={() => setZoom((z) => Math.min(18, z + 1))} className="grid h-8 w-8 place-items-center hover:bg-canvas" aria-label="Zoom in"><span className="ms">add</span></button>
        <button onPointerDown={(e) => e.stopPropagation()} onClick={() => setZoom((z) => Math.max(6, z - 1))} className="grid h-8 w-8 place-items-center border-t border-hair hover:bg-canvas" aria-label="Zoom out"><span className="ms">remove</span></button>
        <button onPointerDown={(e) => e.stopPropagation()} onClick={() => { setZoom(fitZoom(pins, size.w, size.h)); setPan({ x: 0, y: 0 }); }} className="grid h-8 w-8 place-items-center border-t border-hair hover:bg-canvas" aria-label="Fit all"><span className="ms">my_location</span></button>
      </div>
      <span className="absolute bottom-1 left-1 rounded bg-white/80 px-1 text-[9px] text-muted">© OpenStreetMap</span>
    </div>
  );
}

function centre(pins: Pin[], z: number) {
  if (!pins.length) return project(26.92, 75.82, z);
  const ps = pins.map((p) => project(p.lat, p.lon, z));
  return { x: (Math.min(...ps.map((p) => p.x)) + Math.max(...ps.map((p) => p.x))) / 2, y: (Math.min(...ps.map((p) => p.y)) + Math.max(...ps.map((p) => p.y))) / 2 };
}
