import { SAFETY_DEPTHS_M } from "./map/safetyIsobathSpec";

const WMS_LAYERS = [
  { id: "bathymetry", labelKey: "scienceWmsBathymetry" },
  { id: "substrate", labelKey: "scienceWmsSubstrate" },
  { id: "cables", labelKey: "scienceWmsCables" },
];

export const DEFAULT_SCIENCE_WMS = {
  bathymetry: false,
  cables: false,
  substrate: false,
};

/**
 * Map layers (BI data, isobath, EMODnet).
 * Shown in the Settings panel (gear icon).
 */
export default function MapLayersSidebar({
  t,
  overlayOn,
  onToggleOverlay,
  scienceWms,
  onToggleWms,
  safetyM,
  onSafetyM,
  noaaAidsOn = false,
  onToggleNoaaAids,
  showNoaa = false,
}) {
  return (
    <section data-testid="map-layers-sidebar">
      <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-accent/70 mb-2">
        {t("scienceWmsTitle")}
      </p>
      <p className="font-mono text-[9px] text-slate-500 leading-relaxed mb-2">
        {t("scienceWmsHint")}
      </p>
      <label className="flex items-start gap-2 text-[11px] text-slate-300 cursor-pointer mb-2">
        <input
          type="checkbox"
          data-testid="overlay-bi-toggle"
          className="mt-0.5 accent-accent"
          checked={!!overlayOn}
          onChange={(e) => onToggleOverlay && onToggleOverlay(e.target.checked)}
        />
        <span>{t("overlayBiToggle")}</span>
      </label>
      <label className="flex items-center justify-between gap-2 text-[11px] text-slate-300 mb-2">
        <span>{t("safetyIsobath")}</span>
        <select
          data-testid="safety-isobath"
          value={safetyM}
          onChange={(e) => onSafetyM && onSafetyM(Number(e.target.value))}
          className="bg-raised border border-line text-slate-200 text-[11px] rounded-sm px-1 py-0.5"
        >
          {SAFETY_DEPTHS_M.map((m) => (
            <option key={m} value={m}>{m} m</option>
          ))}
        </select>
      </label>
      {showNoaa ? (
        <label className="flex items-start gap-2 text-[11px] text-slate-300 cursor-pointer mb-2">
          <input
            type="checkbox"
            data-testid="noaa-aids-toggle"
            className="mt-0.5 accent-accent"
            checked={!!noaaAidsOn}
            onChange={(e) => onToggleNoaaAids && onToggleNoaaAids(e.target.checked)}
          />
          <span>{t("noaaAidsToggle")}</span>
        </label>
      ) : null}
      <div className="space-y-1.5 mt-2" data-testid="emodnet-wms-box">
        {WMS_LAYERS.map((layer) => {
          const on = !!(scienceWms && scienceWms[layer.id]);
          return (
            <label
              key={layer.id}
              className="flex items-start gap-2 text-[11px] text-slate-300 cursor-pointer"
            >
              <input
                type="checkbox"
                data-testid={`map-wms-${layer.id}`}
                className="mt-0.5 accent-accent"
                checked={on}
                onChange={(e) => onToggleWms && onToggleWms(layer.id, e.target.checked)}
              />
              <span>{t(layer.labelKey)}</span>
            </label>
          );
        })}
      </div>
    </section>
  );
}
