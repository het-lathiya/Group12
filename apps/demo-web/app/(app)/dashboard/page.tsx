"use client";

import Link from "next/link";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";
import { CountUp, Reveal, Tilt } from "@/components/fx";
import { Icon } from "@/components/ui";
import { destinations, trips, user } from "@/lib/data";

const tone: Record<string, string> = { Planning: "bg-coral-wash text-coral", Draft: "bg-sky text-body", Ready: "bg-mint-wash text-mint" };
const filters = ["All", "Planning", "Draft", "Ready"];

function useCountdown(target: string) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => { const t = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(t); }, []);
  const d = Math.max(0, +new Date(target) - now);
  return { d: Math.floor(d / 864e5), h: Math.floor(d / 36e5) % 24, m: Math.floor(d / 6e4) % 60, s: Math.floor(d / 1e3) % 60 };
}

export default function Dashboard() {
  const [f, setF] = useState("All");
  const [q, setQ] = useState("");
  const cd = useCountdown("2026-12-12T06:00:00+05:30");
  const list = trips.filter((t) => (f === "All" || t.status === f) && (t.name + t.dest).toLowerCase().includes(q.toLowerCase()));
  const hour = new Date().getHours();
  const greet = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  return (
    <main className="mx-auto max-w-[1440px] px-4 py-8 md:px-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <p className="label text-coral">Dashboard</p>
          <h1 className="mt-1 text-[32px] font-extrabold leading-10 tracking-tight">{greet}, {user.name} 👋</h1>
          <p className="mt-1 text-sm text-body">You have {trips.length} trips. Pick one up or start something new.</p>
        </motion.div>
        <motion.div whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }}><Link href="/trips/new" className="btn-primary"><Icon name="add" />New trip</Link></motion.div>
      </div>

      {/* Upcoming trip countdown */}
      <Reveal className="mt-6">
        <Link href={`/trips/${trips[0].id}/itinerary`} className="group relative block overflow-hidden rounded-3xl">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={trips[0].img} alt="" className="absolute inset-0 h-full w-full object-cover transition-transform duration-700 group-hover:scale-105" />
          <div className="absolute inset-0 bg-gradient-to-r from-slate/90 via-slate/60 to-transparent" />
          <div className="relative flex flex-wrap items-center justify-between gap-6 p-6 text-white md:p-8">
            <div>
              <span className="inline-flex items-center gap-1 rounded-full bg-white/15 px-2.5 py-1 text-[11px] font-bold backdrop-blur"><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-coral" />Next trip</span>
              <h2 className="mt-2 text-2xl font-extrabold md:text-3xl">{trips[0].name}</h2>
              <p className="text-sm text-white/80">{trips[0].dest} • {trips[0].dates}</p>
            </div>
            <div className="flex gap-2">
              {[["Days", cd.d], ["Hrs", cd.h], ["Min", cd.m], ["Sec", cd.s]].map(([l, v]) => (
                <div key={l} className="glass w-16 rounded-xl py-2 text-center !bg-white/15 !border-white/20">
                  <AnimatePresence mode="popLayout"><motion.p key={v as number} initial={{ y: -10, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 10, opacity: 0 }} className="text-2xl font-extrabold tabular-nums">{String(v).padStart(2, "0")}</motion.p></AnimatePresence>
                  <p className="text-[10px] font-semibold uppercase text-white/70">{l}</p>
                </div>
              ))}
            </div>
          </div>
        </Link>
      </Reveal>

      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        {[["luggage", "Trips planned", trips.length], ["place", "Places saved", 24], ["calendar_month", "Days of travel", 17]].map(([i, l, v], k) => (
          <Reveal key={l as string} delay={k * 0.08}>
            <motion.div whileHover={{ y: -4 }} className="card flex items-center gap-4 p-5">
              <span className="grid h-11 w-11 place-items-center rounded-xl bg-coral-wash text-coral"><Icon name={i as string} /></span>
              <div><p className="text-2xl font-extrabold"><CountUp to={v as number} /></p><p className="text-xs font-semibold text-muted">{l}</p></div>
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
              <button key={x} onClick={() => setF(x)} className={`relative rounded-full px-3 py-1 text-xs font-semibold ${f === x ? "text-white" : "text-muted"}`}>
                {f === x && <motion.span layoutId="tripf" className="absolute inset-0 rounded-full bg-slate" />}<span className="relative">{x}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
      <motion.div layout className="mt-4 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        <AnimatePresence mode="popLayout">
          {list.map((t) => (
            <motion.div key={t.id} layout initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }}>
              <Tilt className="h-full">
                <Link href={`/trips/${t.id}/itinerary`} className="card group block h-full overflow-hidden">
                  <div className="relative h-44 overflow-hidden">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={t.img} alt="" className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-110" />
                    <span className={`absolute left-3 top-3 rounded-full px-2.5 py-1 text-[11px] font-bold ${tone[t.status]}`}>{t.status}</span>
                  </div>
                  <div className="p-5">
                    <p className="text-lg font-bold">{t.name}</p>
                    <p className="mt-1 flex items-center gap-1 text-sm text-body"><Icon name="location_on" className="!text-[16px] text-coral" />{t.dest}</p>
                    <div className="mt-4 flex items-center justify-between text-xs font-semibold text-muted">
                      <span>{t.dates} • {t.days} days</span>
                      <span className="flex items-center gap-1 text-coral transition-transform group-hover:translate-x-1">Open<Icon name="arrow_forward" className="!text-[14px]" /></span>
                    </div>
                  </div>
                </Link>
              </Tilt>
            </motion.div>
          ))}
          <motion.div key="new" layout>
            <Link href="/trips/new" className="group grid h-full min-h-64 place-items-center rounded-2xl border-2 border-dashed border-line text-center text-muted transition hover:border-coral hover:bg-coral-wash/40 hover:text-coral">
              <div><motion.span whileHover={{ rotate: 90 }} className="inline-block"><Icon name="add_circle" className="!text-[40px]" /></motion.span><p className="mt-2 font-semibold">Plan a new trip</p></div>
            </Link>
          </motion.div>
        </AnimatePresence>
      </motion.div>
      {list.length === 0 && <p className="mt-4 text-sm text-muted">No trips match “{q}”.</p>}

      <h2 className="mt-12 text-xl font-bold">Inspiration for you</h2>
      <div className="no-scrollbar mt-4 flex gap-4 overflow-x-auto pb-2">
        {destinations.map((d, i) => (
          <motion.div key={d.name} initial={{ opacity: 0, x: 30 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.06 }}>
            <Link href={`/trips/new?q=${encodeURIComponent("4 days in " + d.name)}`} className="group relative block h-48 w-44 shrink-0 overflow-hidden rounded-2xl">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={d.img} alt={d.name} className="absolute inset-0 h-full w-full object-cover transition-transform duration-500 group-hover:scale-110" />
              <div className="absolute inset-0 bg-gradient-to-t from-slate/80 to-transparent" />
              <p className="absolute bottom-3 left-3 font-bold text-white">{d.name}</p>
            </Link>
          </motion.div>
        ))}
      </div>
    </main>
  );
}
