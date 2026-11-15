"use client";

import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ChipMultiSelect } from "@/components/trips/ChipMultiSelect";
import type { PlaceSearchQuery } from "@/lib/api/queries";
import type { components } from "@/lib/api/schema";

type Schemas = components["schemas"];
type OfferedCategory = Exclude<Schemas["Category"], "stay">;
type InterestTag = Exclude<
  Schemas["Tag"],
  "child_half" | "child_free" | "price_per_group"
>;

/** API-16 filters as the URL query string holds them (IMP-604; names as the API takes them). */
export type PlaceFilters = {
  q: string;
  category: OfferedCategory[];
  interest: InterestTag[];
  price_max: string;
  duration_max_min: string;
  step_free: boolean;
};

export const NO_FILTERS: PlaceFilters = {
  q: "",
  category: [],
  interest: [],
  price_max: "",
  duration_max_min: "",
  step_free: false,
};

const CATEGORY_LABELS: Record<OfferedCategory, string> = {
  sight: "Sight",
  museum: "Museum",
  nature: "Nature",
  food: "Food",
  shopping: "Shopping",
  entertainment: "Entertainment",
  religious: "Religious site",
  activity: "Activity",
};

// Pricing tags (child_half, ...) are budget rules, not interests, so they are not offered.
const INTEREST_TAGS: InterestTag[] = [
  "architecture",
  "art",
  "books",
  "breakfast",
  "cafe",
  "crafts",
  "cycling",
  "dinner",
  "evening",
  "family",
  "games",
  "garden",
  "history",
  "indoor",
  "late",
  "local",
  "lunch",
  "maritime",
  "market",
  "music",
  "outdoor",
  "quiet",
  "seafood",
  "sport",
  "street-food",
  "tea",
  "theatre",
  "vegetarian",
  "views",
  "walking",
  "water",
  "wildlife",
];
const INTEREST_LABELS = Object.fromEntries(
  INTEREST_TAGS.map((tag) => [tag, tag.replaceAll("-", " ")]),
) as Record<InterestTag, string>;

const DURATIONS = ["30", "60", "90", "120", "180", "240"];
const MONEY = /^\d{1,10}(\.\d{1,2})?$/;
const CONTROL =
  "min-h-touch w-full rounded-lg border border-input bg-background px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring focus-visible:ring-offset-2";

const known = <T extends string>(values: string[], allowed: readonly T[]) =>
  values.filter((v): v is T => (allowed as readonly string[]).includes(v));

/** The filters a URL holds; values the API would refuse are dropped, never sent. */
export function filtersFromParams(params: URLSearchParams): PlaceFilters {
  const price = params.get("price_max") ?? "";
  const duration = params.get("duration_max_min") ?? "";
  return {
    q: (params.get("q") ?? "").slice(0, 80),
    category: known(
      params.getAll("category"),
      Object.keys(CATEGORY_LABELS) as OfferedCategory[],
    ),
    interest: known(params.getAll("interest"), INTEREST_TAGS),
    price_max: MONEY.test(price) ? price : "",
    duration_max_min: DURATIONS.includes(duration) ? duration : "",
    step_free: params.get("step_free") === "true",
  };
}

/** The query string of the filters that are set (also what API-16 is sent). */
export function filtersToParams(filters: PlaceFilters): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.q.trim()) params.set("q", filters.q.trim());
  filters.category.forEach((c) => params.append("category", c));
  filters.interest.forEach((t) => params.append("interest", t));
  if (filters.price_max) params.set("price_max", filters.price_max);
  if (filters.duration_max_min) {
    params.set("duration_max_min", filters.duration_max_min);
  }
  if (filters.step_free) params.set("step_free", "true");
  return params;
}

/** The API-16 query of the filters that are set. */
export function filtersToQuery(filters: PlaceFilters): PlaceSearchQuery {
  return {
    q: filters.q.trim() || undefined,
    category: filters.category.length ? filters.category : undefined,
    interest: filters.interest.length ? filters.interest : undefined,
    price_max: filters.price_max || undefined,
    duration_max_min: filters.duration_max_min
      ? Number(filters.duration_max_min)
      : undefined,
    step_free: filters.step_free || undefined,
  };
}

/** The names of the filters that are set, for the "relax these filters" hint (FR-017 AC2). */
export function activeFilterNames(filters: PlaceFilters): string[] {
  return [
    filters.q.trim() && "search text",
    filters.category.length > 0 && "category",
    filters.interest.length > 0 && "interests",
    filters.price_max && "maximum price",
    filters.duration_max_min && "maximum duration",
    filters.step_free && "step-free only",
  ].filter((name): name is string => Boolean(name));
}

export type PlaceFilterBarProps = {
  value: PlaceFilters;
  onChange: (filters: PlaceFilters) => void;
  /** The destination's currency; the maximum price is in it. */
  currency: string;
};

/**
 * Explore filters (§7.5.5; FR-017, IMP-604): search text, category, interests, maximum price and
 * duration, step-free. The page keeps the applied filters in the URL query string, so they survive
 * a reload. Every control is a native input, a select or an aria-pressed chip, operable by keyboard;
 * Apply (or Enter) sends the draft, Clear removes every filter.
 */
export function PlaceFilterBar({
  value,
  onChange,
  currency,
}: PlaceFilterBarProps) {
  const [draft, setDraft] = useState(value);
  const [priceError, setPriceError] = useState(false);
  const set = (changes: Partial<PlaceFilters>) =>
    setDraft((current) => ({ ...current, ...changes }));

  function apply(event: FormEvent) {
    event.preventDefault();
    const price = draft.price_max.trim();
    if (price && !MONEY.test(price)) {
      setPriceError(true);
      return;
    }
    setPriceError(false);
    onChange({ ...draft, price_max: price });
  }

  function clear() {
    setDraft(NO_FILTERS);
    setPriceError(false);
    onChange(NO_FILTERS);
  }

  return (
    <form
      role="search"
      aria-label="Filter places"
      onSubmit={apply}
      className="flex flex-col gap-4 rounded-xl border bg-card p-4 text-card-foreground shadow-xs"
    >
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="flex flex-col gap-2 sm:col-span-2">
          <label htmlFor="filter-q" className="text-sm font-medium">
            Search by name or tag
          </label>
          <Input
            id="filter-q"
            type="search"
            maxLength={80}
            value={draft.q}
            onChange={(e) => set({ q: e.target.value })}
          />
        </div>
        <div className="flex flex-col gap-2">
          <label htmlFor="filter-price" className="text-sm font-medium">
            Maximum price ({currency})
          </label>
          <Input
            id="filter-price"
            inputMode="decimal"
            value={draft.price_max}
            aria-invalid={priceError || undefined}
            aria-describedby={priceError ? "filter-price-error" : undefined}
            onChange={(e) => set({ price_max: e.target.value })}
          />
          {priceError && (
            <p id="filter-price-error" className="text-sm text-destructive">
              Enter an amount such as 10 or 7.50.
            </p>
          )}
        </div>
        <div className="flex flex-col gap-2">
          <label htmlFor="filter-duration" className="text-sm font-medium">
            Maximum duration
          </label>
          <select
            id="filter-duration"
            className={CONTROL}
            value={draft.duration_max_min}
            onChange={(e) => set({ duration_max_min: e.target.value })}
          >
            <option value="">Any length</option>
            {DURATIONS.map((minutes) => (
              <option key={minutes} value={minutes}>
                Up to{" "}
                {Number(minutes) < 60
                  ? `${minutes} min`
                  : `${Number(minutes) / 60} h`}
              </option>
            ))}
          </select>
        </div>
      </div>
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 text-sm font-medium">Category</legend>
        <ChipMultiSelect
          labels={CATEGORY_LABELS}
          value={draft.category}
          onChange={(category) => set({ category })}
        />
      </fieldset>
      <details className="group" open={value.interest.length > 0}>
        <summary className="min-h-touch cursor-pointer content-center text-sm font-medium">
          Interests
          {draft.interest.length > 0 ? ` (${draft.interest.length})` : ""}
        </summary>
        <fieldset className="mt-2">
          <legend className="sr-only">Interests</legend>
          <ChipMultiSelect
            labels={INTEREST_LABELS}
            value={draft.interest}
            onChange={(interest) => set({ interest })}
          />
        </fieldset>
      </details>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-h-touch items-center gap-3">
          <input
            id="filter-step-free"
            type="checkbox"
            className="size-5 accent-primary"
            checked={draft.step_free}
            onChange={(e) => set({ step_free: e.target.checked })}
          />
          <label htmlFor="filter-step-free" className="text-sm">
            Step-free only (places confirmed step-free)
          </label>
        </div>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="outline"
            className="min-h-touch"
            onClick={clear}
          >
            Clear filters
          </Button>
          <Button type="submit" className="min-h-touch">
            Apply filters
          </Button>
        </div>
      </div>
    </form>
  );
}
