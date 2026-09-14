import { useEffect, useRef, useState } from "react";
import L from "leaflet";

import { BASEMAPS, stripUnavailableSources } from "./basemaps";
import { maplibreWorkerUrl } from "./maplibreWorker";

/**
 * Load MapLibre GL + the pmtiles:// protocol once, on demand
 * (~800 KB: nothing is paid while the user stays on raster basemaps).
 * pmtiles:// reads the self-hosted archive by byte ranges — no tile
 * server needed; static nginx is enough.
 */
let glLoader = null;
export function loadGl() {
  if (!glLoader) {
    glLoader = (async () => {
      // A single Promise.all: sequential imports would queue behind
      // API requests (6 HTTP/1.1 connections per origin).
      const [maplibreModule, , pmtilesModule] = await Promise.all([
        import("maplibre-gl"),
        import("maplibre-gl/dist/maplibre-gl.css"),
        import("pmtiles"),
        import("@maplibre/maplibre-gl-leaflet"),
      ]);
      // maplibre-gl v6 is an ESM module with named exports, no default.
      const maplibregl = maplibreModule.default ?? maplibreModule;
      // Before the first Map: the worker is not in the webpack chunk.
      if (typeof maplibregl.setWorkerUrl === "function") {
        maplibregl.setWorkerUrl(maplibreWorkerUrl());
      }
      const protocol = new pmtilesModule.Protocol();
      maplibregl.addProtocol("pmtiles", protocol.tile);
      return maplibregl;
    })();
    // A failure must not stay cached: the next pass will retry.
    glLoader.catch(() => { glLoader = null; });
  }
  return glLoader;
}

let seaStyleLoader = null;
function loadSeaStyle(styleUrl) {
  if (!seaStyleLoader) {
    seaStyleLoader = fetch(styleUrl)
      .then((r) => {
        if (!r.ok) throw new Error(`style ${r.status}`);
        return r.json();
      })
      .then((style) => stripUnavailableSources(style))
      .catch((err) => {
        seaStyleLoader = null;
        throw err;
      });
  }
  return seaStyleLoader;
}

function restoreRaster(map, tileRef) {
  if (!map || !tileRef.current) return;
  if (!map.hasLayer(tileRef.current)) tileRef.current.addTo(map);
}

function dropGlLayer(map, glRef) {
  if (!glRef.current) return;
  try {
    if (map && map.hasLayer(glRef.current)) map.removeLayer(glRef.current);
  } catch (_) { /* layer already destroyed */ }
  glRef.current = null;
}

function isWebGlFailure(err) {
  const msg = String(err?.message || err || "");
  return /WebGL|GPUInitialization|Failed to initialize/i.test(msg);
}

/**
 * Toggle raster basemap (Esri) ↔ vector sea chart (Open Waters: Seamap).
 * Returns `true` when the sea chart is shown — the caller then displays
 * the "Not for navigation" warning.
 */
export default function useNauticalBasemap({
  mapObj, tileRef, basemap, enabled = true, onGlMap,
}) {
  const glRef = useRef(null);
  const [nauticalActive, setNauticalActive] = useState(false);
  const onGlMapRef = useRef(onGlMap);
  onGlMapRef.current = onGlMap;

  // Preload on mount: on HTTP/1.1 the browser has only 6 connections
  // per origin, quickly saturated by long API requests.
  // If requested later (on click), the maplibre chunk would sit in the
  // queue behind them until the webpack timeout.
  useEffect(() => {
    loadGl().catch(() => {});
  }, []);

  useEffect(() => {
    const map = mapObj.current;
    if (!map) return undefined;
    const conf = BASEMAPS[basemap] || BASEMAPS.dark;
    let cancelled = false;
    const wantGl = conf.kind === "gl" && enabled !== false;

    if (wantGl) {
      Promise.all([
        loadGl(),
        loadSeaStyle(conf.styleUrl).catch(() => conf.styleUrl),
      ])
        .then(([, style]) => {
          if (cancelled || !mapObj.current) return;
          const m = mapObj.current;
          if (!glRef.current) {
            glRef.current = L.maplibreGL({
              style,
              pane: "basemap-gl",
              attribution: conf.attribution,
            });
          }
          if (tileRef.current && m.hasLayer(tileRef.current)) {
            m.removeLayer(tileRef.current);
          }
          try {
            if (!m.hasLayer(glRef.current)) glRef.current.addTo(m);
          } catch (err) {
            dropGlLayer(m, glRef);
            restoreRaster(m, tileRef);
            throw err;
          }
          const glMap = glRef.current.getMaplibreMap?.() || glRef.current._glMap;
          setNauticalActive(true);
          if (typeof onGlMapRef.current === "function") onGlMapRef.current(glMap || null);
          if (glMap && typeof glMap.on === "function") {
            glMap.on("error", (ev) => {
              const err = ev?.error || ev;
              if (!isWebGlFailure(err)) return;
              console.error("[carte marine] chargement impossible :", err);
              dropGlLayer(m, glRef);
              restoreRaster(m, tileRef);
              setNauticalActive(false);
              if (typeof onGlMapRef.current === "function") onGlMapRef.current(null);
            });
          }
        })
        .catch((err) => {
          // maplibre unavailable (offline, no WebGL…): keep the current raster.
          console.error("[carte marine] chargement impossible :", err);
          dropGlLayer(mapObj.current, glRef);
          restoreRaster(mapObj.current, tileRef);
          setNauticalActive(false);
          if (typeof onGlMapRef.current === "function") onGlMapRef.current(null);
        });
    } else {
      dropGlLayer(map, glRef);
      restoreRaster(map, tileRef);
      if (tileRef.current) {
        const raster = conf.kind === "raster" ? conf : BASEMAPS.dark;
        tileRef.current.setUrl(raster.url);
      }
      setNauticalActive(false);
      if (typeof onGlMapRef.current === "function") onGlMapRef.current(null);
    }
    return () => { cancelled = true; };
    // eslint-disable-next-line
  }, [basemap, enabled]);

  return nauticalActive;
}
