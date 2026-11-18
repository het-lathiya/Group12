"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Icon } from "@/components/ui";

const steps = [
  ["travel_explore", "Reading your preferences"],
  ["place", "Finding places that match"],
  ["route", "Routing days to cut travel time"],
  ["payments", "Checking your budget"],
  ["verified", "Validating opening hours"],
];

export default function Generate() {
  const { tripId } = useParams<{ tripId: string }>();
  const router = useRouter();
  const [done, setDone] = useState(0);

  // TODO: POST /api/v1/trips/{id}/generations then poll GET /generations/{generation_id}
  useEffect(() => {
    if (done >= steps.length) { const t = setTimeout(() => router.push(`/trips/${tripId}/itinerary`), 700); return () => clearTimeout(t); }
    const t = setTimeout(() => setDone((d) => d + 1), 800);
    return () => clearTimeout(t);
  }, [done, router, tripId]);

  return (
    <div className="mx-auto max-w-xl py-10">
      <div className="card p-8 text-center">
        <span className="mx-auto grid h-16 w-16 animate-pulse place-items-center rounded-2xl bg-coral-wash text-coral"><Icon name="auto_awesome" className="!text-[32px]" /></span>
        <h2 className="mt-5 text-2xl font-bold">Building your itinerary</h2>
        <p className="mt-1 text-sm text-body">This usually takes under a minute.</p>
        <div className="mt-6 h-2 overflow-hidden rounded-full bg-sky">
          <div className="h-full rounded-full bg-coral transition-all duration-700" style={{ width: `${(done / steps.length) * 100}%` }} />
        </div>
        <ul className="mt-6 space-y-3 text-left">
          {steps.map(([i, l], k) => (
            <li key={l} className={`flex items-center gap-3 rounded-xl p-3 ${k < done ? "bg-mint-wash" : k === done ? "bg-coral-wash" : "bg-canvas"}`}>
              <Icon name={k < done ? "check_circle" : i} fill={k < done} className={k < done ? "text-mint" : k === done ? "text-coral" : "text-muted"} />
              <span className={`text-sm font-semibold ${k > done ? "text-muted" : ""}`}>{l}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
