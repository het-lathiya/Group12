import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LandingPage from "@/app/(public)/page";
import {
  CC_BY_SA_URL,
  LiveAttribution,
} from "@/components/labels/LiveAttribution";
import type { Attribution } from "@/components/labels/TierBadge";

import { axeViolations } from "../../axe";

// TC-484 (Amendment A2 §9.2, §9.3, IMP-729): the attribution footer of a live destination shows
// the API-79 texts verbatim, links only https sources with rel="noopener noreferrer", adds the
// CC BY-SA 4.0 licence link to Wikivoyage and Wikipedia text, and is keyboard reachable. It renders
// nothing for curated or SAMPLE destinations or with `any_city_mode` OFF.
vi.mock("@/lib/auth/supabase", () => ({
  getSupabase: () => ({
    auth: {
      getSession: async () => ({ data: { session: null } }),
      onAuthStateChange: () => ({
        data: { subscription: { unsubscribe: () => {} } },
      }),
    },
  }),
}));
vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useParams: () => ({}),
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
}));
const flag = vi.hoisted(() => ({ anyCity: true }));
vi.mock("@/lib/flags", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/flags")>();
  return {
    ...actual,
    isEnabled: (name: Parameters<typeof actual.isEnabled>[0]) =>
      name === "any_city_mode" ? flag.anyCity : actual.isEnabled(name),
  };
});

const OSM: Attribution = {
  source_name: "OpenStreetMap",
  licence: "ODbL-1.0",
  attribution_text:
    "Place data © OpenStreetMap contributors, available under the Open Database Licence (ODbL)",
  url: "https://www.openstreetmap.org/copyright",
};
const WIKIVOYAGE: Attribution = {
  source_name: "Wikivoyage",
  licence: "CC BY-SA 4.0",
  attribution_text:
    "Guide text from Wikivoyage, by its contributors, under CC BY-SA 4.0; excerpts, some sections left out",
  url: "https://en.wikivoyage.org/wiki/Udaipur",
};
const WIKIPEDIA: Attribution = {
  source_name: "Wikipedia",
  licence: "CC-BY-SA-4.0",
  attribution_text:
    "Guide text from Wikipedia, by its contributors, under CC BY-SA 4.0; excerpts, some sections left out",
  url: "https://en.wikipedia.org/wiki/Udaipur",
};
const ROWS = [OSM, WIKIVOYAGE, WIKIPEDIA];

beforeEach(() => {
  flag.anyCity = true;
});

describe("LiveAttribution (TC-484)", () => {
  it("renders every attribution text verbatim on a live destination", () => {
    render(<LiveAttribution tier="live" attribution={ROWS} />);
    expect(
      screen.getByRole("heading", { name: "Data sources" }),
    ).toBeInTheDocument();
    for (const row of ROWS) {
      expect(screen.getByText(row.attribution_text ?? "")).toBeInTheDocument();
    }
  });

  it("links the OpenStreetMap copyright page and the CC BY-SA licence, safely", () => {
    render(<LiveAttribution tier="live" attribution={ROWS} />);
    const osm = screen.getByRole("link", { name: /OpenStreetMap source/ });
    expect(osm).toHaveAttribute(
      "href",
      "https://www.openstreetmap.org/copyright",
    );
    const wikivoyage = screen.getByRole("link", { name: /Wikivoyage source/ });
    expect(wikivoyage).toHaveAttribute(
      "href",
      "https://en.wikivoyage.org/wiki/Udaipur",
    );
    const licences = screen.getAllByRole("link", {
      name: /CC BY-SA 4.0 licence/,
    });
    expect(licences).toHaveLength(2); // Wikivoyage and Wikipedia, not OpenStreetMap
    for (const link of screen.getAllByRole("link")) {
      expect(link).toHaveAttribute("rel", "noopener noreferrer");
      expect(link.getAttribute("href")).toMatch(/^https:\/\//);
    }
    expect(licences[0]).toHaveAttribute("href", CC_BY_SA_URL);
  });

  it("never links a URL that is not https", () => {
    render(
      <LiveAttribution
        tier="live"
        attribution={[
          { ...OSM, url: "http://www.openstreetmap.org/copyright" },
          { ...OSM, source_name: "Other", url: "javascript:alert(1)" },
        ]}
      />,
    );
    expect(screen.queryAllByRole("link")).toHaveLength(0);
    expect(screen.getAllByText(OSM.attribution_text ?? "")).toHaveLength(2);
  });

  it("every link is reachable with the keyboard, in order", async () => {
    const user = userEvent.setup();
    render(<LiveAttribution tier="live" attribution={ROWS} />);
    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(5);
    for (const link of links) {
      await user.tab();
      expect(link).toHaveFocus();
      expect(link.className).toMatch(/focus-visible:ring/);
    }
  });

  it("has no axe findings", async () => {
    const { container } = render(
      <LiveAttribution tier="live" attribution={ROWS} />,
    );
    expect(await axeViolations(container)).toEqual([]);
  });

  it("renders nothing for a curated destination", () => {
    const { container } = render(
      <LiveAttribution tier="curated" attribution={ROWS} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing while the tier is unknown or with no rows", () => {
    const { container } = render(
      <>
        <LiveAttribution tier={undefined} attribution={ROWS} />
        <LiveAttribution tier="live" attribution={[]} />
      </>,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing with the switch OFF", () => {
    flag.anyCity = false;
    const { container } = render(
      <LiveAttribution tier="live" attribution={ROWS} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});

describe("landing page copy (Amendment A2 §9.2)", () => {
  it("keeps today's text with the switch OFF", () => {
    flag.anyCity = false;
    render(<LandingPage />);
    expect(
      screen.getByText(/Plans are drafts built from curated sample data\./),
    ).toBeInTheDocument();
    expect(screen.queryByText(/live open data/)).not.toBeInTheDocument();
  });

  it("names curated or live open data with the switch ON", () => {
    render(<LandingPage />);
    expect(
      screen.getByText(
        /Plans are drafts built from curated or live open data\./,
      ),
    ).toBeInTheDocument();
  });
});
