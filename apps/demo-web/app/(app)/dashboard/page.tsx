"use client";

import Link from "next/link";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";
import { CountUp, Reveal, Tilt, useToast } from "@/components/fx";
import { Empty, ErrorBox, Skeleton } from "@/components/states";
import { Icon } from "@/components/ui";
import { api, destinationPhoto, fmtDate, money, type Trip } from "@/lib/api";
import { useLoad, useSession } from "@/lib/session";

const tone: Record<string, string> = { draft: "bg-sky text-body", ready: "bg-mint-wash text-mint", archived: "bg-line text-muted" };
const filters = ["all", "draft", "ready"];

function useCountdown(target: string | undefined) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => { const t = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(t); }, []);
  const d = target ? Math.max(0, +new Date(target + "T06:00:00") - now) : 0;
  return { d: Math.floor(d / 864e5), h: Math.floor(d / 36e5) % 24, m: Math.floor(d / 6e4) % 60, s: Math.floor(d / 1e3) % 60 };
}

export default function Dashboard() {
  const toast = useToast();
  const { user } = useSession();
  const { data, error, loading, reload, setData } = useLoad(() => api.trips(), []);
  const [f, setF] = useState("all");
  const [q, setQ] = useState("");
  const trips = data?.items ?? [];
  const today = new Date().toISOString().slice(0, 10);
  const next = [...trips].filter((t) => t.start_date >= today).sort((a, b) => a.start_date.localeCompare(b.start_date))[0];
  const cd = useCountdown(next?.start_date);
  const list = trips.filter((t) => (f === "all" || t.status === f) && (t.title + t.destination.name).toLowerCase().includes(q.toLowerCase()));
  const hour = new Date().getHours();
  const greet = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
  const name = (user?.user_metadata?.display_name as string | undefined) || user?.email?.split("@")[0] || "traveller";

  const remove = async (t: Trip) => {
    if (!confirm(`Delete “${t.title}”? This cannot be undone.`)) return;
    try {
      await api.deleteTrip(t.id);
      setData((d) => d && { ...d, items: d.items.filter((x) => x.id !== t.id), total: d.total - 1 });
      toast({ text: `Deleted ${t.title}`, icon: "delete" });
    } catch (e) { toast({ text: (e as Error).message, icon: "error" }); }
  };
  const duplicate = async (t: Trip) => {
    try { await api.duplicate(t.id); toast({ text: `Duplicated ${t.title}`, icon: "content_copy" }); reload(); }
    catch (e) { toast({ text: (e as Error).message, icon: "error" }); }
  };

  return (
    <main className="mx-auto max-w-[1440px] px-4 py-8 md:px-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <p className="label text-coral">Dashboard</p>
          <h1 className="mt-1 text-[32px] font-extrabold leading-10 tracking-tight">{greet}, {name} 👋</h1>
          <p className="mt-1 text-sm text-body">{loading ? "Loading your trips…" : `You have ${trips.length} trip${trips.length === 1 ? "" : "s"}. Pick one up or start something new.`}</p>
        </motion.div>
        <motion.div whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }}><Link href="/trips/new/" className="btn-primary"><Icon name="add" />New trip</Link></motion.div>
      </div>

      {error && <div className="mt-6"><ErrorBox error={error} onRetry={reload} /></div>}

      {next && (
        <Reveal className="mt-6">
          <Link href={`/trips/${next.id}/itinerary/`} className="group relative block overflow-hidden rounded-3xl">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={destinationPhoto(next.destination.name)} alt="" className="absolute inset-0 h-full w-full object-cover transition-transform duration-700 group-hover:scale-105" />
            <div className="absolute inset-0 bg-gradient-to-r from-slate/90 via-slate/60 to-transparent" />
            <div className="relative flex flex-wrap items-center justify-between gap-6 p-6 text-white md:p-8">
              <div>
                <span className="inline-flex items-center gap-1 rounded-full bg-white/15 px-2.5 py-1 text-[11px] font-bold backdrop-blur"><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-coral" />Next trip</span>
                <h2 className="mt-2 text-2xl font-extrabold md:text-3xl">{next.title}</h2>
                <p className="text-sm text-white/80">{next.destination.name} • {fmtDate(next.start_date, { month: "short", day: "numeric" })} – {fmtDate(next.end_date, { month: "short", day: "numeric" })}</p>
              </div>
              <div className="flex gap-2">
                {[["Days", cd.d], ["Hrs", cd.h], ["Min", cd.m], ["Sec", cd.s]].map(([l, v]) => (
                  <div key={l} className="w-16 rounded-xl border border-white/20 bg-white/15 py-2 text-center backdrop-blur">
                    <AnimatePresence mode="popLayout"><motion.p key={v as number} initial={{ y: -10, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 10, opacity: 0 }} className="text-2xl font-extrabold tabular-nums">{String(v).padStart(2, "0")}</motion.p></AnimatePresence>
                    <p className="text-[10px] font-semibold uppercase text-white/70">{l}</p>
                  </div>
                ))}
              </div>
            </div>
          </Link>
        </Reveal>
      )}

      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        {[["luggage", "Trips", trips.length], ["event_available", "With itinerary", trips.filter((t) => t.has_itinerary).length], ["calendar_month", "Days of travel", trips.reduce((s, t) => s + t.num_days, 0)]].map(([i, l, v], k) => (
          <Reveal key={l as string} delay={k * 0.08}>
            <motion.div whileHover={{ y: -4 }} className="card flex items-center gap-4 p-5">
              <span className="grid h-11 w-11 place-items-center rounded-xl bg-coral-wash text-coral"><Icon name={i as string} /></span>
              <div><p className="text-2xl font-extrabold">{loading ? "–" : <CountUp to={v as number} />}</p><p className="text-xs font-semibold text-muted">{l}</p></div>
            </motion.div>
          </Reveal>
        ))}
      </div>

      <div className="mt-10 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xl font-bold">My trips</h2>
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative"><Icon name="search" className="absolute left-3 top-2.5 !text-[16px] text-muted" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search trips" className="input !h-9 !w-48 pl-9 !text-[13px]" /></div>
          <div className="flex rounded-full bg-sky p-1">
            {filters.map((x) => (
              <button key={x} onClick={() => setF(x)} className={`relative rounded-full px-3 py-1 text-xs font-semibold capitalize ${f === x ? "text-white" : "text-muted"}`}>
                {f === x && <motion.span layoutId="tripf" className="absolute inset-0 rounded-full bg-slate" />}<span className="relative">{x}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {loading ? (
        <div className="mt-4 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-72" />)}</div>
      ) : trips.length === 0 && !error ? (
        <div className="mt-4"><Empty icon="flight_takeoff" title="No trips yet" text="Create your first trip and let the AI build a day-by-day plan." action={<Link href="/trips/new/" className="btn-primary"><Icon name="add" />Plan a trip</Link>} /></div>
      ) : (
        <motion.div layout className="mt-4 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          <AnimatePresence mode="popLayout">
            {list.map((t) => (
              <motion.div key={t.id} layout initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }}>
                <Tilt className="h-full">
                  <div className="card group relative h-full overflow-hidden">
                    <Link href={`/trips/${t.id}/${t.has_itinerary ? "itinerary" : "generate"}/`} className="block">
                      <div className="relative h-44 overflow-hidden">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src={destinationPhoto(t.destination.name)} alt="" className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-110" />
                        <span className={`absolute left-3 top-3 rounded-full px-2.5 py-1 text-[11px] font-bold capitalize ${tone[t.status]}`}>{t.status}</span>
                        {!t.has_itinerary && <span className="absolute bottom-3 left-3 rounded-full bg-coral px-2.5 py-1 text-[11px] font-bold text-white">Needs itinerary</span>}
                      </div>
                      <div className="p-5">
                        <p className="text-lg font-bold">{t.title}</p>
                        <p className="mt-1 flex items-center gap-1 text-sm text-body"><Icon name="location_on" className="!text-[16px] text-coral" />{t.destination.name}</p>
                        <div className="mt-4 flex items-center justify-between text-xs font-semibold text-muted">
                          <span>{fmtDate(t.start_date, { month: "short", day: "numeric" })} – {fmtDate(t.end_date, { month: "short", day: "numeric" })} • {t.num_days} days{t.budget ? ` • ${money(t.budget.amount, t.budget.currency)}` : ""}</span>
                          <span className="flex items-center gap-1 text-coral transition-transform group-hover:translate-x-1">Open<Icon name="arrow_forward" className="!text-[14px]" /></span>
                        </div>
                      </div>
                    </Link>
                    <div className="absolute right-3 top-3 flex gap-1 opacity-0 transition group-hover:opacity-100">
                      <button onClick={() => duplicate(t)} className="glass grid h-8 w-8 place-items-center rounded-full" aria-label="Duplicate trip"><Icon name="content_copy" className="!text-[15px]" /></button>
                      <button onClick={() => remove(t)} className="glass grid h-8 w-8 place-items-center rounded-full text-coral" aria-label="Delete trip"><Icon name="delete" className="!text-[15px]" /></button>
                    </div>
                  </div>
                </Tilt>
              </motion.div>
            ))}
            <motion.div key="new" layout>
              <Link href="/trips/new/" className="group grid h-full min-h-64 place-items-center rounded-2xl border-2 border-dashed border-line text-center text-muted transition hover:border-coral hover:bg-coral-wash/40 hover:text-coral">
                <div><motion.span whileHover={{ rotate: 90 }} className="inline-block"><Icon name="add_circle" className="!text-[40px]" /></motion.span><p className="mt-2 font-semibold">Plan a new trip</p></div>
              </Link>
            </motion.div>
          </AnimatePresence>
        </motion.div>
      )}
      {!loading && trips.length > 0 && list.length === 0 && <p className="mt-4 text-sm text-muted">No trips match “{q}”.</p>}
    </main>
  );
}
