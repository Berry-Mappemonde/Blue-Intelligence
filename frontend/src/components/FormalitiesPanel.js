import { ArrowLeft, ChevronRight, Info, Search } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { restoreFocus, zoneRowTestId } from "../lib/a11y";
import ZoneFiche from "./ZoneFiche";
import { TIER_ORDER, tierGlyphSvg } from "./poeRegistry";
import { zoneDisplayName, zoneSearchHaystack, zoneSubtitle } from "./map/zoneLabel";

// Refactor 2026-06 — Formalities mode = world map [EEZ -> Ports of Entry].
// The sidebar lists the ~285 world EEZs (VLIZ Marine Regions) with their
// generation status and PoE count. Clicking a row flies to the EEZ polygon
// and opens its popup on the map.

const STATUS_LABEL_KEY = {
  non_generee:    "poeStatusNonGeneree",
  ia:             "poeStatusIa",
  ia_sans_source: "poeStatusIaSansSource",
  erreur:         "poeStatusErreur",
};

// Mirrors zoneStyle() in map/constants.js: neutral hairlines, amber only when selected.
const ZONE_SWATCH = {
  ia: { background: "rgba(143,143,143,0.10)", border: "1px solid #8f8f8f" },
  non_generee: { background: "rgba(143,143,143,0.03)", border: "1px dotted #6f6f6f" },
  erreur: { background: "rgba(235,90,90,0.10)", border: "1px solid #eb5a5a" },
  selected: { background: "rgba(251,191,36,0.14)", border: "1px solid #fbbf24" },
};

const fmtInt = (n, lang) => Number(n || 0).toLocaleString(lang === "fr" ? "fr-FR" : "en-GB");

/** Tier glyph (status shape + colour), shared with the cards and popups. */
function TierGlyph({ tier }) {
  // Static SVG built by tierGlyphSvg(); no user content inside.
  return <span className="tier-glyph" dangerouslySetInnerHTML={{ __html: tierGlyphSvg(tier) }} />;
}

export default function FormalitiesPanel({ t, lang, zones, zonesLoading, selectedZone, onSelectZone, fiche, ficheLoading, onFlyToPort, onVerify, verifyState }) {
  const [q, setQ] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  // "All zones" hands focus back to the row of the zone that was open.
  const returnToRowRef = useRef(null);
  useEffect(() => {
    if (selectedZone != null || returnToRowRef.current == null) return;
    const id = zoneRowTestId(returnToRowRef.current);
    returnToRowRef.current = null;
    const row = id ? document.querySelector(`[data-testid="${id}"]`) : null;
    if (row) {
      try { row.scrollIntoView({ block: "nearest" }); } catch (_) { /* noop */ }
      restoreFocus(row);
    }
  }, [selectedZone]);

  const items = zones?.items || [];
  const summary = zones?.summary || {};
  const byStatus = summary.by_status || {};
  const generatedCount = (byStatus.ia || 0) + (byStatus.ia_sans_source || 0);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return items.filter((z) => {
      if (statusFilter !== "All" && (z.status || "non_generee") !== statusFilter) return false;
      if (!needle) return true;
      return zoneSearchHaystack(z).includes(needle);
    });
  }, [items, q, statusFilter]);

  // The common case (generated from official sources) says nothing in the row; only
  // the exceptions are labelled, so the label carries information when it appears.
  const statusNote = (status) => {
    const s = status || "non_generee";
    if (s === "ia") return null;
    const danger = s === "erreur";
    return (
      <span className={`text-[12px] leading-4 shrink-0 ${danger ? "text-m-danger-fg" : "text-m-fg3"}`}>
        {t(STATUS_LABEL_KEY[s] || "poeStatusNonGeneree")}
      </span>
    );
  };

  const totalPorts = summary.total_ports || 0;

  return (
    <aside
      className="w-[360px] shrink-0 flex flex-col border-r border-m-line bg-m-shell min-h-0 font-ui text-[13px] leading-[18px] text-m-fg"
      data-testid="formalities-panel"
    >
      {/* Header + search — same structure as the other modes, Meridian type roles */}
      <div className="px-4 pt-4 pb-3 border-b border-m-line shrink-0">
        <div className="flex items-baseline justify-between gap-3">
          {/* Same label as the mode button in the header (consistency). */}
          <h2 className="text-[15px] leading-5 font-medium text-m-fg">{t("modeFormalities")}</h2>
          <span className="text-[12px] leading-4 text-m-fg3 m-num" data-testid="poe-zones-count">
            {fmtInt(items.length, lang)} {t("poeZonesCount")}
          </span>
        </div>

        <p
          data-testid="formalities-disclaimer"
          className="mt-2 flex items-start gap-2 text-[12px] leading-4 text-m-fg2"
        >
          <Info size={14} strokeWidth={1.75} className="mt-px shrink-0 text-m-fg3" aria-hidden="true" />
          <span>{t("formalitiesDisclaimer")}</span>
        </p>

        <div className="relative mt-3">
          <Search size={14} strokeWidth={1.75} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-m-fg3 pointer-events-none" aria-hidden="true" />
          <input
            data-testid="poe-search-input"
            type="search"
            name="poe-search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={t("poeSearch")}
            aria-label={t("poeSearch")}
            className="m-field !pl-8"
          />
        </div>

        {/* Filter by status */}
        <label className="sr-only" htmlFor="poe-status-filter">{t("poeAllStatuses")}</label>
        <select
          id="poe-status-filter"
          data-testid="poe-status-filter"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="m-field m-select mt-2"
        >
          <option value="All">{t("poeAllStatuses")}</option>
          <option value="non_generee">{t("poeStatusNonGeneree")}</option>
          <option value="ia">{t("poeStatusIa")}</option>
          <option value="ia_sans_source">{t("poeStatusIaSansSource")}</option>
          <option value="erreur">{t("poeStatusErreur")}</option>
        </select>

        {/* Legend: marker, port tiers (status pattern), EEZ status */}
        <details className="m-details mt-3 text-[12px] leading-4" data-testid="poe-legend" open={!selectedZone || undefined}>
          <summary className="flex items-center gap-1.5 font-medium text-m-fg2 hover:text-m-fg">
            <ChevronRight size={12} strokeWidth={1.75} className="m-disclosure shrink-0" aria-hidden="true" />
            {t("legend")}
          </summary>
          <div className="m-details-body">
          <div className="mt-1.5 flex items-center gap-2 text-m-fg2">
            <span className="legend-dot" aria-hidden="true" />
            <span>{t("legendPoePort")}</span>
          </div>
          <p className="mt-2 text-m-fg3">{t("poeLegendTiers")}</p>
          <div className="mt-1 grid grid-cols-2 gap-x-3 gap-y-1 text-m-fg2">
            {TIER_ORDER.map((tier) => (
              <div key={tier} className="flex items-center gap-2 min-w-0" title={t(`poeTier_${tier}`)}>
                <TierGlyph tier={tier} />
                <span className="truncate">{t(`poeTierShort_${tier}`)}</span>
              </div>
            ))}
            <div className="flex items-center gap-2 min-w-0 text-m-fg3">
              <TierGlyph tier="none" />
              <span className="truncate">{t("poeTierNone")}</span>
            </div>
          </div>
          <p className="mt-2 text-m-fg3">{t("poeLegendZones")}</p>
          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-m-fg2">
            <span className="flex items-center gap-2"><span className="legend-swatch" style={ZONE_SWATCH.ia} aria-hidden="true" />{t("poeLegendGenerated")}</span>
            <span className="flex items-center gap-2"><span className="legend-swatch" style={ZONE_SWATCH.non_generee} aria-hidden="true" />{t("poeStatusNonGeneree")}</span>
            <span className="flex items-center gap-2"><span className="legend-swatch" style={ZONE_SWATCH.erreur} aria-hidden="true" />{t("poeStatusErreur")}</span>
            <span className="flex items-center gap-2"><span className="legend-swatch" style={ZONE_SWATCH.selected} aria-hidden="true" />{t("poeLegendSelected")}</span>
          </div>
          </div>
        </details>

        {items.length > 0 && (
          <p className="mt-3 text-[12px] leading-4 text-m-fg3 m-num" data-testid="poe-summary">
            {fmtInt(generatedCount, lang)} {t("poeOf")} {fmtInt(items.length, lang)} {t("poeSummary")}, {fmtInt(totalPorts, lang)} {t(totalPorts === 1 ? "poeSummaryPortOne" : "poeSummaryPorts")}
          </p>
        )}
      </div>

      {/* Open zone: the sheet owns the remaining height (its own scroll area);
          the list is one click away behind "All zones". */}
      {(selectedZone || ficheLoading) && (
        <div className="flex-1 min-h-0 flex flex-col bg-m-canvas">
          <div className="shrink-0 px-4 py-2 border-b border-m-line-soft">
            <button
              type="button"
              onClick={() => { returnToRowRef.current = selectedZone; if (onSelectZone) onSelectZone(null); }}
              className="inline-flex items-center gap-1.5 text-[12px] leading-4 text-m-fg2 hover:text-m-fg rounded-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-m-accent"
              data-testid="poe-back-to-list"
            >
              <ArrowLeft size={14} strokeWidth={1.75} aria-hidden="true" />
              {t("poeBackToList")} <span className="m-num text-m-fg3">{fmtInt(items.length, lang)}</span>
            </button>
          </div>
          <div className="flex-1 min-h-0 overflow-y-auto">
            <ZoneFiche t={t} lang={lang} fiche={fiche} loading={ficheLoading && !fiche} onFlyToPort={onFlyToPort} onVerify={onVerify} verifyState={verifyState} />
          </div>
        </div>
      )}

      {/* EEZ list */}
      <div className={`flex-1 overflow-y-auto ${(selectedZone || ficheLoading) ? "hidden" : ""}`} data-testid="poe-zones-list">
        {items.length === 0 && (
          <div className="p-6 text-center text-[13px] text-m-fg3 leading-[18px]">
            {zonesLoading ? t("poeZonesLoading") : t("poeZonesEmpty")}
          </div>
        )}
        {filtered.map((z) => {
          const isSelected = selectedZone === z.mrgid;
          const status = z.status || "non_generee";
          const iso = (z.iso2 || z.sov_iso2 || "").toUpperCase();
          const name = zoneDisplayName(z, t);
          // The second line only earns its place when it adds to the name and the ISO column.
          const rawSubtitle = zoneSubtitle(z);
          const subtitle = rawSubtitle !== name && rawSubtitle.toUpperCase() !== iso ? rawSubtitle : "";
          return (
            <button
              key={z.mrgid}
              type="button"
              data-testid={`poe-zone-row-${z.mrgid}`}
              onClick={() => onSelectZone && onSelectZone(z.mrgid, zoneDisplayName(z, t), z.bbox, z.anchor)}
              title={z.status === "erreur" && z.last_error ? z.last_error : zoneDisplayName(z, t)}
              aria-current={isSelected ? "true" : undefined}
              className={`w-full text-left px-4 py-2.5 border-b border-m-line-soft transition-colors duration-150 focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-m-accent ${
                isSelected ? "bg-m-selected" : "hover:bg-m-raised"
              }`}
            >
              <div className="flex items-start gap-3">
                <span className="m-code w-6 shrink-0 mt-px text-[11px] leading-4 text-m-fg3" aria-hidden="true">
                  {iso || "—"}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-baseline justify-between gap-3">
                    <span
                      className={`truncate text-[13px] leading-[18px] font-medium ${status === "non_generee" ? "text-m-fg2" : "text-m-fg"}`}
                      data-testid="poe-zone-row-label"
                    >
                      {name}
                    </span>
                    {z.poe_count > 0 && (
                      <span className="m-num shrink-0 text-[12px] leading-4 text-m-fg2">
                        {fmtInt(z.poe_count, lang)} {t("poePortsCount")}
                      </span>
                    )}
                  </div>
                  <div className="mt-0.5 flex items-baseline justify-between gap-3">
                    <span className="truncate text-[12px] leading-4 text-m-fg3">{subtitle}</span>
                    <span className="flex items-center gap-2 shrink-0">
                      {statusNote(status)}
                      {z.stale && (
                        <span className="text-[12px] leading-4 text-m-fg3" title={t("poeStaleTooltip")}>
                          {t("poeStale")}
                        </span>
                      )}
                    </span>
                  </div>
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {/* Attributions */}
      <div className="px-4 py-2 border-t border-m-line">
        <p className="text-[11px] leading-4 text-m-fg3">
          {t("poeEezAttribution")}. {t("poeGeocodeAttribution")}.
        </p>
      </div>
    </aside>
  );
}
