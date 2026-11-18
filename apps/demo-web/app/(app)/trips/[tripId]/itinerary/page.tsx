"use client";

import Link from "next/link";
import { AnimatePresence, motion, Reorder, useDragControls } from "motion/react";
import { useMemo, useRef, useState } from "react";
import { useToast } from "@/components/fx";
import { TripMap } from "@/components/map";
import { useTrip } from "@/components/shell";
import { Empty, ErrorBox, LoadingCards } from "@/components/states";
import { Icon } from "@/components/ui";
import { api, ApiError, categoryIcon, fmtDate, fmtTime, legIcon, money, placePhoto, range, type Day, type EditResult, type Finding, type Item, type Itinerary as It, type Place } from "@/lib/api";
import { useLoad } from "@/lib/session";

const dayColor = ["#ff5a36", "#0f172a", "#059669", "#6366f1", "#f59e0b", "#0ea5e9", "#db2777"];
const sevCls = { error: "bg-coral-wash text-coral-deep", warning: "bg-amber-50 text-amber-700", info: "bg-sky text-body" };
const sevIcon = { error: "error", warning: "warning", info: "info" };

export default function ItineraryPage() {
  const { tripId, trip, reloadTrip } = useTrip();
  const toast = useToast();
  const it = useLoad(() => api.itinerary(tripId), [tripId]);
  const places = useLoad(trip ? () => api.places({ destination_id: trip.destination_id, limit: 40 }) : null, [trip?.destination_id]);
  const [filter, setFilter] = useState(0);
  const [sel, setSel] = useState<string>("");
  const [collapsed, setCollapsed] = useState<number[]>([]);
  const [open, setOpen] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [regen, setRegen] = useState<number | null>(null);

  const data = it.data;
  const days = data?.days ?? [];
  const all = days.flatMap((d) => d.items.map((x) => ({ ...x, day: d.day_number })));
  const selected = all.find((s) => s.id === sel) ?? all[0];
  const pins = useMemo(() => all.filter((s) => filter === 0 || s.day === filter).map((s) => ({ id: s.id, lat: s.place.lat, lon: s.place.lon, color: dayColor[(s.day - 1) % dayColor.length] })), [data, filter]); // eslint-disable-line react-hooks/exhaustive-deps
  const inPlan = new Set(all.map((x) => x.place.id));
  const picks = (places.data?.items ?? []).filter((p) => !inPlan.has(p.id) && p.category !== "stay").slice(0, 12);

  const apply = (r: EditResult) => it.setData((d) => d && ({
    ...d, plan_revision: r.plan_revision, totals: r.totals, findings: r.findings,
    days: d.days.map((day) => r.changed_days.find((c) => c.day_number === day.day_number) ?? day),
  }));
  const fail = (e: unknown) => {
    const a = e as ApiError;
    toast({ text: a.code === "STALE_PLAN" ? "This plan changed elsewhere. Reloaded the latest." : a.message, icon: "error" });
    if (a.code === "STALE_PLAN") it.reload();
  };

  const reorder = async (dayN: number, next: Item[]) => {
    if (!data) return;
    const before = days.find((d) => d.day_number === dayN)!.items;
    const moved = next.find((x, i) => before[i]?.id !== x.id && before.findIndex((b) => b.id === x.id) !== i);
    it.setData((d) => d && { ...d, days: d.days.map((day) => (day.day_number === dayN ? { ...day, items: next } : day)) });
    if (!moved) return;
    try { apply(await api.moveItem(moved.id, { plan_revision: data.plan_revision, position: next.indexOf(moved) + 1, day_number: dayN })); toast({ text: `Moved ${moved.place.name}. Times updated.`, icon: "swap_vert" }); }
    catch (e) { fail(e); it.reload(); }
  };
  const remove = async (dayN: number, x: Item) => {
    if (!data) return;
    setBusy(true);
    try {
      const r = await api.deleteItem(x.id, data.plan_revision);
      apply(r);
      toast({ text: `Removed ${x.place.name}`, icon: "delete", undo: async () => {
        try { apply(await api.addItem(tripId, { day_number: dayN, place_id: x.place.id, plan_revision: r.plan_revision })); } catch (e) { fail(e); }
      } });
    } catch (e) { fail(e); } finally { setBusy(false); }
  };
  const add = async (dayN: number, p: Place) => {
    if (!data) return;
    setBusy(true);
    try { apply(await api.addItem(tripId, { day_number: dayN, place_id: p.id, plan_revision: data.plan_revision })); toast({ text: `Added ${p.name} to Day ${dayN}`, icon: "add_location_alt" }); }
    catch (e) { fail(e); } finally { setBusy(false); }
  };
  const regenerateDay = async (dayN: number) => {
    if (!data) return;
    setRegen(dayN);
    try {
      let g = await api.regenerateDay(tripId, dayN, data.plan_revision);
      while (g.status !== "completed" && g.status !== "failed") { await new Promise((r) => setTimeout(r, 1500)); g = await api.generation(g.id); }
      if (g.status === "failed") toast({ text: g.failure_message ?? "Couldn't regenerate that day.", icon: "error" });
      else toast({ text: `Day ${dayN} regenerated`, icon: "auto_awesome" });
      it.reload(); reloadTrip();
    } catch (e) { fail(e); } finally { setRegen(null); }
  };

  if (it.error) {
    if ((it.error as ApiError).code === "NOT_FOUND") return <Empty icon="auto_awesome" title="No itinerary yet" text="Let the AI build a day-by-day plan for this trip." action={<Link href={`/trips/${tripId}/generate/`} className="btn-primary"><Icon name="auto_awesome" />Generate itinerary</Link>} />;
    return <ErrorBox error={it.error} onRetry={it.reload} />;
  }
  if (it.loading && !data) return <LoadingCards n={4} />;
  if (data && days.every((d) => d.items.length === 0) && !trip?.has_itinerary) {
    return <Empty icon="auto_awesome" title="No itinerary yet" text="Let the AI build a day-by-day plan for this trip." action={<Link href={`/trips/${tripId}/generate/`} className="btn-primary"><Icon name="auto_awesome" />Generate itinerary</Link>} />;
  }
  if (!data) return null;
  const cur = data.totals.currency;

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
      <div className="min-w-0 space-y-8">
        {/* totals strip */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="card flex flex-wrap items-center gap-x-6 gap-y-3 p-4 text-sm">
          <div className="flex items-center gap-2"><Icon name="place" className="text-coral" /><b>{all.length}</b> stops</div>
          <div className="flex items-center gap-2"><Icon name="payments" className="text-coral" /><b>{range(data.totals.estimate.min, data.totals.estimate.max, cur)}</b> est.</div>
          <div className="flex items-center gap-2"><Icon name="route" className="text-coral" /><b>{(all.reduce((s, x) => s + (x.travel_from_previous?.distance_m ?? 0), 0) / 1000).toFixed(1)} km</b> travel</div>
          {data.source && <span className={data.source.outcome === "fallback_rule_based" ? "chip" : "badge-mint"}><Icon name={data.source.outcome === "fallback_rule_based" ? "rule" : "auto_awesome"} className="!text-[13px]" />{data.source.outcome === "fallback_rule_based" ? "Rule-based plan" : `AI plan • ${data.source.provider}`}</span>}
          <div className="ml-auto flex items-center gap-2 text-xs text-muted">{busy ? <><span className="h-3 w-3 animate-spin rounded-full border-2 border-coral/30 border-t-coral" />Saving…</> : <><Icon name="drag_indicator" className="!text-[16px]" />Drag cards to reorder</>}</div>
        </motion.div>

        {days.map((day, d) => {
          const isCol = collapsed.includes(day.day_number);
          const color = d === 0 ? "#b52603" : dayColor[d % dayColor.length];
          return (
            <section key={day.day_number}>
              <div className="flex items-start gap-3">
                <button onClick={() => setCollapsed((c) => isCol ? c.filter((x) => x !== day.day_number) : [...c, day.day_number])} className="flex flex-1 items-start gap-3 text-left">
                  <span className="rounded-lg px-2.5 py-1 text-xs font-bold text-white" style={{ background: color }}>Day {day.day_number}</span>
                  <div className="flex-1">
                    <h2 className="text-lg font-bold leading-tight md:text-xl">{day.theme ?? `Day ${day.day_number} in ${trip?.destination.name ?? ""}`}</h2>
                    <p className="text-xs text-muted">{fmtDate(day.date)} • {range(day.day_cost.min, day.day_cost.max, day.day_cost.currency)}{day.day_cost.complete ? "" : " (some prices unknown)"}</p>
                  </div>
                </button>
                <span className="rounded-full bg-sky px-2.5 py-1 text-[11px] font-semibold text-body">{day.items.length} stops</span>
                <motion.button whileTap={{ scale: 0.9 }} disabled={regen !== null} onClick={() => regenerateDay(day.day_number)} title="Regenerate this day with AI"
                  className="grid h-7 w-7 place-items-center rounded-full text-muted hover:bg-coral-wash hover:text-coral disabled:opacity-40" aria-label={`Regenerate day ${day.day_number}`}>
                  {regen === day.day_number ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-coral/30 border-t-coral" /> : <Icon name="autorenew" />}
                </motion.button>
                <motion.span animate={{ rotate: isCol ? -90 : 0 }} className="text-muted"><Icon name="expand_more" /></motion.span>
              </div>

              <AnimatePresence initial={false}>
                {!isCol && (
                  <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.3 }} className="overflow-hidden">
                    <Reorder.Group axis="y" values={day.items} onReorder={(v) => reorder(day.day_number, v)} className={`relative mt-4 space-y-3 border-l-2 border-dashed border-line pl-6 md:ml-2 ${regen === day.day_number ? "pointer-events-none opacity-50" : ""}`}>
                      {day.items.map((x, i) => (
                        <StopCard key={x.id} x={x} i={i} color={dayColor[d % dayColor.length]} cur={cur} active={selected?.id === x.id} expanded={open === x.id}
                          findings={data.findings.filter((f) => f.item_id === x.id)}
                          onSelect={() => setSel(x.id)} onToggle={() => setOpen(open === x.id ? null : x.id)} onRemove={() => remove(day.day_number, x)} />
                      ))}
                    </Reorder.Group>
                    {day.items.length === 0 && <p className="mt-4 rounded-xl border-2 border-dashed border-line p-6 text-center text-sm text-muted">Nothing planned. Add a place from the picks below.</p>}
                  </motion.div>
                )}
              </AnimatePresence>
            </section>
          );
        })}
      </div>

      {/* RIGHT */}
      <aside className="min-w-0 space-y-5 lg:sticky lg:top-20 lg:self-start">
        <div className="card overflow-hidden p-3">
          <div className="flex flex-wrap gap-1.5">
            {["All Days", ...days.map((d) => `Day ${d.day_number}`)].map((l, i) => (
              <button key={l} onClick={() => setFilter(i)} className={`relative rounded-full px-3 py-1 text-xs font-semibold ${filter === i ? "text-white" : "text-body hover:bg-canvas"}`}>
                {filter === i && <motion.span layoutId="mapfilter" className="absolute inset-0 rounded-full bg-slate" transition={{ type: "spring", stiffness: 400, damping: 30 }} />}
                <span className="relative">{l}</span>
              </button>
            ))}
          </div>
          <div className="relative mt-3 h-72 overflow-hidden rounded-xl md:h-80">
            <TripMap pins={pins} selected={selected?.id} onSelect={(id) => { setSel(id); document.getElementById("stop-" + id)?.scrollIntoView({ behavior: "smooth", block: "center" }); }} />
            {selected && (
              <AnimatePresence mode="wait">
                <motion.div key={selected.id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 10 }} className="glass absolute bottom-3 left-3 right-14 flex items-center gap-3 rounded-xl p-2 shadow-lg">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={placePhoto(selected.place.category, selected.place.id)} alt="" className="h-12 w-12 rounded-lg object-cover" />
                  <div className="min-w-0 flex-1">
                    <p className="text-[10px] font-bold capitalize text-mint">● Day {selected.day} • {selected.place.category}</p>
                    <p className="truncate text-sm font-bold">{selected.place.name}</p>
                    <p className="truncate text-[11px] text-muted">{fmtTime(selected.start_time)} – {fmtTime(selected.end_time)}</p>
                  </div>
                  <button onClick={() => document.getElementById("stop-" + selected.id)?.scrollIntoView({ behavior: "smooth", block: "center" })} className="rounded-lg bg-coral-deep px-3 py-1.5 text-xs font-bold text-white">Focus</button>
                </motion.div>
              </AnimatePresence>
            )}
          </div>
        </div>

        <PlanChecks data={data} onRegenerate={regenerateDay} busyDay={regen} onJump={(id) => { if (id) { setSel(id); document.getElementById("stop-" + id)?.scrollIntoView({ behavior: "smooth", block: "center" }); } }} />
      </aside>

      {/* PICKS from the curated places API */}
      <Picks picks={picks} loading={places.loading} days={days} onAdd={add} cityName={trip?.destination.name ?? ""} />
    </div>
  );
}

function StopCard({ x, i, color, cur, active, expanded, findings, onSelect, onToggle, onRemove }: {
  x: Item; i: number; color: string; cur: string; active: boolean; expanded: boolean; findings: Finding[];
  onSelect: () => void; onToggle: () => void; onRemove: () => void;
}) {
  const controls = useDragControls();
  const leg = x.travel_from_previous;
  return (
    <Reorder.Item value={x} id={"stop-" + x.id} dragListener={false} dragControls={controls}
      initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, x: -40 }}
      whileDrag={{ scale: 1.02, boxShadow: "0 24px 40px -8px rgba(15,23,42,0.25)", zIndex: 30 }} className="relative list-none">
      {leg && i > 0 && (
        <p className={`mb-3 flex items-center gap-2 text-[12px] ${leg.mode === "local_transport" ? "rounded-xl bg-coral-wash/60 px-3 py-2 text-coral-deep" : "pl-1 text-muted"}`}>
          <Icon name={legIcon[leg.mode]} className="!text-[16px]" />{leg.minutes} min {leg.mode.replace("_", " ")} ({(leg.distance_m / 1000).toFixed(1)} km){leg.source === "fallback_estimate" ? " • estimate" : ""}
        </p>
      )}
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
          <img src={placePhoto(x.place.category, x.place.id)} alt="" className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-110" />
          <span className="absolute bottom-2 left-2 grid h-6 w-6 place-items-center rounded-full text-[11px] font-bold text-white" style={{ background: color }}>{i + 1}</span>
          {x.must_visit && <span className="absolute left-2 top-2 rounded-md bg-slate/80 px-1.5 py-0.5 text-[10px] font-bold text-white backdrop-blur">★ Must visit</span>}
          {x.is_locked && <span className="glass absolute right-2 top-2 grid h-7 w-7 place-items-center rounded-full"><Icon name="lock" className="!text-[14px]" /></span>}
        </div>
        <div className="min-w-0 flex-1 sm:pr-6">
          <div className="flex items-start justify-between gap-2">
            <p className="label text-coral">{fmtTime(x.start_time)} • {x.slot_type === "meal" ? "Meal" : x.place.category}</p>
            {x.place.hours_label === "curated" ? <span className="badge-mint">Hours checked</span> : x.place.hours_label === "unavailable" ? <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-bold text-amber-700">Hours unknown</span> : null}
          </div>
          <h3 className="mt-1 font-semibold">{x.place.name}</h3>
          {x.note && <p className={`mt-1 text-[13px] leading-5 text-body ${expanded ? "" : "line-clamp-2"}`}>{x.note_origin === "ai" && <Icon name="auto_awesome" className="!text-[13px] text-coral" />} {x.note}</p>}
          {findings.map((f) => (
            <p key={f.id} className={`mt-2 flex gap-1.5 rounded-lg p-2 text-[12px] leading-4 ${sevCls[f.severity]}`}><Icon name={sevIcon[f.severity]} className="!text-[14px]" />{f.message}</p>
          ))}
          <AnimatePresence>
            {expanded && (
              <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                <div className="mt-3 grid grid-cols-3 gap-2 text-center text-[11px]">
                  <div className="rounded-lg bg-canvas p-2"><Icon name="schedule" className="text-coral" /><p className="mt-1 font-semibold">{x.duration_min} min</p></div>
                  <div className="rounded-lg bg-canvas p-2"><Icon name={categoryIcon[x.place.category] ?? "place"} className="text-coral" /><p className="mt-1 font-semibold capitalize">{x.place.category}</p></div>
                  <div className="rounded-lg bg-canvas p-2"><Icon name="sell" className="text-coral" /><p className="mt-1 font-semibold capitalize">{x.cost?.label ?? "no price"}</p></div>
                </div>
                {x.sources.length > 0 && (
                  <div className="mt-3 rounded-lg bg-canvas p-2 text-[11px] text-muted">
                    <p className="font-bold text-slate">Sources</p>
                    {x.sources.slice(0, 3).map((s, k) => <p key={k} className="truncate">• {s.url ? <a href={s.url} target="_blank" rel="noreferrer" className="underline">{s.title}</a> : s.title} ({s.source_name})</p>)}
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[12px] text-body">
            <span>{fmtTime(x.start_time)} – {fmtTime(x.end_time)}</span>
            <span>{x.cost ? range(x.cost.min, x.cost.max, x.cost.currency || cur) : "Price unknown"}{x.cost?.label === "estimate" ? " (est.)" : ""}</span>
            <span className="ml-auto flex items-center gap-1">
              <button onClick={(e) => { e.stopPropagation(); onToggle(); }} className="rounded-md bg-sky px-2 py-1 text-[11px] font-semibold">{expanded ? "Less" : "Details"}</button>
              <button onClick={(e) => { e.stopPropagation(); onRemove(); }} disabled={x.is_locked} className="rounded-md p-1 text-muted hover:bg-coral-wash hover:text-coral disabled:opacity-30" aria-label={`Remove ${x.place.name}`}><Icon name="delete" className="!text-[16px]" /></button>
            </span>
          </div>
        </div>
      </motion.article>
    </Reorder.Item>
  );
}

function PlanChecks({ data, onRegenerate, busyDay, onJump }: { data: It; onRegenerate: (d: number) => void; busyDay: number | null; onJump: (itemId: string | null) => void }) {
  const counts = { error: 0, warning: 0, info: 0 };
  data.findings.forEach((f) => counts[f.severity]++);
  const ok = counts.error === 0 && counts.warning === 0;
  return (
    <div className="card p-4">
      <div className="flex items-center gap-3">
        <span className={`relative grid h-9 w-9 place-items-center rounded-xl ${ok ? "bg-mint-wash text-mint" : "bg-coral-wash text-coral"}`}><Icon name={ok ? "verified" : "fact_check"} />
          <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full border-2 border-white bg-mint" /></span>
        <div className="flex-1"><p className="font-semibold">Plan checks</p><p className="text-[11px] text-muted">Validated by the server on every change</p></div>
        <span className="rounded-full bg-sky px-2 py-1 text-[10px] font-semibold text-body">Rev {data.plan_revision}</span>
      </div>
      <div className="mt-4 grid grid-cols-3 gap-2 text-center">
        {(["error", "warning", "info"] as const).map((s) => (
          <div key={s} className={`rounded-xl p-2 ${sevCls[s]}`}><p className="text-lg font-extrabold">{counts[s]}</p><p className="text-[10px] font-bold uppercase">{s}s</p></div>
        ))}
      </div>
      <div className="mt-3 max-h-72 space-y-2 overflow-y-auto pr-1">
        <AnimatePresence initial={false}>
          {data.findings.length === 0 && <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="rounded-xl bg-mint-wash p-3 text-[13px] text-mint">Everything checks out. No problems found.</motion.p>}
          {data.findings.map((f) => (
            <motion.button key={f.id} layout initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }} onClick={() => onJump(f.item_id)}
              className={`flex w-full gap-2 rounded-xl p-2.5 text-left text-[12px] leading-4 ${sevCls[f.severity]}`}>
              <Icon name={sevIcon[f.severity]} className="!text-[15px]" />
              <span className="flex-1">{f.day_number ? <b>Day {f.day_number}: </b> : null}{f.message}{f.suggested_fix && <span className="mt-1 block opacity-80">Fix: {f.suggested_fix}</span>}</span>
            </motion.button>
          ))}
        </AnimatePresence>
      </div>
      <div className="mt-4 border-t border-hair pt-3">
        <p className="label mb-2 text-muted">AI tools</p>
        <div className="flex flex-wrap gap-2">
          {data.days.map((d) => (
            <motion.button whileTap={{ scale: 0.95 }} key={d.day_number} disabled={busyDay !== null} onClick={() => onRegenerate(d.day_number)} className="chip hover:border-coral disabled:opacity-50">
              {busyDay === d.day_number ? <span className="h-3 w-3 animate-spin rounded-full border-2 border-coral/30 border-t-coral" /> : <Icon name="autorenew" className="!text-[14px] text-coral" />}Redo Day {d.day_number}
            </motion.button>
          ))}
        </div>
      </div>
    </div>
  );
}

function Picks({ picks, loading, days, onAdd, cityName }: { picks: Place[]; loading: boolean; days: Day[]; onAdd: (day: number, p: Place) => void; cityName: string }) {
  const row = useRef<HTMLDivElement>(null);
  const [target, setTarget] = useState(1);
  const scroll = (dir: number) => row.current?.scrollBy({ left: dir * 300, behavior: "smooth" });
  if (!loading && picks.length === 0) return null;
  return (
    <section className="min-w-0 lg:col-span-2">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="label flex items-center gap-1 text-coral"><Icon name="auto_awesome" className="!text-[14px]" />Curated places not in your plan</p>
          <h2 className="mt-1 text-xl font-bold">More to see in {cityName}</h2>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted">Add to</span>
          <select value={target} onChange={(e) => setTarget(+e.target.value)} className="input !h-9 !w-28 !text-xs">{days.map((d) => <option key={d.day_number} value={d.day_number}>Day {d.day_number}</option>)}</select>
          <motion.button whileTap={{ scale: 0.9 }} onClick={() => scroll(-1)} className="grid h-9 w-9 place-items-center rounded-full border border-line bg-white hover:bg-canvas" aria-label="Previous"><Icon name="chevron_left" /></motion.button>
          <motion.button whileTap={{ scale: 0.9 }} onClick={() => scroll(1)} className="grid h-9 w-9 place-items-center rounded-full border border-line bg-white hover:bg-canvas" aria-label="Next"><Icon name="chevron_right" /></motion.button>
        </div>
      </div>
      <div ref={row} className="no-scrollbar mt-4 flex snap-x gap-4 overflow-x-auto pb-4">
        {loading && [0, 1, 2, 3].map((i) => <div key={i} className="h-64 w-64 shrink-0 animate-pulse rounded-2xl bg-line/60" />)}
        {picks.map((p, i) => (
          <motion.article key={p.id} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: (i % 4) * 0.08 }}
            whileHover={{ y: -6 }} className="card w-64 shrink-0 snap-start overflow-hidden">
            <div className="group relative h-36 overflow-hidden">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={placePhoto(p.category, p.id)} alt="" className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-110" />
              <span className="absolute left-2 top-2 rounded-md bg-coral px-2 py-0.5 text-[10px] font-bold capitalize text-white">{p.category}</span>
              {p.verification_status === "curated_checked" && <span className="absolute right-2 top-2 badge-mint !bg-white">✓ Curated</span>}
            </div>
            <div className="p-4">
              <p className="font-semibold leading-snug">{p.name}</p>
              <p className="mt-1 line-clamp-1 text-[11px] text-muted">{p.tags.slice(0, 3).join(" • ") || " "}</p>
              <div className="mt-3 flex items-center justify-between">
                <span className="text-xs text-body">{p.price ? (p.price.max && p.price.max !== p.price.min ? range(p.price.min, p.price.max, p.price.currency) : money(p.price.min, p.price.currency)) : "Free / unknown"} • {p.typical_duration_min}m</span>
                <motion.button whileTap={{ scale: 0.9 }} onClick={() => onAdd(target, p)} className="flex items-center gap-1 rounded-lg border border-line px-2 py-1 text-[11px] font-semibold text-coral hover:bg-coral-wash">
                  <Icon name="add" className="!text-[14px]" />Day {target}
                </motion.button>
              </div>
            </div>
          </motion.article>
        ))}
      </div>
    </section>
  );
}
