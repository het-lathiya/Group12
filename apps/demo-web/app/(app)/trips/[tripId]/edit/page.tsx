"use client";

import { useState } from "react";
import { Icon } from "@/components/ui";
import { days as initial, type Day } from "@/lib/data";

export default function Edit() {
  const [days, setDays] = useState<Day[]>(initial);

  // TODO: PATCH/DELETE /api/v1/itinerary/items/{id}, POST /trips/{id}/itinerary/items, POST .../days/{n}/regenerate
  const move = (d: number, i: number, dir: -1 | 1) => setDays((ds) => ds.map((day, k) => {
    if (k !== d) return day;
    const s = [...day.stops]; const j = i + dir;
    if (j < 0 || j >= s.length) return day;
    [s[i], s[j]] = [s[j], s[i]];
    return { ...day, stops: s };
  }));
  const remove = (d: number, i: number) => setDays((ds) => ds.map((day, k) => (k === d ? { ...day, stops: day.stops.filter((_, j) => j !== i) } : day)));
  const setTime = (d: number, i: number, time: string) => setDays((ds) => ds.map((day, k) => (k === d ? { ...day, stops: day.stops.map((s, j) => (j === i ? { ...s, time } : s)) } : day)));

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="card flex flex-wrap items-center justify-between gap-3 p-4">
        <div className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-coral-wash text-coral"><Icon name="edit_note" /></span>
          <div><p className="font-semibold">Edit itinerary</p><p className="text-xs text-muted">Reorder, retime, remove or regenerate any day.</p></div>
        </div>
        <div className="flex gap-2">
          <button className="btn-soft"><Icon name="fact_check" className="!text-[16px]" />Validate plan</button>
          <button className="btn-primary"><Icon name="save" />Save version</button>
        </div>
      </div>

      {days.map((day, d) => (
        <section key={day.n} className="card p-5">
          <div className="flex flex-wrap items-center gap-3">
            <span className="rounded-lg bg-slate px-2.5 py-1 text-xs font-bold text-white">Day {day.n}</span>
            <input defaultValue={day.title} className="min-w-0 flex-1 rounded-lg px-2 py-1 font-semibold outline-none hover:bg-canvas focus:bg-canvas" />
            <button className="btn-soft !text-xs"><Icon name="autorenew" className="!text-[15px]" />Regenerate day</button>
          </div>
          <ul className="mt-4 space-y-2">
            {day.stops.map((s, i) => (
              <li key={s.id} className="flex items-center gap-3 rounded-xl border border-hair bg-canvas/60 p-2">
                <div className="flex flex-col">
                  <button onClick={() => move(d, i, -1)} disabled={i === 0} className="text-muted disabled:opacity-30" aria-label="Move up"><Icon name="keyboard_arrow_up" /></button>
                  <button onClick={() => move(d, i, 1)} disabled={i === day.stops.length - 1} className="text-muted disabled:opacity-30" aria-label="Move down"><Icon name="keyboard_arrow_down" /></button>
                </div>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={s.img} alt="" className="h-12 w-12 rounded-lg object-cover" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold">{s.name}</p>
                  <p className="text-xs text-muted">{s.category} • {s.price}</p>
                </div>
                <input value={s.time} onChange={(e) => setTime(d, i, e.target.value)} className="w-24 rounded-lg border border-line bg-white px-2 py-1.5 text-xs" aria-label="Time" />
                <button className="rounded-lg p-1.5 text-muted hover:bg-white" aria-label="Find alternative"><Icon name="swap_horiz" /></button>
                <button onClick={() => remove(d, i)} className="rounded-lg p-1.5 text-muted hover:bg-white hover:text-coral" aria-label="Remove"><Icon name="delete" /></button>
              </li>
            ))}
          </ul>
          <button className="mt-3 flex w-full items-center justify-center gap-1 rounded-xl border-2 border-dashed border-line py-2.5 text-sm font-semibold text-muted hover:border-coral hover:text-coral">
            <Icon name="add" />Add a stop
          </button>
        </section>
      ))}
    </div>
  );
}
