"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";
import { Icon, Logo } from "@/components/ui";
import { destinations } from "@/lib/data";
import { supabase } from "@/lib/api";

function nextPath() {
  const n = new URLSearchParams(window.location.search).get("next");
  return n && n.startsWith("/") && !n.startsWith("//") ? n : "/dashboard/";
}

const slides = [
  { ...destinations[2], place: "Lake Pichola Sunset Cruise", meta: "Day 3 • ★ 4.9 • ₹900 / pp", tip: "Board at 5:30 PM for golden hour" },
  { ...destinations[0], place: "Amber Fort at opening", meta: "Day 2 • ★ 4.7 • ₹500 entry", tip: "Arrive at 8 AM to skip the crowds" },
  { ...destinations[3], place: "Alleppey Houseboat Night", meta: "Day 2 • ★ 4.8 • ₹7,500 / night", tip: "Ask for the upper-deck room" },
  { ...destinations[1], place: "Sunset at Vagator Beach", meta: "Day 1 • ★ 4.6 • Free", tip: "Grab a spot at Chapora Fort by 5:45" },
];

const item = { hidden: { opacity: 0, y: 14 }, show: { opacity: 1, y: 0 } };

function strength(p: string) {
  let s = 0;
  if (p.length >= 8) s++;
  if (/[A-Z]/.test(p) && /[a-z]/.test(p)) s++;
  if (/\d/.test(p)) s++;
  if (/[^A-Za-z0-9]/.test(p)) s++;
  return s;
}
const sLabel = ["Too short", "Weak", "Okay", "Good", "Strong"];
const sColor = ["#e2e8f0", "#ff5a36", "#f59e0b", "#22c55e", "#059669"];

export function AuthPage({ mode }: { mode: "in" | "up" }) {
  const router = useRouter();
  const up = mode === "up";
  const [slide, setSlide] = useState(0);
  const [show, setShow] = useState(false);
  const [pw, setPw] = useState("");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [shake, setShake] = useState(0);
  const [magic, setMagic] = useState(false);
  const s = strength(pw);
  const emailOk = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

  useEffect(() => { const t = setInterval(() => setSlide((x) => (x + 1) % slides.length), 4500); return () => clearInterval(t); }, []);

  const [err, setErr] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [name, setName] = useState("");

  useEffect(() => {
    supabase().auth.getSession().then(({ data }) => { if (data.session) router.replace(nextPath()); });
  }, [router]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null); setInfo(null);
    if (!emailOk || pw.length < 8) { setShake((x) => x + 1); setErr(!emailOk ? "Enter a valid email." : "Password must be at least 8 characters."); return; }
    setLoading(true);
    try {
      if (up) {
        const { data, error } = await supabase().auth.signUp({ email, password: pw, options: { data: { display_name: name || undefined }, emailRedirectTo: `${window.location.origin}/dashboard/` } });
        if (error) throw error;
        if (!data.session) { setLoading(false); setInfo("Account created. Check your email to confirm it, then sign in."); return; }
      } else {
        const { error } = await supabase().auth.signInWithPassword({ email, password: pw });
        if (error) throw error;
      }
      setLoading(false); setDone(true);
      setTimeout(() => router.push(nextPath()), 600);
    } catch (e2) {
      setLoading(false); setShake((x) => x + 1);
      setErr(e2 instanceof Error ? e2.message : "Sign-in failed.");
    }
  };

  const sendMagic = async () => {
    setErr(null);
    if (!emailOk) { setShake((x) => x + 1); setErr("Enter your email first."); return; }
    const { error } = await supabase().auth.signInWithOtp({ email, options: { emailRedirectTo: `${window.location.origin}/dashboard/`, shouldCreateUser: false } });
    if (error) setErr(error.message); else setMagic(true);
  };

  const cur = slides[slide];

  return (
    <main className="relative grid min-h-screen overflow-hidden lg:grid-cols-2">
      {/* animated background blobs */}
      <motion.div aria-hidden className="pointer-events-none absolute -left-32 -top-32 h-96 w-96 rounded-full bg-coral/20 blur-3xl" animate={{ x: [0, 60, 0], y: [0, 40, 0] }} transition={{ duration: 14, repeat: Infinity }} />
      <motion.div aria-hidden className="pointer-events-none absolute -bottom-40 left-1/4 h-96 w-96 rounded-full bg-mint/15 blur-3xl" animate={{ x: [0, -50, 0], y: [0, -30, 0] }} transition={{ duration: 16, repeat: Infinity }} />

      <div className="relative flex flex-col px-6 py-6 md:px-12">
        <Logo />
        <motion.div key={mode} initial="hidden" animate="show" transition={{ staggerChildren: 0.07, delayChildren: 0.1 }} className="mx-auto my-auto w-full max-w-sm py-12">
          <motion.div variants={item} className="mb-6 inline-flex rounded-full bg-sky p-1 text-xs font-semibold">
            {[["in", "Sign in", "/sign-in"], ["up", "Sign up", "/sign-up"]].map(([m, l, h]) => (
              <Link key={m} href={h + "/"} className={`relative rounded-full px-4 py-1.5 ${mode === m ? "text-white" : "text-muted"}`}>
                {mode === m && <motion.span layoutId="authtab" className="absolute inset-0 rounded-full bg-slate" />}
                <span className="relative">{l}</span>
              </Link>
            ))}
          </motion.div>

          <motion.h1 variants={item} className="text-[32px] font-extrabold leading-10 tracking-tight">
            {up ? "Create your account" : <>Welcome back <motion.span className="inline-block origin-[70%_70%]" animate={{ rotate: [0, 18, -8, 18, 0] }} transition={{ duration: 1.6, repeat: Infinity, repeatDelay: 2.5 }}>👋</motion.span></>}
          </motion.h1>
          <motion.p variants={item} className="mt-2 text-sm text-body">{up ? "Save trips, collaborate and keep every version." : "Sign in to continue planning your trips."}</motion.p>

          <motion.form key={shake} onSubmit={submit} noValidate animate={shake ? { x: [0, -10, 10, -6, 6, 0] } : {}} transition={{ duration: 0.4 }} className="mt-8 space-y-4">
            {up && (
              <motion.label variants={item} className="block"><span className="label text-muted">Full name</span>
                <div className="relative mt-1.5"><Icon name="person" className="absolute left-3.5 top-3.5 text-muted" /><input value={name} onChange={(e) => setName(e.target.value)} className="input pl-11" placeholder="Your name" /></div>
              </motion.label>
            )}
            <motion.label variants={item} className="block"><span className="label text-muted">Email</span>
              <div className="relative mt-1.5">
                <Icon name="mail" className="absolute left-3.5 top-3.5 text-muted" />
                <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" className="input pl-11 pr-10" placeholder="you@example.com" />
                <AnimatePresence>{emailOk && (
                  <motion.span initial={{ scale: 0 }} animate={{ scale: 1 }} exit={{ scale: 0 }} className="absolute right-3 top-3.5 text-mint"><Icon name="check_circle" fill /></motion.span>
                )}</AnimatePresence>
              </div>
            </motion.label>
            <motion.label variants={item} className="block">
              <span className="flex justify-between"><span className="label text-muted">Password</span>{!up && <a href="#" className="text-xs font-semibold text-coral">Forgot?</a>}</span>
              <div className="relative mt-1.5">
                <Icon name="lock" className="absolute left-3.5 top-3.5 text-muted" />
                <input value={pw} onChange={(e) => setPw(e.target.value)} type={show ? "text" : "password"} className="input pl-11 pr-11" placeholder="At least 8 characters" />
                <button type="button" onClick={() => setShow((x) => !x)} className="absolute right-3 top-3 text-muted hover:text-slate" aria-label={show ? "Hide password" : "Show password"}>
                  <AnimatePresence mode="wait" initial={false}><motion.span key={String(show)} initial={{ rotate: -90, opacity: 0 }} animate={{ rotate: 0, opacity: 1 }} exit={{ rotate: 90, opacity: 0 }} className="block"><Icon name={show ? "visibility_off" : "visibility"} /></motion.span></AnimatePresence>
                </button>
              </div>
              <AnimatePresence>
                {up && pw && (
                  <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                    <div className="mt-2 grid grid-cols-4 gap-1">
                      {[0, 1, 2, 3].map((i) => <motion.span key={i} className="h-1.5 rounded-full" animate={{ backgroundColor: i < s ? sColor[s] : "#e2e8f0" }} />)}
                    </div>
                    <p className="mt-1 text-[11px] font-semibold" style={{ color: sColor[s] === "#e2e8f0" ? "#64748b" : sColor[s] }}>{sLabel[s]}</p>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.label>

            <AnimatePresence>
              {(err || info) && (
                <motion.p initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}
                  className={`flex items-start gap-2 rounded-xl p-3 text-[13px] ${err ? "bg-coral-wash text-coral-deep" : "bg-mint-wash text-mint"}`}>
                  <Icon name={err ? "error" : "mark_email_read"} className="!text-[16px]" />{err ?? info}
                </motion.p>
              )}
            </AnimatePresence>
            <motion.button variants={item} whileHover={{ scale: loading || done ? 1 : 1.02 }} whileTap={{ scale: 0.97 }} disabled={loading || done}
              className={`btn-primary relative w-full overflow-hidden !py-3 ${done ? "!bg-mint !shadow-none" : ""}`}>
              <AnimatePresence mode="wait" initial={false}>
                {loading ? (
                  <motion.span key="l" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="flex items-center gap-2">
                    <motion.span animate={{ rotate: 360 }} transition={{ duration: 0.8, repeat: Infinity, ease: "linear" }} className="block h-4 w-4 rounded-full border-2 border-white/40 border-t-white" />
                    {up ? "Creating account…" : "Signing in…"}
                  </motion.span>
                ) : done ? (
                  <motion.span key="d" initial={{ scale: 0 }} animate={{ scale: 1 }} className="flex items-center gap-2"><Icon name="check_circle" fill />You&apos;re in!</motion.span>
                ) : (
                  <motion.span key="i" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="flex items-center gap-2">
                    {up ? "Create account" : "Sign in"}<Icon name="arrow_forward" className="!text-[16px]" />
                  </motion.span>
                )}
              </AnimatePresence>
            </motion.button>
          </motion.form>

          <motion.div variants={item} className="my-6 flex items-center gap-3 text-xs text-muted"><span className="h-px flex-1 bg-line" />or<span className="h-px flex-1 bg-line" /></motion.div>
          <motion.button variants={item} whileHover={{ y: -2 }} whileTap={{ scale: 0.98 }} onClick={sendMagic}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-line bg-white py-3 text-sm font-semibold hover:bg-canvas">
            <AnimatePresence mode="wait" initial={false}>
              {magic ? (
                <motion.span key="m" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center gap-2 text-mint"><Icon name="mark_email_read" />Magic link sent. Check your inbox</motion.span>
              ) : (
                <motion.span key="n" exit={{ opacity: 0 }} className="flex items-center gap-2"><Icon name="auto_awesome" className="text-coral" />Continue with magic link</motion.span>
              )}
            </AnimatePresence>
          </motion.button>
          <motion.p variants={item} className="mt-8 text-center text-sm text-body">
            {up ? "Already have an account? " : "New to TripBook? "}
            <Link href={up ? "/sign-in/" : "/sign-up/"} className="font-semibold text-coral hover:underline">{up ? "Sign in" : "Create one"}</Link>
          </motion.p>
        </motion.div>
      </div>

      {/* right: rotating destination slideshow */}
      <div className="relative hidden overflow-hidden lg:block">
        <AnimatePresence initial={false}>
          <motion.img key={cur.name} src={cur.img} alt="" initial={{ opacity: 0, scale: 1.12 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}
            transition={{ opacity: { duration: 1 }, scale: { duration: 6, ease: "linear" } }} className="absolute inset-0 h-full w-full object-cover" />
        </AnimatePresence>
        <div className="absolute inset-0 bg-gradient-to-t from-slate/80 via-slate/10 to-slate/30" />

        <motion.div animate={{ y: [0, -10, 0] }} transition={{ duration: 5, repeat: Infinity }} className="glass absolute right-10 top-10 rounded-2xl px-4 py-3 shadow-xl">
          <p className="flex items-center gap-1 text-[11px] font-bold text-coral"><Icon name="auto_awesome" className="!text-[14px]" />AI tip</p>
          <AnimatePresence mode="wait"><motion.p key={cur.tip} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} className="text-sm font-bold">{cur.tip}</motion.p></AnimatePresence>
        </motion.div>
        <motion.div animate={{ y: [0, 8, 0] }} transition={{ duration: 6, repeat: Infinity }} className="glass absolute left-10 top-36 flex items-center gap-2 rounded-full px-3 py-2 shadow-xl">
          <div className="flex -space-x-2">{["A", "R", "M"].map((c, i) => <span key={c} className="grid h-7 w-7 place-items-center rounded-full border-2 border-white text-[11px] font-bold text-white" style={{ background: ["#ff5a36", "#059669", "#6366f1"][i] }}>{c}</span>)}</div>
          <span className="text-xs font-semibold">12k+ trips planned</span>
        </motion.div>

        <div className="absolute bottom-10 left-10 right-10">
          <AnimatePresence mode="wait">
            <motion.div key={cur.place} initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} transition={{ duration: 0.5 }} className="glass rounded-2xl p-5 shadow-2xl">
              <span className="badge-mint"><Icon name="verified" className="!text-[14px]" />AI curated • {cur.name}</span>
              <p className="mt-2 text-lg font-bold">{cur.place}</p>
              <p className="text-sm text-body">{cur.meta}</p>
            </motion.div>
          </AnimatePresence>
          <div className="mt-4 flex justify-center gap-2">
            {slides.map((x, i) => (
              <button key={x.name} onClick={() => setSlide(i)} aria-label={`Show ${x.name}`} className="h-1.5 overflow-hidden rounded-full bg-white/40 transition-all" style={{ width: i === slide ? 32 : 10 }}>
                {i === slide && <motion.span key={slide} className="block h-full bg-white" initial={{ width: 0 }} animate={{ width: "100%" }} transition={{ duration: 4.5, ease: "linear" }} />}
              </button>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
