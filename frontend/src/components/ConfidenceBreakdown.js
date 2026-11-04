import React from "react";

/**
 * « Pourquoi ce score » — décomposition de la confiance d'un port.
 *
 * Les données existent déjà : `apply_score()` écrit `confidence_parts`
 * (source / reading / map / external) et `confidence_reasons`. On ne calcule
 * rien ici, on montre seulement ce que le backend a décidé, et pourquoi.
 *
 * La barre est graduée sur 100 points : chaque segment vaut les points obtenus,
 * le reste de la piste est le score non gagné. L'ordre et les libellés suivent
 * `poe_confidence.score_port` et le cahier des charges PoE.
 */
const PARTS = [
  { key: "source", label: "poePartSource", color: "#fbbf24" },
  { key: "reading", label: "poePartReading", color: "#38bdf8" },
  { key: "map", label: "poePartMap", color: "#2dd4bf" },
  { key: "external", label: "poePartExternal", color: "#a78bfa" },
];

export function breakdownModel(parts, reasons, reasonsEn, lang) {
  const entries = PARTS
    .map((p) => ({ ...p, value: Math.max(0, Number(parts?.[p.key]) || 0) }))
    .filter((p) => p.value > 0);
  return {
    entries,
    total: entries.reduce((sum, p) => sum + p.value, 0),
    // Les raisons sont produites en français ; l'API en fournit la traduction.
    list: lang === "en" ? (reasonsEn || []) : (reasons || []),
  };
}

export default function ConfidenceBreakdown({
  parts, reasons, reasonsEn, lang, t,
}) {
  const { entries, total, list } = breakdownModel(parts, reasons, reasonsEn, lang);

  return (
    <div data-testid="poe-confidence-breakdown" className="mt-2 font-ui">
      <div
        className="flex h-1.5 w-full overflow-hidden rounded-sm bg-m-raised"
        role="img"
        aria-label={`${t("poeBreakdown")}: ${total}`}
        data-testid="poe-confidence-bar"
      >
        {entries.map((p) => (
          <span
            key={p.key}
            title={`${t(p.label)} ${p.value}`}
            style={{ width: `${p.value}%`, backgroundColor: p.color }}
            data-testid={`poe-confidence-seg-${p.key}`}
          />
        ))}
      </div>

      {entries.length ? (
        <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-0.5">
          {entries.map((p) => (
            <span key={p.key} className="inline-flex items-center gap-1.5 text-[12px] leading-4 text-m-fg3 m-num">
              <span
                className="inline-block h-2 w-2 rounded-sm"
                style={{ backgroundColor: p.color }}
                aria-hidden="true"
              />
              {t(p.label)} <span className="text-m-fg2">{p.value}</span>
            </span>
          ))}
        </div>
      ) : null}

      {list.length ? (
        <ul className="mt-1.5 space-y-0.5 pl-3 list-disc marker:text-m-fg4" data-testid="poe-confidence-reasons">
          {list.map((reason, i) => (
            <li key={`${i}-${reason}`} className="text-[12px] leading-4 text-m-fg3">
              {reason}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-1.5 text-[12px] leading-4 text-m-fg3" data-testid="poe-confidence-no-reasons">
          {t("poeNoReasons")}
        </p>
      )}
    </div>
  );
}
