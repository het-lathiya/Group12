"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useState } from "react";
import { Controller, useForm, useWatch } from "react-hook-form";

import { ErrorState } from "@/components/states/ErrorState";
import { LoadingSkeleton } from "@/components/states/LoadingSkeleton";
import { ChipMultiSelect } from "@/components/trips/ChipMultiSelect";
import { CitySearch } from "@/components/trips/CitySearch";
import { CONTROL_CLASS, Field, FieldSet } from "@/components/trips/Field";
import { Input } from "@/components/ui/input";
import type { LiveDestination } from "@/lib/api/anyCityClient";
import type { ErrorDetail } from "@/lib/api/client";
import { useDestinationDetail, useDestinations } from "@/lib/api/queries";
import { isEnabled } from "@/lib/flags";
import {
  ADULTS_MAX,
  ADULTS_MIN,
  CHILDREN_MAX,
  CHILDREN_MIN,
  fieldErrors,
  GROUP_NEED_LABELS,
  MAX_TRIP_DAYS,
  TITLE_MAX_CHARS,
  tripDetailsSchema,
  type TripDetailsValues,
} from "@/lib/validation/trip";

const FIELDS = [
  "destination_id",
  "title",
  "start_date",
  "end_date",
  "adults",
  "children",
  "group_needs",
  "budget.amount",
  "budget.currency",
] as const;

const DEFAULTS: TripDetailsValues = {
  destination_id: "",
  title: "",
  start_date: "",
  end_date: "",
  adults: 1,
  children: 0,
  group_needs: [],
  budget: { amount: "", currency: "" },
};

/**
 * Step 1: destination (API-06), title, dates, travellers, group needs and the group budget. Once
 * the trip is created the fields are read-only: changing a saved trip needs API-11 (IMP-410).
 */
export function TripDetailsStep({
  formId,
  locked,
  initial,
  onSave,
}: {
  formId: string;
  locked: boolean;
  /** A saved draft's values, so a resumed draft shows what was entered (FR-013 AC2). */
  initial?: TripDetailsValues;
  onSave: (values: TripDetailsValues) => Promise<ErrorDetail[]>;
}) {
  const destinations = useDestinations();
  const {
    register,
    control,
    handleSubmit,
    setError,
    setValue,
    formState: { errors },
  } = useForm<TripDetailsValues>({
    resolver: zodResolver(tripDetailsSchema),
    defaultValues: initial ?? DEFAULTS,
  });

  // A live destination whose import completed (Amendment A2 §9.1; switch ON only).
  const [live, setLive] = useState<LiveDestination | null>(null);
  useEffect(() => {
    if (live) {
      setValue("destination_id", live.destination_id, {
        shouldValidate: true,
      });
    }
  }, [live, setValue]);

  // A resumed draft whose destination is live: API-06 lists curated destinations only, so the
  // select reads it from API-79 (switch ON only; no request when the id is curated or empty).
  const draftId = initial?.destination_id ?? "";
  const draftNeedsDetail =
    isEnabled("any_city_mode") &&
    draftId !== "" &&
    destinations.isSuccess &&
    !destinations.data.some((item) => item.id === draftId);
  const draftDetail = useDestinationDetail(draftNeedsDetail ? draftId : "");
  const draftLive =
    draftNeedsDetail && draftDetail.data?.id === draftId
      ? draftDetail.data
      : undefined;
  const draftLiveId = draftLive?.id;
  useEffect(() => {
    // The option appears after the form registered the select, so select it again.
    if (draftLiveId) {
      setValue("destination_id", draftLiveId);
    }
  }, [draftLiveId, setValue]);

  // §9.3.2: the budget is in the destination's currency, which API-06 reports (a live one's from
  // API-77/78/79, IMD-128).
  const destinationId = useWatch({ control, name: "destination_id" });
  const destination = destinations.data?.find(
    (item) => item.id === destinationId,
  );
  const liveChosen =
    live !== null && live.destination_id === destinationId ? live : undefined;
  const draftChosen =
    draftLive !== undefined && draftLive.id === destinationId
      ? draftLive
      : undefined;
  const currency =
    destination?.currency ?? liveChosen?.currency ?? draftChosen?.currency;
  useEffect(() => {
    setValue("budget.currency", currency ?? "");
  }, [currency, setValue]);

  async function submit(values: TripDetailsValues) {
    for (const { field, message } of fieldErrors(
      await onSave(values),
      FIELDS,
    )) {
      setError(field, { message });
    }
  }

  return (
    <form
      id={formId}
      noValidate
      onSubmit={handleSubmit(submit)}
      aria-label="Trip details"
    >
      {errors.root && (
        <p role="alert" className="mb-6 text-sm font-medium text-destructive">
          {errors.root.message}
        </p>
      )}
      {locked && (
        <p className="mb-6 text-sm text-muted-foreground">
          These details are saved with your trip and cannot be changed here.
        </p>
      )}
      <fieldset disabled={locked} className="grid gap-6 md:grid-cols-2">
        <Field
          id="destination"
          label="Destination"
          error={errors.destination_id?.message}
          hint={
            destination?.is_sample
              ? "SAMPLE destination: its places and prices are synthetic test data."
              : undefined
          }
          className="md:col-span-2"
        >
          {(describedBy) =>
            destinations.isPending ? (
              <LoadingSkeleton
                shape="text"
                count={1}
                label="Loading destinations"
              />
            ) : destinations.isError ? (
              <ErrorState
                title="Destinations could not be loaded"
                error={destinations.error}
                onRetry={() => void destinations.refetch()}
              />
            ) : (
              <select
                id="destination"
                className={CONTROL_CLASS}
                aria-describedby={describedBy}
                aria-invalid={errors.destination_id ? true : undefined}
                {...register("destination_id")}
              >
                <option value="">Choose a destination</option>
                {destinations.data.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
                {draftLive && live?.destination_id !== draftLive.id && (
                  <option value={draftLive.id}>
                    {draftLive.name} (Live data)
                  </option>
                )}
                {live && (
                  <option value={live.destination_id}>
                    {live.name} (Live data)
                  </option>
                )}
              </select>
            )
          }
        </Field>

        {isEnabled("any_city_mode") && (
          <div className="md:col-span-2">
            <CitySearch
              onReady={setLive}
              onPickCurated={(id) =>
                setValue("destination_id", id, { shouldValidate: true })
              }
            />
          </div>
        )}

        <Field
          id="trip-title"
          label="Trip title"
          hint={`1 to ${TITLE_MAX_CHARS} characters.`}
          error={errors.title?.message}
          className="md:col-span-2"
        >
          {(describedBy) => (
            <Input
              id="trip-title"
              autoComplete="off"
              aria-describedby={describedBy}
              aria-invalid={errors.title ? true : undefined}
              {...register("title")}
            />
          )}
        </Field>

        <Field
          id="start-date"
          label="Start date"
          error={errors.start_date?.message}
        >
          {(describedBy) => (
            <Input
              id="start-date"
              type="date"
              aria-describedby={describedBy}
              aria-invalid={errors.start_date ? true : undefined}
              {...register("start_date")}
            />
          )}
        </Field>

        <Field
          id="end-date"
          label="End date"
          hint={`Trips can be 1 to ${MAX_TRIP_DAYS} days long.`}
          error={errors.end_date?.message}
        >
          {(describedBy) => (
            <Input
              id="end-date"
              type="date"
              aria-describedby={describedBy}
              aria-invalid={errors.end_date ? true : undefined}
              {...register("end_date")}
            />
          )}
        </Field>

        <Field
          id="adults"
          label="Adults"
          hint={`${ADULTS_MIN} to ${ADULTS_MAX}.`}
          error={errors.adults?.message}
        >
          {(describedBy) => (
            <Input
              id="adults"
              type="number"
              inputMode="numeric"
              min={ADULTS_MIN}
              max={ADULTS_MAX}
              aria-describedby={describedBy}
              aria-invalid={errors.adults ? true : undefined}
              {...register("adults", { valueAsNumber: true })}
            />
          )}
        </Field>

        <Field
          id="children"
          label="Children"
          hint={`${CHILDREN_MIN} to ${CHILDREN_MAX}.`}
          error={errors.children?.message}
        >
          {(describedBy) => (
            <Input
              id="children"
              type="number"
              inputMode="numeric"
              min={CHILDREN_MIN}
              max={CHILDREN_MAX}
              aria-describedby={describedBy}
              aria-invalid={errors.children ? true : undefined}
              {...register("children", { valueAsNumber: true })}
            />
          )}
        </Field>

        <FieldSet
          id="group-needs"
          legend="Group needs"
          hint="Select any that apply to your group."
          error={errors.group_needs?.message}
          className="md:col-span-2"
        >
          <Controller
            control={control}
            name="group_needs"
            render={({ field }) => (
              <ChipMultiSelect
                labels={GROUP_NEED_LABELS}
                value={field.value}
                onChange={field.onChange}
              />
            )}
          />
        </FieldSet>

        <Field
          id="budget-amount"
          label="Budget (optional)"
          hint="Total for the whole group. Leave empty for no budget."
          error={errors.budget?.amount?.message}
        >
          {(describedBy) => (
            <Input
              id="budget-amount"
              inputMode="decimal"
              autoComplete="off"
              aria-describedby={describedBy}
              aria-invalid={errors.budget?.amount ? true : undefined}
              {...register("budget.amount")}
            />
          )}
        </Field>

        <Field
          id="budget-currency"
          label="Currency"
          hint="The currency of the destination."
          error={errors.budget?.currency?.message}
        >
          {(describedBy) => (
            <select
              id="budget-currency"
              className={CONTROL_CLASS}
              aria-describedby={describedBy}
              aria-invalid={errors.budget?.currency ? true : undefined}
              {...register("budget.currency")}
            >
              {currency ? (
                <option value={currency}>{currency}</option>
              ) : (
                <option value="">Choose a destination first</option>
              )}
            </select>
          )}
        </Field>
      </fieldset>
    </form>
  );
}
