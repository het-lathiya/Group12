import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import GeneratePage from "@/app/(app)/trips/[tripId]/generate/page";
import {
  FALLBACK_TEXT,
  FallbackNotice,
  PausedAiNotice,
} from "@/components/generation/FallbackNotice";
import { GenerationProgress } from "@/components/generation/GenerationProgress";
import { ERROR_CATALOGUE } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";

// IMP-403 (FR-037, UI side): the labelled rule-based plan, the paused-AI option on provider quota,
// and the ErrorState of a failed generation, each from API-23's outcome and failure_reason.
vi.mock("@/lib/auth/supabase", () => ({
  getSupabase: () => ({
    auth: {
      getSession: async () => ({ data: { session: { access_token: "t" } } }),
    },
  }),
}));
vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test/api/v1");

const TRIP_ID = "00000000-0000-4000-8000-000000000002";
const GEN_ID = "00000000-0000-4000-8000-0000000000a1";
const NEXT_ID = "00000000-0000-4000-8000-0000000000b2";

const router = { push: vi.fn(), replace: vi.fn() };
vi.mock("next/navigation", () => ({
  useParams: () => ({ tripId: TRIP_ID }),
  useRouter: () => router,
  useSearchParams: () => new URLSearchParams(`generation=${GEN_ID}`),
}));

type Generation = components["schemas"]["GenerationOut"];

function failed(
  failure_reason: Generation["failure_reason"],
  failure_message: string,
  next_action: Generation["next_action"],
): Generation {
  return {
    id: GEN_ID,
    trip_id: TRIP_ID,
    status: "failed",
    mode: "ai",
    scope: "full",
    day_number: null,
    outcome: "failed",
    failure_reason,
    failure_message,
    next_action,
    fallback_reason: null,
    provider: "MOCK",
    model_id: "mock-1",
    prompt_version: "1",
    embedding_model_id: null,
    retrieval_mode: null,
    retrieval_ms: null,
    repair_attempts: 0,
    deterministic_repairs: 0,
    validation_summary: { errors: 0, warnings: 0, infos: 0 },
    latency_ms: null,
    itinerary_version_id: null,
    plan_revision: null,
    created_at: "2026-11-04T10:00:00Z",
    completed_at: "2026-11-04T10:00:05Z",
  };
}

const QUOTA = failed(
  "provider_quota_exhausted",
  "AI generation is paused for today.",
  "retry_rule_based",
);

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

/** API-23 answers `generation`; API-22 records its body and answers a new queued generation. */
function fakeApi(generation: Generation) {
  const posts: unknown[] = [];
  vi.stubGlobal("fetch", async (request: Request) => {
    const path = new URL(request.url).pathname;
    if (request.method === "GET" && path === "/api/v1/me") {
      return json({ ai_notice_ack_at: "2026-11-01T10:00:00Z" });
    }
    if (request.method === "GET" && path === `/api/v1/generations/${GEN_ID}`) {
      return json(generation);
    }
    if (request.method === "POST" && path.endsWith("/generations")) {
      posts.push(await request.json());
      return json({ ...generation, id: NEXT_ID, status: "queued" }, 202);
    }
    return json({ ...generation, id: NEXT_ID, status: "queued" });
  });
  return posts;
}

function withClient(node: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>{node}</QueryClientProvider>,
  );
}

function progress(generation: Generation) {
  fakeApi(generation);
  const onRetry = vi.fn();
  const onRuleBased = vi.fn();
  withClient(
    <GenerationProgress
      generationId={GEN_ID}
      onRetry={onRetry}
      onRuleBased={onRuleBased}
    />,
  );
  return { onRetry, onRuleBased };
}

afterEach(() => vi.unstubAllGlobals());

describe("FallbackNotice", () => {
  it("labels a rule-based plan with the exact text, as an info notice without an AI badge", () => {
    const { container } = render(
      <FallbackNotice outcome="fallback_rule_based" />,
    );

    const notice = screen.getByText(FALLBACK_TEXT);
    expect(FALLBACK_TEXT).toBe(
      "Built by rules because the AI service was unavailable or its answer failed checks",
    );
    expect(notice).toHaveClass("bg-info-soft", "text-info");
    expect(notice).not.toHaveClass("text-destructive");
    expect(screen.queryByRole("alert")).toBeNull();
    expect(container).not.toHaveTextContent("AI-written");
  });

  it("says nothing on a model plan and notes a repaired one", () => {
    const { container, rerender } = render(<FallbackNotice outcome="model" />);
    expect(container).toBeEmptyDOMElement();

    rerender(<FallbackNotice outcome="model_repaired" />);
    expect(screen.getByText("Some details were adjusted")).toBeVisible();
  });
});

describe("PausedAiNotice", () => {
  it("shows the catalogue text and a primary Build a rule-based plan button", () => {
    const onBuild = vi.fn();
    render(<PausedAiNotice onBuildRuleBased={onBuild} />);

    expect(
      screen.getByText(ERROR_CATALOGUE.AI_QUOTA_REACHED.what),
    ).toBeVisible();
    expect(
      screen.getByText(ERROR_CATALOGUE.AI_QUOTA_REACHED.next),
    ).toBeVisible();
    fireEvent.click(
      screen.getByRole("button", { name: "Build a rule-based plan" }),
    );
    expect(onBuild).toHaveBeenCalledOnce();
  });

  it("is busy while the rule-based plan starts", () => {
    render(<PausedAiNotice onBuildRuleBased={vi.fn()} building />);

    const button = screen.getByRole("button", {
      name: "Build a rule-based plan",
    });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
  });
});

describe("GenerationProgress outcomes (IMP-403)", () => {
  it("FR-037 AC2: provider quota shows the paused-AI notice, not an error", async () => {
    const { onRuleBased } = progress(QUOTA);

    fireEvent.click(
      await screen.findByRole("button", { name: "Build a rule-based plan" }),
    );
    expect(onRuleBased).toHaveBeenCalledOnce();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("a configuration failure shows ErrorState with its reference and the rule-based action", async () => {
    const { onRuleBased } = progress(
      failed(
        "config_error",
        "The AI service is not available right now.",
        "retry_rule_based",
      ),
    );

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      "The AI service is not available right now.",
    );
    expect(alert).toHaveTextContent(`Reference: ${GEN_ID}`);
    fireEvent.click(
      screen.getByRole("button", { name: "Build a rule-based plan" }),
    );
    expect(onRuleBased).toHaveBeenCalledOnce();
  });

  it("an unresolved plan offers to edit the trip", async () => {
    progress(
      failed(
        "unresolved_validation",
        "No plan satisfied the checks; adjust the trip or must-visit places.",
        "edit_trip",
      ),
    );

    expect(
      await screen.findByRole("link", { name: "Edit trip" }),
    ).toHaveAttribute("href", `/trips/new?draft=${TRIP_ID}`);
  });

  it("an internal failure offers Try again", async () => {
    const { onRetry } = progress(
      failed("internal", "Something went wrong on our side.", "retry"),
    );

    fireEvent.click(await screen.findByRole("button", { name: "Try again" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });
});

describe("Generate page", () => {
  it("Build a rule-based plan starts API-22 with mode rule_based", async () => {
    const posts = fakeApi(QUOTA);
    withClient(<GeneratePage />);

    fireEvent.click(
      await screen.findByRole("button", { name: "Build a rule-based plan" }),
    );

    await waitFor(() => expect(posts).toEqual([{ mode: "rule_based" }]));
    await waitFor(() =>
      expect(router.replace).toHaveBeenCalledWith(
        `/trips/${TRIP_ID}/generate?generation=${NEXT_ID}`,
        { scroll: false },
      ),
    );
  });
});
