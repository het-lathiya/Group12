"use client";

import { MapPin, Search } from "lucide-react";
import { useState, type KeyboardEvent } from "react";

import { LoadingSkeleton } from "@/components/states/LoadingSkeleton";
import { ImportProgress } from "@/components/trips/ImportProgress";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { CityCandidate, LiveDestination } from "@/lib/api/anyCityClient";
import { ApiError, OFFLINE_MESSAGE } from "@/lib/api/client";
import { useCitySearch, useResolveCity } from "@/lib/api/queries";
import { isEnabled } from "@/lib/flags";

export const LIVE_DATA_HINT =
  "Live data comes from OpenStreetMap and Wikivoyage. It is not checked by our team: opening hours and prices are unknown.";
export const SEARCH_ATTRIBUTION =
  "Search by Nominatim · © OpenStreetMap contributors";

const QUERY_MIN_CHARS = 2; // API-76 q, after trimming
const QUERY_MAX_CHARS = 100;

function countryName(code: string): string {
  try {
    return (
      new Intl.DisplayNames(["en"], { type: "region" }).of(
        code.toUpperCase(),
      ) ?? code
    );
  } catch {
    return code; // not a known region code: show the code itself
  }
}

/** "Udaipur, Rajasthan, India · city" */
export function candidateLabel(candidate: CityCandidate): string {
  const place = [
    candidate.name,
    candidate.region,
    countryName(candidate.country_code),
  ]
    .filter((part): part is string => Boolean(part))
    .join(", ");
  return `${place} · ${candidate.kind}`;
}

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : OFFLINE_MESSAGE;
}

/**
 * "Any city (live data)" (Amendment A2 §9.1): API-76 runs only when the traveller submits a term
 * (the button or Enter, never on each keystroke). Choosing a result resolves it (API-77) and shows
 * its import; a completed import is handed to the trip form. Renders nothing while the switch is OFF.
 */
export function CitySearch({
  onReady,
  onPickCurated,
}: {
  onReady: (live: LiveDestination) => void;
  /** A result that is already a curated destination is chosen in the list above instead. */
  onPickCurated?: (destinationId: string) => void;
}) {
  if (!isEnabled("any_city_mode")) return null;
  return <CitySearchField onReady={onReady} onPickCurated={onPickCurated} />;
}

function CitySearchField({
  onReady,
  onPickCurated,
}: {
  onReady: (live: LiveDestination) => void;
  onPickCurated?: (destinationId: string) => void;
}) {
  const [term, setTerm] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [tooShort, setTooShort] = useState(false);
  const [chosen, setChosen] = useState<LiveDestination | null>(null);
  const [lastRef, setLastRef] = useState<string | null>(null);
  const search = useCitySearch(submitted);
  const resolve = useResolveCity();

  function runSearch(value: string) {
    const q = value.trim();
    if (q.length < QUERY_MIN_CHARS) {
      setTooShort(true);
      return;
    }
    setTooShort(false);
    setChosen(null);
    resolve.reset();
    setSubmitted(q);
  }

  // The field sits inside the trip details form: Enter searches instead of submitting the trip.
  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      event.preventDefault();
      runSearch(term);
    }
  }

  function choose(candidate: CityCandidate) {
    if (
      candidate.data_tier === "curated" &&
      candidate.destination_id &&
      onPickCurated
    ) {
      onPickCurated(candidate.destination_id);
      return;
    }
    setLastRef(candidate.osm_ref);
    setChosen(null);
    resolve.mutate(candidate.osm_ref, { onSuccess: setChosen });
  }

  function searchNearby(city: string) {
    setTerm(city);
    runSearch(city);
  }

  const hintId = "city-search-hint";
  const errorId = "city-search-error";
  const results = search.data?.results;

  return (
    <div className="grid gap-3">
      <div className="flex flex-col gap-2">
        <Label htmlFor="city-search">Any city (live data)</Label>
        <div className="flex flex-col gap-2 sm:flex-row">
          <div className="relative min-w-0 flex-1">
            <MapPin
              aria-hidden="true"
              className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
            />
            <Input
              id="city-search"
              type="search"
              value={term}
              maxLength={QUERY_MAX_CHARS}
              autoComplete="off"
              onChange={(event) => setTerm(event.target.value)}
              onKeyDown={onKeyDown}
              aria-describedby={tooShort ? `${hintId} ${errorId}` : hintId}
              aria-invalid={tooShort ? true : undefined}
              className="pl-9"
            />
          </div>
          <Button
            type="button"
            variant="outline"
            onClick={() => runSearch(term)}
            className="min-h-touch"
          >
            <Search aria-hidden="true" />
            Search
          </Button>
        </div>
        <p id={hintId} className="text-sm text-muted-foreground">
          {LIVE_DATA_HINT}
        </p>
        <p
          id={errorId}
          aria-live="polite"
          className="text-sm font-medium text-destructive empty:hidden"
        >
          {tooShort ? `Enter at least ${QUERY_MIN_CHARS} characters.` : null}
        </p>
      </div>

      {submitted !== "" && search.isPending && (
        <LoadingSkeleton count={2} label="Searching cities" />
      )}
      {submitted !== "" && search.isError && (
        <p role="alert" className="text-sm font-medium text-destructive">
          {errorMessage(search.error)}
        </p>
      )}
      {results && results.length === 0 && (
        <p role="status" className="text-sm text-muted-foreground">
          No city, town or village matches your search.
        </p>
      )}
      {results && results.length > 0 && (
        <div className="grid gap-2">
          <ul
            aria-label="City search results"
            className="divide-y divide-border rounded-lg border bg-background"
          >
            {results.map((candidate) => (
              <li key={candidate.osm_ref}>
                <button
                  type="button"
                  onClick={() => choose(candidate)}
                  disabled={resolve.isPending}
                  aria-pressed={
                    lastRef === candidate.osm_ref ? true : undefined
                  }
                  className="flex min-h-touch w-full items-center px-4 py-2 text-left text-sm font-medium break-words transition-colors outline-none hover:bg-muted focus-visible:bg-muted focus-visible:ring-3 focus-visible:ring-ring disabled:cursor-not-allowed disabled:text-muted-foreground disabled:hover:bg-transparent"
                >
                  {candidateLabel(candidate)}
                </button>
              </li>
            ))}
          </ul>
          <p className="text-xs text-muted-foreground">{SEARCH_ATTRIBUTION}</p>
        </div>
      )}

      {resolve.isPending && (
        <p role="status" className="text-sm text-muted-foreground">
          Checking this place…
        </p>
      )}
      {resolve.isError && (
        <p role="alert" className="text-sm font-medium text-destructive">
          {errorMessage(resolve.error)}
        </p>
      )}
      {chosen && (
        <ImportProgress
          key={chosen.destination_id}
          live={chosen}
          onReady={onReady}
          onSearchNearby={searchNearby}
          onRetry={
            lastRef
              ? () => resolve.mutate(lastRef, { onSuccess: setChosen })
              : undefined
          }
        />
      )}
    </div>
  );
}
