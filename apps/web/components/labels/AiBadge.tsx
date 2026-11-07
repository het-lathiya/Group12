import { Sparkles } from "lucide-react";

/** Marks text the model wrote (§7.8; guide §12). */
export function AiBadge() {
  return (
    <span className="inline-flex h-6 shrink-0 items-center gap-1 rounded-full bg-ai-soft px-2 text-xs font-medium text-ai">
      <Sparkles aria-hidden="true" className="size-3" />
      AI-written
    </span>
  );
}
