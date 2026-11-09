import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ErrorState } from "@/components/states/ErrorState";
import { ApiError } from "@/lib/api/client";
import { ERROR_CATALOGUE } from "@/lib/api/errors";

const apiError = (
  code: ConstructorParameters<typeof ApiError>[1],
  message = "The API's safe message.",
  retryAfterS: number | null = null,
) => new ApiError(500, code, message, [], "req-123", retryAfterS);

// FR-116 (TC-281): a failed request states what happened and what to do next.
describe("ErrorState", () => {
  it("TC-281: shows what happened, what to do next, one action and the reference", async () => {
    const onRetry = vi.fn();
    render(<ErrorState error={apiError("INTERNAL")} onRetry={onRetry} />);

    const alert = screen.getByRole("alert");
    expect(
      screen.getByRole("heading", { name: ERROR_CATALOGUE.INTERNAL.what }),
    ).toBeInTheDocument();
    expect(alert).toHaveTextContent("The API's safe message.");
    expect(alert).toHaveTextContent(ERROR_CATALOGUE.INTERNAL.next);
    expect(alert).toHaveTextContent("Reference: req-123");

    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("copies the reference", async () => {
    const user = userEvent.setup();
    const writeText = vi
      .spyOn(navigator.clipboard, "writeText")
      .mockResolvedValue();
    render(<ErrorState error={apiError("INTERNAL")} />);

    await user.click(screen.getByRole("button", { name: "Copy reference" }));

    expect(writeText).toHaveBeenCalledWith("req-123");
    expect(
      await screen.findByRole("button", { name: "Reference copied" }),
    ).toBeInTheDocument();
  });

  it("RATE_LIMITED says when to try again", () => {
    render(<ErrorState error={apiError("RATE_LIMITED", "Slow down.", 30)} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Try again in 30 s");
  });

  it("a page title replaces the catalogue's what-happened line", () => {
    render(
      <ErrorState
        title="Your trips could not be loaded"
        error={apiError("NOT_FOUND")}
      />,
    );
    expect(
      screen.getByRole("heading", { name: "Your trips could not be loaded" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(
      ERROR_CATALOGUE.NOT_FOUND.next,
    );
  });

  it("inline errors are polite, not role=alert", () => {
    render(<ErrorState inline error={apiError("CONFLICT")} />);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("leaves out the reference and action when they are not given", () => {
    render(<ErrorState error={{ message: "Network error." }} />);

    expect(screen.getByRole("alert")).not.toHaveTextContent("Reference");
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("never renders a stack trace or a JSON body", () => {
    const thrown = new TypeError("Failed to fetch");
    thrown.stack = "TypeError: Failed to fetch\n    at secret.ts:1:1";
    const { container, unmount } = render(<ErrorState error={thrown} />);
    expect(container).toHaveTextContent(ERROR_CATALOGUE.NETWORK.what);
    expect(container.textContent).not.toMatch(/at secret\.ts|Failed to fetch/);
    unmount();

    const json = apiError(
      "INTERNAL",
      '{"detail":"Traceback (most recent call last)"}',
    );
    const second = render(<ErrorState error={json} />);
    expect(second.container.textContent).not.toMatch(/Traceback|[{}]/);

    second.unmount();
    const object = render(
      <ErrorState error={{ message: { secret: "x" }, stack: "at y" }} />,
    );
    expect(object.container.textContent).not.toMatch(/secret|at y|\[object/);
  });

  it("the catalogue has an entry for every §6.3 code and network error", () => {
    expect(Object.keys(ERROR_CATALOGUE).sort()).toEqual(
      [
        "AI_QUOTA_REACHED",
        "CONFLICT",
        "GENERATION_IN_PROGRESS",
        "INTERNAL",
        "INVALID_EDIT",
        "NETWORK",
        "NOT_FOUND",
        "NOT_IMPLEMENTED",
        "RATE_LIMITED",
        "SERVICE_UNAVAILABLE",
        "STALE_PLAN",
        "UNAUTHENTICATED",
        "VALIDATION_ERROR",
      ].sort(),
    );
    for (const { what, next } of Object.values(ERROR_CATALOGUE)) {
      expect(what.length).toBeGreaterThan(0);
      expect(next.length).toBeGreaterThan(0);
    }
  });
});
