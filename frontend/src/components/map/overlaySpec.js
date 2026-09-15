/**
 * Spec MapLibre de l'overlay hebdomadaire tippecanoe
 * (`-L projects|marinas|anchorages|capitaineries|amp|poe|route`).
 */
export const BI_OVERLAY_SOURCE_ID = "bi-weekly";

export const OVERLAY_LAYER_COLORS = {
  projects: "#06b6d4",
  marinas: "#ef4444",
  anchorages: "#f97316",
  capitaineries: "#7dd3fc",
  amp: "#22c55e",
  poe: "#d97706",
  route: "#38bdf8",
};

export function overlayUrlFromEnv(env = process.env) {
  return env.REACT_APP_BI_OVERLAY_URL || "/tiles/bi-overlay/current.pmtiles";
}

export function absoluteOverlayUrl(raw, origin) {
  const url = raw || overlayUrlFromEnv();
  if (/^https?:\/\//i.test(url) || /^pmtiles:\/\//i.test(url)) return url;
  const base = origin || (typeof window !== "undefined" ? window.location.origin : "");
  if (!base) return url;
  return new URL(url, `${base.replace(/\/$/, "")}/`).href;
}

export function overlayPmtilesHref(raw, origin) {
  const abs = absoluteOverlayUrl(raw, origin);
  if (abs.startsWith("pmtiles://")) return abs;
  return `pmtiles://${abs}`;
}

export function overlayStyle(pmtilesHref) {
  return {
    version: 8,
    name: "Blue Intelligence overlay",
    sources: {
      [BI_OVERLAY_SOURCE_ID]: {
        type: "vector",
        url: pmtilesHref,
      },
    },
    layers: [
      {
        id: "bi-overlay-background",
        type: "background",
        paint: {
          "background-color": "#000000",
          "background-opacity": 0,
        },
      },
      {
        id: "bi-overlay-route",
        type: "line",
        source: BI_OVERLAY_SOURCE_ID,
        "source-layer": "route",
        paint: {
          "line-color": OVERLAY_LAYER_COLORS.route,
          "line-width": 2,
          "line-opacity": 0.75,
        },
      },
      {
        id: "bi-overlay-amp",
        type: "fill",
        source: BI_OVERLAY_SOURCE_ID,
        "source-layer": "amp",
        paint: {
          "fill-color": OVERLAY_LAYER_COLORS.amp,
          "fill-opacity": 0.18,
        },
      },
      ...["projects", "marinas", "anchorages", "capitaineries", "poe"].map((id) => ({
        id: `bi-overlay-${id}`,
        type: "circle",
        source: BI_OVERLAY_SOURCE_ID,
        "source-layer": id,
        paint: {
          "circle-radius": 3,
          "circle-color": OVERLAY_LAYER_COLORS[id],
          "circle-opacity": 0.85,
          "circle-stroke-width": 0.6,
          "circle-stroke-color": "#0f172a",
        },
      })),
    ],
  };
}
