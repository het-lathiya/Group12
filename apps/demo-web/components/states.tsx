"use client";

import { motion } from "motion/react";
import { Icon } from "@/components/ui";

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-xl bg-line/60 ${className}`} />;
}

export function LoadingCards({ n = 3, h = "h-40" }: { n?: number; h?: string }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: n }).map((_, i) => <Skeleton key={i} className={h} />)}
    </div>
  );
}

export function ErrorBox({ error, onRetry }: { error: Error; onRetry?: () => void }) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="card flex flex-wrap items-center gap-4 border-coral/30 p-5">
      <span className="grid h-10 w-10 place-items-center rounded-xl bg-coral-wash text-coral"><Icon name="error" /></span>
      <div className="flex-1"><p className="font-semibold">Couldn&apos;t load this</p><p className="text-sm text-body">{error.message}</p></div>
      {onRetry && <button onClick={onRetry} className="btn-soft"><Icon name="refresh" className="!text-[16px]" />Try again</button>}
    </motion.div>
  );
}

export function Empty({ icon, title, text, action }: { icon: string; title: string; text: string; action?: React.ReactNode }) {
  return (
    <div className="card grid place-items-center p-10 text-center">
      <span className="grid h-14 w-14 place-items-center rounded-2xl bg-coral-wash text-coral"><Icon name={icon} className="!text-[28px]" /></span>
      <p className="mt-4 text-lg font-bold">{title}</p>
      <p className="mt-1 max-w-sm text-sm text-body">{text}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function FullPageSpinner({ text = "Loading…" }: { text?: string }) {
  return (
    <div className="grid min-h-[50vh] place-items-center">
      <div className="flex flex-col items-center gap-3 text-sm text-muted">
        <motion.span animate={{ rotate: 360 }} transition={{ duration: 0.9, repeat: Infinity, ease: "linear" }} className="block h-8 w-8 rounded-full border-[3px] border-coral/25 border-t-coral" />
        {text}
      </div>
    </div>
  );
}
