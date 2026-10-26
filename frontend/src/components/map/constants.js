/** Shared map-layer constants (tiles, colors, styles, helpers). */

export const TILE_URLS = {
  dark: "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
  light: "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
};

export const FALLBACK_COLORS = {
  "MPA": "#00f0ff", "Conservation": "#39ff14", "Research": "#c084fc",
  "Fisheries": "#fbbf24", "Policy & Advocacy": "#f472b6", "Pollution": "#ff4a4a",
  "Coastal & Habitat": "#34d399", "Education": "#60a5fa", "Other": "#94a3b8",
};

// Formalities mode = world EEZ choropleth + PoE markers.
export const ZONE_COLORS = {
  non_generee: "#64748b", ia: "#fbbf24", ia_sans_source: "#fbbf24", erreur: "#ff4a4a",
};

/** ProtectedSeas fishing-protection level (LFP 0–5). */
export const LFP_COLORS = {
  0: "#64748b",
  1: "#86efac",
  2: "#4ade80",
  3: "#38bdf8",
  4: "#f59e0b",
  5: "#ef4444",
};

export const ampStyle = (lfp) => {
  const n = Number(lfp);
  const color = LFP_COLORS[n] || LFP_COLORS[0];
  return {
    color,
    weight: 1.4,
    opacity: 0.9,
    fillColor: color,
    fillOpacity: n >= 4 ? 0.28 : n >= 3 ? 0.18 : 0.12,
  };
};

// EEZ polygons are neutral hairlines (generated a little stronger than not
// generated, errors in the danger colour); only the selected zone is amber, so
// amber otherwise stays reserved for the PoE markers.
export const ZONE_SELECTED_COLOR = "#fbbf24";
export const ZONE_NEUTRAL_LINE = "#5e5e5e";
export const ZONE_NEUTRAL_FILL = "#8f8f8f";
export const ZONE_ERROR_COLOR = "#eb5a5a";
export const zoneStyle = (status, selected = false) => {
  const s = status || "non_generee";
  if (selected) {
    return { color: ZONE_SELECTED_COLOR, weight: 1.5, opacity: 0.95, fillColor: ZONE_SELECTED_COLOR, fillOpacity: 0.05, dashArray: null };
  }
  const generated = s === "ia" || s === "ia_sans_source";
  const erreur = s === "erreur";
  // Generated: solid fg-3 hairline. Not generated: dotted fg-4. No official source: dashed.
  return {
    color: erreur ? ZONE_ERROR_COLOR : generated ? ZONE_NEUTRAL_FILL : ZONE_NEUTRAL_LINE,
    weight: 1,
    opacity: erreur ? 0.7 : generated ? 0.6 : 0.55,
    fillColor: erreur ? ZONE_ERROR_COLOR : ZONE_NEUTRAL_FILL,
    fillOpacity: erreur ? 0.04 : generated ? 0.04 : 0.015,
    dashArray: s === "ia_sans_source" ? "4 4" : s === "non_generee" ? "1 4" : null,
    lineCap: s === "non_generee" ? "round" : "butt",
  };
};

export const flagEmoji = (iso2) => {
  if (!iso2 || iso2.length !== 2) return "🌐";
  const cc = iso2.toUpperCase();
  return String.fromCodePoint(0x1f1e6 + cc.charCodeAt(0) - 65, 0x1f1e6 + cc.charCodeAt(1) - 65);
};

/** HTML escape for any content injected into Leaflet popups. */
export const escH = (s) => String(s ?? "")
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;").replace(/'/g, "&#39;");

// Neutral route styling that reads on both dark and light basemaps.
// Two-layer stroke (dark casing + light main) gives contrast in every context.
export const ROUTE_MAIN_COLOR = "#e2e8f0";     // slate-200 top line
export const ROUTE_CASING_COLOR = "#0f172a";   // deep navy casing for contrast on light map
export const ROUTE_MAIN_WEIGHT = 2.5;
export const ROUTE_CASING_WEIGHT = 5;
export const ESCALE_FILL = "#f8fafc";
export const ESCALE_STROKE = "#0f172a";
export const INTERMEDIATE_FILL = "#94a3b8";
export const INTERMEDIATE_STROKE = "#475569";
