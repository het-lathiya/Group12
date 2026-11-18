"use client";

import { AnimatePresence, motion, useInView, useMotionValue, useSpring, useTransform } from "motion/react";
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

/* ---------- Reveal on scroll ---------- */
export function Reveal({ children, delay = 0, y = 24, className = "" }: { children: React.ReactNode; delay?: number; y?: number; className?: string }) {
  return (
    <motion.div className={className} initial={{ opacity: 0, y }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.55, delay, ease: [0.22, 1, 0.36, 1] }}>
      {children}
    </motion.div>
  );
}

/* ---------- Animated number ---------- */
export function CountUp({ to, prefix = "", suffix = "", duration = 1.2, format = true }: { to: number; prefix?: string; suffix?: string; duration?: number; format?: boolean }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const [v, setV] = useState(0);
  const from = useRef(0);
  useEffect(() => {
    if (!inView) return;
    const start = performance.now(); const a = from.current;
    let raf = 0;
    const tick = (t: number) => {
      const p = Math.max(0, Math.min(1, (t - start) / (duration * 1000)));
      const e = 1 - Math.pow(1 - p, 3);
      setV(a + (to - a) * e);
      if (p < 1) raf = requestAnimationFrame(tick); else from.current = to;
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [to, inView, duration]);
  const n = Math.round(v);
  return <span ref={ref}>{prefix}{format ? n.toLocaleString("en-IN") : n}{suffix}</span>;
}

/* ---------- 3D tilt card ---------- */
export function Tilt({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  const x = useMotionValue(0.5), y = useMotionValue(0.5);
  const rx = useSpring(useTransform(y, [0, 1], [8, -8]), { stiffness: 200, damping: 18 });
  const ry = useSpring(useTransform(x, [0, 1], [-10, 10]), { stiffness: 200, damping: 18 });
  return (
    <motion.div className={className} style={{ rotateX: rx, rotateY: ry, transformPerspective: 900 }}
      onPointerMove={(e) => { const r = e.currentTarget.getBoundingClientRect(); x.set((e.clientX - r.left) / r.width); y.set((e.clientY - r.top) / r.height); }}
      onPointerLeave={() => { x.set(0.5); y.set(0.5); }}>
      {children}
    </motion.div>
  );
}

/* ---------- Typewriter placeholder ---------- */
export function useTypewriter(lines: string[], speed = 45, pause = 1600) {
  const [text, setText] = useState("");
  useEffect(() => {
    let i = 0, c = 0, del = false;
    let t: ReturnType<typeof setTimeout>;
    const step = () => {
      const line = lines[i % lines.length];
      if (!del) { c++; setText(line.slice(0, c)); if (c === line.length) { del = true; t = setTimeout(step, pause); return; } }
      else { c--; setText(line.slice(0, c)); if (c === 0) { del = false; i++; } }
      t = setTimeout(step, del ? speed / 2 : speed);
    };
    t = setTimeout(step, 400);
    return () => clearTimeout(t);
  }, [lines, speed, pause]);
  return text;
}

/* ---------- Rotating word ---------- */
export function RotatingWord({ words, className = "" }: { words: string[]; className?: string }) {
  const [i, setI] = useState(0);
  useEffect(() => { const t = setInterval(() => setI((x) => (x + 1) % words.length), 2200); return () => clearInterval(t); }, [words.length]);
  return (
    <span className={`relative inline-grid overflow-hidden align-bottom ${className}`}>
      <AnimatePresence mode="popLayout" initial={false}>
        <motion.span key={words[i]} initial={{ y: "100%", opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: "-100%", opacity: 0 }}
          transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }} className="col-start-1 row-start-1 whitespace-nowrap">
          {words[i]}
        </motion.span>
      </AnimatePresence>
    </span>
  );
}

/* ---------- Toasts ---------- */
type Toast = { id: number; text: string; icon?: string; undo?: () => void };
const ToastCtx = createContext<(t: Omit<Toast, "id">) => void>(() => {});
export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [list, setList] = useState<Toast[]>([]);
  const push = useCallback((t: Omit<Toast, "id">) => {
    const id = Date.now() + Math.random();
    setList((l) => [...l.slice(-2), { ...t, id }]);
    setTimeout(() => setList((l) => l.filter((x) => x.id !== id)), 3800);
  }, []);
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="pointer-events-none fixed bottom-5 left-1/2 z-[100] flex w-[min(92vw,420px)] -translate-x-1/2 flex-col gap-2">
        <AnimatePresence>
          {list.map((t) => (
            <motion.div key={t.id} layout initial={{ opacity: 0, y: 30, scale: 0.95 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 10, scale: 0.95 }}
              className="pointer-events-auto flex items-center gap-3 rounded-2xl bg-slate px-4 py-3 text-sm text-white shadow-2xl">
              <span aria-hidden className="ms ms-fill text-coral">{t.icon ?? "check_circle"}</span>
              <span className="flex-1">{t.text}</span>
              {t.undo && <button onClick={() => { t.undo!(); setList((l) => l.filter((x) => x.id !== t.id)); }} className="font-bold text-coral">Undo</button>}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastCtx.Provider>
  );
}

/* ---------- Streaming text (AI replies) ---------- */
export function Stream({ text, onDone }: { text: string; onDone?: () => void }) {
  const [n, setN] = useState(0);
  useEffect(() => {
    if (n >= text.length) { onDone?.(); return; }
    const t = setTimeout(() => setN((x) => Math.min(text.length, x + 3)), 18);
    return () => clearTimeout(t);
  }, [n, text, onDone]);
  return <>{text.slice(0, n)}{n < text.length && <span className="ml-0.5 inline-block h-3.5 w-1.5 animate-pulse bg-coral align-middle" />}</>;
}

export function TypingDots() {
  return (
    <span className="inline-flex gap-1">
      {[0, 1, 2].map((i) => (
        <motion.span key={i} className="h-1.5 w-1.5 rounded-full bg-muted" animate={{ y: [0, -4, 0], opacity: [0.4, 1, 0.4] }} transition={{ duration: 0.9, repeat: Infinity, delay: i * 0.15 }} />
      ))}
    </span>
  );
}

export { motion, AnimatePresence };
