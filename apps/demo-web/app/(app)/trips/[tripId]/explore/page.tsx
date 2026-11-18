"use client";

import { AnimatePresence, motion } from "motion/react";
import { useEffect, useMemo, useState } from "react";
import { useToast } from "@/components/fx";
import { TripMap } from "@/components/map";
import { useTrip } from "@/components/shell";
import { ErrorBox, Skeleton } from "@/components/states";
import { Icon } from "@/components/ui";
import { api, categoryIcon, money, placePhoto, range, type Place } from "@/lib/api";
import { useLoad } from "@/lib/session";

const cats = [["", "All"], ["sight", "Sights"], ["museum", "Museums"], ["food", "Food"], ["nature", "Nature"], ["shopping", "Shopping"], ["religious", "Religious"], ["activity", "Activities"], ["saved", "Saved"]];

export default function Explore() {
  const { tripId, trip } = useTrip();
  const toast = useToast();
  const [cat, setCat] = useState("");
  const [q, setQ] = useState("");
  const [dq, setDq] = useState("");
  const [sel, setSel] = useState<Place | null>(null);
  useEffect(() => { const t = setTimeout(() => setDq(q), 300); return () => clearTimeout(t); }, [q]);
  const places = useLoad(trip && cat !== "saved" ? () => api.places({ destination_id: trip.destination_id, q: dq, category: cat || undefined, limit: 50 }) : null, [trip?.destination_id, dq, cat]);
  const saved = useLoad(tripId ? () => api.savedPlaces(tripId) : null, [tripId]);
  const savedIds = useMemo(() => new Set((saved.data ?? []).map((p) => p.id)), [saved.data]);
  const list = cat === "saved" ? (saved.data ?? []).filter((p) => p.name.toLowerCase().includes(q.toLowerCase())) : places.data?.items ?? [];
  const loading = cat === "saved" ? saved.loading : places.loading;
  const current = sel && list.find((p) => p.id === sel.id) ? sel : list[0];

  const toggle = async (p: Place) => {
    const was = savedIds.has(p.id);
    saved.setData((s) => was ? (s ?? []).filter((x) => x.id !== p.id) : [...(s ?? []), p]);
    try { if (was) await api.unsavePlace(tripId, p.id); else await api.savePlace(tripId, p.id); toast({ text: was ? `Removed ${p.name}` : `Saved ${p.name}`, icon: "bookmark" }); }
    catch (e) { saved.reload(); toast({ text: (e as Error).message, icon: "error" }); }
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
      <div className="min-w-0">
        <div className="relative">
          <Icon name="search" className="absolute left-4 top-3.5 text-muted" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={`Search curated places in ${trip?.destination.name ?? "…"}`} className="input pl-11" />
          {places.loading && cat !== "saved" && <span className="absolute right-4 top-4 h-4 w-4 animate-spin rounded-full border-2 border-coral/30 border-t-coral" />}
        </div>
        <div className="no-scrollbar mt-4 flex gap-2 overflow-x-auto">
          {cats.map(([v, l]) => (
            <button key={v} onClick={() => setCat(v)} className={`relative shrink-0 rounded-full border px-3 py-1 text-xs font-semibold ${cat === v ? "border-slate text-white" : "border-line bg-white text-body"}`}>
              {cat === v && <motion.span layoutId="excat" className="absolute inset-0 rounded-full bg-slate" />}
              <span className="relative">{l}{v === "saved" && ` (${savedIds.size})`}</span>
            </button>
          ))}
        </div>
        {places.error && cat !== "saved" && <div className="mt-4"><ErrorBox error={places.error} onRetry={places.reload} /></div>}
        <p className="mt-4 text-xs text-muted">{loading ? "Searching…" : `${list.length} place${list.length === 1 ? "" : "s"}${cat !== "saved" && places.data ? ` of ${places.data.total}` : ""}`}</p>
        <motion.div layout className="mt-3 grid gap-4 sm:grid-cols-2">
          {loading && list.length === 0 && [0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-60" />)}
          <AnimatePresence mode="popLayout">
            {list.map((p, i) => (
              <motion.article key={p.id} layout initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95 }} transition={{ delay: Math.min(i, 8) * 0.03 }}
                onClick={() => setSel(p)} whileHover={{ y: -4 }} className={`card cursor-pointer overflow-hidden ${current?.id === p.id ? "ring-2 ring-coral/40" : ""}`}>
                <div className="group relative h-36 overflow-hidden">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={placePhoto(p.category, p.id)} alt="" className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-110" />
                  <motion.button whileTap={{ scale: 1.4 }} onClick={(e) => { e.stopPropagation(); toggle(p); }} className="glass absolute right-2 top-2 grid h-8 w-8 place-items-center rounded-full" aria-label="Save place">
                    <Icon name="bookmark" fill={savedIds.has(p.id)} className={`!text-[16px] ${savedIds.has(p.id) ? "text-coral" : ""}`} />
                  </motion.button>
                  {p.verification_status === "curated_checked" && <span className="absolute left-2 top-2 badge-mint !bg-white">✓ Curated</span>}
                </div>
                <div className="p-4">
                  <p className="label flex items-center gap-1 text-coral"><Icon name={categoryIcon[p.category] ?? "place"} className="!text-[13px]" />{p.category}</p>
                  <p className="mt-1 font-semibold">{p.name}</p>
                  <div className="mt-2 flex items-center justify-between text-xs text-body">
                    <span>{p.typical_duration_min} min{p.suitability.step_free ? " • step-free" : ""}{p.suitability.child_friendly ? " • kids" : ""}</span>
                    <span>{p.price ? (p.price.max && p.price.max !== p.price.min ? range(p.price.min, p.price.max, p.price.currency) : money(p.price.min, p.price.currency)) : "—"}</span>
                  </div>
                </div>
              </motion.article>
            ))}
          </AnimatePresence>
        </motion.div>
        {!loading && list.length === 0 && <p className="py-10 text-center text-muted">{cat === "saved" ? "No saved places yet. Tap the bookmark on any place." : "No places match."}</p>}
      </div>
      <aside className="card h-[420px] overflow-hidden p-0 lg:sticky lg:top-20 lg:h-[calc(100vh-7rem)]">
        <div className="relative h-full">
          <TripMap route={false} pins={list.map((p) => ({ id: p.id, lat: p.lat, lon: p.lon, color: savedIds.has(p.id) ? "#b52603" : "#ff5a36" }))} selected={current?.id} onSelect={(id) => setSel(list.find((x) => x.id === id) ?? null)} />
          {current && (
            <AnimatePresence mode="wait">
              <motion.div key={current.id} initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="glass absolute left-3 right-14 top-3 rounded-xl p-3 shadow-lg">
                <p className="text-sm font-bold">{current.name}</p>
                <p className="text-xs capitalize text-muted">{current.category} • {current.tags.slice(0, 3).join(", ")}</p>
              </motion.div>
            </AnimatePresence>
          )}
        </div>
      </aside>
    </div>
  );
}
