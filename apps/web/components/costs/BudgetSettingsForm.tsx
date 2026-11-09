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

type CostSummary = components["schemas"]["CostSummaryOut"];

// Mirrors the server (§6.6.6 API-34, numeric(12,2)): empty means not set, else a decimal ≥ 0.
const ALLOWANCE = /^\d{1,10}(\.\d{1,2})?$/;
const allowance = z
  .string()
  .trim()
  .refine((value) => value === "" || ALLOWANCE.test(value), {
    error: "Enter 0 or more, with at most 2 decimal places.",
  });

export const budgetSettingsSchema = z.object({
  transport_allowance_per_day: allowance,
  stay_budget_per_night: allowance,
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

/**
 * BudgetSettingsForm (§7.5; FR-072, IMP-411): the traveller's own transport and stay figures,
 * saved with API-34. Each line shows what the API returned; the browser computes no totals.
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
    formState: { errors },
  } = useForm<Values>({
    resolver: zodResolver(budgetSettingsSchema),
    defaultValues: {
      transport_allowance_per_day:
        costs.settings.transport_allowance_per_day ?? "",
      stay_budget_per_night: costs.settings.stay_budget_per_night ?? "",
    },
  });
  const shown = update.data ?? costs;

  async function submit(values: Values) {
    try {
      await update.mutateAsync({
        transport_allowance_per_day: values.transport_allowance_per_day || null,
        stay_budget_per_night: values.stay_budget_per_night || null,
      });
    } catch (error) {
      if (!(error instanceof ApiError)) return; // shown below from update.error
      for (const { field, message } of error.details) {
        const known = FIELDS.find(({ name }) => field === name);
        if (known) setError(known.name, { message });
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
      </div>
      {update.isError &&
        !(update.error instanceof ApiError && update.error.details.length) && (
          <ErrorState
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
