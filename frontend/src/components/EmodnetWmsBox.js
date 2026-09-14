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
 * Encadré EMODnet dans la barre latérale — tout décoché au départ.
 */
export default function EmodnetWmsBox({ t, scienceWms, onToggleWms }) {
  return (
    <section
      className="shrink-0 border-t border-line p-3 bg-surface"
      data-testid="emodnet-wms-box"
    >
      <p className="font-heading text-[12px] font-semibold text-slate-200 mb-1">
        {t("scienceWmsTitle")}
      </p>
      <p className="font-mono text-[9px] text-slate-500 leading-relaxed mb-2">
        {t("scienceWmsHint")}
      </p>
      <div className="space-y-1.5">
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
                onChange={() => onToggleWms && onToggleWms(layer.id, !on)}
              />
              <span>{t(layer.labelKey)}</span>
            </label>
          );
        })}
      </div>
    </section>
  );
}
