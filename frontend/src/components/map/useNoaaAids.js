import { useEffect, useRef } from "react";
import L from "leaflet";
import api from "../../api";
import { circleOpts } from "./points";

const COLOR = "#fbbf24";

function parseBbox(map) {
  const b = map.getBounds();
  return [
    Math.max(-180, b.getWest()),
    Math.max(-85, b.getSouth()),
    Math.min(180, b.getEast()),
    Math.min(85, b.getNorth()),
  ].map((n) => n.toFixed(4)).join(",");
}

/**
 * NOAA ENC Direct lights / buoys — US waters only (the backend filters).
 */
export default function useNoaaAids({ mapObj, enabled }) {
  const groupRef = useRef(null);
  const timerRef = useRef(null);
  const lastKey = useRef("");

  useEffect(() => {
    const map = mapObj.current;
    if (!map) return undefined;
    if (!groupRef.current) groupRef.current = L.layerGroup();
    const group = groupRef.current;

    if (!enabled) {
      if (map.hasLayer(group)) map.removeLayer(group);
      group.clearLayers();
      lastKey.current = "";
      return undefined;
    }
    if (!map.hasLayer(group)) group.addTo(map);

    const load = async () => {
      const bbox = parseBbox(map);
      if (bbox === lastKey.current) return;
      lastKey.current = bbox;
      try {
        const { data } = await api.get("/noaa/aids", { params: { bbox } });
        group.clearLayers();
        const zoom = map.getZoom();
        for (const f of data?.features || []) {
          if (f.geometry?.type !== "Point") continue;
          const [lon, lat] = f.geometry.coordinates;
          const p = f.properties || {};
          const m = L.circleMarker([lat, lon], circleOpts(COLOR, { zoom, fillOpacity: 0.85 }));
          m.bindPopup(
            `<strong>${p.name || p.kind || "NOAA"}</strong>`
            + `<div style="font-size:11px;color:#94a3b8">${p.kind || ""} · ${p.service || ""}</div>`
            + `<p style="font-size:10px;color:#64748b;margin:6px 0 0">ENC Direct — not for navigation</p>`,
          );
          group.addLayer(m);
        }
      } catch (_) {
        lastKey.current = "";
      }
    };

    const schedule = () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(load, 420);
    };
    load();
    map.on("moveend", schedule);
    return () => {
      map.off("moveend", schedule);
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [mapObj, enabled]);
}
