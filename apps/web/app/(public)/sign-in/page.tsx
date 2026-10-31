import type { Metadata } from "next";

import { SignInForm } from "@/components/auth/SignInForm";
import { AppShell } from "@/components/shell/AppShell";
import { safeNextPath } from "@/lib/auth/redirect";

export const metadata: Metadata = { title: "Sign in · AI Travel Planner" };

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

// Sign-in (§7.5.2). Thin server component (§7.1): it reads the query string and renders the form.
export default async function SignInPage({
  searchParams,
}: PageProps<"/sign-in">) {
  const params = await searchParams;
  return (
    <AppShell variant="public">
      <SignInForm
        next={safeNextPath(first(params.next))}
        confirmationFailed={first(params.error) === "confirmation"}
      />
    </AppShell>
  );
}
