import { Suspense, type ReactNode } from "react";

import { AppShell } from "@/components/shell/AppShell";
import { AuthGuard } from "@/components/shell/AuthGuard";
import { LoadingSkeleton } from "@/components/states/LoadingSkeleton";

// Signed-in pages: AuthGuard (IMP-109, §7.2) admits only a signed-in user, and its context gives
// the shell's account menu the user and sign-out. AuthGuard reads the pathname, which a dynamic
// route such as /trips/[tripId] knows only at request time, so with cacheComponents it streams in
// behind Suspense; the fallback is the guard's own loading state.
export default function SignedInLayout({ children }: { children: ReactNode }) {
  return (
    <Suspense
      fallback={
        <div className="mx-auto w-full max-w-6xl px-4 py-6">
          <LoadingSkeleton label="Checking your session" />
        </div>
      }
    >
      <AuthGuard>
        <AppShell>{children}</AppShell>
      </AuthGuard>
    </Suspense>
  );
}
