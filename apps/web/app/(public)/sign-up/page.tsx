import type { Metadata } from "next";

import { SignUpForm } from "@/components/auth/SignUpForm";
import { AppShell } from "@/components/shell/AppShell";
import { safeNextPath } from "@/lib/auth/redirect";

export const metadata: Metadata = {
  title: "Create an account · AI Travel Planner",
};

// Sign-up (§7.5.2). Thin server component (§7.1): it reads the query string and renders the form.
export default async function SignUpPage({
  searchParams,
}: PageProps<"/sign-up">) {
  const { next } = await searchParams;
  return (
    <AppShell variant="public">
      <SignUpForm next={safeNextPath(Array.isArray(next) ? next[0] : next)} />
    </AppShell>
  );
}
