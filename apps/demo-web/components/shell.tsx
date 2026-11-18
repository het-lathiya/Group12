"use client";

import { useRouter } from "next/navigation";
import { createContext, useContext, useEffect } from "react";
import { AppNav, Footer, TripHeader } from "@/components/ui";
import { ErrorBox, FullPageSpinner } from "@/components/states";
import { api, type Trip } from "@/lib/api";
import { useLoad, useSession, useTripId } from "@/lib/session";

/** Signed-in area: redirects to /sign-in when there is no Supabase session. */
export function AuthGate({ children }: { children: React.ReactNode }) {
  const { status } = useSession();
  const router = useRouter();
  useEffect(() => {
    if (status === "signed_out") router.replace(`/sign-in/?next=${encodeURIComponent(window.location.pathname)}`);
  }, [status, router]);
  if (status !== "signed_in") return <FullPageSpinner text={status === "loading" ? "Checking your session…" : "Redirecting to sign in…"} />;
  return (<><AppNav />{children}<Footer /></>);
}

type TripCtx = { tripId: string; trip?: Trip; reloadTrip: () => void };
const Ctx = createContext<TripCtx>({ tripId: "", reloadTrip: () => {} });
export const useTrip = () => useContext(Ctx);

export function TripShell({ children }: { children: React.ReactNode }) {
  const tripId = useTripId();
  const { data: trip, error, reload } = useLoad(tripId ? () => api.trip(tripId) : null, [tripId]);
  return (
    <Ctx.Provider value={{ tripId, trip, reloadTrip: reload }}>
      <TripHeader trip={trip} tripId={tripId} />
      <div className="mx-auto max-w-[1440px] px-4 py-6 md:px-6">
        {error ? <ErrorBox error={error} onRetry={reload} /> : tripId ? children : <FullPageSpinner />}
      </div>
    </Ctx.Provider>
  );
}
