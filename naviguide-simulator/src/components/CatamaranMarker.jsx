import { useEffect, useRef } from "react";
import L from "leaflet";
import { catamaranSvg, catamaranTransform } from "../engine/catamaranIcon.js";
import { markerWorldLngs, wrapLon } from "../utils/waypointFlags.js";

function buildIconHtml() {
  return catamaranSvg(0);
}

function patchHeading(marker, bearing) {
  const svg = marker.getElement()?.querySelector('svg[data-bow="north"]');
  if (!svg) return;
  const heading = ((Number(bearing) || 0) % 360 + 360) % 360;
  svg.dataset.heading = String(heading);
  svg.style.transform = catamaranTransform(heading);
}

export function useCatamaranMarker(mapRef, {
  visible,
  lat,
  lon,
  bearing,
  onDrag,
  onDragStart,
  mapReady,
  draggable = true,
  className = "catamaran-divicon",
}) {
  const markersRef = useRef([]);

  useEffect(() => {
    const map = mapRef.current;
    const clear = () => {
      markersRef.current.forEach((m) => m.remove());
      markersRef.current = [];
    };
    if (!map || !mapReady || !visible || lat == null || lon == null) {
      clear();
      return undefined;
    }

    const makeIcon = () => L.divIcon({
      className,
      html: buildIconHtml(),
      iconSize: [64, 64],
      iconAnchor: [32, 32],
    });

    const sync = () => {
      const cam = map.getCenter()?.lng;
      const lngs = markerWorldLngs(lon, cam);
      if (markersRef.current.length !== lngs.length) {
        clear();
        markersRef.current = lngs.map((lng, i) => {
          const primary = i === 0;
          const m = L.marker([lat, lng], {
            icon: makeIcon(),
            draggable: Boolean(draggable) && primary,
            pane: "boat",
            interactive: Boolean(draggable) && primary,
          }).addTo(map);
          if (draggable && primary) {
            m.on("dragstart", () => onDragStart?.());
            m.on("drag", (e) => {
              const ll = e.target.getLatLng();
              onDrag?.({ lat: ll.lat, lon: wrapLon(ll.lng) });
            });
          }
          return m;
        });
      }
      markersRef.current.forEach((m, i) => {
        m.setLatLng([lat, lngs[i]]);
        patchHeading(m, bearing);
      });
    };

    sync();
    map.on("moveend", sync);
    return () => {
      map.off("moveend", sync);
    };
  }, [mapRef, mapReady, visible, lat, lon, bearing, onDrag, onDragStart, draggable, className]);

  useEffect(() => () => {
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];
  }, []);
}
