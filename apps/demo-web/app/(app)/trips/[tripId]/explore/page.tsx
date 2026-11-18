"use client";

import { useState } from "react";
import { Icon } from "@/components/ui";
import { TripMap } from "@/components/map";
import { useToast } from "@/components/fx";
import { picks, places, trip } from "@/lib/data";

const cats = ["All", "Sights", "Food", "Stays", "Hidden gems", "Saved"];
const all = [
  ...places.map((p) => ({ name: p.name, kind: p.category, img: p.img, rating: p.rating ?? 4.5, price: p.price, lat: p.lat, lon: p.lon })),
  ...picks.map((p) => ({ name: p.name, kind: p.kind, img: p.img, rating: p.rating, price: p.price, lat: trip.city.lat, lon: trip.city.lon })),
];

export default function Explore() {
  const [cat, setCat] = useState("All");
  const [q, setQ] = useState("");
  const [saved, setSaved] = useState<string[]>(["Amber Fort"]);
  const [sel, setSel] = useState(all[0]);
  const toast = useToast();
  // TODO: GET /api/v1/places?q=&category= and PUT/DELETE /trips/{id}/saved-places/{place_id}
  const list = all.filter((p) => (cat === "Saved" ? saved.includes(p.name) : true) && p.name.toLowerCase().includes(q.toLowerCase()));

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
      <div className="min-w-0">
        <div className="relative">
          <Icon name="search" className="absolute left-4 top-3.5 text-muted" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={`Search places in ${trip.city.name}…`} className="input pl-11" />
        </div>
        <div className="no-scrollbar mt-4 flex gap-2 overflow-x-auto">
          {cats.map((c) => <button key={c} onClick={() => setCat(c)} className={`chip shrink-0 ${cat === c ? "chip-active" : ""}`}>{c}{c === "Saved" && ` (${saved.length})`}</button>)}
        </div>
        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          {list.map((p) => (
            <article key={p.name} onClick={() => setSel(p)} className={`card card-hover cursor-pointer overflow-hidden ${sel.name === p.name ? "ring-2 ring-coral/40" : ""}`}>
              <div className="relative h-40">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={p.img} alt="" className="h-full w-full object-cover" />
                <button onClick={(e) => { e.stopPropagation(); setSaved((s) => s.includes(p.name) ? s.filter((x) => x !== p.name) : [...s, p.name]); toast({ text: saved.includes(p.name) ? `Removed ${p.name}` : `Saved ${p.name}`, icon: "bookmark" }); }}
                  className="glass absolute right-2 top-2 grid h-8 w-8 place-items-center rounded-full" aria-label="Save place">
                  <Icon name="bookmark" fill={saved.includes(p.name)} className={`!text-[16px] ${saved.includes(p.name) ? "text-coral" : ""}`} />
                </button>
              </div>
              <div className="p-4">
                <p className="label text-coral">{p.kind}</p>
                <p className="mt-1 font-semibold">{p.name}</p>
                <div className="mt-2 flex items-center justify-between text-xs text-body">
                  <span className="flex items-center gap-0.5"><Icon name="star" fill className="!text-[14px] text-amber-400" />{p.rating}</span>
                  <span>{p.price}</span>
                </div>
              </div>
            </article>
          ))}
          {list.length === 0 && <p className="col-span-full py-10 text-center text-muted">No places match.</p>}
        </div>
      </div>
      <aside className="card h-[420px] overflow-hidden p-0 lg:sticky lg:top-20 lg:h-[calc(100vh-7rem)]">
        <div className="relative h-full">
          <TripMap route={false} pins={list.map((p) => ({ id: p.name, lat: p.lat + (p.lat === trip.city.lat ? (p.name.length % 7) * 0.004 : 0), lon: p.lon + (p.lon === trip.city.lon ? (p.name.length % 5) * 0.005 : 0) }))} selected={sel.name} onSelect={(id) => setSel(all.find((x) => x.name === id) ?? sel)} />
          <div className="glass absolute left-3 right-14 top-3 rounded-xl p-3 shadow-lg">
            <p className="text-sm font-bold">{sel.name}</p>
            <p className="text-xs text-muted">{sel.kind} • {sel.price}</p>
          </div>
        </div>
      </aside>
    </div>
  );
}
