import { useEffect, useRef } from "react";
import L from "leaflet";

import { loadGl } from "./useNauticalBasemap";
import { absoluteOverlayUrl, overlayPmtilesHref, overlayStyle, overlayUrlFromEnv } from "./overlaySpec";

/**
 * Overlay tippecanoe hebdomadaire — second contexte GL sur le pane
 * `bi-overlay` (270), sous la route Leaflet.
 */
export default function useBiOverlay({ mapObj, enabled, url }) {
  const glRef = useRef(null);

  useEffect(() => {
    const map = mapObj.current;
    if (!map) return undefined;
    let cancelled = false;

    if (!enabled) {
      dropOverlay(map, glRef);
      return undefined;
    }

    const raw = url || overlayUrlFromEnv();
    const abs = absoluteOverlayUrl(raw);
    const href = overlayPmtilesHref(abs);

    loadGl()
      .then(() => {
        if (cancelled || !mapObj.current) return;
        const m = mapObj.current;
        if (!glRef.current) {
          glRef.current = L.maplibreGL({
            style: overlayStyle(href),
            pane: "bi-overlay",
            attribution: "© Blue Intelligence — overlay hebdomadaire",
          });
        }
        try {
          if (!m.hasLayer(glRef.current)) glRef.current.addTo(m);
        } catch (err) {
          console.error("[overlay BI] chargement impossible :", err);
          dropOverlay(m, glRef);
        }
      })
      .catch((err) => {
        console.error("[overlay BI] MapLibre indisponible :", err);
        dropOverlay(mapObj.current, glRef);
      });

    return () => {
      cancelled = true;
    };
  }, [mapObj, enabled, url]);
}

function dropOverlay(map, glRef) {
  if (!glRef.current) return;
  try {
    if (map && map.hasLayer(glRef.current)) map.removeLayer(glRef.current);
  } catch (_) { /* déjà détruit */ }
  glRef.current = null;
}
