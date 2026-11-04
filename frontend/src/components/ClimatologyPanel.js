import { ChevronRight, Cloud, Waves, Wind } from "lucide-react";

const MONTHS = [
  { n: 1, fr: "Janv.", en: "Jan" },
  { n: 2, fr: "Févr.", en: "Feb" },
  { n: 3, fr: "Mars", en: "Mar" },
  { n: 4, fr: "Avr.", en: "Apr" },
  { n: 5, fr: "Mai", en: "May" },
  { n: 6, fr: "Juin", en: "Jun" },
  { n: 7, fr: "Juil.", en: "Jul" },
  { n: 8, fr: "Août", en: "Aug" },
  { n: 9, fr: "Sept.", en: "Sep" },
  { n: 10, fr: "Oct.", en: "Oct" },
  { n: 11, fr: "Nov.", en: "Nov" },
  { n: 12, fr: "Déc.", en: "Dec" },
];

const FILTERS = [
  { id: "wind", labelKey: "climoFilterWind" },
  { id: "wave", labelKey: "climoFilterWave" },
  { id: "current", labelKey: "climoFilterCurrent" },
  { id: "cyclones", labelKey: "climoFilterCyclones" },
];

/**
 * ClimatologyPanel — January–December slider + Wind / Wave /
 * Current / Cyclone filters. Pattern: SciencePanel (Sextant / Argo).
 */
export default function ClimatologyPanel({
  t, lang = "fr",
  month = 1, onMonth,
  filters, onToggleFilter,
  waveStat = "mean", onWaveStat,
  meta, point,
}) {
  const monthLabel = MONTHS[month - 1];
  const label = lang === "en" ? monthLabel?.en : monthLabel?.fr;
  const snaps = meta?.snapshot || {};

  return (
    <aside className="w-[360px] max-w-full shrink-0 flex flex-col border-r border-m-line bg-m-shell min-h-0 font-ui text-[13px] leading-[18px] text-m-fg" data-testid="climatology-panel">
      <div className="px-4 pt-4 pb-3 border-b border-m-line shrink-0 max-h-[65%] overflow-y-auto [scrollbar-color:rgb(var(--m-line-strong))_transparent]">
        <div className="flex items-baseline justify-between gap-3 mb-1">
          <h2 className="text-[15px] leading-5 font-medium text-m-fg">{t("modeClimatologyFull")}</h2>
        </div>
        <p className="text-[12px] leading-4 text-m-fg3 mb-3">
          {t("climoSubtitle")}
        </p>

        <label className="flex items-baseline justify-between gap-3 text-[12px] leading-4 font-medium text-m-fg2 mb-1.5" htmlFor="climo-month">
          {t("climoMonth")} <span className="text-m-fg3">{label}</span>
        </label>
        <input
          id="climo-month"
          data-testid="climatology-month"
          type="range"
          min={1}
          max={12}
          step={1}
          value={month}
          onChange={(e) => onMonth && onMonth(Number(e.target.value))}
          className="w-full accent-m-accent mb-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-m-accent"
        />
        <div className="flex justify-between text-[11px] leading-4 text-m-fg3 mb-3">
          <span>J</span><span>F</span><span>M</span><span>A</span><span>M</span><span>J</span>
          <span>J</span><span>A</span><span>S</span><span>O</span><span>N</span><span>D</span>
        </div>

        <div className="flex flex-wrap gap-1 mb-2" data-testid="climatology-filters">
          {FILTERS.map((f) => (
            <button
              key={f.id}
              type="button"
              data-testid={`climatology-filter-${f.id}`}
              onClick={() => onToggleFilter && onToggleFilter(f.id, !(filters && filters[f.id]))}
              aria-pressed={Boolean(filters && filters[f.id])}
              className={`min-h-7 px-2 text-[12px] leading-4 border rounded-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-m-accent ${
                filters && filters[f.id]
                  ? "border-m-line-strong bg-m-selected text-m-fg"
                  : "border-m-line text-m-fg2 hover:text-m-fg hover:bg-m-raised"
              }`}
            >
              {t(f.labelKey)}
            </button>
          ))}
        </div>

        {filters?.wave && (
          <div className="flex flex-wrap gap-1 mb-3" data-testid="climatology-wave-stat">
            {(snaps.wave_stat === "p50_p90" ? ["p50", "p90"] : ["mean"]).map((s) => (
              <button
                key={s}
                type="button"
                data-testid={`climatology-wave-${s}`}
                onClick={() => onWaveStat && onWaveStat(s)}
                aria-pressed={waveStat === s}
                className={`min-h-7 px-2 text-[12px] leading-4 border rounded-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-m-accent ${
                  waveStat === s
                    ? "border-m-line-strong bg-m-selected text-m-fg"
                    : "border-m-line text-m-fg2 hover:text-m-fg hover:bg-m-raised"
                }`}
              >
                {s === "p50" ? t("climoWaveP50") : s === "p90" ? t("climoWaveP90") : t("climoWaveMean")}
              </button>
            ))}
          </div>
        )}

        <details className="m-details mt-3 text-[12px] leading-4" data-testid="climatology-legend" open>
          <summary className="flex items-center gap-1.5 font-medium text-m-fg2 hover:text-m-fg">
            <ChevronRight size={12} strokeWidth={1.75} className="m-disclosure shrink-0" aria-hidden="true" />
            {t("legend")}
          </summary>
          <div className="m-details-body mt-1.5 space-y-1">
            <div className="flex items-center gap-2">
              <Wind size={14} strokeWidth={1.75} className="text-accent shrink-0" aria-hidden="true" />
              <span className="text-[12px] leading-4 text-m-fg2">{t("climoLegendWind")}</span>
            </div>
            <div className="flex items-center gap-2">
              <Waves size={14} strokeWidth={1.75} className="text-accent shrink-0" aria-hidden="true" />
              <span className="text-[12px] leading-4 text-m-fg2">{t("climoLegendWave")}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-0.5 shrink-0 bg-accent" />
              <span className="text-[12px] leading-4 text-m-fg2">{t("climoLegendCurrent")}</span>
            </div>
            <div className="flex items-center gap-2">
              <Cloud size={14} strokeWidth={1.75} className="text-accent shrink-0" aria-hidden="true" />
              <span className="text-[12px] leading-4 text-m-fg2">{t("climoLegendCyclones")}</span>
            </div>
          </div>
        </details>

        <div className="text-[12px] leading-4 text-m-fg3 space-y-1 mt-3 mb-2" data-testid="climatology-snapshot-status">
          {["wind", "wave", "current", "cyclones"].map((k) => (
            <div key={k} className="flex items-baseline justify-between gap-3">
              {t(`climoFilter${k[0].toUpperCase()}${k.slice(1)}`)}
              <span className="text-right">{snaps[k] ? t("climoSnapshotOn") : t("climoSnapshotOff")}</span>
            </div>
          ))}
        </div>
        <p className="text-[12px] leading-4 text-m-fg3 leading-relaxed">{t("climoHint")}</p>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto [scrollbar-color:rgb(var(--m-line-strong))_transparent] p-4" data-testid="climatology-point">
        {point ? (
          <PointCard t={t} point={point} />
        ) : (
          <p className="text-[13px] leading-[18px] text-m-fg3">{t("climoClickHint")}</p>
        )}
      </div>

      <div className="shrink-0 px-4 py-2 border-t border-m-line space-y-1">
        <p className="text-[12px] leading-4 text-m-fg2" data-testid="climatology-disclaimer">
          {t("climoDisclaimer")}
        </p>
        <p className="text-[11px] leading-4 text-m-fg3" data-testid="climatology-attribution">
          {t("climoAttribution")}
        </p>
      </div>
    </aside>
  );
}

function PointCard({ t, point }) {
  const land = point.coordinates?.cell_selection === "land";
  const w = point.wind_atlas;
  const wave = point.wave;
  const cur = point.current;
  const cyc = point.cyclone;
  return (
    <div className="space-y-3" data-testid="climatology-point-card">
      <p className="text-[12px] leading-4 text-m-fg3 m-num">
        {Number(point.coordinates?.latitude).toFixed(2)}°, {Number(point.coordinates?.longitude).toFixed(2)}°
        {" · "}{land ? t("climoOnLand") : t("climoAtSea")}
        {" · "}{t("climoKind")} {point.kind}
      </p>
      {land && (
        <p className="text-[13px] leading-[18px] text-m-fg2">{t("climoLandNull")}</p>
      )}
      <Block title={t("climoFilterWind")} empty={!w} emptyLabel={t("climoNoValue")}>
        {w && (
          <>
            <Row k={t("climoStatistic")} v={w.stat || (w.most_likely ? "rose" : "average")} />
            {w.most_likely && (
              <Row k={t("climoMostLikely")} v={`${w.most_likely.speed_knots} kn / ${w.most_likely.dir_deg}°`} />
            )}
            {w.vector_mean && (
              <Row k={t("climoAverage")} v={`${w.vector_mean.speed_knots} kn / ${w.vector_mean.dir_deg}°`} />
            )}
            {w.calm_pct != null && (
              <Row k={t("climoCalmGale")} v={`${w.calm_pct}% / ${w.gale_pct}%`} />
            )}
            {w.sample_count != null && <Row k={t("climoSamples")} v={String(w.sample_count)} />}
          </>
        )}
      </Block>
      <Block title={t("climoFilterWave")} empty={!wave} emptyLabel={t("climoNoValue")}>
        {wave && (
          <>
            <Row k={t("climoStatistic")} v={wave.stat} />
            {wave.hs_p50_m != null && <Row k="P50" v={`${wave.hs_p50_m} m`} />}
            {wave.hs_p90_m != null && <Row k="P90" v={`${wave.hs_p90_m} m`} />}
            {wave.hs_mean_m != null && <Row k={t("climoMean")} v={`${wave.hs_mean_m} m`} />}
            {wave.period_s != null && <Row k={t("climoPeriod")} v={`${wave.period_s} s`} />}
            {wave.dir_deg != null && <Row k={t("climoDirection")} v={`${wave.dir_deg}°`} />}
          </>
        )}
      </Block>
      <Block title={t("climoFilterCurrent")} empty={!cur} emptyLabel={t("climoNoValue")}>
        {cur && (
          <>
            <Row k={t("climoSpeed")} v={String(cur.speed_knots)} />
            <Row k={t("climoDirectionTo")} v={`${cur.direction_to_deg}°`} />
            {cur.below_threshold && <Row k={t("climoFlag")} v={t("climoBelowThreshold")} />}
          </>
        )}
      </Block>
      <Block title={t("climoFilterCyclones")} empty={false}>
        <Row k={t("climoTracks")} v={String(cyc?.tracks_in_month ?? 0)} />
        {cyc?.crossings_if_leg && (
          <Row k={t("climoCrossings")} v={String(cyc.crossings_if_leg.count)} />
        )}
      </Block>
      <p className="text-[12px] leading-4 text-m-fg3 leading-relaxed">
        {point.provenance?.wind}
      </p>
    </div>
  );
}

function Block({ title, empty, emptyLabel, children }) {
  return (
    <div>
      <p className="text-[12px] leading-4 font-medium text-m-fg2 mb-1.5">{title}</p>
      {empty ? <p className="text-[12px] leading-4 text-m-fg3">{emptyLabel}</p> : <div className="space-y-0.5">{children}</div>}
    </div>
  );
}

function Row({ k, v }) {
  return (
    <div className="flex justify-between gap-3 text-[12px] leading-4">
      <span className="text-m-fg3">{k}</span>
      <span className="text-m-fg2 text-right m-num">{v}</span>
    </div>
  );
}
