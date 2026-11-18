"use client";

import { AnimatePresence, motion, Reorder, useDragControls } from "motion/react";
import { useMemo, useRef, useState } from "react";
import { Stream, TypingDots, useToast } from "@/components/fx";
import { TripMap } from "@/components/map";
import { Icon } from "@/components/ui";
import { days as initialDays, picks, trip, type Day, type Stop } from "@/lib/data";

const toneCls = { mint: "badge-mint", coral: "bg-coral-wash text-coral-deep border border-[#ffd2c6] rounded-full px-2.5 py-0.5 text-[11px] font-bold", sky: "bg-sky text-body rounded-full px-2.5 py-0.5 text-[11px] font-bold" };
const legIcon = { walk: "directions_walk", transit: "directions_bus", car: "local_taxi" };
const dayColor = ["#ff5a36", "#0f172a", "#059669", "#6366f1", "#f59e0b"];
const weather = [["sunny", "24° / 11°"], ["partly_cloudy_day", "23° / 10°"], ["sunny", "26° / 13°"]];

type Msg = { id: number; from: "me" | "ai"; text: string; place?: Stop; streamed?: boolean };

const copilotReplies: Record<string, { text: string; place?: Partial<Stop> }> = {
  food: { text: "For an evening food walk, Masala Chowk in Ram Niwas Garden has 20+ old-city stalls in one place. Pyaaz kachori and kulfi are musts. It's 10 minutes from Hawa Mahal.", place: { name: "Masala Chowk Food Court", category: "Street food", lat: 26.9118, lon: 75.8195 } },
  quiet: { text: "Panna Meena ka Kund is already on Day 2. For another quiet one, Chand Baori is a day trip, but Toorji ka Jhalra stepwell in Jodhpur style is closer. I'd keep it simple and stay with what's planned.", },
  train: { text: "The 6:00 AM Jaipur → Udaipur Intercity reaches at 1:05 PM. There's also a 2:45 PM train arriving at 10:15 PM. The morning one leaves your evening free for the Lake Pichola cruise." },
  default: { text: "Good idea! Based on your pace and budget, I'd slot that into Day 2 afternoon, after lunch at 1135 AD. Want me to add a rooftop café nearby too?", place: { name: "Rooftop café, Amer", category: "Café", lat: 26.9846, lon: 75.8528 } },
};
const pickReply = (t: string) => /food|eat|street/i.test(t) ? copilotReplies.food : /quiet|stepwell/i.test(t) ? copilotReplies.quiet : /train|timing/i.test(t) ? copilotReplies.train : copilotReplies.default;

export default function Itinerary() {
  const toast = useToast();
  const [days, setDays] = useState<Day[]>(initialDays);
  const [filter, setFilter] = useState(0);
  const [sel, setSel] = useState<string>(initialDays[0].stops[1].id);
  const [collapsed, setCollapsed] = useState<number[]>([]);
  const [open, setOpen] = useState<string | null>(null);
  const [saved, setSaved] = useState<string[]>([]);
  const [ask, setAsk] = useState("");
  const [thinking, setThinking] = useState(false);
  const [chat, setChat] = useState<Msg[]>([
    { id: 1, from: "me", text: "Is there a good late-night chai spot near Hawa Mahal for Day 1?" },
    { id: 2, from: "ai", text: "Try Tapri Central, a rooftop tea house 6 minutes from Hawa Mahal, open until 11 PM with views over the old city.", streamed: true,
      place: { id: "tapri", time: "09:30 PM", category: "Chai & snacks", name: "Tapri Central", desc: "Rooftop tea house with old-city views.", img: picks[0].img, price: "₹ • ₹250 / pp", cost: 500, lat: 26.9089, lon: 75.8035 } },
  ]);
  const chatEnd = useRef<HTMLDivElement>(null);

  const all = days.flatMap((d) => d.stops.map((s) => ({ ...s, day: d.n })));
  const selected = all.find((s) => s.id === sel) ?? all[0];
  const pins = useMemo(() => all.filter((s) => filter === 0 || s.day === filter).map((s) => ({ id: s.id, lat: s.lat, lon: s.lon, color: dayColor[(s.day - 1) % 5] })), [days, filter]); // eslint-disable-line react-hooks/exhaustive-deps
  const total = all.reduce((s, x) => s + x.cost, 0);

  const reorder = (d: number, stops: Stop[]) => setDays((ds) => ds.map((x, i) => (i === d ? { ...x, stops } : x)));
  const remove = (d: number, s: Stop) => {
    const before = days;
    setDays((ds) => ds.map((x, i) => (i === d ? { ...x, stops: x.stops.filter((y) => y.id !== s.id) } : x)));
    toast({ text: `Removed ${s.name}`, icon: "delete", undo: () => setDays(before) });
  };
  const addTo = (dayN: number, s: Stop) => {
    setDays((ds) => ds.map((x) => (x.n === dayN ? { ...x, stops: [...x.stops, { ...s, id: s.id + "-" + Date.now() }] } : x)));
    toast({ text: `Added ${s.name} to Day ${dayN}`, icon: "add_location_alt" });
  };

  const send = (text: string) => {
    if (!text.trim() || thinking) return;
    setChat((c) => [...c, { id: Date.now(), from: "me", text }]);
    setAsk(""); setThinking(true);
    setTimeout(() => chatEnd.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }), 50);
    // TODO: call the AI endpoint
    setTimeout(() => {
      const r = pickReply(text);
      const place = r.place ? { id: "ai" + Date.now(), time: "06:00 PM", desc: "", img: picks[2].img, price: "₹₹", cost: 400, ...r.place } as Stop : undefined;
      setChat((c) => [...c, { id: Date.now(), from: "ai", text: r.text, place }]);
      setThinking(false);
    }, 1100);
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
      <div className="min-w-0 space-y-8">
        {/* AI prompt */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="card bg-gradient-to-br from-white to-coral-wash/60 p-4">
          <form onSubmit={(e) => { e.preventDefault(); send(ask); }} className="flex items-center gap-3">
            <motion.span animate={{ rotate: [0, 15, -10, 0] }} transition={{ duration: 2.5, repeat: Infinity, repeatDelay: 2 }} className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-coral-wash text-coral"><Icon name="auto_awesome" /></motion.span>
            <input value={ask} onChange={(e) => setAsk(e.target.value)} placeholder="Ask TripBook: e.g. find a quiet rooftop café near Amber Fort…" className="input !h-11 flex-1 !rounded-xl" />
            <motion.button whileTap={{ scale: 0.9 }} whileHover={{ scale: 1.05 }} className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-coral-deep text-white" aria-label="Send"><Icon name="send" /></motion.button>
          </form>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span className="label text-muted">Try asking:</span>
            {[["nightlife", "Add evening street food tour"], ["self_improvement", "Find quiet stepwells"], ["train", "Check train timing"]].map(([i, t]) => (
              <motion.button whileHover={{ y: -2 }} key={t} onClick={() => send(t)} className="chip !text-[11px] hover:border-coral"><Icon name={i} className="!text-[14px] text-coral" />{t}</motion.button>
            ))}
          </div>
        </motion.div>

        {/* Trip progress strip */}
        <div className="card flex flex-wrap items-center gap-x-6 gap-y-3 p-4 text-sm">
          <div className="flex items-center gap-2"><Icon name="place" className="text-coral" /><b>{all.length}</b> stops</div>
          <div className="flex items-center gap-2"><Icon name="payments" className="text-coral" /><b>₹{total.toLocaleString("en-IN")}</b> est.</div>
          <div className="flex items-center gap-2"><Icon name="directions_walk" className="text-coral" /><b>4.8 km</b> / day</div>
          <div className="ml-auto flex items-center gap-2 text-xs text-muted"><Icon name="drag_indicator" className="!text-[16px]" />Drag cards to reorder</div>
        </div>

        {days.map((day, d) => {
          const isCol = collapsed.includes(day.n);
          return (
            <section key={day.n}>
              <button onClick={() => setCollapsed((c) => isCol ? c.filter((x) => x !== day.n) : [...c, day.n])} className="flex w-full items-start gap-3 text-left">
                <span className="rounded-lg px-2.5 py-1 text-xs font-bold text-white" style={{ background: d === 0 ? "#b52603" : dayColor[d % 5] }}>Day {day.n}</span>
                <div className="flex-1">
                  <h2 className="text-lg font-bold leading-tight md:text-xl">{day.title}</h2>
                  <p className="flex flex-wrap items-center gap-x-2 text-xs text-muted">{day.date} • {day.area}
                    <span className="inline-flex items-center gap-0.5 text-amber-600"><Icon name={weather[d % 3][0]} className="!text-[14px]" />{weather[d % 3][1]}</span>
                  </p>
                </div>
                <span className="rounded-full bg-sky px-2.5 py-1 text-[11px] font-semibold text-body">{day.stops.length} Activities</span>
                <motion.span animate={{ rotate: isCol ? -90 : 0 }} className="text-muted"><Icon name="expand_more" /></motion.span>
              </button>

              <AnimatePresence initial={false}>
                {!isCol && (
                  <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.3 }} className="overflow-hidden">
                    <Reorder.Group axis="y" values={day.stops} onReorder={(v) => reorder(d, v)} className="relative mt-4 space-y-3 border-l-2 border-dashed border-line pl-6 md:ml-2">
                      {day.stops.map((s, i) => (
                        <StopCard key={s.id} s={s} i={i} color={dayColor[d % 5]} active={sel === s.id} expanded={open === s.id} saved={saved.includes(s.id)}
                          leg={i < day.stops.length - 1 ? day.legs[i] : undefined}
                          onSelect={() => setSel(s.id)} onToggle={() => setOpen(open === s.id ? null : s.id)}
                          onSave={() => { setSaved((x) => x.includes(s.id) ? x.filter((y) => y !== s.id) : [...x, s.id]); toast({ text: saved.includes(s.id) ? "Removed from saved" : `Saved ${s.name}`, icon: "bookmark" }); }}
                          onRemove={() => remove(d, s)} />
                      ))}
                    </Reorder.Group>
                    {day.stops.length === 0 && <p className="mt-4 rounded-xl border-2 border-dashed border-line p-6 text-center text-sm text-muted">No plans yet. Ask Copilot to suggest something.</p>}
                  </motion.div>
                )}
              </AnimatePresence>
            </section>
          );
        })}

        <motion.button whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }} onClick={() => send("Suggest an evening activity")} className="flex w-full items-center justify-center gap-2 rounded-2xl bg-sky py-4 text-sm font-semibold hover:bg-[#dce9ff]">
          <span className="grid h-6 w-6 place-items-center rounded-full bg-coral text-white"><Icon name="add" className="!text-[16px]" /></span>
          Add custom place or let TripBook suggest an evening activity
        </motion.button>
      </div>

      {/* RIGHT */}
      <aside className="min-w-0 space-y-5 lg:sticky lg:top-20 lg:self-start">
        <div className="card overflow-hidden p-3">
          <div className="relative flex flex-wrap gap-1.5">
            {["All Days", ...days.map((d) => `Day ${d.n}`)].map((l, i) => (
              <button key={l} onClick={() => setFilter(i)} className={`relative rounded-full px-3 py-1 text-xs font-semibold ${filter === i ? "text-white" : "text-body hover:bg-canvas"}`}>
                {filter === i && <motion.span layoutId="mapfilter" className="absolute inset-0 rounded-full bg-slate" transition={{ type: "spring", stiffness: 400, damping: 30 }} />}
                <span className="relative">{l}</span>
              </button>
            ))}
          </div>
          <div className="relative mt-3 h-72 overflow-hidden rounded-xl md:h-80">
            <TripMap pins={pins} selected={sel} onSelect={(id) => { setSel(id); document.getElementById("stop-" + id)?.scrollIntoView({ behavior: "smooth", block: "center" }); }} />
            <AnimatePresence mode="wait">
              <motion.div key={selected.id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 10 }} className="glass absolute bottom-3 left-3 right-14 flex items-center gap-3 rounded-xl p-2 shadow-lg">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={selected.img} alt="" className="h-12 w-12 rounded-lg object-cover" />
                <div className="min-w-0 flex-1">
                  <p className="text-[10px] font-bold text-mint">● Day {selected.day} • {selected.category}</p>
                  <p className="truncate text-sm font-bold">{selected.name}</p>
                  <p className="truncate text-[11px] text-muted">{selected.time} • {selected.price}</p>
                </div>
                <button onClick={() => document.getElementById("stop-" + selected.id)?.scrollIntoView({ behavior: "smooth", block: "center" })} className="rounded-lg bg-coral-deep px-3 py-1.5 text-xs font-bold text-white">Focus</button>
              </motion.div>
            </AnimatePresence>
          </div>
        </div>

        {/* Copilot */}
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <span className="relative grid h-9 w-9 place-items-center rounded-xl bg-coral-wash text-coral"><Icon name="smart_toy" />
              <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full border-2 border-white bg-mint" /></span>
            <div className="flex-1"><p className="font-semibold">TripBook Copilot</p><p className="text-[11px] text-muted">{thinking ? "Thinking…" : "Contextual advice • real-time schedule"}</p></div>
            <span className="rounded-full bg-sky px-2 py-1 text-[10px] font-semibold text-body">{trip.city.name} local</span>
          </div>
          <div className="mt-4 max-h-80 space-y-3 overflow-y-auto pr-1">
            <AnimatePresence initial={false}>
              {chat.map((m) => m.from === "me" ? (
                <motion.p key={m.id} initial={{ opacity: 0, x: 20, scale: 0.95 }} animate={{ opacity: 1, x: 0, scale: 1 }} className="ml-auto w-fit max-w-[85%] rounded-2xl rounded-tr-sm bg-slate px-3 py-2 text-[13px] text-white">{m.text}</motion.p>
              ) : (
                <motion.div key={m.id} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} className="max-w-[92%] rounded-2xl rounded-tl-sm bg-canvas p-3 text-[13px] leading-5 text-body">
                  <p>{m.streamed ? m.text : <Stream text={m.text} onDone={() => setChat((c) => c.map((x) => x.id === m.id ? { ...x, streamed: true } : x))} />}</p>
                  {m.place && m.streamed && (
                    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="mt-2 flex flex-wrap gap-2">
                      <motion.button whileTap={{ scale: 0.95 }} onClick={() => addTo(1, m.place!)} className="flex items-center gap-1 rounded-lg bg-coral-deep px-2.5 py-1 text-[11px] font-bold text-white"><Icon name="add_circle" className="!text-[14px]" />Insert into Day 1</motion.button>
                      <button onClick={() => addTo(2, m.place!)} className="flex items-center gap-1 rounded-lg bg-white px-2.5 py-1 text-[11px] font-semibold"><Icon name="add" className="!text-[14px]" />Day 2</button>
                    </motion.div>
                  )}
                </motion.div>
              ))}
            </AnimatePresence>
            {thinking && <div className="w-fit rounded-2xl bg-canvas px-4 py-3"><TypingDots /></div>}
            <div ref={chatEnd} />
          </div>
          <form onSubmit={(e) => { e.preventDefault(); send(ask); }} className="mt-3 flex items-center gap-2 rounded-full border border-line px-3 py-1.5 transition focus-within:border-coral focus-within:ring-4 focus-within:ring-coral/10">
            <input value={ask} onChange={(e) => setAsk(e.target.value)} placeholder="Reply to Copilot or ask about weather…" className="min-w-0 flex-1 bg-transparent text-[13px] outline-none" />
            <button aria-label="Voice" type="button" className="text-muted"><Icon name="mic" /></button>
            <button aria-label="Send" className="text-coral"><Icon name="send" /></button>
          </form>
        </div>
      </aside>

      <Picks onAdd={addTo} />
    </div>
  );
}

function StopCard({ s, i, color, active, expanded, saved, leg, onSelect, onToggle, onSave, onRemove }: {
  s: Stop; i: number; color: string; active: boolean; expanded: boolean; saved: boolean; leg?: { text: string; mode: "walk" | "transit" | "car" };
  onSelect: () => void; onToggle: () => void; onSave: () => void; onRemove: () => void;
}) {
  const controls = useDragControls();
  return (
    <Reorder.Item value={s} id={"stop-" + s.id} dragListener={false} dragControls={controls}
      initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, x: -40, height: 0 }}
      whileDrag={{ scale: 1.02, boxShadow: "0 24px 40px -8px rgba(15,23,42,0.25)", zIndex: 30 }} className="relative list-none">
      <motion.article onClick={onSelect} whileHover={{ y: -2 }} layout="position"
        className={`card relative flex cursor-pointer flex-col gap-4 p-3 transition-shadow sm:flex-row ${active ? "ring-2 ring-coral/50" : ""}`}>
        <span className="absolute -left-[33px] top-6 grid h-4 w-4 place-items-center rounded-full ring-4 ring-canvas" style={{ background: color }}>
          {active && <span className="absolute h-4 w-4 animate-ping rounded-full" style={{ background: color, opacity: 0.4 }} />}
        </span>
        <button onPointerDown={(e) => controls.start(e)} onClick={(e) => e.stopPropagation()} className="absolute right-2 top-1/2 hidden -translate-y-1/2 cursor-grab touch-none rounded p-1 text-line hover:bg-canvas hover:text-muted active:cursor-grabbing sm:block" aria-label="Drag to reorder">
          <Icon name="drag_indicator" />
        </button>
        <div className="group relative h-40 shrink-0 overflow-hidden rounded-xl sm:h-32 sm:w-44">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={s.img} alt="" className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-110" />
          <span className="absolute bottom-2 left-2 grid h-6 w-6 place-items-center rounded-full text-[11px] font-bold text-white" style={{ background: color }}>{i + 1}</span>
          {s.tag && <span className="absolute left-2 top-2 flex items-center gap-1 rounded-md bg-slate/80 px-1.5 py-0.5 text-[10px] font-bold text-white backdrop-blur"><Icon name="star" fill className="!text-[11px] text-amber-300" />{s.tag}</span>}
          <motion.button whileTap={{ scale: 1.4 }} onClick={(e) => { e.stopPropagation(); onSave(); }} className="glass absolute right-2 top-2 grid h-7 w-7 place-items-center rounded-full" aria-label="Save">
            <Icon name="favorite" fill={saved} className={`!text-[15px] ${saved ? "text-coral" : ""}`} />
          </motion.button>
        </div>
        <div className="min-w-0 flex-1 sm:pr-6">
          <div className="flex items-start justify-between gap-2">
            <p className="label text-coral">{s.time} • {s.category}</p>
            {s.status && <span className={toneCls[s.status.tone]}>{s.status.text}</span>}
          </div>
          <h3 className="mt-1 font-semibold">{s.name}</h3>
          <p className={`mt-1 text-[13px] leading-5 text-body ${expanded ? "" : "line-clamp-2"}`}>{s.desc}</p>
          {s.tip && (
            <p className="mt-2 flex gap-1.5 rounded-lg bg-coral-wash/70 p-2 text-[12px] leading-4 text-coral-deep">
              <Icon name="lightbulb" className="!text-[14px]" /><span><b>TripBook tip:</b> {s.tip}</span>
            </p>
          )}
          <AnimatePresence>
            {expanded && (
              <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                <div className="mt-3 grid grid-cols-3 gap-2 text-center text-[11px]">
                  {[["schedule", "1.5 – 2 hrs"], ["accessible", "Step-free"], ["photo_camera", "Photo spot"]].map(([ic, t]) => (
                    <div key={t} className="rounded-lg bg-canvas p-2"><Icon name={ic} className="text-coral" /><p className="mt-1 font-semibold">{t}</p></div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[12px] text-body">
            {s.rating && <span className="flex items-center gap-0.5"><Icon name="star" fill className="!text-[14px] text-amber-400" />{s.rating}{s.reviews ? ` (${s.reviews})` : ""}</span>}
            <span>{s.price}</span>
            <span className="ml-auto flex items-center gap-1">
              <button onClick={(e) => { e.stopPropagation(); onToggle(); }} className="rounded-md bg-sky px-2 py-1 text-[11px] font-semibold">{expanded ? "Less" : "Details"}</button>
              <button onClick={(e) => { e.stopPropagation(); onRemove(); }} className="rounded-md p-1 text-muted hover:bg-coral-wash hover:text-coral" aria-label={`Remove ${s.name}`}><Icon name="delete" className="!text-[16px]" /></button>
            </span>
          </div>
        </div>
      </motion.article>
      {leg && (
        <p className={`mt-3 flex items-center gap-2 text-[12px] ${leg.mode === "transit" ? "rounded-xl bg-coral-wash/60 px-3 py-2 text-coral-deep" : "pl-1 text-muted"}`}>
          <Icon name={legIcon[leg.mode]} className="!text-[16px]" />{leg.text}
        </p>
      )}
    </Reorder.Item>
  );
}

function Picks({ onAdd }: { onAdd: (day: number, s: Stop) => void }) {
  const row = useRef<HTMLDivElement>(null);
  const [added, setAdded] = useState<string[]>([]);
  const scroll = (dir: number) => row.current?.scrollBy({ left: dir * 300, behavior: "smooth" });
  return (
    <section className="min-w-0 lg:col-span-2">
      <div className="flex items-end justify-between">
        <div>
          <p className="label flex items-center gap-1 text-coral"><Icon name="auto_awesome" className="!text-[14px]" />Intelligent recommendations</p>
          <h2 className="mt-1 text-xl font-bold">TripBook AI curated picks for {trip.city.name}</h2>
        </div>
        <div className="flex gap-2">
          <motion.button whileTap={{ scale: 0.9 }} onClick={() => scroll(-1)} className="grid h-9 w-9 place-items-center rounded-full border border-line bg-white hover:bg-canvas" aria-label="Previous"><Icon name="chevron_left" /></motion.button>
          <motion.button whileTap={{ scale: 0.9 }} onClick={() => scroll(1)} className="grid h-9 w-9 place-items-center rounded-full border border-line bg-white hover:bg-canvas" aria-label="Next"><Icon name="chevron_right" /></motion.button>
        </div>
      </div>
      <div ref={row} className="no-scrollbar mt-4 flex snap-x gap-4 overflow-x-auto pb-4">
        {[...picks, ...picks.map((p) => ({ ...p, name: p.name + " ", tag: "More like this" }))].map((p, i) => {
          const done = added.includes(p.name);
          return (
            <motion.article key={p.name + i} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: (i % 4) * 0.08 }}
              whileHover={{ y: -6 }} className="card w-64 shrink-0 snap-start overflow-hidden">
              <div className="group relative h-40 overflow-hidden">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={p.img} alt="" className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-110" />
                <span className="absolute left-2 top-2 rounded-md bg-coral px-2 py-0.5 text-[10px] font-bold text-white">{p.tag}</span>
              </div>
              <div className="p-4">
                <div className="flex justify-between text-[11px] text-muted"><span>{p.kind}</span><span className="flex items-center gap-0.5 text-amber-500"><Icon name="star" fill className="!text-[13px]" />{p.rating}</span></div>
                <p className="mt-1 font-semibold leading-snug">{p.name}</p>
                <div className="mt-3 flex items-center justify-between">
                  <span className="text-xs text-body">{p.price}</span>
                  <motion.button whileTap={{ scale: 0.9 }} disabled={done}
                    onClick={() => { setAdded((a) => [...a, p.name]); onAdd(p.day, { id: "pick" + i, time: "04:00 PM", category: p.kind, name: p.name.trim(), desc: "Added from AI picks.", img: p.img, price: p.price, cost: 500, rating: p.rating, lat: trip.city.lat + (i % 3) * 0.01, lon: trip.city.lon - (i % 2) * 0.012 }); }}
                    className={`flex items-center gap-1 rounded-lg px-2 py-1 text-[11px] font-semibold transition ${done ? "bg-mint-wash text-mint" : "border border-line text-coral hover:bg-coral-wash"}`}>
                    <Icon name={done ? "check" : "add"} className="!text-[14px]" />{done ? "Added" : `Add to Day ${p.day}`}
                  </motion.button>
                </div>
              </div>
            </motion.article>
          );
        })}
      </div>
    </section>
  );
}
