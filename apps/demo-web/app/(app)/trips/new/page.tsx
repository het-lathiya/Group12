"use client";

import { AnimatePresence, motion } from "motion/react";
import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Icon } from "@/components/ui";
import { destinations, inr, trip } from "@/lib/data";

const interests = [["restaurant", "Food"], ["fort", "Heritage"], ["forest", "Nature"], ["nightlife", "Nightlife"], ["shopping_bag", "Shopping"], ["hiking", "Adventure"], ["palette", "Art"], ["spa", "Relaxing"]];
const paces = [["self_improvement", "Relaxed", "2–3 stops a day"], ["balance", "Balanced", "3–4 stops a day"], ["bolt", "Packed", "5+ stops a day"]];
const who = [["person", "Solo"], ["favorite", "Couple"], ["family_restroom", "Family"], ["groups", "Friends"]];
const stepNames = ["Where", "When & who", "Your vibe", "Review"];

export default function NewTripPage() { return <Suspense><NewTrip /></Suspense>; }

function NewTrip() {
  const router = useRouter();
  const q = useSearchParams().get("q") ?? "";
  const guess = destinations.find((d) => q.toLowerCase().includes(d.name.toLowerCase()))?.name ?? "";
  const [step, setStep] = useState(0);
  const [dir, setDir] = useState(1);
  const [dest, setDest] = useState(guess);
  const [prompt, setPrompt] = useState(q);
  const [start, setStart] = useState("2026-12-12");
  const [end, setEnd] = useState("2026-12-16");
  const [group, setGroup] = useState("Couple");
  const [travelers, setTravelers] = useState(2);
  const [budget, setBudget] = useState(48000);
  const [picked, setPicked] = useState<string[]>(["Food", "Heritage"]);
  const [pace, setPace] = useState("Balanced");

  const nights = Math.max(0, Math.round((+new Date(end) - +new Date(start)) / 864e5));
  const level = budget < 25000 ? "Budget" : budget < 70000 ? "Moderate" : "Luxury";
  const can = [dest.trim().length > 1, nights > 0, picked.length > 0, true][step];
  const go = (n: number) => { setDir(n > step ? 1 : -1); setStep(n); };
  const toggle = (s: string) => setPicked((p) => (p.includes(s) ? p.filter((x) => x !== s) : [...p, s]));
  const matches = destinations.filter((d) => d.name.toLowerCase().includes(dest.toLowerCase()));

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 md:px-6">
      <p className="label text-coral">New trip</p>
      <h1 className="mt-1 text-[32px] font-extrabold leading-10 tracking-tight">Let&apos;s plan something great</h1>

      {/* stepper */}
      <div className="mt-6 flex items-center gap-2">
        {stepNames.map((n, i) => (
          <button key={n} onClick={() => i < step && go(i)} className="flex flex-1 flex-col gap-1.5 text-left">
            <div className="h-1.5 overflow-hidden rounded-full bg-line">
              <motion.div className="h-full bg-coral" initial={false} animate={{ width: i <= step ? "100%" : "0%" }} transition={{ duration: 0.4 }} />
            </div>
            <span className={`text-[11px] font-bold ${i === step ? "text-coral" : i < step ? "text-slate" : "text-muted"}`}>{i < step ? "✓ " : ""}{n}</span>
          </button>
        ))}
      </div>

      <div className="relative mt-6 min-h-[420px]">
        <AnimatePresence mode="wait" custom={dir}>
          <motion.section key={step} custom={dir} initial={{ opacity: 0, x: dir * 60 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: dir * -60 }} transition={{ duration: 0.3 }} className="card p-6">
            {step === 0 && (
              <div className="space-y-5">
                <h2 className="text-xl font-bold">Where do you want to go?</h2>
                <div className="relative"><Icon name="search" className="absolute left-4 top-3.5 text-coral" />
                  <input autoFocus value={dest} onChange={(e) => setDest(e.target.value)} placeholder="Search a city or region" className="input pl-11 !text-base" /></div>
                <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
                  {(matches.length ? matches : destinations).map((d) => (
                    <motion.button whileHover={{ y: -4 }} whileTap={{ scale: 0.95 }} key={d.name} onClick={() => setDest(d.name)}
                      className={`relative overflow-hidden rounded-xl ring-offset-2 transition ${dest === d.name ? "ring-2 ring-coral" : ""}`}>
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={d.img} alt="" className="h-24 w-full object-cover" />
                      <div className="absolute inset-0 bg-gradient-to-t from-slate/80 to-transparent" />
                      <span className="absolute bottom-1.5 left-2 text-xs font-bold text-white">{d.name}</span>
                      {dest === d.name && <motion.span layoutId="destcheck" className="absolute right-1.5 top-1.5 grid h-5 w-5 place-items-center rounded-full bg-coral text-white"><Icon name="check" className="!text-[14px]" /></motion.span>}
                    </motion.button>
                  ))}
                </div>
                <label className="block"><span className="label text-muted">Anything else? (optional)</span>
                  <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={2} placeholder="e.g. We love old forts and street food, no early mornings" className="input mt-1.5 !h-auto py-3" /></label>
              </div>
            )}

            {step === 1 && (
              <div className="space-y-6">
                <h2 className="text-xl font-bold">When, and who&apos;s coming?</h2>
                <div className="grid gap-4 sm:grid-cols-[1fr_auto_1fr] sm:items-end">
                  <label><span className="label text-muted">Start</span><input type="date" value={start} onChange={(e) => setStart(e.target.value)} className="input mt-1.5" /></label>
                  <motion.span key={nights} initial={{ scale: 0.6 }} animate={{ scale: 1 }} className="mb-2 self-center justify-self-center rounded-full bg-coral-wash px-3 py-1 text-xs font-bold text-coral">{nights} nights</motion.span>
                  <label><span className="label text-muted">End</span><input type="date" value={end} min={start} onChange={(e) => setEnd(e.target.value)} className="input mt-1.5" /></label>
                </div>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  {who.map(([ic, l]) => (
                    <motion.button whileTap={{ scale: 0.95 }} key={l} onClick={() => { setGroup(l); setTravelers(l === "Solo" ? 1 : l === "Couple" ? 2 : 4); }}
                      className={`flex flex-col items-center gap-2 rounded-xl border p-4 transition ${group === l ? "border-coral bg-coral-wash text-coral" : "border-line hover:bg-canvas"}`}>
                      <Icon name={ic} className="!text-[26px]" /><span className="text-sm font-semibold">{l}</span>
                    </motion.button>
                  ))}
                </div>
                <div className="flex items-center justify-between rounded-xl bg-canvas p-3">
                  <span className="text-sm font-semibold">Travelers</span>
                  <div className="flex items-center gap-3">
                    <motion.button whileTap={{ scale: 0.85 }} onClick={() => setTravelers((t) => Math.max(1, t - 1))} className="grid h-9 w-9 place-items-center rounded-full bg-white shadow-sm" aria-label="Fewer"><Icon name="remove" /></motion.button>
                    <motion.span key={travelers} initial={{ y: -8, opacity: 0 }} animate={{ y: 0, opacity: 1 }} className="w-6 text-center text-lg font-bold">{travelers}</motion.span>
                    <motion.button whileTap={{ scale: 0.85 }} onClick={() => setTravelers((t) => t + 1)} className="grid h-9 w-9 place-items-center rounded-full bg-white shadow-sm" aria-label="More"><Icon name="add" /></motion.button>
                  </div>
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="space-y-6">
                <h2 className="text-xl font-bold">What&apos;s your vibe?</h2>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  {interests.map(([ic, s]) => {
                    const on = picked.includes(s);
                    return (
                      <motion.button whileTap={{ scale: 0.93 }} key={s} onClick={() => toggle(s)} animate={{ scale: on ? 1.02 : 1 }}
                        className={`flex items-center gap-2 rounded-xl border px-3 py-3 text-sm font-semibold transition ${on ? "border-slate bg-slate text-white" : "border-line hover:bg-canvas"}`}>
                        <Icon name={ic} className={on ? "text-coral" : "text-muted"} />{s}
                      </motion.button>
                    );
                  })}
                </div>
                <div>
                  <div className="flex items-end justify-between"><span className="label text-muted">Total budget</span>
                    <span className="text-right"><motion.b key={level} initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mr-2 rounded-full bg-mint-wash px-2 py-0.5 text-[11px] text-mint">{level}</motion.b><b className="text-xl">{inr(budget)}</b></span></div>
                  <input type="range" min={10000} max={150000} step={1000} value={budget} onChange={(e) => setBudget(+e.target.value)} className="mt-3 w-full accent-coral" aria-label="Budget" />
                  <p className="mt-1 text-xs text-muted">≈ {inr(Math.round(budget / Math.max(1, travelers) / Math.max(1, nights)))} per person per night</p>
                </div>
                <div className="grid gap-3 sm:grid-cols-3">
                  {paces.map(([ic, p, d]) => (
                    <motion.button whileTap={{ scale: 0.96 }} key={p} onClick={() => setPace(p)} className={`rounded-xl border p-4 text-left transition ${pace === p ? "border-coral bg-coral-wash" : "border-line hover:bg-canvas"}`}>
                      <Icon name={ic} className={pace === p ? "text-coral" : "text-muted"} /><p className="mt-1 font-semibold">{p}</p><p className="text-xs text-muted">{d}</p>
                    </motion.button>
                  ))}
                </div>
              </div>
            )}

            {step === 3 && (
              <div className="space-y-5">
                <h2 className="text-xl font-bold">Looks good?</h2>
                <div className="relative h-40 overflow-hidden rounded-xl">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={destinations.find((d) => d.name === dest)?.img ?? trip.cover} alt="" className="h-full w-full object-cover" />
                  <div className="absolute inset-0 bg-gradient-to-t from-slate/80 to-transparent" />
                  <p className="absolute bottom-3 left-4 text-2xl font-extrabold text-white">{dest}</p>
                </div>
                <dl className="grid grid-cols-2 gap-3 text-sm">
                  {[["calendar_month", "Dates", `${start} → ${end} (${nights}n)`], ["group", "Who", `${group}, ${travelers} people`], ["payments", "Budget", `${inr(budget)} • ${level}`], ["speed", "Pace", pace]].map(([ic, k, v], i) => (
                    <motion.div key={k} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.07 }} className="rounded-xl bg-canvas p-3">
                      <dt className="flex items-center gap-1 text-xs text-muted"><Icon name={ic} className="!text-[14px] text-coral" />{k}</dt><dd className="mt-0.5 font-semibold">{v}</dd>
                    </motion.div>
                  ))}
                </dl>
                <div className="flex flex-wrap gap-2">{picked.map((p) => <span key={p} className="chip chip-active">{p}</span>)}</div>
              </div>
            )}
          </motion.section>
        </AnimatePresence>
      </div>

      <div className="mt-5 flex items-center justify-between">
        <button onClick={() => go(step - 1)} disabled={step === 0} className="btn-soft disabled:opacity-0"><Icon name="arrow_back" className="!text-[16px]" />Back</button>
        {step < 3 ? (
          <motion.button whileTap={{ scale: 0.96 }} disabled={!can} onClick={() => go(step + 1)} className="btn-dark disabled:opacity-40">Continue<Icon name="arrow_forward" className="!text-[16px]" /></motion.button>
        ) : (
          // TODO: POST /api/v1/trips then PUT /trips/{id}/preferences
          <motion.button whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.96 }} onClick={() => router.push(`/trips/${trip.id}/generate`)} className="btn-primary !px-6 !py-3"><Icon name="auto_awesome" />Generate itinerary</motion.button>
        )}
      </div>
    </main>
  );
}
