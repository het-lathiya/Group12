"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "motion/react";
import { trip, user } from "@/lib/data";

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
  ["Explore", "/trips/" + trip.id + "/explore"],
  ["My Trips", "/dashboard"],
  ["Saved Places", "/trips/" + trip.id + "/explore?saved=1"],
  ["New Trip", "/trips/new"],
];

export function AppNav() {
  const path = usePathname();
  return (
    <header className="sticky top-0 z-40 border-b border-hair bg-white/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-[1440px] items-center gap-6 px-4 md:px-6">
        <Logo />
        <nav className="hidden items-center gap-1 lg:flex">
          {links.map(([l, h]) => {
            const active = path === h.split("?")[0] && l !== "Saved Places";
            return (
              <Link key={l} href={h} className={`rounded-lg px-3 py-2 text-sm font-semibold ${active ? "text-coral" : "text-body hover:bg-canvas"}`}>{l}</Link>
            );
          })}
        </nav>
        <div className="ml-auto hidden max-w-sm flex-1 items-center gap-2 rounded-full border border-line bg-canvas px-4 py-2 md:flex">
          <Icon name="auto_awesome" className="text-coral" />
          <input placeholder="Ask TripBook anything or plan a new trip…" className="min-w-0 flex-1 bg-transparent text-sm outline-none" />
          <kbd className="rounded border border-line bg-white px-1.5 text-[10px] text-muted">⌘K</kbd>
        </div>
        <Link href="/profile" aria-label="Profile" className="ml-auto grid h-9 w-9 place-items-center rounded-full bg-slate text-xs font-bold text-white md:ml-0">{user.initials}</Link>
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

export function TripHeader({ tripId }: { tripId: string }) {
  const path = usePathname();
  return (
    <section className="border-b border-hair bg-white">
      <div className="mx-auto flex max-w-[1440px] flex-col gap-4 px-4 py-5 md:px-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-1 text-xs font-semibold text-muted">
            <Link href="/dashboard" className="hover:text-coral">{trip.folder}</Link>
            <Icon name="chevron_right" className="!text-[14px]" />
            <span className="text-slate">{trip.name}</span>
            <span className="ml-1 inline-flex items-center gap-1 rounded-full bg-sky px-2 py-0.5 text-[11px]">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-mint" />Auto-saved
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button className="btn-soft"><Icon name="person_add" className="!text-[16px]" />Collaborate</button>
            <button className="btn-soft"><Icon name="ios_share" className="!text-[16px]" />Share</button>
            <Link href={`/trips/${tripId}/edit`} className="btn-primary"><Icon name="add" />Add Place</Link>
          </div>
        </div>

        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="label flex items-center gap-1 text-coral"><Icon name="route" className="!text-[14px]" />Curated AI itinerary • Smart routing</p>
            <h1 className="mt-1 max-w-3xl text-2xl font-extrabold leading-tight tracking-tight md:text-[34px] md:leading-[42px]">{trip.title}</h1>
            <div className="mt-3 flex flex-wrap gap-2">
              <span className="chip"><Icon name="calendar_month" className="!text-[14px] text-coral" />{trip.dates}</span>
              <span className="chip"><Icon name="group" className="!text-[14px] text-coral" />{trip.travelers} Travelers</span>
              <span className="chip"><Icon name="payments" className="!text-[14px] text-coral" />{trip.budget}</span>
              <span className="badge-mint !py-1 !text-xs"><Icon name="restaurant" className="!text-[14px]" />{trip.vibe}</span>
            </div>
          </div>
          <nav className="no-scrollbar flex max-w-full gap-1 overflow-x-auto rounded-xl bg-sky p-1">
            {tabs.map(([l, seg]) => {
              const href = `/trips/${tripId}/${seg}`;
              const active = path === href;
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

// Static OpenStreetMap tile mosaic (no iframe, works everywhere). Swap for maplibre-gl when needed.
export function MapEmbed({ lat, lon, zoom = 0.06, className = "" }: { lat: number; lon: number; zoom?: number; className?: string }) {
  const z = zoom <= 0.03 ? 15 : 14;
  const n = 2 ** z;
  const fx = ((lon + 180) / 360) * n;
  const r = (lat * Math.PI) / 180;
  const fy = ((1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2) * n;
  const tx = Math.floor(fx), ty = Math.floor(fy);
  const ox = (fx - tx) * 256, oy = (fy - ty) * 256;
  const R = 2;
  const tiles = [];
  for (let dy = -R; dy <= R; dy++) for (let dx = -R; dx <= R; dx++) tiles.push([dx, dy]);
  return (
    <div className={`relative h-full w-full overflow-hidden bg-[#e8eef5] ${className}`}>
      <div className="absolute left-1/2 top-1/2" style={{ transform: `translate(${-ox}px, ${-oy}px)` }}>
        {tiles.map(([dx, dy]) => (
          // eslint-disable-next-line @next/next/no-img-element
          <img key={`${dx},${dy}`} alt="" draggable={false} src={`https://tile.openstreetmap.org/${z}/${tx + dx}/${ty + dy}.png`}
            className="absolute h-64 w-64 max-w-none select-none" style={{ left: dx * 256, top: dy * 256 }} />
        ))}
      </div>
      <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-full text-coral drop-shadow-md">
        <span aria-hidden className="ms ms-fill !text-[40px]">location_on</span>
      </span>
      <a href={`https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=${z}/${lat}/${lon}`} target="_blank" rel="noreferrer"
        className="absolute bottom-1 right-1 rounded bg-white/80 px-1 text-[9px] text-muted">© OpenStreetMap</a>
    </div>
  );
}
