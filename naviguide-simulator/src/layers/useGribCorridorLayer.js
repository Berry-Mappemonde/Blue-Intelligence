import { useEffect, useRef } from "react";
import L from "leaflet";
import { corridorForBoat } from "../utils/gribCorridor.js";
import {
  gribBarbSvg,
  pickGribSlice,
  waveHsColor,
  worldCopyLngs,
} from "../utils/gribSymbols.js";

function lonNearBox(lon, west, east) {
  const x = Number(lon);
  if (west <= east) return x >= west - 1 && x <= east + 1;
  return x >= west - 1 || x <= east + 1;
}

/** Barbules OMM + disques Hs. Jamais un rectangle de couloir. */
export function useGribCorridorLayer(mapRef, { grib, mapReady, visible, whenIso, lat, lon }) {
  const groupRef = useRef(null);

  useEffect(() => {
    const map = mapRef.current;
    if (groupRef.current) {
      groupRef.current.remove();
      groupRef.current = null;
    }
    if (!map || !mapReady || !visible || grib?.status !== "ready") return undefined;
    const box = corridorForBoat(grib.bbox, lat, lon);
    if (!box) return undefined;
    const [south, north, west, east] = box;

    const group = L.layerGroup().addTo(map);
    groupRef.current = group;

    const near = (grib.samples || []).filter((s) => (
      s.lat != null && s.lat >= south - 1 && s.lat <= north + 1
      && s.lon != null && lonNearBox(s.lon, west, east)
    ));
    const slice = pickGribSlice(near.length ? near : grib.samples, whenIso);
    for (const s of slice) {
      for (const lng of worldCopyLngs(s.lon)) {
        if (s.hs != null) {
          L.circleMarker([s.lat, lng], {
            radius: 7,
            color: waveHsColor(s.hs),
            fillColor: waveHsColor(s.hs),
            fillOpacity: 0.28,
            weight: 0,
            pane: "overlayPane",
            interactive: false,
          }).addTo(group);
        }
        if (s.windKnots == null) continue;
        L.marker([s.lat, lng], {
          icon: L.divIcon({
            className: "grib-barb",
            html: gribBarbSvg(s),
            iconSize: [32, 32],
            iconAnchor: [16, 16],
          }),
          interactive: false,
          keyboard: false,
        }).addTo(group);
      }
    }
    return () => {
      group.remove();
      groupRef.current = null;
    };
  }, [mapRef, mapReady, visible, grib, whenIso, lat, lon]);
}
