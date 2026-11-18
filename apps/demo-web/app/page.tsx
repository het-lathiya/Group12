"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AnimatePresence, CountUp, motion, Reveal, RotatingWord, Tilt, useTypewriter } from "@/components/fx";
import { TripMap } from "@/components/map";
import { Footer, Icon, Logo } from "@/components/ui";
import { days, destinations } from "@/lib/data";

const prompts = ["3 days in Jaipur with family", "Goa beach weekend on a budget", "Romantic Udaipur getaway", "Kerala backwaters, 7 days"];
const typed = ["5 days in Manali, love hikes and cafés…", "Weekend in Goa under ₹15,000…", "Heritage walk + street food in Delhi…", "Honeymoon in Udaipur with lake views…"];
const steps = [
  { icon: "forum", title: "Tell it your plan", text: "Type where, when, who and what you love. Plain words, no forms." },
  { icon: "auto_awesome", title: "AI builds the days", text: "Real places, routed to cut travel time, checked against opening hours and budget." },
  { icon: "drag_indicator", title: "Drag, swap, done", text: "Reorder stops, swap any place for an alternative, and save every version." },
];
const reviews = [
  ["Riya", "Planned our whole Rajasthan trip in 10 minutes. The routing is magic."],
  ["Arjun", "Loved swapping restaurants with one tap. Budget tracker kept us honest."],
  ["Meera", "Copilot found a rooftop chai spot I would never have found."],
  ["Kabir", "Versions saved us when my friend messed up Day 2 😂"],
  ["Ananya", "Finally a planner that shows travel time between stops."],
  ["Dev", "The map view + day tabs is so clean. Shared it with family instantly."],
];

export default function Home() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const ph = useTypewriter(typed);
  const [step, setStep] = useState(0);
  const go = (t: string) => t.trim() && router.push(`/trips/new?q=${encodeURIComponent(t)}`);
  useEffect(() => { const t = setInterval(() => setStep((s) => (s + 1) % steps.length), 3500); return () => clearInterval(t); }, []);

  return (
    <main className="overflow-x-hidden">
      <header className="sticky top-0 z-40 border-b border-transparent bg-canvas/80 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-[1440px] items-center justify-between px-4 md:px-6">
          <Logo />
          <nav className="hidden gap-6 text-sm font-semibold text-body md:flex">
            <a href="#how" className="hover:text-coral">How it works</a>
            <a href="#places" className="hover:text-coral">Destinations</a>
            <a href="#love" className="hover:text-coral">Reviews</a>
          </nav>
          <div className="flex items-center gap-2">
            <Link href="/sign-in" className="rounded-xl px-4 py-2 text-sm font-semibold hover:bg-white">Sign in</Link>
            <Link href="/sign-up" className="btn-dark">Get started</Link>
          </div>
        </div>
      </header>

      {/* HERO */}
      <section className="relative mx-auto grid max-w-[1440px] items-center gap-12 px-4 pb-20 pt-10 md:px-6 lg:grid-cols-2 lg:pt-16">
        <div aria-hidden className="pointer-events-none absolute -left-40 -top-40 h-[480px] w-[480px] rounded-full bg-coral/20 blur-3xl" />
        <div aria-hidden className="pointer-events-none absolute -right-20 top-40 h-[380px] w-[380px] rounded-full bg-mint/15 blur-3xl" />

        <div className="relative">
          <motion.span initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="badge-mint">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-mint" />AI itineraries with real places, costs & routes
          </motion.span>
          <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
            className="mt-5 text-[38px] font-extrabold leading-[46px] tracking-[-0.03em] md:text-[60px] md:leading-[68px]">
            Plan your trip to<br />
            <RotatingWord words={["Jaipur", "Goa", "Kerala", "Manali", "Udaipur", "Varanasi"]} className="text-coral" />
            <br />in one chat.
          </motion.h1>
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.25 }} className="mt-5 max-w-lg text-base leading-relaxed text-body md:text-lg">
            Tell TripBook where you want to go. Get a day-by-day plan with a live map, travel times and costs, then drag things around until it feels right.
          </motion.p>

          <motion.form initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35 }}
            onSubmit={(e) => { e.preventDefault(); go(q || ph); }}
            className="glass group mt-8 flex max-w-xl items-center gap-2 rounded-full p-2 pl-5 shadow-[0_12px_32px_-4px_rgba(15,23,42,0.12)] ring-coral/30 transition focus-within:ring-4">
            <Icon name="auto_awesome" className="text-coral" />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={ph} className="min-w-0 flex-1 bg-transparent py-2 text-sm outline-none md:text-base" />
            <motion.button whileHover={{ scale: 1.08, rotate: -8 }} whileTap={{ scale: 0.9 }} className="grid h-11 w-11 place-items-center rounded-full bg-coral text-white shadow-[0_8px_20px_-4px_rgba(255,90,54,0.6)]" aria-label="Plan trip">
              <Icon name="arrow_upward" />
            </motion.button>
          </motion.form>
          <div className="mt-4 flex flex-wrap gap-2">
            {prompts.map((p, i) => (
              <motion.button key={p} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.45 + i * 0.07 }}
                whileHover={{ y: -2 }} onClick={() => go(p)} className="chip hover:border-coral hover:text-coral">{p}</motion.button>
            ))}
          </div>

          <div className="mt-10 flex gap-8">
            {[[12000, "+", "trips planned"], [4.9, "", "avg rating"], [38, "%", "less travel time"]].map(([n, s, l]) => (
              <div key={l as string}>
                <p className="text-2xl font-extrabold">{n === 4.9 ? "4.9★" : <CountUp to={n as number} suffix={s as string} />}</p>
                <p className="text-xs font-semibold text-muted">{l}</p>
              </div>
            ))}
          </div>
        </div>

        <HeroDemo />
      </section>

      {/* HOW IT WORKS */}
      <section id="how" className="bg-white py-20">
        <div className="mx-auto grid max-w-[1440px] items-center gap-12 px-4 md:px-6 lg:grid-cols-2">
          <Reveal>
            <p className="label text-coral">How it works</p>
            <h2 className="mt-2 text-3xl font-extrabold tracking-tight md:text-4xl">From idea to itinerary in three steps</h2>
            <div className="mt-8 space-y-3">
              {steps.map((s, i) => (
                <button key={s.title} onClick={() => setStep(i)} className={`relative w-full overflow-hidden rounded-2xl border p-5 text-left transition ${step === i ? "border-coral/40 bg-coral-wash/50" : "border-hair hover:bg-canvas"}`}>
                  <div className="flex gap-4">
                    <span className={`grid h-11 w-11 shrink-0 place-items-center rounded-xl transition ${step === i ? "bg-coral text-white" : "bg-sky text-slate"}`}><Icon name={s.icon} /></span>
                    <div><p className="font-semibold">{i + 1}. {s.title}</p>
                      <AnimatePresence initial={false}>{step === i && (
                        <motion.p initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden text-sm text-body">{s.text}</motion.p>
                      )}</AnimatePresence>
                    </div>
                  </div>
                  {step === i && <motion.span key={"bar" + step} className="absolute bottom-0 left-0 h-0.5 bg-coral" initial={{ width: 0 }} animate={{ width: "100%" }} transition={{ duration: 3.5, ease: "linear" }} />}
                </button>
              ))}
            </div>
          </Reveal>
          <Reveal delay={0.1}>
            <div className="relative aspect-[4/3] overflow-hidden rounded-3xl bg-gradient-to-br from-sky to-coral-wash p-6">
              <AnimatePresence mode="wait">
                <motion.div key={step} initial={{ opacity: 0, scale: 0.95, y: 20 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95, y: -20 }} transition={{ duration: 0.4 }} className="grid h-full place-items-center">
                  {step === 0 && <ChatMock />}
                  {step === 1 && <GenMock />}
                  {step === 2 && <DragMock />}
                </motion.div>
              </AnimatePresence>
            </div>
          </Reveal>
        </div>
      </section>

      {/* DESTINATIONS */}
      <section id="places" className="mx-auto max-w-[1440px] px-4 py-20 md:px-6">
        <Reveal className="flex items-end justify-between">
          <div><p className="label text-coral">Trending this season</p><h2 className="mt-1 text-3xl font-extrabold tracking-tight">Where travellers are heading</h2></div>
        </Reveal>
        <div className="mt-8 grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
          {destinations.map((d, i) => (
            <Reveal key={d.name} delay={i * 0.06}>
              <Tilt className="group relative h-72 cursor-pointer overflow-hidden rounded-2xl shadow-md">
                <button onClick={() => go(`4 days in ${d.name}`)} className="absolute inset-0 text-left">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={d.img} alt={d.name} className="absolute inset-0 h-full w-full object-cover transition-transform duration-700 group-hover:scale-110" />
                  <div className="absolute inset-0 bg-gradient-to-t from-slate/85 via-slate/10 to-transparent" />
                  <div className="absolute bottom-0 p-4 text-white">
                    <p className="text-lg font-bold">{d.name}</p>
                    <p className="text-xs opacity-80">{d.country}</p>
                    <span className="mt-2 inline-flex translate-y-3 items-center gap-1 rounded-full bg-coral px-3 py-1 text-xs font-bold opacity-0 transition group-hover:translate-y-0 group-hover:opacity-100">Plan this <Icon name="arrow_forward" className="!text-[14px]" /></span>
                  </div>
                </button>
              </Tilt>
            </Reveal>
          ))}
        </div>
      </section>

      {/* REVIEWS MARQUEE */}
      <section id="love" className="overflow-hidden bg-slate py-16 text-white">
        <Reveal className="px-4 text-center"><p className="label text-coral">Loved by travellers</p><h2 className="mt-2 text-3xl font-extrabold">Trips people actually took</h2></Reveal>
        <div className="mt-10 flex w-max animate-[marquee_40s_linear_infinite] gap-4 hover:[animation-play-state:paused]">
          {[...reviews, ...reviews].map(([n, t], i) => (
            <figure key={i} className="w-80 shrink-0 rounded-2xl bg-white/5 p-5 ring-1 ring-white/10">
              <p className="text-amber-300">★★★★★</p>
              <blockquote className="mt-2 text-sm leading-relaxed text-white/85">{t}</blockquote>
              <figcaption className="mt-3 flex items-center gap-2 text-sm font-semibold"><span className="grid h-7 w-7 place-items-center rounded-full bg-coral text-xs">{n[0]}</span>{n}</figcaption>
            </figure>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-[1440px] px-4 py-20 md:px-6">
        <Reveal>
          <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-coral to-coral-deep px-6 py-16 text-center text-white">
            <motion.div aria-hidden className="absolute -right-10 -top-10 h-56 w-56 rounded-full bg-white/10" animate={{ scale: [1, 1.15, 1] }} transition={{ duration: 6, repeat: Infinity }} />
            <motion.div aria-hidden className="absolute -bottom-16 -left-10 h-64 w-64 rounded-full bg-white/10" animate={{ scale: [1.1, 1, 1.1] }} transition={{ duration: 7, repeat: Infinity }} />
            <h2 className="relative text-3xl font-extrabold tracking-tight md:text-5xl">Your next trip is one prompt away</h2>
            <p className="relative mt-3 text-white/80">Free while in beta. No credit card.</p>
            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.97 }} className="relative mt-8 inline-block">
              <Link href="/trips/new" className="inline-flex items-center gap-2 rounded-xl bg-white px-6 py-3 font-bold text-coral-deep shadow-xl">Start planning<Icon name="arrow_forward" /></Link>
            </motion.div>
          </div>
        </Reveal>
      </section>
      <Footer />
    </main>
  );
}

function HeroDemo() {
  const stops = days[0].stops.concat(days[1].stops.slice(0, 1));
  const [sel, setSel] = useState(0);
  useEffect(() => { const t = setInterval(() => setSel((s) => (s + 1) % stops.length), 2600); return () => clearInterval(t); }, [stops.length]);
  return (
    <motion.div initial={{ opacity: 0, x: 40 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.3, duration: 0.7 }} className="relative">
      <div className="card overflow-hidden p-3 shadow-[0_30px_60px_-20px_rgba(15,23,42,0.25)]">
        <div className="flex items-center gap-2 px-1 pb-3">
          <span className="h-2.5 w-2.5 rounded-full bg-[#ff5f57]" /><span className="h-2.5 w-2.5 rounded-full bg-[#febc2e]" /><span className="h-2.5 w-2.5 rounded-full bg-[#28c840]" />
          <span className="ml-2 text-xs font-semibold text-muted">Jaipur • 2 days</span>
        </div>
        <div className="h-64 overflow-hidden rounded-xl md:h-72">
          <TripMap pins={stops.map((s) => ({ id: s.id, lat: s.lat, lon: s.lon }))} selected={stops[sel].id} onSelect={(id) => setSel(stops.findIndex((s) => s.id === id))} />
        </div>
        <div className="mt-3 space-y-2">
          {stops.map((s, i) => (
            <motion.button key={s.id} onClick={() => setSel(i)} animate={{ backgroundColor: i === sel ? "#fff1ec" : "#ffffff" }} className="flex w-full items-center gap-3 rounded-xl p-2 text-left">
              <span className={`grid h-6 w-6 place-items-center rounded-full text-[11px] font-bold text-white ${i === sel ? "bg-coral-deep" : "bg-coral"}`}>{i + 1}</span>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={s.img} alt="" className="h-9 w-9 rounded-lg object-cover" />
              <div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold">{s.name}</p><p className="text-[11px] text-muted">{s.time} • {s.category}</p></div>
              {i === sel && <motion.span layoutId="demo-dot" className="badge-mint">Now</motion.span>}
            </motion.button>
          ))}
        </div>
      </div>
      <motion.div animate={{ y: [0, -10, 0] }} transition={{ duration: 4, repeat: Infinity }} className="glass absolute -left-6 top-24 hidden rounded-2xl p-3 shadow-xl md:block">
        <p className="text-[11px] font-bold text-mint">✓ Budget check</p><p className="text-sm font-bold">₹4,050 under budget</p>
      </motion.div>
      <motion.div animate={{ y: [0, 10, 0] }} transition={{ duration: 5, repeat: Infinity }} className="glass absolute -right-4 bottom-28 hidden rounded-2xl p-3 shadow-xl md:block">
        <p className="flex items-center gap-1 text-[11px] font-bold text-coral"><Icon name="auto_awesome" className="!text-[14px]" />AI tip</p><p className="text-sm font-bold">Go at 8 AM, skip the crowds</p>
      </motion.div>
    </motion.div>
  );
}

function ChatMock() {
  return (
    <div className="w-full max-w-sm space-y-3">
      <motion.p initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="ml-auto w-fit rounded-2xl rounded-tr-sm bg-slate px-4 py-2 text-sm text-white">4 days in Kerala, slow pace, love food 🍛</motion.p>
      <motion.p initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.5 }} className="w-fit rounded-2xl rounded-tl-sm bg-white px-4 py-2 text-sm shadow">Lovely! Kochi → Alleppey → Munnar. Houseboat night on Day 2?</motion.p>
      <motion.p initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 1 }} className="ml-auto w-fit rounded-2xl rounded-tr-sm bg-slate px-4 py-2 text-sm text-white">Yes please!</motion.p>
    </div>
  );
}
function GenMock() {
  return (
    <div className="w-full max-w-sm space-y-2">
      {["Finding places", "Routing days", "Checking budget", "Validating hours"].map((t, i) => (
        <motion.div key={t} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.4 }} className="flex items-center gap-3 rounded-xl bg-white p-3 shadow-sm">
          <motion.span initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: i * 0.4 + 0.3, type: "spring" }} className="ms ms-fill text-mint">check_circle</motion.span>
          <span className="text-sm font-semibold">{t}</span>
        </motion.div>
      ))}
    </div>
  );
}
function DragMock() {
  const items = ["Amber Fort", "Panna Meena ka Kund", "1135 AD lunch"];
  return (
    <div className="w-full max-w-sm space-y-2">
      {items.map((t, i) => (
        <motion.div key={t} animate={i === 1 ? { y: [0, 52, 52, 0], rotate: [0, 2, 2, 0], boxShadow: ["0 1px 2px #0001", "0 20px 30px #0002", "0 20px 30px #0002", "0 1px 2px #0001"] } : i === 2 ? { y: [0, -52, -52, 0] } : {}}
          transition={{ duration: 3, repeat: Infinity, times: [0, 0.3, 0.7, 1] }} className="flex items-center gap-3 rounded-xl bg-white p-3">
          <span className="ms text-muted">drag_indicator</span><span className="text-sm font-semibold">{t}</span>
        </motion.div>
      ))}
    </div>
  );
}
