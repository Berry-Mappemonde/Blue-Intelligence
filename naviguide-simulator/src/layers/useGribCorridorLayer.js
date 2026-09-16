import { useEffect, useRef } from "react";
import L from "leaflet";
import { corridorForBoat } from "../utils/gribCorridor.js";
import {
  gribBarbSvg,
  gribDisplayPoints,
  gribRenderKey,
  waveHsColor,
} from "../utils/gribSymbols.js";
import { cameraLngForBoat, markerWorldLngs, wrapLon } from "../utils/waypointFlags.js";

function lonNearBox(lon, west, east) {
  const x = Number(lon);
  const w = Number(west);
  const e = Number(east);
  if (w <= e) return x >= w - 2 && x <= e + 2;
  return x >= w - 2 || x <= e + 2;
}

function sampleNearBox(s, south, north, west, east) {
  if (s.lat == null || s.lon == null) return false;
  if (s.lat < south - 1 || s.lat > north + 1) return false;
  const copies = markerWorldLngs(s.lon);
  return copies.some((lng) => lonNearBox(lng, west, east) || lonNearBox(lng, wrapLon(west), wrapLon(east)));
}

function cellKey(value) {
  return value == null ? null : Math.round(Number(value) * 20) / 20;
}

/** Barbules OMM + disques Hs en stencil. Jamais un rectangle de couloir. */
export function useGribCorridorLayer(mapRef, { grib, mapReady, visible, whenIso, lat, lon }) {
  const groupRef = useRef(null);
  const entriesRef = useRef(new Map());
  const latCell = cellKey(lat);
  const lonCell = cellKey(lon);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return undefined;
    if (!groupRef.current) groupRef.current = L.layerGroup().addTo(map);
    return () => {
      entriesRef.current.forEach(({ wave, wind }) => {
        wave?.remove();
        wind?.remove();
      });
      entriesRef.current.clear();
      groupRef.current?.remove();
      groupRef.current = null;
    };
  }, [mapRef, mapReady]);

  useEffect(() => {
    const map = mapRef.current;
    const group = groupRef.current;
    if (!map || !mapReady || !group) return undefined;

    const clearEntries = () => {
      entriesRef.current.forEach(({ wave, wind }) => {
        if (wave) group.removeLayer(wave);
        if (wind) group.removeLayer(wind);
      });
      entriesRef.current.clear();
    };
    if (!visible || grib?.status !== "ready") {
      clearEntries();
      return undefined;
    }

    const camLon = cameraLngForBoat(lonCell, map.getCenter()?.lng);
    const box = corridorForBoat(grib.bbox, latCell, camLon);
    if (!box) {
      clearEntries();
      return undefined;
    }
    const [south, north, west, east] = box;
    const near = (grib.samples || []).filter((s) => sampleNearBox(s, south, north, west, east));
    const slice = gribDisplayPoints(near.length ? near : grib.samples, {
      lat: latCell,
      lon: camLon,
      whenIso,
    });
    const pane = map.getPane("grib") ? "grib" : "overlayPane";
    const cam = Number.isFinite(camLon) ? camLon : map.getCenter()?.lng;
    const nextKeys = new Set();
    for (const s of slice) {
      for (const [world, lng] of markerWorldLngs(s.lon, cam).entries()) {
        const key = gribRenderKey(s, lng, world);
        if (!key) continue;
        nextKeys.add(key);
        let entry = entriesRef.current.get(key);
        if (!entry) {
          entry = { wave: null, wind: null };
          entriesRef.current.set(key, entry);
        }
        if (s.hs != null) {
          const color = waveHsColor(s.hs);
          if (!entry.wave) {
            entry.wave = L.circleMarker([s.lat, lng], {
              radius: 10,
              color,
              fillColor: color,
              fillOpacity: 0.38,
              weight: 0,
              pane,
              interactive: false,
            }).addTo(group);
          } else {
            entry.wave.setLatLng([s.lat, lng]);
            entry.wave.setStyle({ color, fillColor: color });
          }
        } else if (entry.wave) {
          group.removeLayer(entry.wave);
          entry.wave = null;
        }
        if (s.windKnots != null) {
          const html = gribBarbSvg(s);
          if (!entry.wind) {
            entry.wind = L.marker([s.lat, lng], {
              icon: L.divIcon({
                className: "grib-barb",
                html,
                iconSize: [36, 36],
                iconAnchor: [18, 18],
              }),
              pane,
              interactive: false,
              keyboard: false,
            }).addTo(group);
          } else {
            entry.wind.setLatLng([s.lat, lng]);
            const element = entry.wind.getElement();
            if (element && element.innerHTML !== html) element.innerHTML = html;
          }
        } else if (entry.wind) {
          group.removeLayer(entry.wind);
          entry.wind = null;
        }
        if (!entry.wave && !entry.wind) entriesRef.current.delete(key);
      }
    }
    entriesRef.current.forEach((entry, key) => {
      if (nextKeys.has(key)) return;
      if (entry.wave) group.removeLayer(entry.wave);
      if (entry.wind) group.removeLayer(entry.wind);
      entriesRef.current.delete(key);
    });
  }, [mapRef, mapReady, visible, grib, whenIso, latCell, lonCell]);
}
