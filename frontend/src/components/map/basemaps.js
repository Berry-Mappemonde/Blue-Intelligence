/**
 * Basemap registry.
 *
 * `raster` = classic L.tileLayer (Esri Canvas); `gl` = Open Waters: Seamap
 * vector sea chart rendered by MapLibre GL (loaded on demand via
 * maplibre-gl-leaflet — ISC licence, maplibre-gl BSD-3-Clause,
 * pmtiles BSD-3-Clause; we do NOT depend on the @openwaters/seamap npm
 * package, GPL-3.0 — we consume the served style, licensed CC-BY 4.0).
 *
 * `REACT_APP_SEAMAP_STYLE_URL` points at the self-hosted mirror in
 * production (see infra/vps/seamap/); default is the public style.
 */
import { TILE_URLS } from "./constants";

export const SEAMAP_STYLE_URL =
  process.env.REACT_APP_SEAMAP_STYLE_URL ||
  "https://tiles.openwaters.io/seamap/style.json";

export const BASEMAPS = {
  dark: {
    kind: "raster",
    url: TILE_URLS.dark,
    attribution: "&copy; Esri &copy; OpenStreetMap contributors",
  },
  light: {
    kind: "raster",
    url: TILE_URLS.light,
    attribution: "&copy; Esri &copy; OpenStreetMap contributors",
  },
  sea: {
    kind: "gl",
    styleUrl: SEAMAP_STYLE_URL,
    attribution:
      '© <a href="https://openwaters.io/charts/seamap" target="_blank" rel="noreferrer">Open Waters: Seamap</a> (CC-BY 4.0) '
      + "· © OpenStreetMap contributors · © Mapterhorn · Seascape",
    notForNavigation: true,
  },
};

export const BASEMAP_CYCLE = ["dark", "light", "sea"];

export function nextBasemap(current) {
  const idx = BASEMAP_CYCLE.indexOf(current);
  return BASEMAP_CYCLE[(idx + 1) % BASEMAP_CYCLE.length];
}

/**
 * The Seamap style references an `elevation` source (Versatiles hillshade)
 * that is often missing: each 404 tile pollutes the console and draws nothing.
 * We drop source + layers; the rest of the style is unchanged.
 */
export const SEAMAP_OPTIONAL_SOURCES = ["elevation"];

export function stripUnavailableSources(style, drop = SEAMAP_OPTIONAL_SOURCES) {
  if (!style || typeof style !== "object") return style;
  const skip = new Set(drop);
  const next = { ...style };
  if (style.sources) {
    next.sources = { ...style.sources };
    skip.forEach((id) => { delete next.sources[id]; });
  }
  if (Array.isArray(style.layers)) {
    next.layers = style.layers.filter((l) => !skip.has(l.source));
  }
  return next;
}
