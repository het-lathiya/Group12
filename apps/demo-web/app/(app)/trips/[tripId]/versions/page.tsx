"use client";

import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";
import { useToast } from "@/components/fx";
import { useTrip } from "@/components/shell";
import { Empty, ErrorBox, LoadingCards } from "@/components/states";
import { Icon } from "@/components/ui";
import { api } from "@/lib/api";
import { useLoad } from "@/lib/session";

export default function Versions() {
  const { tripId, trip, reloadTrip } = useTrip();
  const toast = useToast();
  const v = useLoad(() => api.versions(tripId), [tripId]);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const list = [...(v.data ?? [])].sort((a, b) => b.version_no - a.version_no);
  const rev = trip?.plan_revision ?? 0;

  const save = async () => {
    if (!name.trim()) return;
    setBusy("save");
    try { await api.saveVersion(tripId, name.trim(), rev); setName(""); toast({ text: "Version saved", icon: "bookmark_add" }); v.reload(); reloadTrip(); }
    catch (e) { toast({ text: (e as Error).message, icon: "error" }); } finally { setBusy(null); }
  };
  const restore = async (id: string, no: number) => {
    if (!confirm(`Restore version ${no}? The current plan is kept as a version too.`)) return;
    setBusy(id);
    try { await api.restoreVersion(tripId, id, rev); toast({ text: `Restored version ${no}`, icon: "restore" }); v.reload(); reloadTrip(); }
    catch (e) { toast({ text: (e as Error).message, icon: "error" }); } finally { setBusy(null); }
  };

  return (
    <div className="mx-auto max-w-3xl">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div><h2 className="text-xl font-bold">Version history</h2><p className="text-sm text-muted">Every generation and edit is kept. Restore any version.</p></div>
        <form onSubmit={(e) => { e.preventDefault(); save(); }} className="flex gap-2">
          <input value={name} onChange={(e) => setName(e.target.value)} maxLength={60} placeholder="Name this version" className="input !h-10 !w-52" />
          <button disabled={!name.trim() || busy !== null || !trip?.has_itinerary} className="btn-primary disabled:opacity-50"><Icon name="bookmark_add" />Save</button>
        </form>
      </div>
      {v.error ? <div className="mt-6"><ErrorBox error={v.error} onRetry={v.reload} /></div> : v.loading ? <div className="mt-6"><LoadingCards n={4} h="h-20" /></div> : list.length === 0 ? (
        <div className="mt-6"><Empty icon="history" title="No versions yet" text="Versions appear after the first itinerary is generated." /></div>
      ) : (
        <ol className="relative mt-6 space-y-3 border-l-2 border-dashed border-line pl-6">
          <AnimatePresence initial={false}>
            {list.map((x, i) => {
              const current = i === 0;
              const ai = x.kind.includes("generat");
              return (
                <motion.li key={x.id} layout initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.04 }} className="card relative flex flex-wrap items-center gap-4 p-4">
                  <span className={`absolute -left-[33px] top-6 h-3 w-3 rounded-full ring-4 ring-canvas ${current ? "bg-coral" : "bg-line"}`} />
                  <span className={`grid h-10 w-10 place-items-center rounded-xl ${ai ? "bg-coral-wash text-coral" : "bg-sky text-slate"}`}><Icon name={ai ? "auto_awesome" : x.kind.includes("restore") ? "restore" : x.name ? "bookmark" : "edit"} /></span>
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold">v{x.version_no} • {x.name ?? x.reason.replace(/_/g, " ")}</p>
                    <p className="text-xs text-muted">{x.kind.replace(/_/g, " ")} • {new Date(x.created_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}
                      {x.validation_summary.warnings + x.validation_summary.errors > 0 && ` • ${x.validation_summary.errors} errors, ${x.validation_summary.warnings} warnings`}</p>
                  </div>
                  {current ? <span className="badge-mint">Latest</span> : (
                    <motion.button whileTap={{ scale: 0.95 }} disabled={busy !== null} onClick={() => restore(x.id, x.version_no)} className="btn-soft !text-xs disabled:opacity-50">
                      {busy === x.id ? <span className="h-3 w-3 animate-spin rounded-full border-2 border-coral/30 border-t-coral" /> : <Icon name="restore" className="!text-[15px]" />}Restore
                    </motion.button>
                  )}
                </motion.li>
              );
            })}
          </AnimatePresence>
        </ol>
      )}
    </div>
  );
}
