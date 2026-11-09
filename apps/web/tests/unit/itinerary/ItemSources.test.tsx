import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { ItemSources } from "@/components/itinerary/ItemSources";
import { ItineraryItemCard } from "@/components/itinerary/ItineraryItemCard";
import type { components } from "@/lib/api/schema";

import { axeViolations } from "../../axe";
import { ITEM } from "./fixtures";

type SourceRef = components["schemas"]["SourceRef"];

const GUIDE: SourceRef = {
  chunk_id: "00000000-0000-4000-8000-0000000000d1",
  kind: "guide",
  title: "Sampleton old town (sample)",
  source_name: "Sampleton Guide Team (sample)",
  licence: "CC BY 4.0",
  attribution_text: "Sample attribution line",
  url: "https://example.test/guide",
  retrieved_on: "2026-11-14",
};

const PLACE: SourceRef = {
  chunk_id: "00000000-0000-4000-8000-0000000000d2",
  kind: "place",
  title: "Old Mill Museum (sample)",
  source_name: "Sample Records (sample)",
  licence: "CC0",
  attribution_text: null,
  url: null,
  retrieved_on: null,
};

const toggle = () => screen.getByRole("button", { name: /^Sources/ });

async function renderOpen(sources: SourceRef[]) {
  const view = render(<ItemSources sources={sources} />);
  await userEvent.click(toggle());
  return view;
}

// TC-457, FR-139 AC2 and AC3, NFR-025.
describe("ItemSources", () => {
  it("lists each source's title, kind, source name, licence or attribution and date", async () => {
    await renderOpen([GUIDE, PLACE]);

    const [guide, place] = screen.getAllByRole("listitem");
    expect(guide).toHaveTextContent("Sampleton old town (sample)");
    expect(guide).toHaveTextContent(
      "Guide · Sampleton Guide Team (sample) · Sample attribution line · Retrieved 14 Nov 2026",
    );
    expect(place).toHaveTextContent(
      "Place record · Sample Records (sample) · CC0",
    );
    expect(place).not.toHaveTextContent("Retrieved");
  });

  it("renders nothing for an empty list", () => {
    const { container } = render(<ItemSources sources={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("starts closed, with the button naming the count and its list", () => {
    render(<ItemSources sources={[GUIDE, PLACE]} />);

    expect(toggle()).toHaveAccessibleName("Sources (2)");
    expect(toggle()).toHaveAttribute("aria-expanded", "false");
    const list = document.getElementById(
      toggle().getAttribute("aria-controls") ?? "",
    );
    expect(list).not.toBeVisible();
  });

  it.each([
    ["Enter", "{Enter}"],
    ["Space", " "],
  ])("toggles with %s", async (_name, key) => {
    render(<ItemSources sources={[GUIDE]} />);
    const user = userEvent.setup();

    await user.tab();
    expect(toggle()).toHaveFocus();
    await user.keyboard(key);
    expect(toggle()).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("list")).toBeVisible();

    await user.keyboard(key);
    expect(toggle()).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });

  it("links an https title outside the app, safely", async () => {
    await renderOpen([GUIDE]);

    const link = screen.getByRole("link", { name: /Sampleton old town/ });
    expect(link).toHaveAttribute("href", "https://example.test/guide");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it.each([
    "http://example.test/guide",
    "javascript:alert(1)",
    "data:text/html,sample",
  ])("shows %s as text, never as a link", async (url) => {
    await renderOpen([{ ...GUIDE, url }]);

    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.getByText("Sampleton old town (sample)")).toBeInTheDocument();
    expect(screen.getByText(url)).toBeInTheDocument();
  });

  it("shows no chunk ID", async () => {
    const { container } = await renderOpen([GUIDE, PLACE]);

    expect(container).not.toHaveTextContent(GUIDE.chunk_id);
    expect(container).not.toHaveTextContent(PLACE.chunk_id);
  });

  it("has no axe violation, closed or open", async () => {
    const { container } = render(<ItemSources sources={[GUIDE, PLACE]} />);
    expect(await axeViolations(container)).toEqual([]);

    await userEvent.click(toggle());
    expect(await axeViolations(container)).toEqual([]);
  });
});

describe("ItineraryItemCard sources", () => {
  it("shows them under an AI-written note, which keeps its badge", () => {
    render(<ItineraryItemCard item={{ ...ITEM, sources: [GUIDE] }} />);

    const note = screen.getByText(ITEM.note ?? "").parentElement as HTMLElement;
    expect(within(note).getByText("AI-written")).toBeInTheDocument();
    expect(
      note.compareDocumentPosition(toggle()) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it("shows nothing extra for an item without citations", () => {
    render(<ItineraryItemCard item={ITEM} />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("shows no sources under a note the traveller wrote", () => {
    render(
      <ItineraryItemCard
        item={{ ...ITEM, note_origin: "user", sources: [GUIDE] }}
      />,
    );
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
