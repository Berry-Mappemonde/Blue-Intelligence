import { useEffect, useRef } from "react";
import L from "leaflet";
import api from "../../api";
import { escH, zoneStyle } from "./constants";
import { circleOpts, POPUP_OPTS } from "./points";
import { portKey, registryBadgeHtml, verdictLabel } from "../poeRegistry";

/**
 * Formalities layers: EEZ choropleth + Ports of Entry dots (canvas).
 */
export default function useFormalitiesLayers({
  mapObj, eezLayerRef, eezLayersByMrgid, zoneItemsRef, poeClusterRef,
  poeMarkersById,
  mode, poeZones, poePorts, flyToZone, tRef, zoneFicheRef,
  selectedZone, selectedZoneRef,
}) {
  const eezSigRef = useRef("");
  const poeSigRef = useRef("");

  useEffect(() => {
    if (mode !== "formalities") return;
    const layer = eezLayerRef.current;
    if (!layer) return;
    const ids = (poeZones || []).map((z) => z.mrgid).sort().join(",");
    if (ids === eezSigRef.current) return;
    eezSigRef.current = ids;
    (async () => {
      try {
        const res = await api.get("/poe/zones/geojson");
        const data = res.data;
        layer.clearLayers();
        if (eezLayersByMrgid?.current) eezLayersByMrgid.current.clear();
        if ((data?.features || []).length) layer.addData(data);
      } catch (e) {
        eezSigRef.current = "";
      }
    })();
    // eslint-disable-next-line
  }, [mode, poeZones]);

  useEffect(() => {
    const byMrgid = new Map();
    for (const z of poeZones || []) byMrgid.set(z.mrgid, z);
    zoneItemsRef.current = byMrgid;
    const layer = eezLayerRef.current;
    if (layer) {
      layer.eachLayer((lyr) => {
        const mrgid = lyr.feature?.properties?.mrgid;
        const selected = selectedZoneRef?.current != null && Number(selectedZoneRef.current) === Number(mrgid);
        try { lyr.setStyle(zoneStyle(byMrgid.get(mrgid)?.status, selected)); } catch (_) { /* noop */ }
      });
    }
    const map = mapObj.current;
    const popup = map?._popup;
    if (popup && typeof popup.update === "function") {
      try { popup.update(); } catch (_) { /* noop */ }
    }
    // eslint-disable-next-line
  }, [poeZones]);

  // Only the selected polygon is amber; the previous one goes back to neutral.
  useEffect(() => {
    const layer = eezLayerRef.current;
    if (!layer) return;
    layer.eachLayer((lyr) => {
      const mrgid = lyr.feature?.properties?.mrgid;
      const selected = selectedZone != null && Number(selectedZone) === Number(mrgid);
      try {
        lyr.setStyle(zoneStyle(zoneItemsRef.current.get(mrgid)?.status, selected));
        if (selected && typeof lyr.bringToFront === "function") lyr.bringToFront();
      } catch (_) { /* noop */ }
    });
    // eslint-disable-next-line
  }, [selectedZone]);

  useEffect(() => {
    const cluster = poeClusterRef.current;
    const map = mapObj.current;
    if (!cluster) return;
    const feats = poePorts?.features || [];
    const sig = feats.map((f) => `${f.properties.id}|${f.properties.validated ? 1 : 0}|${f.properties.osm_confidence ?? ""}|${f.properties.confidence ?? ""}|${f.properties.spatial_anomaly ? 1 : 0}`).join(",");
    if (sig === poeSigRef.current && cluster.getLayers().length) return;
    poeSigRef.current = sig;
    cluster.clearLayers();
    if (poeMarkersById?.current) poeMarkersById.current.clear();
    const renderer = cluster._biRenderer;
    const zoom = map ? map.getZoom() : 2;
    const markers = feats.map((f) => {
      const [lon, lat] = f.geometry.coordinates;
      const p = f.properties;
      // SVG dot in the "poe-ports" pane: the visible dot is the fill; the wide
      // transparent stroke is the click target (SVG hit-tests painted strokes
      // whatever their opacity), like the canvas tolerance it replaces.
      const m = L.circleMarker([lat, lon], {
        ...circleOpts("#fbbf24", { zoom, bump: 0.5, fillOpacity: 0.95, renderer }),
        weight: 9,
        opacity: 0,
        pane: "poe-ports",
      });
      m._biBump = 0.5; // applyPenRadii keeps the fill radius on zoom
      m.bindPopup(() => {
        const t = tRef.current;
        // Same look as the sidebar card: name, tier chip, score, verdict in words.
        // The tier and verdict come from the open zone sheet when it holds this port.
        const fiche = zoneFicheRef?.current;
        const sheetPort = fiche && Number(fiche.mrgid) === Number(p.mrgid)
          ? (fiche.ports || []).find((fp) => portKey(fp.name) === portKey(p.name))
          : null;
        const placement = p.spatial_kind === "inland_river"
          ? `<span class="poe-popup__chip poe-popup__chip--ok">${escH(t("poeInlandRiver"))}</span>`
          : p.spatial_kind === "coastal_land"
          ? `<span class="poe-popup__chip poe-popup__chip--ok">${escH(t("poeCoastalLand"))}</span>`
          : p.validated
          ? `<span class="poe-popup__chip poe-popup__chip--ok">${escH(t("poeValidated"))}</span>`
          : `<span class="poe-popup__chip poe-popup__chip--danger">${escH(t("poeOutsideEez"))}${p.distance_km != null ? " ~" + escH(p.distance_km) + " km" : ""}</span>`;
        const score = sheetPort?.confidence ?? p.confidence;
        const conf = score != null
          ? `<span data-testid="poe-confidence" class="poe-popup__chip poe-popup__chip--num"><span style="color:rgb(var(--m-fg-3));margin-right:4px;">${escH(t("poeScore"))}</span>${Number(score)}</span>`
          : "";
        const tierChip = sheetPort ? registryBadgeHtml(sheetPort, t, escH) : "";
        const verdict = sheetPort ? verdictLabel(sheetPort, t) : null;
        const verdictHtml = verdict
          ? `<span class="poe-popup__verdict ${verdict.key === "pass" ? "poe-popup__verdict--pass" : ""}">${escH(verdict.text)}</span>`
          : "";
        const srcs = (p.source_urls || []).slice(0, 3).map((u) => `
          <div class="poe-popup__src"><a href="${escH(u)}" target="_blank" rel="noreferrer" title="${escH(u)}" style="word-break:break-all;">${escH(u.replace(/^https?:\/\/(www\.)?/, ""))}</a></div>`).join("");
        let osmBadge = "";
        if (p.osm_confidence != null) {
          const c = Number(p.osm_confidence);
          const label = c > 0
            ? `${escH(t("poeOsmConfidence"))} ${c.toFixed(2)}`
            : escH(t("poeOsmNoMatch"));
          const tags = (p.osm_tags || []).join(", ");
          osmBadge = `<span data-testid="poe-osm-badge" title="${escH(tags)}" class="poe-popup__chip poe-popup__chip--num">${label}</span>`;
        }
        const anomBadge = p.spatial_anomaly
          ? `<span data-testid="poe-anomaly-badge" class="poe-popup__chip poe-popup__chip--danger">${escH(t("poeAnomaly"))}</span>`
          : "";
        const evidence = (sheetPort?.registry?.official_evidence || []).slice(0, 2).map((e) => `
          <details class="poe-popup__details" style="margin-top:6px;">
            <summary>${escH(t("poeEvidenceTitle"))}: <a href="${escH(e.url)}" target="_blank" rel="noreferrer" style="color:rgb(var(--m-accent-fg));text-decoration:none;">${escH(e.domain || "")}</a> (${escH(t(e.evidence_source === "stored_snippet" ? "poeEvidenceStored" : "poeEvidenceFetched"))})</summary>
            <p class="poe-popup__excerpt">${escH(e.snippet || "")}</p>
          </details>`).join("");
        const meta = [p.city, p.zone_name].filter(Boolean).map(escH).join(" · ");
        return `<div class="poe-popup" style="min-width:230px;max-width:300px;">
          <div class="poe-popup__title">${escH(p.name)}</div>
          ${meta ? `<div class="poe-popup__meta">${meta}</div>` : ""}
          <div class="poe-popup__row">${tierChip}${verdictHtml}</div>
          <div class="poe-popup__row">${conf}${placement}${osmBadge}${anomBadge}</div>
          ${p.note ? `<div class="poe-popup__note">${escH(p.note)}</div>` : ""}
          ${evidence}
          ${srcs ? `<div class="poe-popup__h">${escH(t("poeSourcesTitle"))}</div>${srcs}` : ""}
          <div class="poe-popup__footer">${escH(t("poeGeocodeAttribution"))}${p.extracted_at ? " · " + escH(String(p.extracted_at).slice(0, 10)) : ""}${p.geocode_source ? " · " + escH(p.geocode_source) : ""}</div>
        </div>`;
      }, { ...POPUP_OPTS, maxWidth: 310 });
      if (poeMarkersById?.current && p.id) poeMarkersById.current.set(p.id, m);
      return m;
    });
    cluster.addLayers(markers);
    // eslint-disable-next-line
  }, [poePorts]);

  useEffect(() => {
    if (!flyToZone) return;
    const map = mapObj.current;
    if (!map) return;
    const [w, s, e, n] = flyToZone.bbox;
    const anchor = flyToZone.anchor;
    const anchorLatLng = anchor ? L.latLng(anchor[1], anchor[0]) : null;
    const open = () => {
      const lyr = eezLayersByMrgid.current.get(flyToZone.mrgid);
      if (!lyr) return;
      let at = anchorLatLng;
      if (at) {
        const b = map.getBounds();
        const mLng = (b.getEast() - b.getWest()) * 0.12;
        const mLat = (b.getNorth() - b.getSouth()) * 0.12;
        at = L.latLng(
          Math.min(Math.max(at.lat, b.getSouth() + mLat), b.getNorth() - mLat),
          Math.min(Math.max(at.lng, b.getWest() + mLng), b.getEast() - mLng),
        );
      }
      try { lyr.openPopup(at || undefined); } catch (_) { /* not attached yet */ }
    };
    map.once("moveend", open);
    try {
      if (e - w > 350 && anchorLatLng) {
        map.flyTo(anchorLatLng, 5, { duration: 0.8 });
      } else {
        map.flyToBounds(L.latLngBounds([s, w], [n, e]), { duration: 0.8, maxZoom: 7, padding: [30, 30] });
      }
    } catch (_) { /* noop */ }
    const safety = setTimeout(open, 1400);
    return () => { clearTimeout(safety); map.off("moveend", open); };
    // eslint-disable-next-line
  }, [flyToZone]);
}
