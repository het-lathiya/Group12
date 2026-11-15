import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ProfileForm } from "@/components/profile/ProfileForm";
import type { ErrorDetail } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

// FR-004 (TC-060 to TC-062) web side: the form mirrors the API-04 rules and sends ProfilePatch.
const PROFILE: components["schemas"]["Profile"] = {
  id: "00000000-0000-4000-8000-000000000009",
  email: "traveller@example.test",
  display_name: "Asha",
  home_country: "IN",
  preferred_currency: "INR",
  default_preferences: { pace: "relaxed", interests: ["museum"] },
  ai_notice_ack_at: null,
};

type Save = (
  body: components["schemas"]["ProfilePatch"],
) => Promise<ErrorDetail[]>;

function renderForm(onSave = vi.fn<Save>(async () => []), profile = PROFILE) {
  render(<ProfileForm profile={profile} onSave={onSave} />);
  return { user: userEvent.setup(), onSave };
}

describe("ProfileForm (FR-004)", () => {
  it("shows the saved profile and its default preferences", () => {
    renderForm();
    expect(screen.getByLabelText("Display name")).toHaveValue("Asha");
    expect(screen.getByLabelText("Home currency")).toHaveValue("INR");
    expect(screen.getByLabelText("Home country")).toHaveValue("IN");
    expect(screen.getByRole("radio", { name: "Relaxed" })).toBeChecked();
  });

  it("TC-060, TC-061: saves name, currency and defaults as one ProfilePatch", async () => {
    const { user, onSave } = renderForm();
    const name = screen.getByLabelText("Display name");
    await user.clear(name);
    await user.type(name, "  Asha Patel ");
    const currency = screen.getByLabelText("Home currency");
    await user.clear(currency);
    await user.type(currency, "gbp");
    await user.click(screen.getByLabelText("I need step-free access"));
    await user.click(screen.getByRole("button", { name: "Save profile" }));

    await waitFor(() => expect(onSave).toHaveBeenCalledTimes(1));
    expect(onSave).toHaveBeenCalledWith({
      display_name: "Asha Patel",
      preferred_currency: "GBP",
      home_country: "IN",
      default_preferences: {
        interests: ["museum"],
        pace: "relaxed",
        budget_priority: "balanced",
        transport_pref: "walking",
        accommodation_type: "any",
        step_free_required: true,
      },
    });
  });

  it("TC-060: refuses a display name over 60 characters before calling the API", async () => {
    const { user, onSave } = renderForm();
    const name = screen.getByLabelText("Display name");
    await user.clear(name);
    await user.type(name, "x".repeat(61));
    await user.click(screen.getByRole("button", { name: "Save profile" }));

    expect(
      await screen.findByText("Enter a display name of 1 to 60 characters."),
    ).toBeInTheDocument();
    expect(onSave).not.toHaveBeenCalled();
  });

  it("TC-062: refuses an invalid currency code before calling the API", async () => {
    const { user, onSave } = renderForm();
    const currency = screen.getByLabelText("Home currency");
    await user.clear(currency);
    await user.type(currency, "R1");
    await user.click(screen.getByRole("button", { name: "Save profile" }));

    expect(
      await screen.findByText(
        "Enter a three-letter ISO 4217 code, such as INR.",
      ),
    ).toBeInTheDocument();
    expect(currency).toHaveAttribute("aria-invalid", "true");
    expect(onSave).not.toHaveBeenCalled();
  });

  it("shows API-04 field errors on their fields, default preferences included", async () => {
    const onSave = vi.fn<Save>(async () => [
      { field: "preferred_currency", message: "Unknown currency." },
      { field: "default_preferences.pace", message: "Choose a pace." },
    ]);
    const { user } = renderForm(onSave);
    await user.click(screen.getByRole("button", { name: "Save profile" }));

    expect(await screen.findByText("Unknown currency.")).toBeInTheDocument();
    expect(screen.getByText("Choose a pace.")).toBeInTheDocument();
  });

  it("an empty name and currency are sent as null to clear them", async () => {
    const { user, onSave } = renderForm();
    await user.clear(screen.getByLabelText("Display name"));
    await user.clear(screen.getByLabelText("Home currency"));
    await user.click(screen.getByRole("button", { name: "Save profile" }));

    await waitFor(() =>
      expect(onSave).toHaveBeenCalledWith(
        expect.objectContaining({
          display_name: null,
          preferred_currency: null,
        }),
      ),
    );
  });
});
