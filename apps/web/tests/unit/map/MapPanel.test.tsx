import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MapPanel } from "@/components/map/MapPanel";
import type { components } from "@/lib/api/schema";
import { MAPLIBRE_WORKER_URL, OPENFREEMAP_STYLE_URL } from "@/lib/map";

import { ITEM } from "../itinerary/fixtures";

type Item = components["schemas"]["Item"];

// §9: MapLibre is mocked; the fake records what the panel draws and lets a test fire map events.
const fake = vi.hoisted(() => ({
  workerUrls: [] as string[],
  maps: [] as {
    options: { style: string; attributionControl?: unknown };
    workerUrlAtCreate: string | undefined;
    handlers: Record<string, ((...args: unknown[]) => void)[]>;
    line: unknown;
    removed: boolean;
  }[],
}));

vi.mock("maplibre-gl", () => {
  class FakeMap {
    handlers: Record<string, ((...args: unknown[]) => void)[]> = {};
    line: unknown = null;
    removed = false;
    options: { style: string; attributionControl?: unknown };
    workerUrlAtCreate = fake.workerUrls.at(-1);
    constructor(options: { style: string; attributionControl?: unknown }) {
      this.options = options;
      fake.maps.push(this);
    }
    on(type: string, fn: () => void) {
      (this.handlers[type] ??= []).push(fn);
      return this;
    }
    once(type: string, fn: () => void) {
      return this.on(type, fn);
    }
    addSource() {}
    addLayer() {}
    getSource() {
      return { setData: (data: unknown) => (this.line = data) };
    }
    fitBounds() {}
    remove() {
      this.removed = true;
    }
  }
  class Marker {
    element: HTMLElement;
    constructor({ element }: { element: HTMLElement }) {
      this.element = element;
    }
    setLngLat() {
      return this;
    }
    addTo() {
      document.body.append(this.element);
      return this;
    }
    remove() {
      this.element.remove();
    }
  }
  class LngLatBounds {
    extend() {
      return this;
    }
  }
  const setWorkerUrl = (url: string) => fake.workerUrls.push(url);
  return { Map: FakeMap, Marker, LngLatBounds, setWorkerUrl };
});

const item = (
  id: string,
  position: number,
  name: string,
  lon: number,
  lat: number,
): Item => ({
  ...ITEM,
  id: `00000000-0000-4000-8000-0000000000${id}`,
  position,
  start_time: `1${position}:00`,
  end_time: `1${position}:45`,
  place: { ...ITEM.place, name, lon, lat },
});

// Sent out of order on purpose: the panel numbers by position, not by array order.
const ITEMS = [
  item("b2", 2, "Harbour Steps (sample)", 77.6, 12.98),
  item("a1", 1, "Old Mill Museum (sample)", 77.59, 12.97),
  item("c3", 3, "Lantern Market (sample)", 77.61, 12.99),
];

function emit(type: string) {
  act(() => fake.maps.at(-1)?.handlers[type]?.forEach((fn) => fn()));
}

function renderPanel(selectedItemId: string | null = null) {
  const onSelectItem = vi.fn();
  const view = render(
    <MapPanel
      items={ITEMS}
      selectedItemId={selectedItemId}
      onSelectItem={onSelectItem}
    />,
  );
  return { onSelectItem, view };
}

const stopNames = () =>
  screen
    .getAllByRole("button", { name: /^Stop/ })
    .map((b) => b.getAttribute("aria-label"));

beforeEach(() => {
  fake.maps.length = 0;
  fake.workerUrls.length = 0;
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(
    {} as RenderingContext,
  );
});
afterEach(() => vi.restoreAllMocks());

describe("MapPanel", () => {
  it("TC-238: shows one numbered marker per stop in visit order, joined in that order", () => {
    renderPanel();
    expect(fake.maps[0].options.style).toBe(OPENFREEMAP_STYLE_URL);
    expect(fake.maps[0].options.attributionControl).toMatchObject({
      compact: false,
      customAttribution: expect.stringContaining(
        'href="https://www.openstreetmap.org/copyright"',
      ),
    });
    expect(
      (
        fake.maps[0].options.attributionControl as {
          customAttribution: string;
        }
      ).customAttribution,
    ).toContain("OpenStreetMap contributors");
    emit("load");

    expect(stopNames()).toEqual([
      "Stop 1: Old Mill Museum (sample)",
      "Stop 2: Harbour Steps (sample)",
      "Stop 3: Lantern Market (sample)",
    ]);
    expect(
      screen
        .getAllByRole("button", { name: /^Stop/ })
        .map((b) => b.textContent),
    ).toEqual(["1", "2", "3"]);
    expect(fake.maps[0].line).toMatchObject({
      geometry: {
        type: "LineString",
        coordinates: [
          [77.59, 12.97],
          [77.6, 12.98],
          [77.61, 12.99],
        ],
      },
    });
  });

  it("IMP-508: the map worker is the bundled asset, set before the map is created", () => {
    renderPanel();

    // MapLibre 6 derives its own worker URL from import.meta.url, which the production bundle
    // turns into a file: URL; the panel hands it a served URL first.
    expect(MAPLIBRE_WORKER_URL).toMatch(/maplibre-gl-worker\.mjs$/);
    expect(fake.workerUrls).toEqual([MAPLIBRE_WORKER_URL]);
    expect(fake.maps[0].workerUrlAtCreate).toBe(MAPLIBRE_WORKER_URL);
  });

  it("TC-239: selecting a marker opens that stop's card; the selected card's marker is highlighted", () => {
    const { onSelectItem, view } = renderPanel();
    emit("load");

    fireEvent.click(
      screen.getByRole("button", { name: "Stop 2: Harbour Steps (sample)" }),
    );
    expect(onSelectItem).toHaveBeenCalledWith(ITEMS[0].id);

    view.rerender(
      <MapPanel
        items={ITEMS}
        selectedItemId={ITEMS[0].id}
        onSelectItem={onSelectItem}
      />,
    );
    expect(
      screen.getByRole("button", { name: "Stop 2: Harbour Steps (sample)" }),
    ).toHaveAttribute("aria-current", "true");
    expect(
      screen.getByRole("button", { name: "Stop 1: Old Mill Museum (sample)" }),
    ).toHaveAttribute("aria-current", "false");
  });

  it("TC-240: a tile or style error swaps the map for the numbered list, which still works", () => {
    const { onSelectItem } = renderPanel();
    emit("load");
    emit("error");

    expect(screen.getByRole("status")).toHaveTextContent(
      "Map unavailable; list view shown",
    );
    expect(fake.maps[0].removed).toBe(true);
    const list = screen.getByRole("list", { name: "Stops" });
    expect(list).toHaveTextContent("13:00–13:45");
    const entries = within(list).getAllByRole("button");
    expect(entries[0]).toHaveAccessibleName(
      /^Stop\s*1\s*Old Mill Museum \(sample\)/,
    );
    expect(entries[1]).toHaveAccessibleName(
      /^Stop\s*2\s*Harbour Steps \(sample\)/,
    );
    expect(entries[2]).toHaveAccessibleName(
      /^Stop\s*3\s*Lantern Market \(sample\)/,
    );
    // WCAG 2.5.3: the visible text is part of the accessible name.
    entries.forEach((b) => {
      expect(b).not.toHaveAttribute("aria-label");
    });

    fireEvent.click(entries[2]);
    expect(onSelectItem).toHaveBeenCalledWith(ITEMS[2].id);
  });

  it("TC-240: without WebGL the list is shown and no map is created", () => {
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
    renderPanel();

    expect(fake.maps).toHaveLength(0);
    expect(screen.getByRole("status")).toHaveTextContent(
      "Map unavailable; list view shown",
    );
    expect(stopNames()).toHaveLength(3);
  });
});
