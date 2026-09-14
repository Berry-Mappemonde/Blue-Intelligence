import { SCIENCE_WMS_LAYERS } from "./useScienceWms";
import { SAFETY_DEPTHS_M } from "./safetyIsobathSpec";

/**
 * Chrome carte commun : overlay hebdo, WMS EMODnet (tous modes),
 * isobathe de sécurité si fond mer.
 */
export default function MapChrome({
  t,
  overlayOn,
  onToggleOverlay,
  scienceWms,
  onToggleWms,
  nauticalActive,
  safetyM,
  onSafetyM,
  mode,
  noaaAidsOn = false,
  onToggleNoaaAids,
}) {
  return (
    <div
      className="absolute z-[1100] top-3 left-3 max-w-xs pointer-events-auto"
      data-testid="map-chrome"
    >
      <div className="flex flex-wrap gap-1 bg-surface/90 border border-line rounded-sm p-1.5">
        <button
          type="button"
          data-testid="overlay-bi-toggle"
          onClick={() => onToggleOverlay && onToggleOverlay(!overlayOn)}
          className={`px-1.5 py-1 font-mono text-[9px] uppercase tracking-wide border rounded-sm ${
            overlayOn
              ? "border-accent/60 bg-accent/15 text-accent"
              : "border-line text-slate-500 hover:text-slate-300"
          }`}
        >
          {t("overlayBiToggle")}
        </button>
        {SCIENCE_WMS_LAYERS.map((layer) => (
          <button
            key={layer.id}
            type="button"
            data-testid={`map-wms-${layer.id}`}
            onClick={() => onToggleWms && onToggleWms(layer.id, !(scienceWms && scienceWms[layer.id]))}
            className={`px-1.5 py-1 font-mono text-[9px] uppercase tracking-wide border rounded-sm ${
              scienceWms && scienceWms[layer.id]
                ? "border-accent/60 bg-accent/15 text-accent"
                : "border-line text-slate-500 hover:text-slate-300"
            }`}
          >
            {t(
              layer.id === "bathymetry"
                ? "scienceWmsBathymetry"
                : layer.id === "substrate"
                  ? "scienceWmsSubstrate"
                  : "scienceWmsCables",
            )}
          </button>
        ))}
        {mode === "capitaineries" ? (
          <button
            type="button"
            data-testid="noaa-aids-toggle"
            onClick={() => onToggleNoaaAids && onToggleNoaaAids(!noaaAidsOn)}
            className={`px-1.5 py-1 font-mono text-[9px] uppercase tracking-wide border rounded-sm ${
              noaaAidsOn
                ? "border-accent/60 bg-accent/15 text-accent"
                : "border-line text-slate-500 hover:text-slate-300"
            }`}
          >
            {t("noaaAidsToggle")}
          </button>
        ) : null}
        {nauticalActive ? (
          <label className="flex items-center gap-1 px-1.5 font-mono text-[9px] uppercase tracking-wide text-slate-400">
            <span>{t("safetyIsobath")}</span>
            <select
              data-testid="safety-isobath"
              value={safetyM}
              onChange={(e) => onSafetyM && onSafetyM(Number(e.target.value))}
              className="bg-raised border border-line text-slate-200 text-[9px] rounded-sm"
            >
              {SAFETY_DEPTHS_M.map((m) => (
                <option key={m} value={m}>{m} m</option>
              ))}
            </select>
          </label>
        ) : null}
      </div>
    </div>
  );
}
