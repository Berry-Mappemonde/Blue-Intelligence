import { ChevronRight, ExternalLink, FlaskConical, MapPin, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import api from "../api";

const LIST_CAP = 250;
const COLOR = "#a78bfa";

const SOURCE_FILTERS = [
  { id: "all", labelKey: "scienceAllSources" },
  { id: "sextant", label: "Sextant" },
  { id: "odatis", label: "ODATIS" },
  { id: "edmed", label: "EDMED" },
  { id: "argo", label: "Argo" },
  { id: "csr", label: "CSR" },
  { id: "sentinel-pilot", labelKey: "scienceFilterSentinel" },
];

/**
 * SciencePanel — Science-mode side list: ocean datasets
 * (Sextant/ODATIS/EDMED) + Argo floats + CSR tracks, filtered by source.
 * EMODnet WMS layers live in MapLayersSidebar (right bar).
 */
export default function SciencePanel({
  t, science, onFlyTo, onRefresh,
  sourceFilter = "argo", onSourceFilter,
}) {
  const [query, setQuery] = useState("");
  const setSourceFilter = onSourceFilter || (() => {});
  const features = science?.features || [];

  // When a harvest finishes, refresh the map + the list.
  useEffect(() => {
    let live = true;
    let wasRunning = false;
    const check = async () => {
      try {
        const { data } = await api.get("/science/build/status");
        if (!live) return;
        if (wasRunning && !data.running) {
          if (onRefresh) onRefresh();
        }
        wasRunning = data.running;
      } catch (_) { /* transient */ }
    };
    check();
    const iv = setInterval(check, 4000);
    return () => { live = false; clearInterval(iv); };
  }, [onRefresh]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return features.filter((f) => {
      const p = f.properties || {};
      if (sourceFilter !== "all" && p.source !== sourceFilter) return false;
      if (!q) return true;
      return (
        (p.name || "").toLowerCase().includes(q)
        || (p.provider || "").toLowerCase().includes(q)
        || (p.doi || "").toLowerCase().includes(q)
        || String(p.wmo || "").toLowerCase().includes(q)
        || String(p.ship || "").toLowerCase().includes(q)
      );
    });
  }, [features, query, sourceFilter]);

  const visible = filtered.slice(0, LIST_CAP);
  const truncated = filtered.length > LIST_CAP;
  const argoCount = features.filter((f) => f.properties?.kind === "argo_float").length;
  const cruiseCount = features.filter((f) => f.properties?.kind === "cruise").length;
  const datasetCount = features.length - argoCount - cruiseCount;

  return (
    <aside className="w-[360px] max-w-full shrink-0 flex flex-col border-r border-m-line bg-m-shell min-h-0 font-ui text-[13px] leading-[18px] text-m-fg" data-testid="science-panel">
      <div className="px-4 pt-4 pb-3 border-b border-m-line shrink-0 max-h-[65%] overflow-y-auto [scrollbar-color:rgb(var(--m-line-strong))_transparent]">
        <div className="flex items-baseline justify-between gap-3 mb-1">
          <h2 className="text-[15px] leading-5 font-medium text-m-fg">{t("modeScience")}</h2>
          <span className="ml-auto shrink-0 text-right text-[12px] leading-4 text-m-fg3 m-num" data-testid="science-count">
            {features.length} {t("scienceCount")}
          </span>
        </div>
        <p className="text-[12px] leading-4 text-m-fg3 mb-3">
          {t("scienceSubtitle")}
        </p>
        <div className="relative mb-2">
          <Search size={14} strokeWidth={1.75} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-m-fg3 pointer-events-none" aria-hidden="true" />
          <input
            data-testid="science-search-input"
            type="text"
            name="science-search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t("scienceSearch")}
            aria-label={t("scienceSearch")}
            className="m-field !pl-8"
          />
        </div>
        <div className="flex flex-wrap gap-1 mb-2" data-testid="science-source-filter">
          {SOURCE_FILTERS.map((s) => (
            <button
              key={s.id}
              type="button"
              data-testid={`science-filter-${s.id}`}
              onClick={() => setSourceFilter(s.id)}
              aria-pressed={sourceFilter === s.id}
              className={`min-h-7 px-2 text-[12px] leading-4 border rounded-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-m-accent ${
                sourceFilter === s.id
                  ? "border-m-line-strong bg-m-selected text-m-fg"
                  : "border-m-line text-m-fg2 hover:text-m-fg hover:bg-m-raised"
              }`}
            >
              {s.labelKey ? t(s.labelKey) : s.label}
            </button>
          ))}
        </div>
        <details className="m-details mt-3 text-[12px] leading-4" data-testid="science-legend" open>
          <summary className="flex items-center gap-1.5 font-medium text-m-fg2 hover:text-m-fg">
            <ChevronRight size={12} strokeWidth={1.75} className="m-disclosure shrink-0" aria-hidden="true" />
            {t("legend")}
          </summary>
          <div className="m-details-body mt-1.5 space-y-1">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full shrink-0" style={{ background: COLOR }} />
              <span className="text-[12px] leading-4 text-m-fg2">{t("legendScienceDataset")}</span>
              <span className="ml-auto shrink-0 text-right text-m-fg3 m-num">{datasetCount}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full shrink-0 border-2" style={{ borderColor: COLOR, background: "rgba(167,139,250,0.2)" }} />
              <span className="text-[12px] leading-4 text-m-fg2">{t("legendScienceArgo")}</span>
              <span className="ml-auto shrink-0 text-right text-m-fg3 m-num">{argoCount}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-6 h-0.5 shrink-0" style={{ background: COLOR }} />
              <span className="text-[12px] leading-4 text-m-fg2">{t("legendScienceCruise")}</span>
              <span className="ml-auto shrink-0 text-right text-m-fg3 m-num">{cruiseCount}</span>
            </div>
          </div>
        </details>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto [scrollbar-color:rgb(var(--m-line-strong))_transparent]" data-testid="science-list">
        {features.length === 0 && (
          <div className="p-6 text-center text-[13px] leading-[18px] text-m-fg3">
            <FlaskConical size={24} strokeWidth={1.75} className="mx-auto mb-3 text-m-fg4" aria-hidden="true" />
            {t("scienceEmpty")}
          </div>
        )}
        {truncated && (
          <p className="px-4 py-2 text-[12px] leading-4 text-m-fg3 m-num" data-testid="science-list-truncated">
            {t("marinasListTruncated").replace("{shown}", String(LIST_CAP)).replace("{total}", String(filtered.length))}
          </p>
        )}
        {visible.map((f) => {
          const p = f.properties || {};
          const isArgo = p.kind === "argo_float";
          const isCruise = p.kind === "cruise";
          const lat = p.lat != null ? Number(p.lat) : (f.geometry?.type === "Point" ? f.geometry.coordinates[1] : 0);
          const lon = p.lon != null ? Number(p.lon) : (f.geometry?.type === "Point" ? f.geometry.coordinates[0] : 0);
          const sub = isArgo
            ? [p.wmo ? `WMO ${p.wmo}` : null, p.profile_date ? String(p.profile_date).slice(0, 10) : null]
              .filter(Boolean).join(" · ")
            : isCruise
              ? [p.ship, [p.start, p.end].filter(Boolean).join(" → ")].filter(Boolean).join(" · ")
              : (p.provider || (p.date ? String(p.date).slice(0, 10) : `${Number(lat).toFixed(2)}, ${Number(lon).toFixed(2)}`));
          return (
            <button
              key={p.id}
              type="button"
              data-testid={`science-row-${p.id}`}
              onClick={() => onFlyTo && onFlyTo(p.id, lat, lon)}
              className="w-full text-left px-4 py-2.5 border-b border-m-line-soft hover:bg-m-raised focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-m-accent"
              title={t("scienceFlyTo")}
            >
              <div className="flex items-start gap-2">
                <MapPin size={13} className="text-m-fg3 mt-0.5 shrink-0" aria-hidden="true" />
                <div className="flex-1 min-w-0">
                  <div className="text-[13px] leading-[18px] font-medium text-m-fg truncate">
                    {p.name || t(isCruise ? "scienceUnnamedCruise" : "scienceUnnamed")}
                  </div>
                  <div className="text-[12px] leading-4 text-m-fg3 m-num mt-0.5 truncate">
                    {sub}
                  </div>
                  <div className="flex items-center gap-1.5 mt-1.5">
                    <span className="text-[12px] leading-4 text-m-fg3">
                      {isArgo ? t("scienceArgoFloat") : isCruise ? t("scienceCruise") : (p.source || t("scienceDataset"))}
                    </span>
                    {p.doi && (
                      <span className="text-[12px] leading-4 text-m-fg3">
                        DOI
                      </span>
                    )}
                    {p.url && (
                      <ExternalLink size={14} strokeWidth={1.75} className="text-m-fg3 ml-auto shrink-0" aria-hidden="true" />
                    )}
                  </div>
                </div>
              </div>
            </button>
          );
        })}
      </div>

      <div className="shrink-0 px-4 py-2 border-t border-m-line">
        <p className="text-[11px] leading-4 text-m-fg3">
          {t("scienceAttribution")}
        </p>
      </div>
    </aside>
  );
}
