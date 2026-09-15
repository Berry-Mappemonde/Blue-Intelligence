import { useEffect, useRef } from "react";
import L from "leaflet";
import { corridorBboxOk } from "../utils/gribCorridor.js";

function barbPoints(samples, whenIso) {
  const byKey = new Map();
  const target = whenIso ? Date.parse(whenIso) : NaN;
  for (const s of samples || []) {
    if (s.lat == null || s.lon == null || s.windKnots == null) continue;
    const key = `${Number(s.lat).toFixed(2)},${Number(s.lon).toFixed(2)}`;
    const prev = byKey.get(key);
    if (!prev) {
      byKey.set(key, s);
      continue;
    }
    if (!Number.isFinite(target)) continue;
    const dt = Math.abs(Date.parse(s.t) - target);
    const prevDt = Math.abs(Date.parse(prev.t) - target);
    if (dt < prevDt) byKey.set(key, s);
  }
  return [...byKey.values()].slice(0, 24);
}

function windColor(knots) {
  const k = Number(knots) || 0;
  if (k < 8) return "#7dd3fc";
  if (k < 16) return "#38bdf8";
  if (k < 25) return "#fbbf24";
  return "#fb7185";
}

/** Teinte + barbules sur le couloir GRIB. Pas un globe. */
export function useGribCorridorLayer(mapRef, { grib, mapReady, visible, whenIso }) {
  const groupRef = useRef(null);

  useEffect(() => {
    const map = mapRef.current;
    if (groupRef.current) {
      groupRef.current.remove();
      groupRef.current = null;
    }
    if (!map || !mapReady || !visible || grib?.status !== "ready") return undefined;
    const bbox = grib.bbox;
    if (!corridorBboxOk(bbox)) return undefined;
    const [south, north, west, east] = bbox.map(Number);

    const group = L.layerGroup().addTo(map);
    groupRef.current = group;
    L.rectangle([[south, west], [north, east]], {
      color: "#38bdf8",
      weight: 1,
      fillColor: "#0ea5e9",
      fillOpacity: 0.1,
      pane: "overlayPane",
      interactive: false,
    }).addTo(group);

    for (const s of barbPoints(grib.samples, whenIso)) {
      const going = ((Number(s.dirFromDeg) || 0) + 180) % 360;
      const rad = (going * Math.PI) / 180;
      const len = 0.18 + Math.min(0.35, (Number(s.windKnots) || 0) / 80);
      const dest = L.latLng(s.lat + Math.cos(rad) * len, s.lon + Math.sin(rad) * len);
      L.polyline([[s.lat, s.lon], dest], {
        color: windColor(s.windKnots),
        weight: 2,
        opacity: 0.85,
        interactive: false,
      }).addTo(group);
    }
    return () => {
      group.remove();
      groupRef.current = null;
    };
  }, [mapRef, mapReady, visible, grib, whenIso]);
}
