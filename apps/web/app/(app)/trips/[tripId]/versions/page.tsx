"use client";

import Link from "next/link";
import { notFound, useParams } from "next/navigation";
import { type FormEvent, useState } from "react";
import { toast } from "sonner";

import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { LoadingSkeleton } from "@/components/states/LoadingSkeleton";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { VersionList } from "@/components/versions/VersionList";
import { ApiError } from "@/lib/api/client";
import {
  useItinerary,
  useRestoreVersion,
  useSaveVersion,
  useVersions,
} from "@/lib/api/queries";
import { isEnabled } from "@/lib/flags";

const NAME_MAX = 60;

/** /trips/[tripId]/versions (§7.5, IMP-610): history, Save version and Restore (API-36 to API-38). */
export default function VersionsPage() {
  if (!isEnabled("versions")) notFound(); // IMD-11: the switched-off page reads as missing
  return <Versions />;
}

function Versions() {
  const { tripId } = useParams<{ tripId: string }>();
  const itinerary = useItinerary(tripId);
  const versions = useVersions(tripId);
  const saveVersion = useSaveVersion(tripId);
  const restore = useRestoreVersion(tripId);
  const [name, setName] = useState("");
  const revision = itinerary.data?.plan_revision;
  const noPlan =
    itinerary.error instanceof ApiError && itinerary.error.status === 404;

  const save = (event: FormEvent) => {
    event.preventDefault();
    if (revision === undefined) return;
    saveVersion.mutate(
      { plan_revision: revision, name: name.trim() },
      {
        onSuccess: () => {
          setName("");
          toast.success("Version saved");
        },
      },
    );
  };

  return (
    <div className="mx-auto flex w-full max-w-[1120px] flex-col gap-6">
      <header>
        <h1 className="text-2xl font-semibold">Versions</h1>
        <Link
          className="text-primary underline"
          href={`/trips/${tripId}/itinerary`}
        >
          Back to itinerary
        </Link>
      </header>
      {noPlan ? (
        <EmptyState
          title="No itinerary yet"
          description="Versions appear once a plan has been generated."
          action={
            <Button asChild className="min-h-touch">
              <Link href={`/trips/${tripId}/generate`}>Generate a plan</Link>
            </Button>
          }
        />
      ) : versions.isPending || itinerary.isPending ? (
        <LoadingSkeleton shape="text" count={5} label="Loading versions" />
      ) : versions.error || itinerary.error ? (
        <ErrorState
          error={versions.error ?? itinerary.error}
          onRetry={() => {
            void versions.refetch();
            void itinerary.refetch();
          }}
        />
      ) : (
        <>
          <form
            onSubmit={save}
            className="flex flex-wrap items-end gap-3 rounded-xl border bg-card p-4 shadow-xs"
          >
            <div className="flex min-w-0 flex-1 flex-col gap-1">
              <Label htmlFor="version-name">Version name</Label>
              <Input
                id="version-name"
                value={name}
                maxLength={NAME_MAX}
                required
                onChange={(event) => setName(event.target.value)}
                aria-describedby="version-name-help"
              />
              <p
                id="version-name-help"
                className="text-sm text-muted-foreground"
              >
                1 to {NAME_MAX} characters, different from your other versions.
              </p>
            </div>
            <Button
              type="submit"
              className="min-h-touch"
              disabled={saveVersion.isPending || name.trim() === ""}
            >
              Save version
            </Button>
          </form>
          {(saveVersion.error ?? restore.error) && (
            <p role="alert" className="text-destructive">
              {(saveVersion.error ?? restore.error)?.message}
            </p>
          )}
          <VersionList
            versions={versions.data}
            currentRevision={itinerary.data.plan_revision}
            restoring={restore.isPending}
            onRestore={(version) =>
              restore.mutate(
                {
                  versionId: version.id,
                  plan_revision: itinerary.data.plan_revision,
                },
                {
                  onSuccess: () =>
                    toast.success(`Version ${version.version_no} restored`),
                },
              )
            }
          />
        </>
      )}
    </div>
  );
}
