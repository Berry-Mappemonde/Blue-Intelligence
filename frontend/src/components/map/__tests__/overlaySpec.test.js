import {
  BI_OVERLAY_SOURCE_ID,
  absoluteOverlayUrl,
  overlayPmtilesHref,
  overlayStyle,
  overlayUrlFromEnv,
} from "../overlaySpec";

describe("overlaySpec", () => {
  test("URL: env or local nginx copy", () => {
    expect(overlayUrlFromEnv({})).toBe("/tiles/bi-overlay/current.pmtiles");
    expect(overlayUrlFromEnv({ REACT_APP_BI_OVERLAY_URL: "https://example.test/w.pmtiles" }))
      .toBe("https://example.test/w.pmtiles");
  });

  test("pmtiles:// on an absolute URL", () => {
    expect(absoluteOverlayUrl("/tiles/x.pmtiles", "https://bi.test")).toBe(
      "https://bi.test/tiles/x.pmtiles",
    );
    expect(overlayPmtilesHref("/tiles/x.pmtiles", "https://bi.test")).toBe(
      "pmtiles://https://bi.test/tiles/x.pmtiles",
    );
  });

  test("MapLibre style: one source, tippecanoe layers", () => {
    const style = overlayStyle("pmtiles://https://bi.test/o.pmtiles");
    expect(style.version).toBe(8);
    expect(style.sources[BI_OVERLAY_SOURCE_ID].url).toMatch(/^pmtiles:\/\//);
    expect(style.layers[0]).toMatchObject({
      id: "bi-overlay-background",
      type: "background",
      paint: { "background-opacity": 0 },
    });
    const ids = style.layers.map((l) => l["source-layer"]);
    expect(ids).toEqual(expect.arrayContaining([
      "route", "amp", "projects", "marinas", "anchorages", "capitaineries", "poe",
    ]));
  });
});
