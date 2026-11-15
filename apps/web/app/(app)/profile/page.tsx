"use client";

import { toast } from "sonner";

import { ProfileForm } from "@/components/profile/ProfileForm";
import { ErrorState } from "@/components/states/ErrorState";
import { LoadingSkeleton } from "@/components/states/LoadingSkeleton";
import { ApiError, type ErrorDetail } from "@/lib/api/client";
import { useProfile, useUpdateProfile } from "@/lib/api/queries";
import type { components } from "@/lib/api/schema";

/** /profile (§7.5, FR-004; API-03, API-04): the traveller's name, home currency and defaults. */
export default function ProfilePage() {
  const profile = useProfile();
  const update = useUpdateProfile();

  async function save(
    body: components["schemas"]["ProfilePatch"],
  ): Promise<ErrorDetail[]> {
    try {
      await update.mutateAsync(body);
      toast.success("Profile saved");
      return [];
    } catch (error) {
      if (error instanceof ApiError && error.code === "VALIDATION_ERROR") {
        return error.details; // shown on their fields
      }
      toast.error(
        error instanceof ApiError
          ? error.message
          : "The profile could not be saved. Try again.",
      );
      return [];
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-[720px] flex-col gap-6">
      <header>
        <h1 className="font-heading text-2xl font-semibold">Your profile</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {profile.data?.email ?? "Your name and the defaults for new trips."}
        </p>
      </header>
      {profile.isPending ? (
        <LoadingSkeleton shape="text" count={6} label="Loading your profile" />
      ) : profile.isError ? (
        <ErrorState
          title="Your profile could not be loaded"
          error={profile.error as ApiError}
          onRetry={() => void profile.refetch()}
        />
      ) : (
        <div className="rounded-xl border bg-card p-4 text-card-foreground sm:p-6">
          <ProfileForm profile={profile.data} onSave={save} />
        </div>
      )}
    </div>
  );
}
