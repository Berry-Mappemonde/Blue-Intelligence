/**
 * Lock on layer order and the basemap registry.
 *
 * Inspired by Open Waters: Seamap (`style/index.test.ts`): draw order is
 * payload — an accidental reshuffle must break this test, never slip
 * through review unnoticed.
 */
import { LEAFLET_BUILTIN_PANES, PANES, createPanes } from "../layerOrder";
import { SCIENCE_WMS_PANES } from "../useScienceWms";
import { BASEMAPS, BASEMAP_CYCLE, nextBasemap, stripUnavailableSources } from "../basemaps";
import { maplibreWorkerUrl } from "../maplibreWorker";

describe("pane order (locked)", () => {
  test("the exact pane list cannot change without breaking this test", () => {
    expect(PANES.map((p) => `${p.name}@${p.zIndex}`)).toEqual([
      "basemap-gl@190",
      "climatology-raster@250",
      "climatology-vector@260",
      "bi-overlay@270",
      "route@380",
      "amp@420",
      "formalities-escales@500",
    ]);
  });

  test("strictly increasing stack, consistent with Leaflet panes", () => {
    const zs = PANES.map((p) => p.zIndex);
    const sorted = [...zs].sort((a, b) => a - b);
    expect(zs).toEqual(sorted);
    expect(new Set(zs).size).toBe(zs.length);

    const z = Object.fromEntries(PANES.map((p) => [p.name, p.zIndex]));
    // The sea-chart basemap stays UNDER raster tiles.
    expect(z["basemap-gl"]).toBeLessThan(LEAFLET_BUILTIN_PANES.tilePane);
    // NAVIGUIDE route above tiles, under overlayPane.
    expect(z.route).toBeGreaterThan(LEAFLET_BUILTIN_PANES.tilePane);
    expect(z.route).toBeLessThan(LEAFLET_BUILTIN_PANES.overlayPane);
    // MPA above overlayPane, stopovers above MPAs.
    expect(z.amp).toBeGreaterThan(LEAFLET_BUILTIN_PANES.overlayPane);
    expect(z["formalities-escales"]).toBeGreaterThan(z.amp);
    // Everything stays under markers (and therefore under popups).
    PANES.forEach((p) => {
      expect(p.zIndex).toBeLessThan(LEAFLET_BUILTIN_PANES.markerPane);
    });
  });

  test("createPanes applies zIndex values on the map", () => {
    const panes = {};
    const fakeMap = {
      createPane: (name) => { panes[name] = { style: {} }; },
      getPane: (name) => panes[name],
    };
    createPanes(fakeMap);
    PANES.forEach((p) => {
      expect(panes[p.name].style.zIndex).toBe(String(p.zIndex));
      if (p.pointerEvents) {
        expect(panes[p.name].style.pointerEvents).toBe(p.pointerEvents);
      }
    });
    expect(PANES.find((p) => p.name === "climatology-raster").pointerEvents).toBe("none");
    expect(PANES.find((p) => p.name === "climatology-vector").pointerEvents).toBe("none");
    expect(PANES.find((p) => p.name === "bi-overlay").pointerEvents).toBe("none");
  });

  test("EMODnet bathy stays under the climatology atlas", () => {
    expect(SCIENCE_WMS_PANES["science-wms-bathy"]).toBe(240);
    expect(SCIENCE_WMS_PANES["science-wms-bathy"]).toBeLessThan(
      PANES.find((p) => p.name === "climatology-raster").zIndex,
    );
  });
});

describe("basemap registry (locked)", () => {
  test("exactly three basemaps: dark, light, sea", () => {
    expect(Object.keys(BASEMAPS)).toEqual(["dark", "light", "sea"]);
    expect(BASEMAP_CYCLE).toEqual(["dark", "light", "sea"]);
  });

  test("raster basemaps have an https tile URL", () => {
    ["dark", "light"].forEach((k) => {
      expect(BASEMAPS[k].kind).toBe("raster");
      expect(BASEMAPS[k].url).toMatch(/^https:\/\//);
    });
  });

  test("the sea chart is a GL style with attribution and a warning", () => {
    const sea = BASEMAPS.sea;
    expect(sea.kind).toBe("gl");
    expect(sea.styleUrl).toMatch(/^https:\/\/.*style\.json$/);
    expect(sea.notForNavigation).toBe(true);
    expect(sea.attribution).toContain("Open Waters: Seamap");
    expect(sea.attribution).toContain("CC-BY 4.0");
    expect(sea.attribution).toContain("OpenStreetMap");
  });

  test("the basemap cycle returns to its starting point", () => {
    expect(nextBasemap("dark")).toBe("light");
    expect(nextBasemap("light")).toBe("sea");
    expect(nextBasemap("sea")).toBe("dark");
    // unknown value → first basemap in the cycle (never undefined)
    expect(nextBasemap("banana")).toBe("dark");
  });

  test("stripUnavailableSources drops elevation without touching other sources", () => {
    const style = {
      sources: { seamap: { type: "vector" }, elevation: { type: "raster-dem" } },
      layers: [
        { id: "sea", source: "seamap" },
        { id: "hill", source: "elevation" },
      ],
    };
    const out = stripUnavailableSources(style);
    expect(out.sources.elevation).toBeUndefined();
    expect(out.sources.seamap).toEqual({ type: "vector" });
    expect(out.layers.map((l) => l.id)).toEqual(["sea"]);
    expect(style.sources.elevation).toBeDefined();
  });

  test("the MapLibre worker is served as a static file, not via the webpack chunk", () => {
    expect(maplibreWorkerUrl("")).toBe("/maplibre/maplibre-gl-worker.mjs");
    expect(maplibreWorkerUrl("/app")).toBe("/app/maplibre/maplibre-gl-worker.mjs");
    expect(maplibreWorkerUrl("/app/")).toBe("/app/maplibre/maplibre-gl-worker.mjs");
  });
});
