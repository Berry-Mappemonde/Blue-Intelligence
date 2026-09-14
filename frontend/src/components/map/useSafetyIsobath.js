import { useEffect } from "react";

import { SAFETY_ISOBATH_LAYER_ID, safetyIsobathLayers } from "./safetyIsobathSpec";

/**
 * Color Seascape DEPARE features below the skipper threshold, on GL Seamap.
 */
export default function useSafetyIsobath({ glMap, enabled, meters }) {
  useEffect(() => {
    const map = glMap;
    if (!map || typeof map.getSource !== "function") return undefined;

    const remove = () => {
      try {
        if (map.getLayer(SAFETY_ISOBATH_LAYER_ID)) map.removeLayer(SAFETY_ISOBATH_LAYER_ID);
      } catch (_) { /* style not ready yet */ }
    };

    if (!enabled) {
      remove();
      return undefined;
    }

    const apply = () => {
      if (!map.getSource("seascape-vector")) return;
      remove();
      safetyIsobathLayers(meters).forEach((layer) => {
        try {
          map.addLayer(layer);
        } catch (err) {
          console.error("[isobathe] couche refusée :", err);
        }
      });
    };

    if (map.isStyleLoaded && map.isStyleLoaded()) apply();
    else if (typeof map.once === "function") map.once("load", apply);
    else apply();

    return () => { remove(); };
  }, [glMap, enabled, meters]);
}
