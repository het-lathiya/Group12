"use client";

import { motion } from "motion/react";
import { useEffect, useState } from "react";
import { useToast } from "@/components/fx";
import { ErrorBox, LoadingCards } from "@/components/states";
import { Icon } from "@/components/ui";
import { api } from "@/lib/api";
import { useLoad, useSession } from "@/lib/session";

export default function Profile() {
  const toast = useToast();
  const { signOut } = useSession();
  const me = useLoad(() => api.me(), []);
  const [name, setName] = useState("");
  const [country, setCountry] = useState("");
  const [currency, setCurrency] = useState("INR");
  const [saving, setSaving] = useState(false);
  useEffect(() => { if (me.data) { setName(me.data.display_name ?? ""); setCountry(me.data.home_country ?? ""); setCurrency(me.data.preferred_currency ?? "INR"); } }, [me.data]);

  if (me.error) return <main className="mx-auto max-w-3xl px-4 py-8"><ErrorBox error={me.error} onRetry={me.reload} /></main>;
  if (!me.data) return <main className="mx-auto max-w-3xl px-4 py-8"><LoadingCards n={2} h="h-40" /></main>;
  const initials = (name || me.data.email || "?").slice(0, 2).toUpperCase();

  const save = async () => {
    setSaving(true);
    try { me.setData(await api.updateMe({ display_name: name.trim() || undefined, home_country: country.trim().toUpperCase().slice(0, 2) || undefined, preferred_currency: currency })); toast({ text: "Profile saved", icon: "check_circle" }); }
    catch (e) { toast({ text: (e as Error).message, icon: "error" }); } finally { setSaving(false); }
  };

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 md:px-6">
      <p className="label text-coral">Account</p>
      <h1 className="mt-1 text-[32px] font-extrabold tracking-tight">Profile</h1>

      <motion.section initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="card mt-6 flex items-center gap-5 p-6">
        <motion.span whileHover={{ rotate: 8, scale: 1.05 }} className="grid h-16 w-16 place-items-center rounded-full bg-slate text-xl font-bold text-white">{initials}</motion.span>
        <div className="flex-1"><p className="text-lg font-bold">{me.data.display_name ?? "No name yet"}</p><p className="text-sm text-muted">{me.data.email}</p></div>
        {me.data.ai_notice_ack_at && <span className="badge-mint"><Icon name="verified" className="!text-[13px]" />AI notice accepted</span>}
      </motion.section>

      <motion.form initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08 }} onSubmit={(e) => { e.preventDefault(); save(); }} className="card mt-5 space-y-5 p-6">
        <h2 className="text-lg font-semibold">Details</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <label><span className="label text-muted">Display name</span><input value={name} onChange={(e) => setName(e.target.value)} className="input mt-1.5" maxLength={80} /></label>
          <label><span className="label text-muted">Home country (2 letters)</span><input value={country} onChange={(e) => setCountry(e.target.value)} className="input mt-1.5 uppercase" maxLength={2} placeholder="IN" /></label>
          <label><span className="label text-muted">Preferred currency</span>
            <select value={currency} onChange={(e) => setCurrency(e.target.value)} className="input mt-1.5"><option value="INR">INR ₹</option><option value="USD">USD $</option><option value="EUR">EUR €</option><option value="GBP">GBP £</option></select></label>
        </div>
        <div className="flex justify-end gap-2 border-t border-hair pt-5">
          <button type="button" onClick={me.reload} className="btn-soft">Reset</button>
          <motion.button whileTap={{ scale: 0.96 }} disabled={saving} className="btn-primary disabled:opacity-60">{saving ? "Saving…" : "Save changes"}</motion.button>
        </div>
      </motion.form>

      <section className="card mt-5 flex items-center justify-between p-6">
        <div><p className="font-semibold">Sign out</p><p className="text-sm text-muted">You can sign back in anytime.</p></div>
        <button onClick={signOut} className="btn-soft"><Icon name="logout" className="!text-[16px]" />Sign out</button>
      </section>
    </main>
  );
}
