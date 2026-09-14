import {
  BI_OVERLAY_SOURCE_ID,
  absoluteOverlayUrl,
  overlayPmtilesHref,
  overlayStyle,
  overlayUrlFromEnv,
} from "../overlaySpec";

describe("overlaySpec", () => {
  test("URL : env ou copie nginx locale", () => {
    expect(overlayUrlFromEnv({})).toBe("/tiles/bi-overlay/current.pmtiles");
    expect(overlayUrlFromEnv({ REACT_APP_BI_OVERLAY_URL: "https://example.test/w.pmtiles" }))
      .toBe("https://example.test/w.pmtiles");
  });

  test("pmtiles:// sur URL absolue", () => {
    expect(absoluteOverlayUrl("/tiles/x.pmtiles", "https://bi.test")).toBe(
      "https://bi.test/tiles/x.pmtiles",
    );
    expect(overlayPmtilesHref("/tiles/x.pmtiles", "https://bi.test")).toBe(
      "pmtiles://https://bi.test/tiles/x.pmtiles",
    );
  });

  test("style MapLibre : une source, couches tippecanoe", () => {
    const style = overlayStyle("pmtiles://https://bi.test/o.pmtiles");
    expect(style.version).toBe(8);
    expect(style.sources[BI_OVERLAY_SOURCE_ID].url).toMatch(/^pmtiles:\/\//);
    const ids = style.layers.map((l) => l["source-layer"]);
    expect(ids).toEqual(expect.arrayContaining([
      "route", "amp", "projects", "marinas", "anchorages", "capitaineries", "poe",
    ]));
  });
});
