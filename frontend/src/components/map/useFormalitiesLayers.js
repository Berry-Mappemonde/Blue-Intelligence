import { useEffect, useRef } from "react";
import L from "leaflet";
import api from "../../api";
import { escH, zoneStyle } from "./constants";
import { circleOpts, POPUP_OPTS } from "./points";
import { evidenceMarkOptions, evidenceTerms, portKey, registryBadgeHtml, snippetSegments, sourceTitle, verdictLabel } from "../poeRegistry";

/**
 * Formalities layers: EEZ choropleth + Ports of Entry dots (SVG, poe-ports pane).
 */

// PoE marker by zoom: a tiny amber dot with a transparent click halo on the world
// view; from zoom 4 a bigger dot with a dark outline so it reads on any coastline.
export function poeMarkerStyle(zoom) {
  const z = Number(zoom) || 2;
  if (z >= 9) return { radius: 5, weight: 1.5, color: "#121212", opacity: 1, fillOpacity: 1 };
  if (z >= 6) return { radius: 4, weight: 1.5, color: "#121212", opacity: 1, fillOpacity: 1 };
  if (z >= 4) return { radius: 2.5, weight: 1, color: "#121212", opacity: 0.9, fillOpacity: 1 };
  return { radius: 1.6, weight: 9, color: "#fbbf24", opacity: 0, fillOpacity: 0.95 };
}

const CHEVRON = '<svg class="m-disclosure" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m9 18 6-6-6-6"/></svg>';
const CHECK = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>';
const _looksFrench = (s) => /\b(le|la|les|des|du|pour|avec|sur|est|une|un|et|obligatoire|plaisance|douane|port d)\b/i.test(String(s || ""));
export default function useFormalitiesLayers({
  mapObj, eezLayerRef, eezLayersByMrgid, zoneItemsRef, poeClusterRef,
  poeMarkersById,
  mode, poeZones, poePorts, flyToZone, tRef, zoneFicheRef,
  selectedZone, selectedZoneRef, langRef,
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
      // SVG dot in the "poe-ports" pane: the visible dot is the fill; its stroke is
      // either the dark outline (zoomed in) or a transparent click halo (world view),
      // see poeMarkerStyle. applyPenRadii re-applies the style on every zoom.
      const m = L.circleMarker([lat, lon], {
        ...circleOpts("#fbbf24", { zoom, renderer }),
        ...poeMarkerStyle(zoom),
        pane: "poe-ports",
      });
      m._biZoomStyle = poeMarkerStyle;
      m.bindPopup(() => {
        const t = tRef.current;
        // Same look as the sidebar card: name, tier chip, score, verdict in words.
        // The tier and verdict come from the open zone sheet when it holds this port.
        const fiche = zoneFicheRef?.current;
        const sheetPort = fiche && Number(fiche.mrgid) === Number(p.mrgid)
          ? (fiche.ports || []).find((fp) => portKey(fp.name) === portKey(p.name))
          : null;
        // Placement only speaks up when something is off (outside the EEZ).
        const placement = p.validated || p.spatial_kind === "inland_river" || p.spatial_kind === "coastal_land"
          ? ""
          : `<span class="poe-popup__chip poe-popup__chip--danger">${escH(t("poeOutsideEez"))}${p.distance_km != null ? " ~" + escH(p.distance_km) + " km" : ""}</span>`;
        const score = sheetPort?.confidence ?? p.confidence;
        const conf = score != null
          ? `<span data-testid="poe-confidence" class="poe-popup__chip poe-popup__chip--num"><span style="color:rgb(var(--m-fg-3));margin-right:4px;">${escH(t("poeScore"))}</span>${Number(score)}</span>`
          : "";
        const tierChip = sheetPort ? registryBadgeHtml(sheetPort, t, escH) : "";
        const verdict = sheetPort ? verdictLabel(sheetPort, t) : null;
        const verdictHtml = verdict
          ? `<span class="poe-popup__verdict ${verdict.key === "pass" ? "poe-popup__verdict--pass" : ""}">${verdict.key === "pass" ? CHECK : ""}${escH(verdict.text)}</span>`
          : "";
        const srcs = (p.source_urls || []).slice(0, 3).map((u) => `
          <div class="poe-popup__src"><a href="${escH(u)}" target="_blank" rel="noreferrer" title="${escH(u)}">
            <span style="display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escH(sourceTitle(u))}</span>
            <span class="poe-popup__host">${escH(u.replace(/^https?:\/\/(www\.)?/, "").split("/")[0])}</span></a></div>`).join("");
        const anomBadge = p.spatial_anomaly
          ? `<span data-testid="poe-anomaly-badge" class="poe-popup__chip poe-popup__chip--danger">${escH(t("poeAnomaly"))}</span>`
          : "";
        const allEvidence = sheetPort?.registry?.official_evidence || [];
        const evidence = allEvidence.slice(0, 2).map((e) => {
          const { lead, trail, segments } = snippetSegments(e.snippet, evidenceTerms(sheetPort, e), evidenceMarkOptions(e));
          const body = segments.map((s) => (s.mark ? `<mark class="m-mark">${escH(s.text)}</mark>` : escH(s.text))).join("");
          return `
          <details class="poe-popup__details">
            <summary>${CHEVRON}<span>${escH(t("poeEvidenceTitle"))}: <a href="${escH(e.url)}" target="_blank" rel="noreferrer" style="color:rgb(var(--m-accent-fg));text-decoration:none;">${escH(e.domain || "")}</a></span></summary>
            <p class="poe-popup__excerpt">${lead ? "… " : ""}${body}${trail ? " …" : ""}</p>
          </details>`;
        }).join("") + (allEvidence.length > 2
          ? `<div class="poe-popup__muted">+${allEvidence.length - 2} ${escH(t("poeMoreSources"))}</div>`
          : "");
        // The seed note is written in French: shown as is in the French UI, labelled otherwise.
        const lang = langRef?.current || "en";
        const noteHtml = p.note
          ? (lang === "fr" || !_looksFrench(p.note)
            ? `<div class="poe-popup__note">${escH(p.note)}</div>`
            : `<div class="poe-popup__note"><span style="color:rgb(var(--m-fg-3));">${escH(t("poeSourceNoteFr"))}:</span> ${escH(p.note)}</div>`)
          : "";
        const meta = [p.city, p.zone_name].filter(Boolean).map(escH).join(" · ");
        return `<div class="poe-popup" style="min-width:230px;max-width:300px;">
          <div class="poe-popup__title">${escH(p.name)}</div>
          ${meta ? `<div class="poe-popup__meta">${meta}</div>` : ""}
          <div class="poe-popup__row">${tierChip}${verdictHtml}</div>
          <div class="poe-popup__row">${conf}${placement}${anomBadge}</div>
          ${noteHtml}
          ${evidence}
          ${srcs ? `<div class="poe-popup__h">${escH(t("poeSourcesTitle"))}</div>${srcs}` : ""}
          <div class="poe-popup__footer">${escH(t("poeGeocodeAttribution"))}${p.extracted_at ? " · " + escH(String(p.extracted_at).slice(0, 10)) : ""}${p.geocode_source && !/nominatim/i.test(p.geocode_source) ? " · " + escH(p.geocode_source) : ""}</div>
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
        // Whole outline visible: generous padding, the sheet's popup tip included.
        map.flyToBounds(L.latLngBounds([s, w], [n, e]), { duration: 0.8, maxZoom: 7, padding: [48, 48] });
      }
    } catch (_) { /* noop */ }
    const safety = setTimeout(open, 1400);
    return () => { clearTimeout(safety); map.off("moveend", open); };
    // eslint-disable-next-line
  }, [flyToZone]);
}
