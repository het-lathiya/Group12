"use client";

import type { Session } from "@supabase/supabase-js";
import { useParams, usePathname } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { supabase } from "@/lib/api";

export function useSession() {
  const [session, setSession] = useState<Session | null | undefined>(undefined);
  useEffect(() => {
    let on = true;
    supabase().auth.getSession().then(({ data }) => on && setSession(data.session));
    const { data } = supabase().auth.onAuthStateChange((_e, s) => { if (on) setSession(s); });
    return () => { on = false; data.subscription.unsubscribe(); };
  }, []);
  const signOut = useCallback(async () => { await supabase().auth.signOut(); window.location.assign("/sign-in/"); }, []);
  return { status: session === undefined ? "loading" : session ? "signed_in" : "signed_out", session: session ?? null, user: session?.user ?? null, signOut } as const;
}

/**
 * The trip id from the URL. On the static AWS build every trip is served from the prerendered
 * /trips/_/... page (CloudFront rewrites the real id to "_"), so the id is read from the address bar.
 */
export function useTripId(): string {
  const params = useParams<{ tripId?: string }>();
  const path = usePathname();
  const [id, setId] = useState(params.tripId && params.tripId !== "_" ? params.tripId : "");
  useEffect(() => {
    const m = window.location.pathname.match(/\/trips\/([^/]+)\//);
    if (m && m[1] !== "_" && m[1] !== "new") setId(m[1]);
  }, [path]);
  return id;
}

/** Load data from the API with loading / error state and a reload function. */
export function useLoad<T>(fn: (() => Promise<T>) | null, deps: unknown[]) {
  const [data, setData] = useState<T | undefined>(undefined);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (!fn) return;
    let on = true;
    setLoading(true); setError(null);
    fn().then((d) => { if (on) { setData(d); setLoading(false); } }, (e) => { if (on) { setError(e); setLoading(false); } });
    return () => { on = false; };
  }, [...deps, tick]); // eslint-disable-line react-hooks/exhaustive-deps
  return { data, setData, error, loading, reload: () => setTick((t) => t + 1) };
}
