"use client";

import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";
import { CountUp, useToast } from "@/components/fx";
import { Icon } from "@/components/ui";
import { costs, days, inr } from "@/lib/data";

// TODO: GET /api/v1/trips/{id}/costs and PATCH /trips/{id}/budget-settings
export default function Costs() {
  const toast = useToast();
  const [budget, setBudget] = useState(costs.budget);
  const [hover, setHover] = useState<string | null>(null);
  const [openDay, setOpenDay] = useState<number | null>(1);
  const spent = costs.categories.reduce((s, c) => s + c.amount, 0);
  const left = budget - spent;
  const pct = Math.min(100, Math.round((spent / budget) * 100));
  const over = left < 0;

  // donut
  const R = 70, C = 2 * Math.PI * R;
  let acc = 0;
  const segs = costs.categories.map((c) => { const f = c.amount / spent; const s = { ...c, f, off: acc }; acc += f; return s; });
  const active = segs.find((s) => s.name === hover);

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <div className="card p-5"><p className="label text-muted">Total budget</p><p className="mt-2 text-3xl font-extrabold"><CountUp to={budget} prefix="₹" duration={0.5} /></p><p className="text-xs text-muted">for 2 travelers</p></div>
        <div className="card p-5"><p className="label text-muted">Estimated spend</p><p className="mt-2 text-3xl font-extrabold"><CountUp to={spent} prefix="₹" /></p>
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-sky"><motion.div className={`h-full rounded-full ${over ? "bg-coral" : pct > 85 ? "bg-amber-400" : "bg-mint"}`} animate={{ width: `${pct}%` }} transition={{ type: "spring", stiffness: 120, damping: 20 }} /></div>
          <p className="mt-1 text-xs text-muted">{pct}% of budget</p></div>
        <div className="card p-5"><p className="label text-muted">Remaining</p>
          <motion.p key={over ? "o" : "u"} initial={{ scale: 0.9 }} animate={{ scale: 1 }} className={`mt-2 text-3xl font-extrabold ${over ? "text-coral" : "text-mint"}`}>{inr(left)}</motion.p>
          {over ? <span className="mt-1 inline-flex items-center gap-1 rounded-full bg-coral-wash px-2 py-0.5 text-[11px] font-bold text-coral"><Icon name="warning" className="!text-[13px]" />Over budget</span>
            : <span className="badge-mint mt-1"><Icon name="check_circle" className="!text-[13px]" />Within budget</span>}</div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        <section className="card p-6">
          <h2 className="font-semibold">By category</h2>
          <div className="relative mx-auto mt-4 h-52 w-52">
            <svg viewBox="0 0 180 180" className="h-full w-full -rotate-90">
              <circle cx="90" cy="90" r={R} fill="none" stroke="#eff4ff" strokeWidth="22" />
              {segs.map((s, i) => (
                <motion.circle key={s.name} cx="90" cy="90" r={R} fill="none" stroke={s.color} strokeLinecap="butt"
                  strokeDasharray={`${s.f * C} ${C}`} strokeDashoffset={-s.off * C}
                  initial={{ strokeDasharray: `0 ${C}` }} animate={{ strokeDasharray: `${s.f * C - 2} ${C}`, strokeWidth: hover === s.name ? 30 : 22, opacity: hover && hover !== s.name ? 0.35 : 1 }}
                  transition={{ duration: 0.8, delay: i * 0.1 }} onMouseEnter={() => setHover(s.name)} onMouseLeave={() => setHover(null)} className="cursor-pointer" />
              ))}
            </svg>
            <div className="pointer-events-none absolute inset-0 grid place-items-center text-center">
              <AnimatePresence mode="wait">
                <motion.div key={active?.name ?? "total"} initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}>
                  <p className="text-xs font-semibold text-muted">{active?.name ?? "Total"}</p>
                  <p className="text-xl font-extrabold">{inr(active?.amount ?? spent)}</p>
                  {active && <p className="text-[11px] text-muted">{Math.round(active.f * 100)}%</p>}
                </motion.div>
              </AnimatePresence>
            </div>
          </div>
          <ul className="mt-6 space-y-2">
            {costs.categories.map((c) => (
              <li key={c.name} onMouseEnter={() => setHover(c.name)} onMouseLeave={() => setHover(null)}
                className={`flex items-center gap-3 rounded-xl p-2 transition ${hover === c.name ? "bg-canvas" : ""}`}>
                <span className="grid h-9 w-9 place-items-center rounded-xl text-white" style={{ background: c.color }}><Icon name={c.icon} className="!text-[18px]" /></span>
                <span className="flex-1 text-sm font-semibold">{c.name}</span>
                <span className="text-xs text-muted">{Math.round((c.amount / spent) * 100)}%</span>
                <span className="w-20 text-right text-sm font-bold">{inr(c.amount)}</span>
              </li>
            ))}
          </ul>
        </section>

        <section className="card p-6">
          <h2 className="font-semibold">By day</h2>
          <div className="mt-4 space-y-2">
            {days.map((d) => {
              const total = d.stops.reduce((s, x) => s + x.cost, 0);
              const max = Math.max(...days.map((x) => x.stops.reduce((s, y) => s + y.cost, 0)));
              const isOpen = openDay === d.n;
              return (
                <div key={d.n} className="rounded-xl border border-hair">
                  <button onClick={() => setOpenDay(isOpen ? null : d.n)} className="flex w-full items-center gap-3 p-3 text-left">
                    <span className="rounded-lg bg-slate px-2 py-0.5 text-[11px] font-bold text-white">Day {d.n}</span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold">{d.title}</p>
                      <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-sky"><motion.div className="h-full rounded-full bg-coral" initial={{ width: 0 }} whileInView={{ width: `${(total / max) * 100}%` }} viewport={{ once: true }} transition={{ duration: 0.8 }} /></div>
                    </div>
                    <span className="text-sm font-bold">{inr(total)}</span>
                    <motion.span animate={{ rotate: isOpen ? 180 : 0 }}><Icon name="expand_more" className="text-muted" /></motion.span>
                  </button>
                  <AnimatePresence initial={false}>
                    {isOpen && (
                      <motion.ul initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden px-4">
                        {d.stops.map((s) => (
                          <li key={s.id} className="flex justify-between border-t border-hair py-2 text-[13px] text-body"><span>{s.name}</span><span className="font-semibold">{s.cost ? inr(s.cost) : "Free"}</span></li>
                        ))}
                      </motion.ul>
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
          <div className="flex-1"><p className="font-semibold">Budget settings</p><p className="text-xs text-muted">Drag to see how your plan fits. TripBook re-balances picks when you save.</p></div>
          <motion.button whileTap={{ scale: 0.95 }} onClick={() => toast({ text: `Budget updated to ${inr(budget)}`, icon: "savings" })} className="btn-primary">Save budget</motion.button>
        </div>
        <input type="range" min={20000} max={120000} step={500} value={budget} onChange={(e) => setBudget(+e.target.value)} className="mt-5 w-full accent-coral" aria-label="Budget" />
        <div className="mt-1 flex justify-between text-[11px] text-muted"><span>₹20k Budget</span><span>Moderate</span><span>₹1.2L Luxury</span></div>
      </section>
    </div>
  );
}
