/**
 * Single vertical order of map panes — locked source of truth.
 *
 * Inspired by Open Waters: Seamap: draw order is payload; a test
 * (`__tests__/layerOrder.test.js`) freezes the list so no accidental
 * reshuffle can change it. Leaflet landmarks (not editable):
 * tilePane 200 < overlayPane 400 < shadowPane 500 < markerPane 600 <
 * tooltipPane 650 < popupPane 700.
 */
export const LEAFLET_BUILTIN_PANES = {
  tilePane: 200,
  overlayPane: 400,
  shadowPane: 500,
  markerPane: 600,
  tooltipPane: 650,
  popupPane: 700,
};

export const PANES = [
  // Vector "Sea chart" basemap (MapLibre GL) — under raster tiles.
  { name: "basemap-gl", zIndex: 190 },
  // Weekly tippecanoe overlay — above GL Seamap, under the 7th-mode atlas.
  // An opaque GL canvas here used to hide Hs / IBTrACS (those panes sat at 250/260).
  { name: "bi-overlay", zIndex: 250, pointerEvents: "none" },
  // 7th-mode atlas — above the weekly overlay so July Hs and cyclone tracks paint.
  { name: "climatology-raster", zIndex: 280, pointerEvents: "none" },
  { name: "climatology-vector", zIndex: 290, pointerEvents: "none" },
  // NAVIGUIDE route — under clusters and markers.
  { name: "route", zIndex: 380 },
  // MPA polygons — above overlayPane, under stopovers.
  { name: "amp", zIndex: 420 },
  // Formalities stopovers — above everything except markers.
  { name: "formalities-escales", zIndex: 500 },
];

/** Create every custom pane on the map, in the locked order. */
export function createPanes(map) {
  PANES.forEach(({ name, zIndex, pointerEvents }) => {
    map.createPane(name);
    const pane = map.getPane(name);
    pane.style.zIndex = String(zIndex);
    if (pointerEvents) pane.style.pointerEvents = pointerEvents;
  });
}
