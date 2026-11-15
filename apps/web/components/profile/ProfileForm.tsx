"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";

import { ChipMultiSelect } from "@/components/trips/ChipMultiSelect";
import { CONTROL_CLASS, Field, FieldSet } from "@/components/trips/Field";
import { SegmentedChoice } from "@/components/trips/SegmentedChoice";
import { Button } from "@/components/ui/button";
import type { ErrorDetail } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import {
  ACCOMMODATION_LABELS,
  BUDGET_PRIORITY_LABELS,
  fieldErrors,
  INTEREST_LABELS,
  PACE_LABELS,
  preferencesSchema,
  TRANSPORT_LABELS,
} from "@/lib/validation/trip";

type Schemas = components["schemas"];

export const DISPLAY_NAME_MAX = 60; // FR-004

/** The API-04 rules (auth/service.py): name 1 to 60, ISO 4217 currency, ISO 3166-1 country. */
export const profileSchema = preferencesSchema.omit({ notes: true }).extend({
  display_name: z
    .string()
    .trim()
    .max(DISPLAY_NAME_MAX, {
      error: `Enter a display name of 1 to ${DISPLAY_NAME_MAX} characters.`,
    }),
  preferred_currency: z
    .string()
    .trim()
    .toUpperCase()
    .regex(/^([A-Z]{3})?$/, {
      error: "Enter a three-letter ISO 4217 code, such as INR.",
    }),
  home_country: z
    .string()
    .trim()
    .toUpperCase()
    .regex(/^([A-Z]{2})?$/, {
      error: "Enter a two-letter ISO 3166-1 country code, such as IN.",
    }),
});

export type ProfileValues = z.infer<typeof profileSchema>;

const PREFERENCE_KEYS = [
  "interests",
  "pace",
  "budget_priority",
  "transport_pref",
  "accommodation_type",
  "step_free_required",
] as const;
const FIELDS = [
  "display_name",
  "preferred_currency",
  "home_country",
  ...PREFERENCE_KEYS,
] as const;

/** Form values from API-03; default preferences not saved yet show the trip defaults. */
function valuesOf(profile: Schemas["Profile"]): ProfileValues {
  const saved = preferencesSchema
    .omit({ notes: true })
    .partial()
    .safeParse(profile.default_preferences);
  return {
    display_name: profile.display_name ?? "",
    preferred_currency: profile.preferred_currency ?? "",
    home_country: profile.home_country ?? "",
    interests: [],
    pace: "balanced",
    budget_priority: "balanced",
    transport_pref: "walking",
    accommodation_type: "any",
    step_free_required: false,
    ...(saved.success ? saved.data : {}),
  };
}

/** The API-04 body: an empty text field clears it. */
export function toProfilePatch(values: ProfileValues): Schemas["ProfilePatch"] {
  const { display_name, preferred_currency, home_country, ...defaults } =
    values;
  return {
    display_name: display_name || null,
    preferred_currency: preferred_currency || null,
    home_country: home_country || null,
    default_preferences: defaults,
  };
}

/**
 * The profile (§7.5, FR-004): display name, home currency and country, and the default travel
 * preferences that prefill each new trip (IMD-16). Field errors from API-04 are shown on their field.
 */
export function ProfileForm({
  profile,
  onSave,
}: {
  profile: Schemas["Profile"];
  onSave: (body: Schemas["ProfilePatch"]) => Promise<ErrorDetail[]>;
}) {
  const {
    register,
    control,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(profileSchema),
    defaultValues: valuesOf(profile),
  });

  async function submit(values: ProfileValues) {
    const details = (await onSave(toProfilePatch(values))).map((detail) => ({
      ...detail,
      field: detail.field.replace(/^default_preferences\./, ""),
    }));
    for (const { field, message } of fieldErrors(details, FIELDS)) {
      setError(field, { message });
    }
  }

  return (
    <form
      noValidate
      onSubmit={handleSubmit(submit)}
      aria-label="Profile"
      className="grid gap-8"
    >
      {errors.root && (
        <p role="alert" className="text-sm font-medium text-destructive">
          {errors.root.message}
        </p>
      )}
      <Field
        id="display-name"
        label="Display name"
        hint={`Up to ${DISPLAY_NAME_MAX} characters.`}
        error={errors.display_name?.message}
      >
        {(describedBy) => (
          <input
            id="display-name"
            className={CONTROL_CLASS}
            autoComplete="nickname"
            aria-describedby={describedBy}
            aria-invalid={errors.display_name ? true : undefined}
            {...register("display_name")}
          />
        )}
      </Field>
      <div className="grid gap-8 sm:grid-cols-2">
        <Field
          id="preferred-currency"
          label="Home currency"
          hint="A three-letter code, such as INR."
          error={errors.preferred_currency?.message}
        >
          {(describedBy) => (
            <input
              id="preferred-currency"
              className={`${CONTROL_CLASS} uppercase`}
              maxLength={3}
              aria-describedby={describedBy}
              aria-invalid={errors.preferred_currency ? true : undefined}
              {...register("preferred_currency")}
            />
          )}
        </Field>
        <Field
          id="home-country"
          label="Home country"
          hint="A two-letter code, such as IN."
          error={errors.home_country?.message}
        >
          {(describedBy) => (
            <input
              id="home-country"
              className={`${CONTROL_CLASS} uppercase`}
              maxLength={2}
              autoComplete="country"
              aria-describedby={describedBy}
              aria-invalid={errors.home_country ? true : undefined}
              {...register("home_country")}
            />
          )}
        </Field>
      </div>

      <section aria-labelledby="defaults-heading" className="grid gap-8">
        <div>
          <h2 id="defaults-heading" className="text-xl font-semibold">
            Default travel preferences
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            New trips start with these. You can change them for each trip.
          </p>
        </div>
        <FieldSet
          id="interests"
          legend="Interests"
          error={errors.interests?.message}
        >
          <Controller
            control={control}
            name="interests"
            render={({ field }) => (
              <ChipMultiSelect
                labels={INTEREST_LABELS}
                value={field.value}
                onChange={field.onChange}
              />
            )}
          />
        </FieldSet>
        <FieldSet id="pace" legend="Pace" error={errors.pace?.message}>
          <Controller
            control={control}
            name="pace"
            render={({ field }) => (
              <SegmentedChoice
                name="pace"
                labels={PACE_LABELS}
                value={field.value}
                onChange={field.onChange}
              />
            )}
          />
        </FieldSet>
        <FieldSet
          id="budget-priority"
          legend="Budget priority"
          error={errors.budget_priority?.message}
        >
          <Controller
            control={control}
            name="budget_priority"
            render={({ field }) => (
              <SegmentedChoice
                name="budget_priority"
                labels={BUDGET_PRIORITY_LABELS}
                value={field.value}
                onChange={field.onChange}
              />
            )}
          />
        </FieldSet>
        <FieldSet
          id="transport"
          legend="Getting around"
          error={errors.transport_pref?.message}
        >
          <Controller
            control={control}
            name="transport_pref"
            render={({ field }) => (
              <SegmentedChoice
                name="transport_pref"
                labels={TRANSPORT_LABELS}
                value={field.value}
                onChange={field.onChange}
              />
            )}
          />
        </FieldSet>
        <Field
          id="accommodation-type"
          label="Accommodation type"
          error={errors.accommodation_type?.message}
        >
          {(describedBy) => (
            <select
              id="accommodation-type"
              className={CONTROL_CLASS}
              aria-describedby={describedBy}
              {...register("accommodation_type")}
            >
              {Object.entries(ACCOMMODATION_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          )}
        </Field>
        <div className="flex min-h-touch items-center gap-3">
          <input
            id="step-free"
            type="checkbox"
            className="size-5 accent-primary"
            {...register("step_free_required")}
          />
          <label
            htmlFor="step-free"
            className="flex-1 cursor-pointer py-3 text-sm font-medium"
          >
            I need step-free access
          </label>
        </div>
      </section>

      <div>
        <Button
          type="submit"
          disabled={isSubmitting}
          aria-busy={isSubmitting}
          className="w-full sm:w-auto"
        >
          {isSubmitting && (
            <Loader2 aria-hidden="true" className="size-4 animate-spin" />
          )}
          Save profile
        </Button>
      </div>
    </form>
  );
}
