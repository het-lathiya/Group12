"use client";

import { ChevronDown } from "lucide-react";
import { useId, useState } from "react";

import { Button } from "@/components/ui/button";
import type { components } from "@/lib/api/schema";
import { formatDayDate } from "@/lib/format";
import { cn } from "@/lib/utils";

type SourceRef = components["schemas"]["SourceRef"];

const KIND_LABELS: Record<SourceRef["kind"], string> = {
  guide: "Guide",
  place: "Place record",
};

function SourceEntry({ source }: { source: SourceRef }) {
  const { url, title, retrieved_on: retrievedOn } = source;
  // A1 §11: only https is ever a link; a prefix check also refuses javascript: and data: URLs.
  const href = url?.startsWith("https://") ? url : undefined;
  const meta = [
    KIND_LABELS[source.kind],
    source.source_name,
    source.attribution_text || source.licence,
    retrievedOn && `Retrieved ${formatDayDate(retrievedOn)}`,
  ];
  return (
    <li className="min-w-0 text-sm wrap-anywhere">
      {href ? (
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className="rounded-sm font-medium text-primary underline underline-offset-4 outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        >
          {title}
          <span className="sr-only"> (opens in a new tab)</span>
        </a>
      ) : (
        <p className="font-medium text-card-foreground">{title}</p>
      )}
      <p className="text-muted-foreground">
        {meta.filter(Boolean).join(" · ")}
      </p>
      {url && !href && <p className="text-muted-foreground">{url}</p>}
    </li>
  );
}

/**
 * The sources behind an AI-written note (A1 §7.1): a closed disclosure, then each source's title,
 * kind, source name, licence or attribution and retrieval date. Chunk IDs are never shown.
 */
export function ItemSources({ sources }: { sources: SourceRef[] }) {
  const [open, setOpen] = useState(false);
  const listId = useId();
  if (sources.length === 0) return null;
  return (
    <div className="mt-1">
      <Button
        type="button"
        variant="ghost"
        size="sm"
        aria-expanded={open}
        aria-controls={listId}
        onClick={() => setOpen(!open)}
        className="-ml-3 text-muted-foreground"
      >
        Sources ({sources.length})
        <ChevronDown aria-hidden="true" className={cn(open && "rotate-180")} />
      </Button>
      <ul id={listId} hidden={!open} className="mt-1 space-y-2">
        {sources.map((source) => (
          <SourceEntry key={source.chunk_id} source={source} />
        ))}
      </ul>
    </div>
  );
}
