import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import GeneratePage from "@/app/(app)/trips/[tripId]/generate/page";
import { GIVE_UP_AFTER_S } from "@/components/generation/GenerationProgress";
import type { components } from "@/lib/api/schema";

// IMP-213 (US-153 AC1, FR-024, FR-025, IMD-12, IMD-119): the generate page and its polling state
// machine against a fake API, with fake timers. No Supabase and no network.
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
const ACTIVE_ID = "00000000-0000-4000-8000-0000000000b2";

const router = { push: vi.fn(), replace: vi.fn() };
let search = new URLSearchParams();
vi.mock("next/navigation", () => ({
  useParams: () => ({ tripId: TRIP_ID }),
  useRouter: () => router,
  useSearchParams: () => search,
}));

type Generation = components["schemas"]["GenerationOut"];
type Status = Generation["status"];

function generation(
  id: string,
  status: Status,
  extra: Partial<Generation> = {},
): Generation {
  return {
    id,
    trip_id: TRIP_ID,
    status,
    mode: "ai",
    scope: "full",
    day_number: null,
    outcome: status === "completed" ? "model" : null,
    failure_reason: null,
    failure_message: null,
    next_action: null,
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
    completed_at: null,
    ...extra,
  };
}

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

const envelope = (code: string, message: string, details: unknown[] = []) => ({
  error: {
    code,
    message,
    request_id: "req-1",
    details,
    retry_after_s: null,
  },
});

/** API-22 answers `start`; API-23 answers the `statuses` in turn, repeating the last one. */
function fakeApi(start: () => Response, statuses: Generation[]) {
  const posts: number[] = [];
  const polls: { at: number; id: string }[] = [];
  let served = 0;
  vi.stubGlobal("fetch", async (request: Request) => {
    const path = new URL(request.url).pathname;
    if (
      request.method === "POST" &&
      path === `/api/v1/trips/${TRIP_ID}/generations`
    ) {
      expect(await request.json()).toEqual({ mode: "ai" }); // IMD-21
      posts.push(Date.now());
      return start();
    }
    const match = path.match(/^\/api\/v1\/generations\/(.+)$/);
    if (request.method === "GET" && match) {
      polls.push({ at: Date.now(), id: match[1] });
      const answer = statuses[Math.min(served, statuses.length - 1)];
      served += 1;
      return json({ ...answer, id: match[1] });
    }
    throw new Error(`unexpected ${request.method} ${path}`);
  });
  return { posts, polls };
}

const accepted =
  (id = GEN_ID) =>
  () =>
    json(generation(id, "queued"), 202);

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <GeneratePage />
    </QueryClientProvider>,
  );
}

/** Moves the fake clock, then lets responses and their renders settle on the real event loop. */
async function advance(ms: number) {
  await act(() => vi.advanceTimersByTimeAsync(ms));
  for (let turn = 0; turn < 5; turn += 1) {
    await act(() => new Promise((resolve) => setTimeout(resolve, 0)));
  }
}

/** A step of the progress list (the live region repeats the current label). */
const step = (label: string) =>
  within(screen.getByRole("list")).getByText(label).closest("li");
const generateButton = () =>
  screen.getByRole("button", { name: "Generate with AI" });

beforeEach(() => {
  // Only the clocks under test are fake: the poll and elapsed intervals and Date. setTimeout stays
  // real, because TanStack Query and Testing Library schedule their notifications with it.
  vi.useFakeTimers({ toFake: ["setInterval", "clearInterval", "Date"] });
  router.push.mockReset();
  router.replace.mockReset();
  search = new URLSearchParams();
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("GenerationProgress", () => {
  it("US-153 AC1: Generate shows the steps and opens the itinerary on completed", async () => {
    fakeApi(accepted(), [
      generation(GEN_ID, "running"),
      generation(GEN_ID, "validating"),
      generation(GEN_ID, "completed"),
    ]);
    renderPage();

    fireEvent.click(generateButton());
    await advance(0);
    expect(router.replace).toHaveBeenCalledWith(
      `/trips/${TRIP_ID}/generate?generation=${GEN_ID}`,
      { scroll: false },
    );
    const queued = step("Queued");
    expect(queued).toHaveAttribute("aria-current", "step");
    expect(screen.getByText("Elapsed 0:00")).toBeInTheDocument();

    await advance(2000);
    expect(step("Running")).toHaveAttribute("aria-current", "step");
    expect(screen.getByText("Elapsed 0:02")).toBeInTheDocument();

    await advance(3000);
    expect(step("Validating")).toHaveAttribute("aria-current", "step");
    expect(
      within(screen.getByRole("list")).queryByText("Repairing"),
    ).not.toBeInTheDocument();

    await advance(4000);
    expect(screen.getByRole("status")).toHaveTextContent(
      "Plan ready. Opening your itinerary.",
    );
    expect(router.push).toHaveBeenCalledWith(`/trips/${TRIP_ID}/itinerary`);
  });

  it("polls 2 s after the start, then 3, 4 and 5 s, then every 5 s, and stops at the end", async () => {
    const { posts, polls } = fakeApi(accepted(), [
      ...Array.from({ length: 6 }, () => generation(GEN_ID, "running")),
      generation(GEN_ID, "completed"),
    ]);
    renderPage();
    fireEvent.click(generateButton());
    await advance(60_000);

    const gaps = [posts[0], ...polls.map((poll) => poll.at)]
      .slice(1)
      .map((at, index, all) => at - (index === 0 ? posts[0] : all[index - 1]));
    expect(gaps).toEqual([2000, 3000, 4000, 5000, 5000, 5000, 5000]);
    expect(polls).toHaveLength(7); // nothing after `completed`
  });

  it("a failed generation shows failure_message and Try again starts a new one", async () => {
    let next = 0;
    const ids = [GEN_ID, ACTIVE_ID];
    const { posts } = fakeApi(
      () => json(generation(ids[next++], "queued"), 202),
      [
        generation(GEN_ID, "failed", {
          failure_reason: "internal",
          failure_message: "Something went wrong on our side.",
          next_action: "retry",
          outcome: "failed",
        }),
      ],
    );
    renderPage();
    fireEvent.click(generateButton());
    await advance(2000);

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Something went wrong on our side.");
    expect(screen.queryByText("Queued")).not.toBeInTheDocument();
    expect(router.push).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    await advance(0);
    expect(posts).toHaveLength(2);
    expect(router.replace).toHaveBeenLastCalledWith(
      `/trips/${TRIP_ID}/generate?generation=${ACTIVE_ID}`,
      { scroll: false },
    );
  });

  it("IMD-12: still running after 160 s shows the reload message and stops polling", async () => {
    const { polls } = fakeApi(accepted(), [generation(GEN_ID, "running")]);
    renderPage();
    fireEvent.click(generateButton());

    await advance((GIVE_UP_AFTER_S - 1) * 1000);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();

    await advance(1000);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Connection problem. Reload the page.",
    );
    expect(screen.getByRole("button", { name: "Reload" })).toBeInTheDocument();
    const count = polls.length;
    await advance(30_000);
    expect(polls).toHaveLength(count);
  });

  it("a double click starts one generation only", async () => {
    const { posts } = fakeApi(accepted(), [generation(GEN_ID, "running")]);
    renderPage();

    // Both clicks land before React re-renders the button as disabled.
    fireEvent.click(generateButton());
    fireEvent.click(generateButton());
    await advance(0);
    expect(posts).toHaveLength(1);
    expect(generateButton()).toBeDisabled();
  });

  it("IMD-119: a 409 GENERATION_IN_PROGRESS resumes polling the generation it names", async () => {
    const { polls } = fakeApi(
      () =>
        json(
          envelope(
            "GENERATION_IN_PROGRESS",
            "A generation for this trip is already running.",
            [{ field: "generation_id", message: ACTIVE_ID }],
          ),
          409,
        ),
      [generation(ACTIVE_ID, "validating")],
    );
    renderPage();
    fireEvent.click(generateButton());
    await advance(0);

    expect(router.replace).toHaveBeenCalledWith(
      `/trips/${TRIP_ID}/generate?generation=${ACTIVE_ID}`,
      { scroll: false },
    );
    expect(polls.map((poll) => poll.id)).toEqual([ACTIVE_ID]);
    expect(step("Validating")).toHaveAttribute("aria-current", "step");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("a 409 without the generation id shows the message and Reload, without guessing", async () => {
    const { polls } = fakeApi(
      () =>
        json(
          envelope(
            "GENERATION_IN_PROGRESS",
            "A generation for this trip is already running.",
          ),
          409,
        ),
      [generation(ACTIVE_ID, "running")],
    );
    renderPage();
    fireEvent.click(generateButton());
    await advance(0);

    expect(screen.getByRole("alert")).toHaveTextContent(
      "A generation for this trip is already running.",
    );
    expect(screen.getByRole("button", { name: "Reload" })).toBeInTheDocument();
    expect(polls).toHaveLength(0);
    expect(router.replace).not.toHaveBeenCalled();
  });

  it("a reload with ?generation= resumes polling without starting another", async () => {
    search = new URLSearchParams({ generation: GEN_ID });
    const { posts, polls } = fakeApi(accepted(), [
      generation(GEN_ID, "repairing", { repair_attempts: 1 }),
    ]);
    renderPage();
    await advance(0);

    expect(posts).toHaveLength(0);
    expect(polls.map((poll) => poll.id)).toEqual([GEN_ID]);
    expect(step("Repairing")).toHaveAttribute("aria-current", "step");
    expect(generateButton()).toBeDisabled();
  });
});
