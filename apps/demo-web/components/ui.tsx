"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";
import { fmtDate, money, type Trip } from "@/lib/api";
import { useSession } from "@/lib/session";

export function Icon({ name, className = "", fill = false }: { name: string; className?: string; fill?: boolean }) {
  return <span aria-hidden className={`ms ${fill ? "ms-fill" : ""} ${className}`}>{name}</span>;
}

export function Logo() {
  return (
    <Link href="/" className="flex items-center gap-2 text-[17px] font-extrabold tracking-tight">
      <span className="grid h-8 w-8 place-items-center rounded-xl bg-coral text-white shadow-[0_4px_12px_-2px_rgba(255,90,54,0.5)]">
        <Icon name="travel_explore" className="!text-[18px]" />
      </span>
      TripBook
    </Link>
  );
}

const links = [
  ["My Trips", "/dashboard/"],
  ["New Trip", "/trips/new/"],
  ["Profile", "/profile/"],
];

export function AppNav() {
  const path = usePathname();
  const { user, signOut } = useSession();
  const [menu, setMenu] = useState(false);
  const email = user?.email ?? "";
  const initials = (email.split("@")[0] || "?").slice(0, 2).toUpperCase();
  return (
    <header className="sticky top-0 z-40 border-b border-hair bg-white/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-[1440px] items-center gap-6 px-4 md:px-6">
        <Logo />
        <nav className="hidden items-center gap-1 md:flex">
          {links.map(([l, h]) => {
            const active = path === h || path === h.slice(0, -1);
            return (
              <Link key={l} href={h} className={`relative rounded-lg px-3 py-2 text-sm font-semibold ${active ? "text-coral" : "text-body hover:bg-canvas"}`}>
                {l}
                {active && <motion.span layoutId="navline" className="absolute inset-x-3 -bottom-[13px] h-0.5 rounded-full bg-coral" />}
              </Link>
            );
          })}
        </nav>
        <span className="ml-auto hidden items-center gap-1.5 rounded-full bg-mint-wash px-3 py-1 text-[11px] font-bold text-mint sm:inline-flex">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-mint" />Live • staging API
        </span>
        <div className="relative ml-auto sm:ml-0">
          <button onClick={() => setMenu((m) => !m)} aria-label="Account menu" className="grid h-9 w-9 place-items-center rounded-full bg-slate text-xs font-bold text-white">{initials}</button>
          <AnimatePresence>
            {menu && (
              <motion.div initial={{ opacity: 0, y: -6, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -6 }}
                className="card absolute right-0 top-11 w-60 p-2 shadow-xl">
                <p className="truncate px-3 py-2 text-xs text-muted">{email}</p>
                <Link href="/profile/" onClick={() => setMenu(false)} className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm hover:bg-canvas"><Icon name="person" />Profile</Link>
                <button onClick={signOut} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-coral hover:bg-coral-wash"><Icon name="logout" />Sign out</button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </header>
  );
}

const tabs = [
  ["Day-by-Day", "itinerary"],
  ["Explore", "explore"],
  ["Edit", "edit"],
  ["Costs", "costs"],
  ["Versions", "versions"],
  ["Summary", "summary"],
];

export function TripHeader({ trip, tripId }: { trip?: Trip; tripId: string }) {
  const path = usePathname();
  const [hasPath, setHasPath] = useState("");
  useEffect(() => setHasPath(window.location.pathname), [path]);
  const travellers = trip ? trip.adults + trip.children : 0;
  return (
    <section className="border-b border-hair bg-white">
      <div className="mx-auto flex max-w-[1440px] flex-col gap-4 px-4 py-5 md:px-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-1 text-xs font-semibold text-muted">
            <Link href="/dashboard/" className="hover:text-coral">My Trips</Link>
            <Icon name="chevron_right" className="!text-[14px]" />
            <span className="text-slate">{trip?.destination.name ?? "…"}</span>
            {trip && (
              <span className="ml-1 inline-flex items-center gap-1 rounded-full bg-sky px-2 py-0.5 text-[11px]">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-mint" />Rev {trip.plan_revision} • saved
              </span>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Link href={`/trips/${tripId}/explore/`} className="btn-soft"><Icon name="travel_explore" className="!text-[16px]" />Find places</Link>
            <Link href={`/trips/${tripId}/summary/`} className="btn-soft"><Icon name="ios_share" className="!text-[16px]" />Summary</Link>
            <Link href={`/trips/${tripId}/generate/`} className="btn-primary"><Icon name="auto_awesome" />{trip?.has_itinerary ? "Regenerate" : "Generate"}</Link>
          </div>
        </div>

        <div className="flex flex-wrap items-end justify-between gap-4">
          <div className="min-w-0">
            <p className="label flex items-center gap-1 text-coral"><Icon name="route" className="!text-[14px]" />AI itinerary • validated & costed by the API</p>
            {trip ? (
              <motion.h1 initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mt-1 max-w-3xl text-2xl font-extrabold leading-tight tracking-tight md:text-[34px] md:leading-[42px]">{trip.title}</motion.h1>
            ) : <div className="mt-2 h-9 w-80 max-w-full animate-pulse rounded-lg bg-line/60" />}
            {trip && (
              <div className="mt-3 flex flex-wrap gap-2">
                <span className="chip"><Icon name="calendar_month" className="!text-[14px] text-coral" />{fmtDate(trip.start_date, { month: "short", day: "numeric" })} – {fmtDate(trip.end_date, { month: "short", day: "numeric" })} ({trip.num_days} Days)</span>
                <span className="chip"><Icon name="group" className="!text-[14px] text-coral" />{travellers} Traveller{travellers === 1 ? "" : "s"}</span>
                {trip.budget && <span className="chip"><Icon name="payments" className="!text-[14px] text-coral" />Budget {money(trip.budget.amount, trip.budget.currency)}</span>}
                <span className={trip.status === "ready" ? "badge-mint !py-1 !text-xs" : "chip"}><Icon name={trip.status === "ready" ? "check_circle" : "edit_note"} className="!text-[14px]" />{trip.status}</span>
                {trip.plan_stale && <span className="chip !border-amber-300 !text-amber-700"><Icon name="warning" className="!text-[14px]" />Plan out of date</span>}
              </div>
            )}
          </div>
          <nav className="no-scrollbar flex max-w-full gap-1 overflow-x-auto rounded-xl bg-sky p-1">
            {tabs.map(([l, seg]) => {
              const href = `/trips/${tripId}/${seg}/`;
              const active = hasPath.includes(`/${seg}`);
              return (
                <Link key={seg} href={href} className={`relative shrink-0 rounded-lg px-3 py-1.5 text-xs font-semibold ${active ? "text-slate" : "text-muted hover:text-slate"}`}>
                  {active && <motion.span layoutId="triptab" className="absolute inset-0 rounded-lg bg-white shadow-sm" transition={{ type: "spring", stiffness: 400, damping: 32 }} />}
                  <span className="relative">{l}</span>
                </Link>
              );
            })}
          </nav>
        </div>
      </div>
    </section>
  );
}

export function Footer() {
  return (
    <footer className="mt-16 border-t border-hair bg-white">
      <div className="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-3 px-4 py-6 text-xs text-muted md:px-6">
        <p><span className="font-extrabold text-slate">TripBook</span> © 2026 Group 12. Travel planned with AI.</p>
        <div className="flex gap-5"><a href="#">Privacy</a><a href="#">Terms</a><a href="#">Support</a></div>
      </div>
    </footer>
  );
}

