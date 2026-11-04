import L from "leaflet";
import { installPopupFitPolicy } from "./popupFit";

installPopupFitPolicy();

/** "Bic-tip" radius: tiny in world view, a bit more readable when zoomed in. */
export function penRadius(zoom, bump = 0) {
  const z = Number(zoom) || 2;
  let r = 0.7;
  if (z > 3) r = 0.95;
  if (z > 5) r = 1.25;
  if (z > 8) r = 1.8;
  if (z > 12) r = 2.4;
  return Math.max(0.55, r + bump);
}

export const POPUP_OPTS = {
  maxWidth: 330,
  maxHeight: 420,
  autoPan: false,
  autoClose: true,
  closeOnClick: true,
  keepInView: false,
};

/**
 * Point group (no clustering) with addLayers for existing hooks.
 * `pane` + `svg: true` draws the dots as SVG in that pane: only the painted
 * dot (and its invisible hit halo) takes clicks, the rest passes through to
 * the layers below. The default canvas renderer would swallow every click.
 */
export function makePointGroup({ pane, svg = false } = {}) {
  // tolerance 8: the dot stays tiny on screen but the click/tap area
  // around it stays comfortable (otherwise popups are unreachable).
  const renderer = svg
    ? L.svg({ padding: 0.5, ...(pane ? { pane } : {}) })
    : L.canvas({ padding: 0.5, tolerance: 8, ...(pane ? { pane } : {}) });
  const group = L.layerGroup();
  group._biRenderer = renderer;
  group.addLayers = (layers) => {
    (layers || []).forEach((lyr) => group.addLayer(lyr));
    return group;
  };
  return group;
}

export function applyPenRadii(group, zoom) {
  if (!group || typeof group.eachLayer !== "function") return;
  group.eachLayer((lyr) => {
    if (typeof lyr.setRadius !== "function") return;
    // A layer may carry its own zoom-dependent style (PoE markers: dot + halo).
    if (typeof lyr._biZoomStyle === "function") { lyr.setStyle(lyr._biZoomStyle(zoom)); return; }
    const bump = lyr._biBump || 0;
    lyr.setRadius(penRadius(zoom, bump));
  });
}

export function circleOpts(color, {
  zoom = 2, bump = 0, weight = 1, fillOpacity = 0.8, renderer,
} = {}) {
  return {
    radius: penRadius(zoom, bump),
    color,
    weight,
    fillColor: color,
    fillOpacity,
    ...(renderer ? { renderer } : {}),
  };
}
