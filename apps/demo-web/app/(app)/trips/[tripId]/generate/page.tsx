"use client";

import { AnimatePresence, motion } from "motion/react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useTrip } from "@/components/shell";
import { FullPageSpinner } from "@/components/states";
import { Icon } from "@/components/ui";
import { api, ApiError, type Generation } from "@/lib/api";
import { useLoad } from "@/lib/session";

const steps: [Generation["status"][], string, string][] = [
  [["queued"], "hourglass_top", "Queued"],
  [["running"], "travel_explore", "Finding places & asking the AI"],
  [["validating"], "fact_check", "Validating hours, times & costs"],
  [["repairing"], "build", "Repairing any problems"],
  [["completed"], "check_circle", "Saved your itinerary"],
];
const order: Generation["status"][] = ["queued", "running", "validating", "repairing", "completed"];

export default function Generate() {
  const { tripId, trip, reloadTrip } = useTrip();
  const router = useRouter();
  const me = useLoad(() => api.me(), []);
  const [ack, setAck] = useState(false);
  const [gen, setGen] = useState<Generation | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const auto = useRef(false);
  const acked = !!me.data?.ai_notice_ack_at;

  const poll = useCallback(async (g: Generation) => {
    setGen(g);
    let cur = g;
    while (cur.status !== "completed" && cur.status !== "failed") {
      await new Promise((r) => setTimeout(r, 1500));
      cur = await api.generation(cur.id);
      setGen(cur);
    }
    if (cur.status === "completed") {
      reloadTrip();
      setTimeout(() => router.push(`/trips/${tripId}/itinerary/`), 900);
    }
  }, [reloadTrip, router, tripId]);

  const start = useCallback(async (mode: "ai" | "rule_based" = "ai") => {
    setErr(null); setStarting(true); setElapsed(0);
    try {
      if (mode === "ai" && !acked) await api.updateMe({ ai_notice_acknowledged: true });
      const g = await api.startGeneration(tripId, mode);
      setStarting(false);
      await poll(g);
    } catch (e) {
      setStarting(false);
      const a = e as ApiError;
      setErr(a.code === "GENERATION_IN_PROGRESS" ? "A generation is already running for this trip. Wait a moment and open the itinerary." : a.message);
    }
  }, [acked, poll, tripId]);

  // auto-start right after trip creation if the AI notice was accepted before
  useEffect(() => {
    if (auto.current || !me.data || !tripId) return;
    if (new URLSearchParams(window.location.search).get("start") === "1" && acked) { auto.current = true; start("ai"); }
  }, [me.data, acked, tripId, start]);

  const running = gen && gen.status !== "completed" && gen.status !== "failed";
  useEffect(() => {
    if (!running) return;
    const t = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, [running]);

  if (me.loading) return <FullPageSpinner />;
  const idx = gen ? order.indexOf(gen.status) : -1;

  return (
    <div className="mx-auto max-w-xl py-6">
      <motion.div layout className="card p-8">
        <AnimatePresence mode="wait">
          {!gen && !starting ? (
            <motion.div key="intro" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="text-center">
              <span className="mx-auto grid h-16 w-16 place-items-center rounded-2xl bg-coral-wash text-coral"><Icon name="auto_awesome" className="!text-[32px]" /></span>
              <h2 className="mt-5 text-2xl font-bold">{trip?.has_itinerary ? "Regenerate the whole plan?" : "Build your itinerary"}</h2>
              <p className="mt-2 text-sm text-body">{trip?.has_itinerary ? "This replaces the current plan with a new version. Older versions stay in Versions." : "The AI picks places from our curated list. The server then checks every time, travel gap and price."}</p>
              {!acked && (
                <label className="mt-5 flex items-start gap-3 rounded-xl bg-canvas p-4 text-left text-[13px] text-body">
                  <input type="checkbox" checked={ack} onChange={(e) => setAck(e.target.checked)} className="mt-0.5 accent-coral" />
                  <span><b className="text-slate">AI notice.</b> The plan is written by an AI (Gemini) from curated place data. Times, costs and opening hours are estimates; check them before you travel.</span>
                </label>
              )}
              {err && <p className="mt-4 rounded-xl bg-coral-wash p-3 text-left text-sm text-coral-deep">{err}</p>}
              <div className="mt-6 flex flex-wrap justify-center gap-2">
                <motion.button whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.96 }} disabled={!acked && !ack} onClick={() => start("ai")} className="btn-primary !px-6 !py-3 disabled:opacity-40"><Icon name="auto_awesome" />Generate with AI</motion.button>
                <button onClick={() => start("rule_based")} className="btn-soft !py-3"><Icon name="rule" className="!text-[16px]" />Quick rule-based plan</button>
              </div>
              {trip?.has_itinerary && <button onClick={() => router.push(`/trips/${tripId}/itinerary/`)} className="mt-4 text-sm font-semibold text-muted hover:text-slate">Back to current plan</button>}
            </motion.div>
          ) : (
            <motion.div key="run" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="text-center">
              <motion.span animate={gen?.status === "failed" ? {} : { scale: [1, 1.08, 1] }} transition={{ duration: 1.6, repeat: Infinity }}
                className={`mx-auto grid h-16 w-16 place-items-center rounded-2xl ${gen?.status === "failed" ? "bg-coral text-white" : gen?.status === "completed" ? "bg-mint text-white" : "bg-coral-wash text-coral"}`}>
                <Icon name={gen?.status === "failed" ? "error" : gen?.status === "completed" ? "check" : "auto_awesome"} className="!text-[32px]" />
              </motion.span>
              <h2 className="mt-5 text-2xl font-bold">{gen?.status === "failed" ? "Generation failed" : gen?.status === "completed" ? "Your itinerary is ready!" : "Building your itinerary"}</h2>
              <p className="mt-1 text-sm text-body">
                {gen?.status === "failed" ? gen.failure_message ?? "Something went wrong." :
                  gen?.status === "completed" ? `${gen.outcome === "fallback_rule_based" ? "The AI was unavailable, so a rule-based plan was made." : "Validated and saved."} Opening it…` :
                  `Usually 20–60 seconds • ${elapsed}s`}
              </p>
              <div className="mt-6 h-2 overflow-hidden rounded-full bg-sky">
                <motion.div className={`h-full rounded-full ${gen?.status === "failed" ? "bg-coral" : "bg-coral"}`} animate={{ width: `${gen?.status === "completed" ? 100 : Math.max(8, ((idx + 1) / order.length) * 100)}%` }} transition={{ duration: 0.6 }} />
              </div>
              <ul className="mt-6 space-y-2 text-left">
                {steps.map(([sts, ic, l], k) => {
                  const done = gen?.status === "completed" || idx > k;
                  const now = idx === k && gen?.status !== "completed";
                  return (
                    <motion.li key={l} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: k * 0.05 }}
                      className={`flex items-center gap-3 rounded-xl p-3 ${done ? "bg-mint-wash" : now ? "bg-coral-wash" : "bg-canvas"}`}>
                      {now ? <motion.span animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: "linear" }} className="block h-5 w-5 rounded-full border-2 border-coral/30 border-t-coral" />
                        : <Icon name={done ? "check_circle" : ic} fill={done} className={done ? "text-mint" : "text-muted"} />}
                      <span className={`text-sm font-semibold ${!done && !now ? "text-muted" : ""}`}>{l}</span>
                      {sts.includes("validating") && gen && gen.validation_summary && (done || now) && <span className="ml-auto text-[11px] text-muted">{gen.validation_summary.warnings} warnings</span>}
                    </motion.li>
                  );
                })}
              </ul>
              {gen?.status === "failed" && (
                <div className="mt-6 flex flex-wrap justify-center gap-2">
                  {gen.next_action === "retry_rule_based" && <button onClick={() => { setGen(null); start("rule_based"); }} className="btn-primary"><Icon name="rule" />Make a rule-based plan</button>}
                  <button onClick={() => setGen(null)} className="btn-soft"><Icon name="refresh" className="!text-[16px]" />Try again</button>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
