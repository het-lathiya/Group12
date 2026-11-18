"use client";

import Link from "next/link";
import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";
import { useToast } from "@/components/fx";
import { useTrip } from "@/components/shell";
import { Empty, ErrorBox, LoadingCards } from "@/components/states";
import { Icon } from "@/components/ui";
import { api, ApiError, fmtDate, fmtTime, placePhoto, range, type EditResult } from "@/lib/api";
import { useLoad } from "@/lib/session";

export default function Edit() {
  const { tripId, reloadTrip } = useTrip();
  const toast = useToast();
  const it = useLoad(() => api.itinerary(tripId), [tripId]);
  const [busy, setBusy] = useState<string | null>(null);

  const apply = (r: EditResult) => it.setData((d) => d && ({ ...d, plan_revision: r.plan_revision, totals: r.totals, findings: r.findings, days: d.days.map((day) => r.changed_days.find((c) => c.day_number === day.day_number) ?? day) }));
  const run = async (key: string, fn: (rev: number) => Promise<EditResult>, msg: string) => {
    if (!it.data) return;
    setBusy(key);
    try { apply(await fn(it.data.plan_revision)); toast({ text: msg, icon: "check_circle" }); reloadTrip(); }
    catch (e) { const a = e as ApiError; toast({ text: a.message, icon: "error" }); if (a.code === "STALE_PLAN") it.reload(); }
    finally { setBusy(null); }
  };
  const validate = async () => {
    setBusy("validate");
    try { await api.validate(tripId); it.reload(); toast({ text: "Plan re-validated", icon: "fact_check" }); } catch (e) { toast({ text: (e as Error).message, icon: "error" }); } finally { setBusy(null); }
  };

  if (it.error) return (it.error as ApiError).code === "NOT_FOUND" ? <Empty icon="edit_note" title="Nothing to edit yet" text="Generate an itinerary first." action={<Link href={`/trips/${tripId}/generate/`} className="btn-primary"><Icon name="auto_awesome" />Generate</Link>} /> : <ErrorBox error={it.error} onRetry={it.reload} />;
  if (!it.data) return <LoadingCards n={3} h="h-48" />;
  const days = it.data.days;

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="card flex flex-wrap items-center justify-between gap-3 p-4">
        <div className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-coral-wash text-coral"><Icon name="edit_note" /></span>
          <div><p className="font-semibold">Edit itinerary</p><p className="text-xs text-muted">Move, retime, lock or remove stops. The server recalculates times and costs. Rev {it.data.plan_revision}.</p></div>
        </div>
        <motion.button whileTap={{ scale: 0.95 }} onClick={validate} disabled={busy !== null} className="btn-soft disabled:opacity-50"><Icon name="fact_check" className="!text-[16px]" />{busy === "validate" ? "Checking…" : "Validate plan"}</motion.button>
      </div>

      {days.map((day) => (
        <section key={day.day_number} className="card p-5">
          <div className="flex flex-wrap items-center gap-3">
            <span className="rounded-lg bg-slate px-2.5 py-1 text-xs font-bold text-white">Day {day.day_number}</span>
            <p className="flex-1 font-semibold">{day.theme ?? fmtDate(day.date)}</p>
            <span className="text-xs text-muted">{range(day.day_cost.min, day.day_cost.max, day.day_cost.currency)}</span>
          </div>
          <ul className="mt-4 space-y-2">
            <AnimatePresence initial={false}>
              {day.items.map((x, i) => (
                <motion.li key={x.id} layout initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, x: -30 }}
                  className={`flex flex-wrap items-center gap-3 rounded-xl border border-hair bg-canvas/60 p-2 ${busy?.startsWith(x.id) ? "opacity-50" : ""}`}>
                  <div className="flex flex-col">
                    <button onClick={() => run(x.id + "up", (rev) => api.moveItem(x.id, { plan_revision: rev, position: i, day_number: day.day_number }), "Moved up")} disabled={i === 0 || busy !== null || x.is_locked} className="text-muted disabled:opacity-30" aria-label="Move up"><Icon name="keyboard_arrow_up" /></button>
                    <button onClick={() => run(x.id + "dn", (rev) => api.moveItem(x.id, { plan_revision: rev, position: i + 2, day_number: day.day_number }), "Moved down")} disabled={i === day.items.length - 1 || busy !== null || x.is_locked} className="text-muted disabled:opacity-30" aria-label="Move down"><Icon name="keyboard_arrow_down" /></button>
                  </div>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={placePhoto(x.place.category, x.place.id)} alt="" className="h-12 w-12 rounded-lg object-cover" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold">{x.place.name}</p>
                    <p className="text-xs capitalize text-muted">{fmtTime(x.start_time)}–{fmtTime(x.end_time)} • {x.place.category} • {x.duration_min} min</p>
                  </div>
                  {days.length > 1 && (
                    <select value={day.day_number} disabled={busy !== null || x.is_locked} onChange={(e) => run(x.id + "day", (rev) => api.moveItem(x.id, { plan_revision: rev, day_number: +e.target.value }), `Moved to Day ${e.target.value}`)} className="rounded-lg border border-line bg-white px-2 py-1.5 text-xs" aria-label="Move to day">
                      {days.map((d) => <option key={d.day_number} value={d.day_number}>Day {d.day_number}</option>)}
                    </select>
                  )}
                  <input type="time" defaultValue={x.start_time} disabled={busy !== null || x.is_locked} onBlur={(e) => e.target.value !== x.start_time && run(x.id + "t", (rev) => api.moveItem(x.id, { plan_revision: rev, start_time: e.target.value }), "Time updated")} className="w-28 rounded-lg border border-line bg-white px-2 py-1.5 text-xs" aria-label="Start time" />
                  <button onClick={() => run(x.id + "lock", (rev) => api.moveItem(x.id, { plan_revision: rev, is_locked: !x.is_locked }), x.is_locked ? "Unlocked" : "Locked")} disabled={busy !== null} className={`rounded-lg p-1.5 hover:bg-white ${x.is_locked ? "text-coral" : "text-muted"}`} aria-label={x.is_locked ? "Unlock" : "Lock"}><Icon name={x.is_locked ? "lock" : "lock_open"} /></button>
                  <button onClick={() => run(x.id + "del", (rev) => api.deleteItem(x.id, rev), `Removed ${x.place.name}`)} disabled={busy !== null || x.is_locked} className="rounded-lg p-1.5 text-muted hover:bg-white hover:text-coral disabled:opacity-30" aria-label="Remove"><Icon name="delete" /></button>
                </motion.li>
              ))}
            </AnimatePresence>
          </ul>
          <Link href={`/trips/${tripId}/explore/`} className="mt-3 flex w-full items-center justify-center gap-1 rounded-xl border-2 border-dashed border-line py-2.5 text-sm font-semibold text-muted hover:border-coral hover:text-coral">
            <Icon name="add" />Add a stop from Explore
          </Link>
        </section>
      ))}
    </div>
  );
}
