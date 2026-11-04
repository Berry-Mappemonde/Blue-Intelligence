import { ChevronRight, Info, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { LFP_COLORS } from "./map/constants";

const LIST_CAP = 80;

export default function AmpPanel({ t, sites, sitesLoading, onFlyTo, lfpFilter = "All", onLfpFilter }) {
  const [q, setQ] = useState("");
  const setLfpFilter = onLfpFilter || (() => {});

  const features = sites?.features || [];
  const hint = sites?.hint;
  const truncated = Boolean(sites?.truncated);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return features.filter((f) => {
      const p = f.properties || {};
      if (lfpFilter !== "All" && String(p.lfp ?? 0) !== String(lfpFilter)) return false;
      if (!needle) return true;
      const hay = `${p.name || ""} ${p.country || ""} ${p.designation || ""} ${p.managing_authority || ""}`.toLowerCase();
      return hay.includes(needle);
    });
  }, [features, q, lfpFilter]);

  const visible = filtered.slice(0, LIST_CAP);

  return (
    <aside className="w-[360px] max-w-full shrink-0 flex flex-col border-r border-m-line bg-m-shell min-h-0 font-ui text-[13px] leading-[18px] text-m-fg" data-testid="amp-panel">
      <div className="px-4 pt-4 pb-3 border-b border-m-line shrink-0 max-h-[65%] overflow-y-auto [scrollbar-color:rgb(var(--m-line-strong))_transparent]">
        <div className="flex items-baseline justify-between gap-3 mb-3">
          <h2 className="text-[15px] leading-5 font-medium text-m-fg">{t("modeAmp")}</h2>
          <span className="text-[12px] leading-4 text-m-fg3">ProtectedSeas</span>
          <span className="ml-auto shrink-0 text-right text-[12px] leading-4 text-m-fg3 m-num" data-testid="amp-count">
            {features.length} {t("ampCount")}
          </span>
        </div>

        <div data-testid="amp-disclaimer" className="flex items-start gap-2 text-[12px] leading-4 text-m-fg2 mb-3">
          <Info size={14} strokeWidth={1.75} className="mt-px shrink-0 text-m-fg3" aria-hidden="true" />
          <span>{t("mpaDisclaimer")}</span>
        </div>

        <div className="relative mb-3">
          <Search size={14} strokeWidth={1.75} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-m-fg3 pointer-events-none" aria-hidden="true" />
          <input
            data-testid="amp-search-input"
            type="text"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={t("ampSearch")}
            aria-label={t("ampSearch")}
            className="m-field !pl-8"
          />
        </div>

        <div className="flex flex-wrap gap-1 mb-3">
          <button
            type="button"
            data-testid="amp-lfp-all"
            onClick={() => setLfpFilter("All")}
            aria-pressed={lfpFilter === "All"}
            className={`min-h-7 px-2 text-[12px] leading-4 border rounded-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-m-accent ${
              lfpFilter === "All" ? "border-m-line-strong bg-m-selected text-m-fg" : "border-m-line text-m-fg2 hover:bg-m-raised"
            }`}
          >
            {t("ampAllLfp")}
          </button>
          {[1, 2, 3, 4, 5].map((n) => (
            <button
              key={n}
              type="button"
              data-testid={`amp-lfp-${n}`}
              onClick={() => setLfpFilter(String(n))}
              aria-pressed={lfpFilter === String(n)}
              className={`min-h-7 px-2 text-[12px] leading-4 border rounded-md m-num focus-visible:outline focus-visible:outline-2 focus-visible:outline-m-accent ${
                lfpFilter === String(n) ? "border-m-line-strong bg-m-selected text-m-fg" : "border-m-line text-m-fg2 hover:bg-m-raised"
              }`}
            >
              <span className="inline-block w-2 h-2 rounded-sm mr-1.5" style={{ background: LFP_COLORS[n] }} aria-hidden="true" />
              LFP {n}
            </button>
          ))}
        </div>

        <details className="m-details mt-3 text-[12px] leading-4" data-testid="amp-legend" open>
          <summary className="flex items-center gap-1.5 font-medium text-m-fg2 hover:text-m-fg">
            <ChevronRight size={12} strokeWidth={1.75} className="m-disclosure shrink-0" aria-hidden="true" />
            {t("legend")}
          </summary>
          <div className="m-details-body mt-1.5 space-y-1">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ background: LFP_COLORS[5] }} />
              <span className="text-[12px] leading-4 text-m-fg2">{t("lfp5")}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ background: LFP_COLORS[3] }} />
              <span className="text-[12px] leading-4 text-m-fg2">{t("lfp3")}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ background: LFP_COLORS[1] }} />
              <span className="text-[12px] leading-4 text-m-fg2">{t("lfp1")}</span>
            </div>
          </div>
        </details>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto [scrollbar-color:rgb(var(--m-line-strong))_transparent]" data-testid="amp-list">
        {hint === "zoom" && (
          <p className="p-6 text-center text-[13px] leading-[18px] text-m-fg3" data-testid="amp-zoom-hint">
            {t("mpaZoomHint")}
          </p>
        )}
        {hint !== "zoom" && features.length === 0 && (
          <p className="p-6 text-center text-[13px] leading-[18px] text-m-fg3">
            {sitesLoading ? t("ampLoading") : t("ampEmpty")}
          </p>
        )}
        {truncated && (
          <p className="px-4 py-2 text-[12px] leading-4 text-m-fg3 m-num">{t("ampTruncated")}</p>
        )}
        {visible.map((f) => {
          const p = f.properties || {};
          return (
            <button
              key={p.site_id || p.id}
              type="button"
              data-testid={`amp-row-${p.site_id || p.id}`}
              onClick={() => onFlyTo && onFlyTo(p.site_id || p.id, p.lat, p.lon)}
              className="w-full text-left px-4 py-2.5 border-b border-m-line-soft hover:bg-m-raised focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-m-accent"
            >
              <div className="flex items-start gap-2">
                <span
                  className="mt-1.5 w-2 h-2 rounded-sm shrink-0"
                  style={{ background: LFP_COLORS[Number(p.lfp) || 0] }}
                />
                <div className="min-w-0 flex-1">
                  <p className="text-[13px] leading-[18px] font-medium text-m-fg truncate">{p.name}</p>
                  <p className="text-[12px] leading-4 text-m-fg3 truncate">
                    {p.country}{p.designation ? ` · ${p.designation}` : ""}
                  </p>
                  <p className="mt-1 text-[12px] leading-4">
                    <span className="text-m-fg3">{t("ampManagerUrl")}</span>
                    {" · "}
                    {p.visit_url
                      ? <span className="text-m-fg2">{t("ampVisitFound")}</span>
                      : <span className="text-m-fg3">{t("ampVisitMissing")}</span>}
                  </p>
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </aside>
  );
}
