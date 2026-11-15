"use client";

import { AlertCircle, MoreHorizontal } from "lucide-react";
import { useState, type FormEvent } from "react";
import { toast } from "sonner";

import { ConfirmDialog } from "@/components/states/ConfirmDialog";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api/client";
import {
  useDeleteTrip,
  useDuplicateTrip,
  useUpdateTrip,
} from "@/lib/api/queries";
import type { components } from "@/lib/api/schema";
import { isEnabled } from "@/lib/flags";

type Trip = components["schemas"]["TripOut"];
type Open = "rename" | "archive" | "delete" | null;

const TITLE_MAX = 120; // API-07 title rule (trips/domain.py)

function message(error: unknown): string {
  if (error instanceof ApiError)
    return error.details[0]?.message ?? error.message;
  return "Something went wrong. Please try again.";
}

/**
 * Rename, duplicate, archive or restore, and delete one trip (FR-015; API-11, API-12, API-13).
 * Hidden when the trip_management switch is off (IMD-11): the dashboard still lists trips.
 */
export function TripActionsMenu({ trip }: { trip: Trip }) {
  if (!isEnabled("trip_management")) return null;
  return <EnabledActions trip={trip} />;
}

function EnabledActions({ trip }: { trip: Trip }) {
  const [open, setOpen] = useState<Open>(null);
  const update = useUpdateTrip(trip.id);
  const duplicate = useDuplicateTrip(trip.id);
  const remove = useDeleteTrip(trip.id);
  const archived = trip.status === "archived";
  const busy = update.isPending || duplicate.isPending || remove.isPending;

  function run<T>(action: Promise<T>, done: (result: T) => string) {
    action.then(
      (result) => toast.success(done(result)),
      (error: unknown) => toast.error(message(error)),
    );
  }

  return (
    <>
      <DropdownMenu modal={false}>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            aria-label={`Actions for ${trip.title}`}
            disabled={busy}
            aria-busy={busy}
          >
            <MoreHorizontal aria-hidden="true" className="size-5" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-48">
          {!archived && (
            <DropdownMenuItem onSelect={() => setOpen("rename")}>
              Rename
            </DropdownMenuItem>
          )}
          <DropdownMenuItem
            onSelect={() =>
              run(duplicate.mutateAsync(), (copy) => `Copied as ${copy.title}`)
            }
          >
            Duplicate
          </DropdownMenuItem>
          {archived ? (
            <DropdownMenuItem
              onSelect={() =>
                run(
                  update.mutateAsync({ status: "ready" }),
                  () => "Trip restored",
                )
              }
            >
              Restore
            </DropdownMenuItem>
          ) : (
            <DropdownMenuItem onSelect={() => setOpen("archive")}>
              Archive
            </DropdownMenuItem>
          )}
          <DropdownMenuItem
            variant="destructive"
            onSelect={() => setOpen("delete")}
          >
            Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <RenameDialog
        open={open === "rename"}
        onOpenChange={(next) => setOpen(next ? "rename" : null)}
        title={trip.title}
        onRename={(title) => update.mutateAsync({ title })}
      />
      <ConfirmDialog
        open={open === "archive"}
        onOpenChange={(next) => setOpen(next ? "archive" : null)}
        title={`Archive ${trip.title}?`}
        description="An archived trip is read-only until you restore it. It is hidden from your trips unless you show archived trips."
        confirmLabel="Archive trip"
        onConfirm={() =>
          run(update.mutateAsync({ status: "archived" }), () => "Trip archived")
        }
      />
      <ConfirmDialog
        open={open === "delete"}
        onOpenChange={(next) => setOpen(next ? "delete" : null)}
        title={`Delete ${trip.title}?`}
        description="The trip and its itinerary disappear from your trips. They are kept for 30 days and then removed for good."
        confirmLabel="Delete trip"
        destructive
        onConfirm={() => run(remove.mutateAsync(), () => "Trip deleted")}
      />
    </>
  );
}

function RenameDialog({
  open,
  onOpenChange,
  title,
  onRename,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  onRename: (title: string) => Promise<unknown>;
}) {
  const [value, setValue] = useState(title);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  function change(next: boolean) {
    if (next) {
      setValue(title);
      setError(null);
    }
    onOpenChange(next);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const trimmed = value.trim();
    if (trimmed.length < 1 || trimmed.length > TITLE_MAX) {
      setError(`Enter a trip name of 1 to ${TITLE_MAX} characters.`);
      return;
    }
    setSaving(true);
    try {
      await onRename(trimmed);
      toast.success("Trip renamed");
      onOpenChange(false);
    } catch (caught) {
      setError(message(caught));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={change}>
      <DialogContent>
        <form onSubmit={submit} noValidate className="flex flex-col gap-4">
          <DialogHeader>
            <DialogTitle>Rename trip</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-2">
            <Label htmlFor="trip-title">Trip name (required)</Label>
            <Input
              id="trip-title"
              value={value}
              maxLength={TITLE_MAX}
              onChange={(event) => setValue(event.target.value)}
              aria-invalid={error !== null}
              aria-describedby={error ? "trip-title-error" : undefined}
            />
            {error && (
              <p
                id="trip-title-error"
                className="flex items-center gap-1.5 text-sm text-destructive"
              >
                <AlertCircle aria-hidden="true" className="size-4 shrink-0" />
                {error}
              </p>
            )}
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="outline" className="min-h-touch">
                Cancel
              </Button>
            </DialogClose>
            <Button
              type="submit"
              className="min-h-touch"
              disabled={saving}
              aria-busy={saving}
            >
              Save name
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
