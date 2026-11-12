import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import GeneratePage from "@/app/(app)/trips/[tripId]/generate/page";

// IMP-305 step 7 (FR-024, IMD-24, NFR-021): the notice on the generate page against a fake API.
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
const ACKNOWLEDGED_AT = "2026-11-06T10:00:00Z";
// The approved text as one string, so a change to the constants fails here.
const BODY =
  "To write your itinerary, this app sends your trip details, preferences and notes to Google's Gemini API. They are also used to find relevant places and guide passages. Your name and email address are not sent. Google handles this data under the Gemini API terms. Do not enter personal details in your notes.";

let search = new URLSearchParams();
vi.mock("next/navigation", () => ({
  useParams: () => ({ tripId: TRIP_ID }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => search,
}));

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

const envelope = (code: string, message: string, details: unknown[] = []) => ({
  error: { code, message, request_id: "r", details, retry_after_s: null },
});

const queued = () =>
  json({ id: GEN_ID, trip_id: TRIP_ID, status: "queued" }, 202);

type Answers = {
  me?: () => Response | Promise<Response>;
  acknowledge?: () => Response | Promise<Response>;
  start?: () => Response;
};

/** Notes each call in order; the status poll is never reached in these tests' time. */
function fakeApi({
  me = () => json({ ai_notice_ack_at: null }),
  acknowledge = () => json({ ai_notice_ack_at: ACKNOWLEDGED_AT }),
  start = queued,
}: Answers) {
  const calls: string[] = [];
  vi.stubGlobal("fetch", async (request: Request) => {
    const path = new URL(request.url).pathname;
    if (request.method === "GET" && path === "/api/v1/me") return me();
    if (request.method === "PATCH" && path === "/api/v1/me") {
      calls.push("API-04");
      expect(await request.json()).toEqual({ ai_notice_acknowledged: true });
      return acknowledge();
    }
    if (request.method === "POST" && path.endsWith("/generations")) {
      calls.push("API-22");
      return start();
    }
    if (request.method === "GET" && path.startsWith("/api/v1/generations/")) {
      return json({ id: GEN_ID, trip_id: TRIP_ID, status: "running" });
    }
    throw new Error(`unexpected ${request.method} ${path}`);
  });
  return calls;
}

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

// The first query of the file pays for the first render (345 ms alone, 44 ms after); on a starved
// machine that ran past the 1 s default (RUN-059), so the heading gets 4 s, inside the test's 5 s.
const noticeHeading = () =>
  screen.findByRole(
    "heading",
    { name: "Before your first AI-written plan" },
    { timeout: 4000 },
  );
// The progress view counts real seconds, so "Elapsed 0:00" holds only for its first second; a slow
// run that looks later would miss it. Any elapsed value shows the progress view is up.
const progressShown = () => screen.findByText(/^Elapsed \d+:\d{2}$/);
const acceptButton = () =>
  screen.getByRole("button", { name: "I understand, continue" });

beforeEach(() => {
  search = new URLSearchParams();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("PrivacyNotice", () => {
  it("shows the approved text and terms link, in place of the start button", async () => {
    fakeApi({});
    renderPage();

    const heading = await noticeHeading();

    expect(heading.nextElementSibling?.textContent).toBe(BODY);
    const link = screen.getByRole("link", { name: "Gemini API terms" });
    expect(link).toHaveAttribute(
      "href",
      "https://ai.google.dev/gemini-api/terms",
    );
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(acceptButton()).toBeEnabled();
    expect(
      screen.queryByRole("button", { name: "Generate with AI" }),
    ).not.toBeInTheDocument();
  });

  it("moves focus to the heading when shown", async () => {
    fakeApi({});
    renderPage();

    expect(await noticeHeading()).toHaveFocus();
  });

  it("acknowledging sends API-04 and then API-22, once each", async () => {
    const calls = fakeApi({});
    renderPage();
    await noticeHeading();

    fireEvent.click(acceptButton());

    await progressShown();
    expect(calls).toEqual(["API-04", "API-22"]);
    expect(
      screen.queryByText("Before your first AI-written plan"),
    ).not.toBeInTheDocument();
  });

  it("disables the button while the request is in flight", async () => {
    let answer: (response: Response) => void = () => {};
    fakeApi({
      acknowledge: () => new Promise((resolve) => (answer = resolve)),
    });
    renderPage();
    await noticeHeading();

    fireEvent.click(acceptButton());

    await waitFor(() => expect(acceptButton()).toBeDisabled());
    expect(acceptButton()).toHaveAttribute("aria-busy", "true");
    answer(json({ ai_notice_ack_at: ACKNOWLEDGED_AT }));
    await progressShown();
  });

  it("shows an alert when API-04 fails, starts nothing, and the button retries", async () => {
    let failing = true;
    const calls = fakeApi({
      acknowledge: () =>
        failing
          ? json(envelope("INTERNAL", "Something went wrong."), 500)
          : json({ ai_notice_ack_at: ACKNOWLEDGED_AT }),
    });
    renderPage();
    await noticeHeading();

    fireEvent.click(acceptButton());

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Something went wrong.",
    );
    expect(calls).toEqual(["API-04"]);
    await waitFor(() => expect(acceptButton()).toBeEnabled());

    failing = false;
    fireEvent.click(acceptButton());

    await progressShown();
    expect(calls).toEqual(["API-04", "API-04", "API-22"]);
  });

  it("is not shown to an account that has acknowledged it", async () => {
    const calls = fakeApi({
      me: () => json({ ai_notice_ack_at: ACKNOWLEDGED_AT }),
    });
    renderPage();
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Generate with AI" }),
      ).toBeEnabled(),
    );

    fireEvent.click(screen.getByRole("button", { name: "Generate with AI" }));

    await progressShown();
    expect(calls).toEqual(["API-22"]);
    expect(
      screen.queryByText("Before your first AI-written plan"),
    ).not.toBeInTheDocument();
  });

  it("is not shown while a running generation is being resumed", async () => {
    search = new URLSearchParams({ generation: GEN_ID });
    fakeApi({});
    renderPage();

    await progressShown();
    await waitFor(() => expect(screen.getByRole("list")).toBeInTheDocument());
    expect(
      screen.queryByText("Before your first AI-written plan"),
    ).not.toBeInTheDocument();
  });

  it("appears when API-22 answers 422 on ai_notice, then retries API-22 once", async () => {
    let refused = true;
    const calls = fakeApi({
      me: () => json(envelope("INTERNAL", "Down."), 500),
      start: () => {
        if (!refused) return queued();
        refused = false;
        return json(
          envelope("VALIDATION_ERROR", "Some fields need attention.", [
            { field: "ai_notice", message: "Acknowledge the AI notice first." },
          ]),
          422,
        );
      },
    });
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Generate with AI" }));
    await noticeHeading();
    fireEvent.click(acceptButton());

    await progressShown();
    expect(calls).toEqual(["API-22", "API-04", "API-22"]);
  });
});
