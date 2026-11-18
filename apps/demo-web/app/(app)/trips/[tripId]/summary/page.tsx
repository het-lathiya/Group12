"use client";

import { motion } from "motion/react";
import { useRouter } from "next/navigation";
import { CountUp, Reveal, useToast } from "@/components/fx";
import { useTrip } from "@/components/shell";
import { Empty, ErrorBox, LoadingCards } from "@/components/states";
import { Icon } from "@/components/ui";
import { api, ApiError, destinationPhoto, fmtDate, fmtTime, money } from "@/lib/api";
import { useLoad } from "@/lib/session";

export default function Summary() {
  const { tripId } = useTrip();
  const router = useRouter();
  const toast = useToast();
  const s = useLoad(() => api.summary(tripId), [tripId]);
  if (s.error) return (s.error as ApiError).code === "NOT_FOUND" ? <Empty icon="summarize" title="Nothing to summarise yet" text="Generate an itinerary first." /> : <ErrorBox error={s.error} onRetry={s.reload} />;
  if (!s.data) return <LoadingCards n={3} h="h-56" />;
  const { trip, days, costs, unresolved_findings } = s.data;
  const stops = days.reduce((n, d) => n + d.items.length, 0);
  const km = days.flatMap((d) => d.items).reduce((t, x) => t + (x.travel_from_previous?.distance_m ?? 0), 0) / 1000;

  const share = async () => {
    const text = `${trip.title}\n${days.map((d) => `Day ${d.day_number}: ${d.items.map((x) => x.place.name).join(" → ")}`).join("\n")}`;
    try { await navigator.clipboard.writeText(text); toast({ text: "Plan copied to clipboard", icon: "content_copy" }); } catch { toast({ text: "Couldn't copy", icon: "error" }); }
  };
  const duplicate = async () => {
    try { const t = await api.duplicate(tripId); toast({ text: "Trip duplicated", icon: "content_copy" }); router.push(`/trips/${t.id}/itinerary/`); }
    catch (e) { toast({ text: (e as Error).message, icon: "error" }); }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <motion.div initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} className="relative h-56 overflow-hidden rounded-2xl md:h-72">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={destinationPhoto(trip.destination.name)} alt="" className="h-full w-full object-cover" />
        <div className="absolute inset-0 bg-gradient-to-t from-slate/80 to-transparent" />
        <div className="absolute bottom-5 left-6 right-6 text-white">
          <span className={unresolved_findings.length ? "rounded-full bg-amber-400 px-2 py-0.5 text-[11px] font-bold text-slate" : "badge-mint"}>{unresolved_findings.length ? `${unresolved_findings.length} things to check` : "Ready to go"}</span>
          <h2 className="mt-2 text-2xl font-extrabold md:text-3xl">{trip.title}</h2>
          <p className="text-sm opacity-90">{trip.destination.name} • {fmtDate(trip.start_date, { month: "short", day: "numeric" })} – {fmtDate(trip.end_date, { month: "short", day: "numeric", year: "numeric" })} • {trip.adults + trip.children} travellers</p>
        </div>
      </motion.div>

      <div className="grid gap-4 sm:grid-cols-4">
        {[["calendar_month", "Days", <CountUp key="d" to={days.length} />], ["place", "Stops", <CountUp key="s" to={stops} />], ["payments", "Planning total", money(costs.planning_total, costs.currency)], ["route", "Travel", `${km.toFixed(1)} km`]].map(([i, l, v], k) => (
          <Reveal key={l as string} delay={k * 0.06}><div className="card p-4"><Icon name={i as string} className="text-coral" /><p className="mt-2 text-xl font-extrabold">{v}</p><p className="text-xs text-muted">{l}</p></div></Reveal>
        ))}
      </div>

      <section className="card p-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="font-semibold">At a glance</h3>
          <div className="flex flex-wrap gap-2">
            <button onClick={duplicate} className="btn-soft !text-xs"><Icon name="content_copy" className="!text-[15px]" />Duplicate trip</button>
            <button onClick={() => window.print()} className="btn-soft !text-xs"><Icon name="print" className="!text-[15px]" />Print</button>
            <button onClick={share} className="btn-primary !text-xs"><Icon name="ios_share" className="!text-[15px]" />Copy plan</button>
          </div>
        </div>
        <div className="mt-5 space-y-6">
          {days.map((d, i) => (
            <Reveal key={d.day_number} delay={i * 0.05}>
              <div className="flex gap-4">
                <span className="h-fit rounded-lg bg-slate px-2.5 py-1 text-xs font-bold text-white">Day {d.day_number}</span>
                <div className="flex-1">
                  <p className="font-semibold">{d.theme ?? fmtDate(d.date)}</p>
                  <p className="text-xs text-muted">{fmtDate(d.date)} • {money(d.day_cost.max, d.day_cost.currency)} max</p>
                  <ol className="mt-2 space-y-1">
                    {d.items.map((x) => <li key={x.id} className="flex gap-3 text-sm text-body"><span className="w-16 shrink-0 text-xs font-semibold text-coral">{fmtTime(x.start_time)}</span>{x.place.name}</li>)}
                  </ol>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {unresolved_findings.length > 0 && (
        <section className="card p-6">
          <h3 className="font-semibold">Before you go</h3>
          <ul className="mt-3 space-y-2 text-sm text-body">
            {unresolved_findings.map((f) => <li key={f.id} className="flex items-start gap-2"><Icon name={f.severity === "error" ? "error" : "warning"} className={f.severity === "error" ? "text-coral" : "text-amber-500"} />{f.day_number ? <b>Day {f.day_number}:</b> : null} {f.message}</li>)}
          </ul>
        </section>
      )}
    </div>
  );
}
