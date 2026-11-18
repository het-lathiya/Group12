"use client";

import { AnimatePresence, motion } from "motion/react";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useToast } from "@/components/fx";
import { ErrorBox, Skeleton } from "@/components/states";
import { Icon } from "@/components/ui";
import { api, destinationPhoto, money } from "@/lib/api";
import { useLoad } from "@/lib/session";

const interests = [["photo_camera", "Sights", "sight"], ["museum", "Museums", "museum"], ["forest", "Nature", "nature"], ["restaurant", "Food", "food"], ["shopping_bag", "Shopping", "shopping"], ["theater_comedy", "Entertainment", "entertainment"], ["temple_hindu", "Religious", "religious"], ["hiking", "Activities", "activity"]];
const paces = [["self_improvement", "Relaxed", "relaxed", "Fewer stops, more breaks"], ["balance", "Balanced", "balanced", "A steady day"], ["bolt", "Busy", "busy", "See as much as possible"]];
const who = [["person", "Solo", 1, 0], ["favorite", "Couple", 2, 0], ["family_restroom", "Family", 2, 2], ["groups", "Friends", 4, 0]] as const;
const transports = [["directions_walk", "Walking", "walking"], ["directions_bus", "Local transport", "local_transport"], ["local_taxi", "Car", "car"]];
const stepNames = ["Where", "When & who", "Your vibe", "Review"];

const iso = (d: Date) => d.toISOString().slice(0, 10);
const addDays = (s: string, n: number) => { const d = new Date(s + "T00:00:00"); d.setDate(d.getDate() + n); return iso(d); };

export default function NewTripPage() { return <Suspense><NewTrip /></Suspense>; }

function NewTrip() {
  const router = useRouter();
  const toast = useToast();
  const q = useSearchParams().get("q") ?? "";
  const dests = useLoad(() => api.destinations(), []);
  const [step, setStep] = useState(0);
  const [dir, setDir] = useState(1);
  const [destId, setDestId] = useState("");
  const [search, setSearch] = useState("");
  const [notes, setNotes] = useState(q);
  const [start, setStart] = useState(() => addDays(iso(new Date()), 14));
  const [end, setEnd] = useState(() => addDays(iso(new Date()), 16));
  const [group, setGroup] = useState("Couple");
  const [adults, setAdults] = useState(2);
  const [children, setChildren] = useState(0);
  const [budget, setBudget] = useState(30000);
  const [useBudget, setUseBudget] = useState(true);
  const [picked, setPicked] = useState<string[]>(["sight", "food"]);
  const [pace, setPace] = useState("balanced");
  const [transport, setTransport] = useState("local_transport");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const list = dests.data ?? [];
  const dest = list.find((d) => d.id === destId);
  const currency = dest?.currency ?? "INR";
  useEffect(() => {
    if (destId || !list.length) return;
    const guess = list.find((d) => q.toLowerCase().includes(d.name.toLowerCase()));
    if (guess) setDestId(guess.id);
  }, [list, q, destId]);

  const days = Math.max(0, Math.round((+new Date(end) - +new Date(start)) / 864e5) + 1);
  const priority = budget < 20000 ? "saving" : budget < 60000 ? "balanced" : "comfort";
  const can = [!!destId, days >= 1 && days <= 14 && adults >= 1, picked.length > 0, true][step];
  const go = (n: number) => { setDir(n > step ? 1 : -1); setStep(n); };
  const toggle = (s: string) => setPicked((p) => (p.includes(s) ? p.filter((x) => x !== s) : [...p, s]));
  const matches = list.filter((d) => (d.name + (d.region ?? "")).toLowerCase().includes(search.toLowerCase()));

  const create = async () => {
    if (!dest) return;
    setBusy(true); setErr(null);
    try {
      const trip = await api.createTrip({
        title: `${days} day${days === 1 ? "" : "s"} in ${dest.name}`,
        destination_id: dest.id, start_date: start, end_date: end, adults, children,
        budget: useBudget ? { amount: budget.toFixed(2), currency } : null,
        group_needs: children > 0 ? ["children"] : [],
      });
      await api.savePreferences(trip.id, { interests: picked, pace, budget_priority: priority, transport_pref: transport, notes: notes.trim() || null });
      toast({ text: "Trip created. Building your itinerary…", icon: "flight_takeoff" });
      router.push(`/trips/${trip.id}/generate/?start=1`);
    } catch (e) {
      setBusy(false);
      setErr((e as Error).message);
    }
  };

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 md:px-6">
      <p className="label text-coral">New trip</p>
      <h1 className="mt-1 text-[32px] font-extrabold leading-10 tracking-tight">Let&apos;s plan something great</h1>

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
                  <input autoFocus value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search destinations" className="input pl-11 !text-base" /></div>
                {dests.error ? <ErrorBox error={dests.error} onRetry={dests.reload} /> : dests.loading ? (
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-28" />)}</div>
                ) : (
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                    {matches.map((d) => (
                      <motion.button whileHover={{ y: -4 }} whileTap={{ scale: 0.95 }} key={d.id} onClick={() => setDestId(d.id)}
                        className={`relative overflow-hidden rounded-xl text-left ring-offset-2 transition ${destId === d.id ? "ring-2 ring-coral" : ""}`}>
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src={destinationPhoto(d.name)} alt="" className="h-28 w-full object-cover" />
                        <div className="absolute inset-0 bg-gradient-to-t from-slate/85 to-transparent" />
                        <span className="absolute bottom-2 left-3 text-white"><b className="block text-sm">{d.name}</b><span className="text-[11px] opacity-80">{d.region ?? d.country_code}{d.is_sample ? " • sample" : ""}</span></span>
                        {destId === d.id && <motion.span layoutId="destcheck" className="absolute right-2 top-2 grid h-6 w-6 place-items-center rounded-full bg-coral text-white"><Icon name="check" className="!text-[16px]" /></motion.span>}
                      </motion.button>
                    ))}
                    {matches.length === 0 && <p className="col-span-full text-sm text-muted">No destination matches “{search}”. Available: {list.map((d) => d.name).join(", ")}.</p>}
                  </div>
                )}
                <label className="block"><span className="label text-muted">Anything the AI should know? (optional)</span>
                  <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} maxLength={500} placeholder="e.g. We love old forts and street food, no early mornings" className="input mt-1.5 !h-auto py-3" /></label>
              </div>
            )}

            {step === 1 && (
              <div className="space-y-6">
                <h2 className="text-xl font-bold">When, and who&apos;s coming?</h2>
                <div className="grid gap-4 sm:grid-cols-[1fr_auto_1fr] sm:items-end">
                  <label><span className="label text-muted">Start</span><input type="date" value={start} min={iso(new Date())} onChange={(e) => { setStart(e.target.value); if (e.target.value > end) setEnd(e.target.value); }} className="input mt-1.5" /></label>
                  <motion.span key={days} initial={{ scale: 0.6 }} animate={{ scale: 1 }} className={`mb-2 self-center justify-self-center rounded-full px-3 py-1 text-xs font-bold ${days > 14 ? "bg-coral text-white" : "bg-coral-wash text-coral"}`}>{days} day{days === 1 ? "" : "s"}</motion.span>
                  <label><span className="label text-muted">End</span><input type="date" value={end} min={start} onChange={(e) => setEnd(e.target.value)} className="input mt-1.5" /></label>
                </div>
                {days > 14 && <p className="text-xs text-coral">Trips can be at most 14 days.</p>}
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  {who.map(([ic, l, a, c]) => (
                    <motion.button whileTap={{ scale: 0.95 }} key={l} onClick={() => { setGroup(l); setAdults(a); setChildren(c); }}
                      className={`flex flex-col items-center gap-2 rounded-xl border p-4 transition ${group === l ? "border-coral bg-coral-wash text-coral" : "border-line hover:bg-canvas"}`}>
                      <Icon name={ic} className="!text-[26px]" /><span className="text-sm font-semibold">{l}</span>
                    </motion.button>
                  ))}
                </div>
                {([["Adults", adults, setAdults, 1], ["Children", children, setChildren, 0]] as const).map(([l, v, set, min]) => (
                  <div key={l} className="flex items-center justify-between rounded-xl bg-canvas p-3">
                    <span className="text-sm font-semibold">{l}</span>
                    <div className="flex items-center gap-3">
                      <motion.button whileTap={{ scale: 0.85 }} onClick={() => set(Math.max(min, v - 1))} className="grid h-9 w-9 place-items-center rounded-full bg-white shadow-sm" aria-label={`Fewer ${l}`}><Icon name="remove" /></motion.button>
                      <motion.span key={v} initial={{ y: -8, opacity: 0 }} animate={{ y: 0, opacity: 1 }} className="w-6 text-center text-lg font-bold">{v}</motion.span>
                      <motion.button whileTap={{ scale: 0.85 }} onClick={() => set(Math.min(20, v + 1))} className="grid h-9 w-9 place-items-center rounded-full bg-white shadow-sm" aria-label={`More ${l}`}><Icon name="add" /></motion.button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {step === 2 && (
              <div className="space-y-6">
                <h2 className="text-xl font-bold">What&apos;s your vibe?</h2>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  {interests.map(([ic, l, v]) => {
                    const on = picked.includes(v);
                    return (
                      <motion.button whileTap={{ scale: 0.93 }} key={v} onClick={() => toggle(v)} animate={{ scale: on ? 1.02 : 1 }}
                        className={`flex items-center gap-2 rounded-xl border px-3 py-3 text-sm font-semibold transition ${on ? "border-slate bg-slate text-white" : "border-line hover:bg-canvas"}`}>
                        <Icon name={ic} className={on ? "text-coral" : "text-muted"} />{l}
                      </motion.button>
                    );
                  })}
                </div>
                <div>
                  <div className="flex items-end justify-between">
                    <label className="flex items-center gap-2 text-sm font-semibold"><input type="checkbox" checked={useBudget} onChange={(e) => setUseBudget(e.target.checked)} className="accent-coral" />Set a total budget</label>
                    {useBudget && <span><motion.b key={priority} initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mr-2 rounded-full bg-mint-wash px-2 py-0.5 text-[11px] capitalize text-mint">{priority}</motion.b><b className="text-xl">{money(budget, currency)}</b></span>}
                  </div>
                  {useBudget && <>
                    <input type="range" min={5000} max={200000} step={1000} value={budget} onChange={(e) => setBudget(+e.target.value)} className="mt-3 w-full accent-coral" aria-label="Budget" />
                    <p className="mt-1 text-xs text-muted">≈ {money(Math.round(budget / Math.max(1, adults + children) / Math.max(1, days)), currency)} per person per day</p>
                  </>}
                </div>
                <div className="grid gap-3 sm:grid-cols-3">
                  {paces.map(([ic, l, v, d]) => (
                    <motion.button whileTap={{ scale: 0.96 }} key={v} onClick={() => setPace(v)} className={`rounded-xl border p-4 text-left transition ${pace === v ? "border-coral bg-coral-wash" : "border-line hover:bg-canvas"}`}>
                      <Icon name={ic} className={pace === v ? "text-coral" : "text-muted"} /><p className="mt-1 font-semibold">{l}</p><p className="text-xs text-muted">{d}</p>
                    </motion.button>
                  ))}
                </div>
                <div className="flex flex-wrap gap-2">
                  {transports.map(([ic, l, v]) => (
                    <button key={v} onClick={() => setTransport(v)} className={`chip ${transport === v ? "chip-active" : ""}`}><Icon name={ic} className="!text-[14px]" />{l}</button>
                  ))}
                </div>
              </div>
            )}

            {step === 3 && dest && (
              <div className="space-y-5">
                <h2 className="text-xl font-bold">Looks good?</h2>
                <div className="relative h-40 overflow-hidden rounded-xl">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={destinationPhoto(dest.name)} alt="" className="h-full w-full object-cover" />
                  <div className="absolute inset-0 bg-gradient-to-t from-slate/80 to-transparent" />
                  <p className="absolute bottom-3 left-4 text-2xl font-extrabold text-white">{dest.name}</p>
                </div>
                <dl className="grid grid-cols-2 gap-3 text-sm">
                  {[["calendar_month", "Dates", `${start} → ${end} (${days}d)`], ["group", "Who", `${adults} adult${adults > 1 ? "s" : ""}${children ? `, ${children} child${children > 1 ? "ren" : ""}` : ""}`], ["payments", "Budget", useBudget ? `${money(budget, currency)} • ${priority}` : "Not set"], ["speed", "Pace", pace]].map(([ic, k, v], i) => (
                    <motion.div key={k} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.07 }} className="rounded-xl bg-canvas p-3">
                      <dt className="flex items-center gap-1 text-xs text-muted"><Icon name={ic} className="!text-[14px] text-coral" />{k}</dt><dd className="mt-0.5 font-semibold capitalize">{v}</dd>
                    </motion.div>
                  ))}
                </dl>
                <div className="flex flex-wrap gap-2">{picked.map((p) => <span key={p} className="chip chip-active capitalize">{p}</span>)}</div>
                {err && <p className="rounded-xl bg-coral-wash p-3 text-sm text-coral-deep">{err}</p>}
              </div>
            )}
          </motion.section>
        </AnimatePresence>
      </div>

      <div className="mt-5 flex items-center justify-between">
        <button onClick={() => go(step - 1)} disabled={step === 0 || busy} className="btn-soft disabled:opacity-0"><Icon name="arrow_back" className="!text-[16px]" />Back</button>
        {step < 3 ? (
          <motion.button whileTap={{ scale: 0.96 }} disabled={!can} onClick={() => go(step + 1)} className="btn-dark disabled:opacity-40">Continue<Icon name="arrow_forward" className="!text-[16px]" /></motion.button>
        ) : (
          <motion.button whileHover={{ scale: busy ? 1 : 1.03 }} whileTap={{ scale: 0.96 }} disabled={busy} onClick={create} className="btn-primary !px-6 !py-3 disabled:opacity-70">
            {busy ? <><motion.span animate={{ rotate: 360 }} transition={{ duration: 0.8, repeat: Infinity, ease: "linear" }} className="block h-4 w-4 rounded-full border-2 border-white/40 border-t-white" />Creating trip…</> : <><Icon name="auto_awesome" />Create & generate</>}
          </motion.button>
        )}
      </div>
    </main>
  );
}
