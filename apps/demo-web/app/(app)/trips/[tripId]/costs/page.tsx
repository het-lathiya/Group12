"use client";

import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";
import { useToast } from "@/components/fx";
import { useTrip } from "@/components/shell";
import { Empty, ErrorBox, LoadingCards } from "@/components/states";
import { Icon } from "@/components/ui";
import { api, ApiError, categoryIcon, money, range } from "@/lib/api";
import { useLoad } from "@/lib/session";

const catColor: Record<string, string> = { accommodation: "#ff5a36", food: "#059669", transport: "#0f172a", activities: "#6366f1", other: "#f59e0b", contingency: "#94a3b8" };

export default function Costs() {
  const { tripId } = useTrip();
  const toast = useToast();
  const c = useLoad(() => api.costs(tripId), [tripId]);
  const [hover, setHover] = useState<string | null>(null);
  const [openDay, setOpenDay] = useState<number | null>(1);
  const [pct, setPct] = useState(10);
  const [stay, setStay] = useState("");
  const [saving, setSaving] = useState(false);
  useEffect(() => { if (c.data) { setPct(c.data.settings.contingency_pct); setStay(c.data.settings.stay_budget_per_night ?? ""); } }, [c.data]);

  if (c.error) return (c.error as ApiError).code === "NOT_FOUND" ? <Empty icon="payments" title="No costs yet" text="Generate an itinerary first; costs are calculated from it." /> : <ErrorBox error={c.error} onRetry={c.reload} />;
  if (!c.data) return <LoadingCards n={3} h="h-48" />;
  const d = c.data, cur = d.currency;
  const lines = d.by_category.filter((x) => parseFloat(x.max) > 0);
  const totalMax = lines.reduce((s, x) => s + parseFloat(x.max), 0) || 1;
  const R = 70, C = 2 * Math.PI * R;
  let acc = 0;
  const segs = lines.map((x) => { const f = parseFloat(x.max) / totalMax; const s = { ...x, f, off: acc }; acc += f; return s; });
  const active = segs.find((s) => s.category === hover);
  const ratio = d.budget.ratio_pct ?? 0;
  const maxDay = Math.max(1, ...d.by_day.map((x) => parseFloat(x.max)));

  const save = async () => {
    setSaving(true);
    try { await api.updateBudget(tripId, { contingency_pct: pct, stay_budget_per_night: stay ? String(stay) : null }); toast({ text: "Budget settings saved. Totals recalculated.", icon: "savings" }); c.reload(); }
    catch (e) { toast({ text: (e as Error).message, icon: "error" }); } finally { setSaving(false); }
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="card p-5">
          <p className="label text-muted">Planning total</p><p className="mt-2 text-3xl font-extrabold">{money(d.planning_total, cur)}</p>
          <p className="text-xs text-muted">Range {range(d.estimate.min, d.estimate.max, cur)} • incl. {d.contingency.pct}% contingency</p>
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.06 }} className="card p-5">
          <p className="label text-muted">Budget</p><p className="mt-2 text-3xl font-extrabold">{d.budget.amount ? money(d.budget.amount, cur) : "Not set"}</p>
          {d.budget.amount && <>
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-sky"><motion.div className={`h-full rounded-full ${d.budget.status === "exceeded" ? "bg-coral" : d.budget.status === "near" ? "bg-amber-400" : "bg-mint"}`} initial={{ width: 0 }} animate={{ width: `${Math.min(100, ratio)}%` }} transition={{ type: "spring", stiffness: 120, damping: 20 }} /></div>
            <p className="mt-1 text-xs text-muted">{ratio}% used</p></>}
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.12 }} className="card p-5">
          <p className="label text-muted">Per traveller</p><p className="mt-2 text-3xl font-extrabold">{money(d.per_traveller.largest_share, cur)}</p>
          {d.budget.status === "exceeded" ? <span className="mt-1 inline-flex items-center gap-1 rounded-full bg-coral-wash px-2 py-0.5 text-[11px] font-bold text-coral"><Icon name="warning" className="!text-[13px]" />Over by {money(d.budget.excess, cur)}</span>
            : d.budget.status === "near" ? <span className="mt-1 inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-bold text-amber-700">Close to budget</span>
            : <span className="badge-mint mt-1"><Icon name="check_circle" className="!text-[13px]" />{d.per_traveller.travellers} traveller{d.per_traveller.travellers > 1 ? "s" : ""}</span>}
        </motion.div>
      </div>

      {d.alerts.length > 0 && (
        <div className="space-y-2">{d.alerts.map((a) => <p key={a.id} className={`flex gap-2 rounded-xl p-3 text-sm ${a.severity === "error" ? "bg-coral-wash text-coral-deep" : "bg-amber-50 text-amber-800"}`}><Icon name="warning" className="!text-[16px]" />{a.message}</p>)}</div>
      )}
      {!d.complete && <p className="flex gap-2 rounded-xl bg-sky p-3 text-[13px] text-body"><Icon name="info" className="!text-[16px]" />{d.incomplete_items.length} item(s) have no price, so the total may be higher.</p>}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        <section className="card p-6">
          <h2 className="font-semibold">By category</h2>
          <div className="relative mx-auto mt-4 h-52 w-52">
            <svg viewBox="0 0 180 180" className="h-full w-full -rotate-90">
              <circle cx="90" cy="90" r={R} fill="none" stroke="#eff4ff" strokeWidth="22" />
              {segs.map((s, i) => (
                <motion.circle key={s.category} cx="90" cy="90" r={R} fill="none" stroke={catColor[s.category] ?? "#64748b"}
                  strokeDashoffset={-s.off * C} initial={{ strokeDasharray: `0 ${C}` }}
                  animate={{ strokeDasharray: `${Math.max(0, s.f * C - 2)} ${C}`, strokeWidth: hover === s.category ? 30 : 22, opacity: hover && hover !== s.category ? 0.35 : 1 }}
                  transition={{ duration: 0.8, delay: i * 0.1 }} onMouseEnter={() => setHover(s.category)} onMouseLeave={() => setHover(null)} className="cursor-pointer" />
              ))}
            </svg>
            <div className="pointer-events-none absolute inset-0 grid place-items-center text-center">
              <AnimatePresence mode="wait">
                <motion.div key={active?.category ?? "t"} initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}>
                  <p className="text-xs font-semibold capitalize text-muted">{active?.category ?? "Total (max)"}</p>
                  <p className="text-xl font-extrabold">{money(active ? active.max : totalMax, cur)}</p>
                  {active && <p className="text-[11px] text-muted">{Math.round(active.f * 100)}% • {active.label}</p>}
                </motion.div>
              </AnimatePresence>
            </div>
          </div>
          <ul className="mt-6 space-y-2">
            {d.by_category.map((x) => (
              <li key={x.category} onMouseEnter={() => setHover(x.category)} onMouseLeave={() => setHover(null)} className={`flex items-center gap-3 rounded-xl p-2 transition ${hover === x.category ? "bg-canvas" : ""}`}>
                <span className="grid h-9 w-9 place-items-center rounded-xl text-white" style={{ background: catColor[x.category] ?? "#64748b" }}><Icon name={categoryIcon[x.category] ?? "category"} className="!text-[18px]" /></span>
                <span className="flex-1 text-sm font-semibold capitalize">{x.category}<span className="ml-2 text-[11px] font-normal text-muted">{x.label.replace("_", " ")}</span></span>
                <span className="text-right text-sm font-bold">{range(x.min, x.max, cur)}</span>
              </li>
            ))}
          </ul>
        </section>

        <section className="card p-6">
          <h2 className="font-semibold">By day</h2>
          <div className="mt-4 space-y-2">
            {d.by_day.map((x) => {
              const isOpen = openDay === x.day_number;
              return (
                <div key={x.day_number} className="rounded-xl border border-hair">
                  <button onClick={() => setOpenDay(isOpen ? null : x.day_number)} className="flex w-full items-center gap-3 p-3 text-left">
                    <span className="rounded-lg bg-slate px-2 py-0.5 text-[11px] font-bold text-white">Day {x.day_number}</span>
                    <div className="min-w-0 flex-1"><div className="h-1.5 overflow-hidden rounded-full bg-sky"><motion.div className="h-full rounded-full bg-coral" initial={{ width: 0 }} whileInView={{ width: `${(parseFloat(x.max) / maxDay) * 100}%` }} viewport={{ once: true }} transition={{ duration: 0.8 }} /></div></div>
                    <span className="text-sm font-bold">{range(x.min, x.max, cur)}</span>
                    <motion.span animate={{ rotate: isOpen ? 180 : 0 }}><Icon name="expand_more" className="text-muted" /></motion.span>
                  </button>
                  <AnimatePresence initial={false}>
                    {isOpen && (
                      <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden px-4 pb-3 text-[13px] text-body">
                        Contingency share: <b>{money(x.contingency_share, cur)}</b>. See the Day-by-Day tab for each stop&apos;s price.
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              );
            })}
          </div>
        </section>
      </div>

      <section className="card p-5">
        <div className="flex flex-wrap items-center gap-4">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-coral-wash text-coral"><Icon name="tune" /></span>
          <div className="flex-1"><p className="font-semibold">Budget settings</p><p className="text-xs text-muted">Saved to the trip; the server recalculates every total.</p></div>
          <motion.button whileTap={{ scale: 0.95 }} disabled={saving} onClick={save} className="btn-primary disabled:opacity-60">{saving ? "Saving…" : "Save settings"}</motion.button>
        </div>
        <div className="mt-5 grid gap-5 sm:grid-cols-2">
          <label><span className="flex justify-between text-sm font-semibold">Contingency <b className="text-coral">{pct}%</b></span>
            <input type="range" min={0} max={50} value={pct} onChange={(e) => setPct(+e.target.value)} className="mt-2 w-full accent-coral" /></label>
          <label><span className="text-sm font-semibold">Stay budget per night ({cur})</span>
            <input type="number" min={0} value={stay} onChange={(e) => setStay(e.target.value)} placeholder="Optional" className="input mt-1.5 !h-10" /></label>
        </div>
      </section>
    </div>
  );
}
