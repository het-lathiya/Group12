import type { components } from "@/lib/api/schema";

type Item = components["schemas"]["Item"];

function focusItem(itemId: string) {
  const target = document.getElementById(`item-${itemId}`);
  target?.scrollIntoView({ behavior: "smooth", block: "center" });
  target?.focus();
}

/** Ordered, accessible alternative when MapLibre, WebGL or map tiles are unavailable. */
export function MapListFallback({
  items,
  reason = "Map unavailable; list view shown",
}: {
  items: Item[];
  reason?: string;
}) {
  return (
    <section aria-label="Map list fallback" className="rounded-xl border bg-card p-4">
      <p role="status" className="text-sm text-muted-foreground">{reason}</p>
      <ol className="mt-3 flex flex-col gap-2">
        {items.map((item, index) => (
          <li key={item.id}>
            <button
              type="button"
              onClick={() => focusItem(item.id)}
              className="flex min-h-11 w-full items-center gap-3 rounded-lg px-2 text-left text-sm hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <span aria-hidden="true" className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground font-semibold tabular-nums">
                {index + 1}
              </span>
              <span className="min-w-0 font-medium">{item.place.name}</span>
              <span className="ml-auto shrink-0 text-muted-foreground tabular-nums">{item.start_time}</span>
            </button>
          </li>
        ))}
      </ol>
    </section>
  );
}
