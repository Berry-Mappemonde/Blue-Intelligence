import { ChevronRight, Radio, ExternalLink, MapPin, Search } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import api from "../api";
import { formatCapitainerieSource } from "../lib/capitainerieSource";
import { phoneQueryMatches } from "../lib/phoneMatch";

const LIST_CAP = 250;
const COLOR = "#38bdf8";

export default function CapitaineriesPanel({ t, capitaineries, onFlyTo, onRefresh }) {
  const [query, setQuery] = useState("");
  const batchPollRef = useRef(null);
  const features = capitaineries?.features || [];

  useEffect(() => {
    let live = true;
    let iv = null;
    let wasRunning = false;
    const check = async () => {
      try {
        const { data } = await api.get("/capitaineries/build/status");
        if (!live) return;
        if (wasRunning && !data.running) {
          if (onRefresh) onRefresh();
        }
        wasRunning = data.running;
      } catch (_) { /* transient */ }
    };
    check();
    iv = setInterval(check, 4000);
    return () => { live = false; if (iv) clearInterval(iv); };
  }, [onRefresh]);

  useEffect(() => {
    let live = true;
    let wasRunning = false;
    const check = async () => {
      try {
        const { data } = await api.get("/capitaineries/enrich-batch/status");
        if (!live) return;
        if (wasRunning && !data.running) {
          if (onRefresh) onRefresh();
        }
        wasRunning = data.running;
      } catch (_) { /* transient */ }
    };
    check();
    batchPollRef.current = setInterval(check, 3000);
    return () => {
      live = false;
      if (batchPollRef.current) clearInterval(batchPollRef.current);
    };
  }, [onRefresh]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return features;
    return features.filter((f) => {
      const p = f.properties || {};
      return (
        (p.name || "").toLowerCase().includes(q)
        || String(p.osm_id || "").toLowerCase().includes(q)
        || String(p.telephone || "").toLowerCase().includes(q)
        || phoneQueryMatches(query, p.telephone)
      );
    });
  }, [features, query]);

  const visible = filtered.slice(0, LIST_CAP);
  const truncated = filtered.length > LIST_CAP;
  const withContact = features.filter((f) => f.properties?.telephone || f.properties?.canal_vhf).length;

  return (
    <aside className="w-[360px] max-w-full shrink-0 flex flex-col border-r border-m-line bg-m-shell min-h-0 font-ui text-[13px] leading-[18px] text-m-fg" data-testid="capitaineries-panel">
      <div className="px-4 pt-4 pb-3 border-b border-m-line shrink-0 max-h-[65%] overflow-y-auto [scrollbar-color:rgb(var(--m-line-strong))_transparent]">
        <div className="flex items-baseline justify-between gap-3 mb-3">
          <h2 className="text-[15px] leading-5 font-medium text-m-fg">{t("modeCapitaineries")}</h2>
          <span className="ml-auto shrink-0 text-right text-[12px] leading-4 text-m-fg3 m-num" data-testid="capitaineries-count">
            {features.length} {t("capitaineriesCount")}
          </span>
        </div>
        <div className="relative mb-3">
          <Search size={14} strokeWidth={1.75} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-m-fg3 pointer-events-none" aria-hidden="true" />
          <input
            data-testid="capitaineries-search-input"
            type="text"
            name="capitaineries-search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t("capitaineriesSearch")}
            aria-label={t("capitaineriesSearch")}
            className="m-field !pl-8"
          />
        </div>
        <details className="m-details mt-3 text-[12px] leading-4" data-testid="capitaineries-legend" open>
          <summary className="flex items-center gap-1.5 font-medium text-m-fg2 hover:text-m-fg">
            <ChevronRight size={12} strokeWidth={1.75} className="m-disclosure shrink-0" aria-hidden="true" />
            {t("legend")}
          </summary>
          <div className="m-details-body mt-1.5 space-y-1">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full shrink-0 opacity-70" style={{ background: COLOR }} />
              <span className="text-[12px] leading-4 text-m-fg2">{t("legendCapitainerie")}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full shrink-0" style={{ background: COLOR }} />
              <span className="text-[12px] leading-4 text-m-fg2">{t("legendCapitainerieContact")}</span>
              <span className="ml-auto shrink-0 text-right text-m-fg3 m-num">{withContact}</span>
            </div>
          </div>
        </details>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto [scrollbar-color:rgb(var(--m-line-strong))_transparent]" data-testid="capitaineries-list">
        {features.length === 0 && (
          <div className="p-6 text-center text-[13px] leading-[18px] text-m-fg3">
            <Radio size={24} strokeWidth={1.75} className="mx-auto mb-3 text-m-fg4" aria-hidden="true" />
            {t("capitaineriesEmpty")}
          </div>
        )}
        {truncated && (
          <p className="px-4 py-2 text-[12px] leading-4 text-m-fg3 m-num" data-testid="capitaineries-list-truncated">
            {t("marinasListTruncated").replace("{shown}", String(LIST_CAP)).replace("{total}", String(filtered.length))}
          </p>
        )}
        {visible.map((f) => {
          const p = f.properties || {};
          const [lon, lat] = f.geometry?.coordinates || [0, 0];
          return (
            <button
              key={p.id || p.osm_id || p.shom_id || p.noaa_id}
              type="button"
              data-testid={`capitainerie-row-${p.id}`}
              onClick={() => onFlyTo && onFlyTo(p.id, lat, lon)}
              className="w-full text-left px-4 py-2.5 border-b border-m-line-soft hover:bg-m-raised focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-m-accent"
              title={t("capitaineriesFlyTo")}
            >
              <div className="flex items-start gap-2">
                <MapPin size={13} className="text-m-fg3 mt-0.5 shrink-0" aria-hidden="true" />
                <div className="flex-1 min-w-0">
                  <div className="text-[13px] leading-[18px] font-medium text-m-fg truncate">
                    {p.name || t("capitaineriesUnnamed")}
                  </div>
                  <div className="text-[12px] leading-4 text-m-fg3 m-num mt-0.5 truncate">
                    {p.telephone || p.canal_vhf
                      ? [p.telephone, p.canal_vhf ? `VHF ${p.canal_vhf}` : null].filter(Boolean).join(" · ")
                      : (p.osm_id || `${Number(lat).toFixed(3)}, ${Number(lon).toFixed(3)}`)}
                  </div>
                  <div className="flex items-center gap-1.5 mt-1.5">
                    <span className="text-[12px] leading-4 text-m-fg3">
                      {formatCapitainerieSource(p.source, t)}
                    </span>
                    {p.website && (
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
          <a
            href="https://www.openstreetmap.org/copyright"
            target="_blank"
            rel="noreferrer"
            className="hover:text-white"
          >
            {t("marinasOdbL")}
          </a>
        </p>
      </div>
    </aside>
  );
}
