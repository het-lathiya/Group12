"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useIsMutating } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { itemCardId } from "@/components/itinerary/ItineraryItemCard";
import { ConfirmDialog } from "@/components/states/ConfirmDialog";
import { Field } from "@/components/trips/Field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api/client";
import { describeError } from "@/lib/api/errors";
import {
  EDIT_UNDO_ENABLED,
  editKey,
  useAddItem,
  useRemoveItem,
  useRetimeItem,
} from "@/lib/api/queries";
import type { components } from "@/lib/api/schema";

type Item = components["schemas"]["Item"];

// Mirrors ItemPatchIn (§6.5): HH:MM in the destination time zone, 15 to 480 whole minutes.
export const MIN_DURATION = 15;
export const MAX_DURATION = 480;
export const itemTimesSchema = z.object({
  start_time: z
    .string()
    .trim()
    .regex(/^([01]\d|2[0-3]):[0-5]\d$/, {
      error: "Enter a time as HH:MM, for example 09:30.",
    }),
  duration_min: z
    .string()
    .trim()
    .refine(
      (value) =>
        /^\d{1,3}$/.test(value) &&
        Number(value) >= MIN_DURATION &&
        Number(value) <= MAX_DURATION,
      {
        error: `Enter whole minutes from ${MIN_DURATION} to ${MAX_DURATION}.`,
      },
    ),
});
type Values = z.infer<typeof itemTimesSchema>;

const focusCard = (itemId: string) =>
  requestAnimationFrame(() =>
    document.getElementById(itemCardId(itemId))?.focus(),
  );

function ServerError({ error }: { error: unknown }) {
  const { what, next } = describeError(error);
  return (
    <p role="alert" className="text-sm font-medium text-destructive">
      {what}. {next}
    </p>
  );
}

export type ItemEditorProps = {
  tripId: string;
  planRevision: number;
  item: Item;
  dayNumber: number;
};

/**
 * ItemEditor (§7; FR-061, FR-063, IMP-408): Edit opens start time and duration fields inside the
 * card (API-26); Remove asks first, then calls API-27. The card shows what the server answers;
 * nothing is hidden or recalculated before it does.
 */
export function ItemEditor({
  tripId,
  planRevision,
  item,
  dayNumber,
}: ItemEditorProps) {
  const [editing, setEditing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const retime = useRetimeItem(tripId);
  const remove = useRemoveItem(tripId);
  const undo = useAddItem(tripId);
  const busy = useIsMutating({ mutationKey: editKey(tripId) }) > 0;
  const name = item.place.name;

  function confirmRemove() {
    // The next card takes focus once this one is gone.
    const row = document.getElementById(itemCardId(item.id))?.closest("li");
    const neighbour = (
      row?.nextElementSibling ?? row?.previousElementSibling
    )?.querySelector<HTMLElement>("[id^='item-']");
    remove.mutate(
      { itemId: item.id, planRevision },
      {
        onSuccess: (result) => {
          requestAnimationFrame(() => neighbour?.focus());
          toast.success(`Removed ${name}`, {
            action: EDIT_UNDO_ENABLED
              ? {
                  label: "Undo",
                  onClick: () =>
                    undo.mutate({
                      plan_revision: result.plan_revision,
                      day_number: dayNumber,
                      place_id: item.place.id,
                      start_time: item.start_time,
                    }),
                }
              : undefined,
          });
        },
        onError: (error) => {
          const { what, next } = describeError(error);
          toast.error(what, { description: next });
        },
      },
    );
  }

  return (
    <div aria-busy={retime.isPending || remove.isPending} className="mt-3">
      {editing ? (
        <EditForm
          item={item}
          saving={retime.isPending}
          error={retime.error}
          onCancel={() => {
            retime.reset();
            setEditing(false);
            focusCard(item.id);
          }}
          onSave={async (changes) => {
            if (Object.keys(changes).length > 0)
              await retime.mutateAsync({
                itemId: item.id,
                plan_revision: planRevision,
                ...changes,
              });
            setEditing(false);
            focusCard(item.id);
          }}
        />
      ) : (
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            className="min-h-touch"
            disabled={busy}
            aria-label={`Edit time of ${name}`}
            onClick={() => setEditing(true)}
          >
            Edit
          </Button>
          <Button
            variant="destructive"
            size="sm"
            className="min-h-touch"
            disabled={busy}
            aria-label={`Remove ${name}`}
            onClick={() => setConfirming(true)}
          >
            {remove.isPending ? "Removing…" : "Remove"}
          </Button>
        </div>
      )}
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title={`Remove ${name} from day ${dayNumber}?`}
        description="Times, costs and checks for the day are worked out again."
        confirmLabel="Remove"
        onConfirm={confirmRemove}
        destructive
      />
    </div>
  );
}

function EditForm({
  item,
  saving,
  error,
  onCancel,
  onSave,
}: {
  item: Item;
  saving: boolean;
  error: Error | null;
  onCancel: () => void;
  onSave: (changes: {
    start_time?: string;
    duration_min?: number;
  }) => Promise<void>;
}) {
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<Values>({
    resolver: zodResolver(itemTimesSchema),
    defaultValues: {
      start_time: item.start_time,
      duration_min: String(item.duration_min),
    },
  });
  const fieldId = (name: keyof Values) => `${name}-${item.id}`;

  async function submit(values: Values) {
    const duration = Number(values.duration_min);
    try {
      await onSave({
        ...(values.start_time !== item.start_time && {
          start_time: values.start_time,
        }),
        ...(duration !== item.duration_min && { duration_min: duration }),
      });
    } catch (caught) {
      if (!(caught instanceof ApiError)) return; // shown below from the mutation's error
      for (const { field, message } of caught.details) {
        if (field === "start_time" || field === "duration_min")
          setError(field, { message });
      }
    }
  }

  const fieldErrorShown =
    error instanceof ApiError &&
    error.details.some(
      ({ field }) => field === "start_time" || field === "duration_min",
    );

  return (
    <form
      noValidate
      aria-label={`Edit time of ${item.place.name}`}
      onSubmit={handleSubmit(submit)}
      className="flex flex-col gap-3"
    >
      <div className="grid gap-3 sm:grid-cols-2">
        <Field
          id={fieldId("start_time")}
          label="Start time"
          hint="HH:MM"
          error={errors.start_time?.message}
        >
          {(describedBy) => (
            <Input
              id={fieldId("start_time")}
              inputMode="numeric"
              autoComplete="off"
              className="min-h-touch"
              aria-describedby={describedBy}
              aria-invalid={errors.start_time ? true : undefined}
              {...register("start_time")}
            />
          )}
        </Field>
        <Field
          id={fieldId("duration_min")}
          label="Duration (minutes)"
          hint={`${MIN_DURATION} to ${MAX_DURATION}`}
          error={errors.duration_min?.message}
        >
          {(describedBy) => (
            <Input
              id={fieldId("duration_min")}
              inputMode="numeric"
              autoComplete="off"
              className="min-h-touch"
              aria-describedby={describedBy}
              aria-invalid={errors.duration_min ? true : undefined}
              {...register("duration_min")}
            />
          )}
        </Field>
      </div>
      {error && !fieldErrorShown && <ServerError error={error} />}
      <div className="flex flex-wrap gap-2">
        <Button
          type="submit"
          size="sm"
          className="min-h-touch"
          disabled={saving}
        >
          {saving ? "Saving…" : "Save"}
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="min-h-touch"
          disabled={saving}
          onClick={onCancel}
        >
          Cancel
        </Button>
      </div>
    </form>
  );
}
