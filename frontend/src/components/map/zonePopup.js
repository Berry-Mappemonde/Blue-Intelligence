import { escH } from "./constants";
import { zoneDisplayName, zoneSubtitle } from "./zoneLabel";
import { registryBadgeHtml, sourceTitle, verdictLabel } from "../poeRegistry";

/**
 * HTML popup for a VLIZ polygon sheet: kept TD URLs,
 * PoE list, BU URL per port. No Generate button.
 * Markup classes live in index.css (.poe-popup*), shared with the port popup.
 */

function _tdUrl(fiche, z) {
  return fiche?.url_td?.url
    || (fiche?.sources_td || [])[0]?.url
    || (z.sources_td || [])[0]?.url
    || (Array.isArray(z.sources) && z.sources[0]?.url)
    || "";
}

function _tdRecs(fiche, z) {
  const list = (fiche?.sources_td || []).filter((rec) => rec?.url);
  if (list.length) return list;
  const one = _tdUrl(fiche, z);
  return one ? [{ url: one, from_arm: fiche?.url_td?.from_arm }] : [];
}

function _buUrl(p) {
  if (typeof p?.url_bu === "string") return p.url_bu;
  return p?.url_bu?.url || (p?.source_urls || [])[0] || "";
}

function _pathHint(url) {
  try {
    const leaf = decodeURIComponent(new URL(url).pathname).split("/").filter(Boolean).pop() || "";
    if (leaf.length < 3) return "";
    return leaf.length > 52 ? `${leaf.slice(0, 50)}…` : leaf;
  } catch (_) {
    return "";
  }
}

const EXT_ICON = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></svg>';

function _tdBlock(t, recs) {
  const rows = (recs || []).map((rec, i) => {
    const url = rec?.url || "";
    const both = rec?.from_arm === "both";
    const host = (url || "").replace(/^https?:\/\/(www\.)?/, "").split("/")[0];
    const leaf = url ? _pathHint(url) : "";
    const testId = i === 0 ? "poe-fiche-popup-td-url" : `poe-fiche-popup-td-url-${i}`;
    return `<div class="poe-popup__src">
        <a href="${escH(url)}" target="_blank" rel="noreferrer" data-testid="${testId}" title="${escH(leaf || url)}">
          <span style="display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escH(sourceTitle(url))}</span>
          <span class="poe-popup__host">${escH(host)}</span>
        </a>
        ${both ? `<span class="poe-popup__chip">${escH(t("poeSourceBoth"))}</span>` : ""}
      </div>`;
  }).join("");
  const link = rows
    || `<div class="poe-popup__muted">${escH(t("poeFicheEmptyTd"))}</div>`;
  return `<div data-testid="poe-fiche-popup-td">
    <div class="poe-popup__h">${escH(t("poeSourcesTd"))}</div>
    ${link}
  </div>`;
}

/**
 * Official sources (deduplicated, clickable) from the V2 payload.
 * Kept consistent between popup and sidebar so both show the same count.
 */
function _officialSourcesBlock(t, sources) {
  const list = (sources || []).filter((u) => u);
  if (!list.length) return "";
  const links = list.map((u, i) => `
    <div class="poe-popup__src">
      <a href="${escH(u)}" target="_blank" rel="noopener noreferrer"
         data-testid="poe-fiche-popup-official-source-${i}" title="${escH(u)}"
         style="word-break:break-all;">${escH(u.replace(/^https?:\/\/(www\.)?/, ""))}</a>
    </div>`).join("");
  return `<div data-testid="poe-fiche-popup-official-sources">
    <div class="poe-popup__h">${escH(t("poeSourcesTitle"))}</div>
    ${links}
  </div>`;
}

function _portsBlock(t, ports) {
  const rows = (ports || []).slice(0, 24).map((p) => {
    const href = _buUrl(p);
    const badge = registryBadgeHtml(p, t, escH);
    const score = p.confidence;
    const verdict = verdictLabel(p, t);
    const scoreHtml = score != null
      ? `<span class="poe-popup__port-score" title="${escH(t("poeConfidence"))}"><span style="color:rgb(var(--m-fg-3));">${escH(t("poeScore"))}</span> ${Number(score)}</span>`
      : "<span></span>";
    const verdictHtml = verdict
      ? `<span class="poe-popup__verdict ${verdict.key === "pass" ? "poe-popup__verdict--pass" : ""}">${escH(verdict.text)}</span>`
      : "";
    const link = href
      ? `<a href="${escH(href)}" target="_blank" rel="noreferrer" data-testid="poe-fiche-popup-port-bu" title="${escH(href)}" style="color:rgb(var(--m-fg-3));margin-left:auto;display:inline-flex;">${EXT_ICON}</a>`
      : "";
    return `<div class="poe-popup__port">
      <span class="poe-popup__port-name" title="${escH(p.name)}">${escH(p.name)}</span>${scoreHtml}
      <span class="poe-popup__port-status">${badge}${verdictHtml}${link}</span>
    </div>`;
  }).join("");
  const more = (ports || []).length > 24
    ? `<div class="poe-popup__muted">+${(ports.length - 24)} ${escH(t("poeMore"))}</div>`
    : "";
  return `<div data-testid="poe-fiche-popup-ports">
    <div class="poe-popup__h">${escH(t("poeFichePorts"))} <span style="color:rgb(var(--m-fg-3));font-variant-numeric:tabular-nums;">${(ports || []).length}</span></div>
    ${rows || `<div class="poe-popup__muted">${escH(t("poeFicheNoPorts"))}</div>`}
    ${more}
  </div>`;
}

function _portsFromGeojson(mrgid, poePorts) {
  const feats = poePorts?.features || poePorts || [];
  const rows = [];
  for (const f of feats) {
    const p = f.properties || f;
    if (p.mrgid !== mrgid) continue;
    rows.push({
      id: p.id,
      name: p.name,
      confidence: p.confidence,
      url_bu: p.url_bu,
      source_urls: p.source_urls || [],
    });
  }
  rows.sort((a, b) => String(a.name || "").localeCompare(String(b.name || "")));
  return rows;
}

export function zonePopupHtml(mrgid, props, { tRef, zoneItemsRef, zoneFicheRef, poePortsRef }) {
  const t = tRef.current;
  const z = zoneItemsRef.current.get(mrgid) || props || {};
  const fiche = (zoneFicheRef?.current && Number(zoneFicheRef.current.mrgid) === Number(mrgid))
    ? zoneFicheRef.current
    : null;
  const status = z.status || "non_generee";
  const statusLabel = {
    non_generee: t("poeStatusNonGeneree"), ia: t("poeStatusIa"),
    ia_sans_source: t("poeStatusIaSansSource"), erreur: t("poeStatusErreur"),
  }[status];
  const gen = z.generated_at ? String(z.generated_at).slice(0, 10) : null;
  const tdRecs = _tdRecs(fiche, z);
  const ports = fiche?.ports || _portsFromGeojson(mrgid, poePortsRef?.current);
  const officialSources = fiche?.official_sources || [];
  const noSourceWarn = status === "ia_sans_source"
    ? `<div class="poe-popup__warn">${escH(t("poeNoSourceWarning"))}</div>`
    : "";
  const errHtml = z.last_error
    ? `<div class="poe-popup__warn">${escH(t("poeLastError"))}: ${escH(z.last_error)}</div>` : "";
  // The sidebar sheet already lists the sources when it is open for this zone:
  // the popup then keeps only what the map needs (status, ports, tiers).
  const sourcesHtml = fiche ? "" : `${_tdBlock(t, tdRecs)}${_officialSourcesBlock(t, officialSources)}`;
  const body = `${noSourceWarn}${errHtml}${sourcesHtml}${_portsBlock(t, ports)}`;
  const polType = z.pol_type || props?.pol_type;
  const confAvg = fiche?.confidence_avg ?? z.confidence_avg;
  const unclosHtml = z.unclos && z.unclos.code
    ? `<div data-testid="zone-unclos-block" class="poe-popup__info">
        <div style="font-weight:500;color:rgb(var(--m-fg-2));">${escH(t("poeUnclosTitle"))}${z.unclos.basis ? ` (${escH(z.unclos.basis)})` : ""}</div>
        <div style="margin-top:2px;">${escH(t("poeUnclos_" + z.unclos.code) || z.unclos.code)}</div>
      </div>`
    : "";
  const nPorts = ports.length || z.poe_count || 0;
  // The common status (generated from official sources) is implied by the port list;
  // only the exceptions are labelled.
  const statusChip = status === "ia" ? "" : `<span class="poe-popup__chip ${status === "erreur" ? "poe-popup__chip--danger" : ""}">${escH(statusLabel)}</span>`;
  const subtitle = zoneSubtitle({ ...props, ...z }) || (polType && polType !== "200NM" ? polType : "");
  return `
    <div data-testid="poe-zone-fiche-popup" class="poe-popup" style="max-width:100%;">
      <div data-testid="poe-fiche-popup-title" class="poe-popup__title">${escH(zoneDisplayName({ ...props, ...z }, t))}</div>
      ${subtitle ? `<div class="poe-popup__meta">${escH(subtitle)}${gen ? ` · ${escH(t("poeGeneratedAt"))} ${escH(gen)}` : ""}</div>` : (gen ? `<div class="poe-popup__meta">${escH(t("poeGeneratedAt"))} ${escH(gen)}</div>` : "")}
      <div class="poe-popup__row">
        <span class="poe-popup__chip poe-popup__chip--num">${nPorts} ${escH(t("poePortsCount"))}</span>
        ${confAvg != null ? `<span data-testid="zone-confidence" class="poe-popup__chip poe-popup__chip--num">${escH(t("poeConfidenceAvg"))} ${Number(confAvg)}</span>` : ""}
        ${statusChip}
        ${z.stale ? `<span class="poe-popup__chip" title="${escH(t("poeStaleTooltip"))}">${escH(t("poeStale"))}</span>` : ""}
      </div>
      ${unclosHtml}
      ${body}
      <div class="poe-popup__footer">${escH(t("poeEezAttribution"))}</div>
    </div>`;
}
