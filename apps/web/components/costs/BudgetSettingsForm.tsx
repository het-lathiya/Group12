"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ErrorState } from "@/components/states/ErrorState";
import { LoadingSkeleton } from "@/components/states/LoadingSkeleton";
import { Field } from "@/components/trips/Field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api/client";
import { useCosts, useUpdateBudgetSettings } from "@/lib/api/queries";
import type { components } from "@/lib/api/schema";
import { isEnabled } from "@/lib/flags";

type CostSummary = components["schemas"]["CostSummaryOut"];

// Mirrors the server (§6.6.6 API-34, numeric(12,2)): empty means not set, else a decimal ≥ 0.
const ALLOWANCE = /^\d{1,10}(\.\d{1,2})?$/;
const allowance = z
  .string()
  .trim()
  .refine((value) => value === "" || ALLOWANCE.test(value), {
    error: "Enter 0 or more, with at most 2 decimal places.",
  });

// API-34 contingency_pct: a whole number from 0 to 50 (BF-08).
const contingency = z
  .string()
  .trim()
  .refine((value) => /^\d{1,2}$/.test(value) && Number(value) <= 50, {
    error: "Enter a whole number from 0 to 50.",
  });

export const budgetSettingsSchema = z.object({
  transport_allowance_per_day: allowance,
  stay_budget_per_night: allowance,
  contingency_pct: contingency.optional(),
});
type Values = z.infer<typeof budgetSettingsSchema>;

const FIELDS = [
  {
    name: "transport_allowance_per_day",
    label: "Transport per day",
    line: "transport",
  },
  {
    name: "stay_budget_per_night",
    label: "Stay per night",
    line: "accommodation",
  },
] as const;
const HINT = "Your own figure. Shown as Traveller input in costs.";
const NO_BUFFER = "No contingency buffer is included in this estimate.";

/**
 * BudgetSettingsForm (§7.5; FR-072, IMP-411): the traveller's own transport and stay figures,
 * and the contingency percentage (FR-075, IMP-608), saved with API-34. Each line shows what the
 * API returned; the browser computes no totals.
 */
export function BudgetSettingsForm({
  tripId,
  currency,
}: {
  tripId: string;
  /** The destination's currency (IMD-128). */
  currency: string;
}) {
  const costs = useCosts(tripId);
  if (costs.isPending) {
    return (
      <LoadingSkeleton shape="text" count={2} label="Loading budget inputs" />
    );
  }
  if (costs.isError) {
    return (
      <ErrorState
        title="Your budget inputs could not be loaded"
        error={costs.error as ApiError}
        onRetry={() => void costs.refetch()}
      />
    );
  }
  return <Form tripId={tripId} currency={currency} costs={costs.data} />;
}

function Form({
  tripId,
  currency,
  costs,
}: {
  tripId: string;
  currency: string;
  costs: CostSummary;
}) {
  const update = useUpdateBudgetSettings(tripId);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, dirtyFields },
  } = useForm<Values>({
    resolver: zodResolver(budgetSettingsSchema),
    defaultValues: {
      transport_allowance_per_day:
        costs.settings.transport_allowance_per_day ?? "",
      stay_budget_per_night: costs.settings.stay_budget_per_night ?? "",
      contingency_pct: String(costs.settings.contingency_pct),
    },
  });
  const shown = update.data ?? costs;
  const contingencyOn = isEnabled("contingency");

  async function submit(values: Values) {
    try {
      await update.mutateAsync({
        transport_allowance_per_day: values.transport_allowance_per_day || null,
        stay_budget_per_night: values.stay_budget_per_night || null,
        // Sent only when changed, so a save of the allowances never touches the buffer.
        ...(contingencyOn && dirtyFields.contingency_pct
          ? { contingency_pct: Number(values.contingency_pct) }
          : {}),
      });
    } catch (error) {
      if (!(error instanceof ApiError)) return; // shown below from update.error
      for (const { field, message } of error.details) {
        const known = FIELDS.find(({ name }) => field === name);
        if (known) setError(known.name, { message });
        if (field === "contingency_pct") setError(field, { message });
      }
    }
  }

  return (
    <form
      noValidate
      aria-label="Budget inputs"
      onSubmit={handleSubmit(submit)}
      className="flex flex-col gap-4"
    >
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        {FIELDS.map(({ name, label, line }) => {
          const costLine = shown.by_category.find(
            (row) => row.category === line,
          );
          return (
            <Field
              key={name}
              id={name}
              label={label}
              hint={HINT}
              error={errors[name]?.message}
            >
              {(describedBy) => (
                <>
                  <div className="flex min-w-0 items-stretch">
                    <span className="inline-flex items-center rounded-l-lg border border-r-0 border-input bg-muted px-3 text-sm text-muted-foreground">
                      {currency}
                    </span>
                    <Input
                      id={name}
                      inputMode="decimal"
                      autoComplete="off"
                      className="rounded-l-none"
                      aria-describedby={describedBy}
                      aria-invalid={errors[name] ? true : undefined}
                      {...register(name)}
                    />
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {costLine?.label === "traveller_input"
                      ? `In costs: ${shown.currency} ${costLine.max}, Traveller input`
                      : "In costs: Unavailable"}
                  </p>
                </>
              )}
            </Field>
          );
        })}
        {contingencyOn ? (
          <Field
            id="contingency_pct"
            label="Contingency buffer (%)"
            hint="From 0 to 50. Added to the high estimate as its own line."
            error={errors.contingency_pct?.message}
          >
            {(describedBy) => (
              <>
                <Input
                  id="contingency_pct"
                  inputMode="numeric"
                  autoComplete="off"
                  aria-describedby={describedBy}
                  aria-invalid={errors.contingency_pct ? true : undefined}
                  {...register("contingency_pct")}
                />
                <p className="text-sm text-muted-foreground">
                  {shown.contingency.pct > 0
                    ? `In costs: ${shown.currency} ${shown.contingency.amount}, Estimate`
                    : NO_BUFFER}
                </p>
              </>
            )}
          </Field>
        ) : (
          <p className="text-sm text-muted-foreground">{NO_BUFFER}</p>
        )}
      </div>
      {update.isError &&
        !(update.error instanceof ApiError && update.error.details.length) && (
          <ErrorState
            inline
            title="Your budget inputs could not be saved"
            error={
              update.error instanceof ApiError
                ? update.error
                : { message: "The server could not be reached. Try again." }
            }
          />
        )}
      <div>
        <Button type="submit" variant="outline" disabled={update.isPending}>
          {update.isPending ? "Saving…" : "Save budget inputs"}
        </Button>
      </div>
    </form>
  );
}
