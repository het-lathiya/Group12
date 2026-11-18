import { Icon } from "@/components/ui";
import { inr, costs, days, trip } from "@/lib/data";

// TODO: GET /api/v1/trips/{id}/summary
export default function Summary() {
  const spent = costs.categories.reduce((s, c) => s + c.amount, 0);
  const stops = days.flatMap((d) => d.stops).length;
  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="relative h-56 overflow-hidden rounded-2xl md:h-72">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={trip.cover} alt="" className="h-full w-full object-cover" />
        <div className="absolute inset-0 bg-gradient-to-t from-slate/80 to-transparent" />
        <div className="absolute bottom-5 left-6 right-6 text-white">
          <span className="badge-mint">Ready to go</span>
          <h2 className="mt-2 text-2xl font-extrabold md:text-3xl">{trip.name}</h2>
          <p className="text-sm opacity-90">{trip.dates} • {trip.travelers} travelers</p>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-4">
        {[["calendar_month", "Days", days.length], ["place", "Stops", stops], ["payments", "Est. cost", inr(spent)], ["directions_walk", "Avg walk / day", "4.8 km"]].map(([i, l, v]) => (
          <div key={l as string} className="card p-4"><Icon name={i as string} className="text-coral" /><p className="mt-2 text-xl font-extrabold">{v}</p><p className="text-xs text-muted">{l}</p></div>
        ))}
      </div>

      <section className="card p-6">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold">At a glance</h3>
          <div className="flex gap-2">
            <button className="btn-soft !text-xs"><Icon name="content_copy" className="!text-[15px]" />Duplicate trip</button>
            <button className="btn-soft !text-xs"><Icon name="print" className="!text-[15px]" />Print</button>
            <button className="btn-primary !text-xs"><Icon name="ios_share" className="!text-[15px]" />Share</button>
          </div>
        </div>
        <div className="mt-5 space-y-5">
          {days.map((d) => (
            <div key={d.n} className="flex gap-4">
              <span className="h-fit rounded-lg bg-slate px-2.5 py-1 text-xs font-bold text-white">Day {d.n}</span>
              <div className="flex-1">
                <p className="font-semibold">{d.title}</p>
                <p className="text-xs text-muted">{d.date}</p>
                <p className="mt-1 text-sm text-body">{d.stops.map((s) => s.name).join(" → ")}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="card p-6">
        <h3 className="font-semibold">Before you go</h3>
        <ul className="mt-3 space-y-2 text-sm text-body">
          {["Reserve Suvarna Mahal dinner (Day 1)", "Carry ID for train boarding (Day 3)", "Pack layers: December evenings drop to 9°C", "Download offline map for Amer"].map((t) => (
            <li key={t} className="flex items-center gap-2"><Icon name="check_circle" className="text-mint" />{t}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}
