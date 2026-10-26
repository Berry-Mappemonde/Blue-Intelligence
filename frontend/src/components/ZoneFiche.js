import React, { useState } from "react";
import { Check, ChevronRight, ExternalLink } from "lucide-react";
import ConfidenceBreakdown from "./ConfidenceBreakdown";
import { evidenceMarkOptions, evidenceTerms, fallbackReasonText, registryBadge, registryNotes, snippetSegments, sourceTitle, telemetryWord, tierGlyphSvg, tierStyle, verdictLabel } from "./poeRegistry";
import { zoneDisplayName } from "./map/zoneLabel";

/**
 * ErrorBoundary — évite l'écran blanc si un composant enfant de la fiche
 * plante au render (champ mannant, objet passé en enfant JSX, etc.).
 */
class ErrorBoundary extends React.Component {
  state = { hasError: false, error: null };
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, errorInfo) {
    // eslint-disable-next-line no-console
    console.error("[ZoneFiche ErrorBoundary]", error, errorInfo);
  }
  render() {
    if (this.state.hasError) {
      return (
        <section className="px-4 py-3 border-b border-m-line font-ui">
          <p className="text-[12px] leading-4 text-m-danger-fg" data-testid="poe-fiche-error">
            Erreur d'affichage de la fiche — champ manquant ou donnée invalide.
          </p>
        </section>
      );
    }
    return this.props.children;
  }
}

function hostOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch (_) {
    return url;
  }
}

function pathHint(url) {
  try {
    const leaf = decodeURIComponent(new URL(url).pathname).split("/").filter(Boolean).pop() || "";
    if (leaf.length < 3) return "";
    return leaf.length > 52 ? `${leaf.slice(0, 50)}…` : leaf;
  } catch (_) {
    return "";
  }
}

function tdListOf(fiche) {
  const list = (fiche?.sources_td || []).filter((rec) => rec?.url);
  if (list.length) return list;
  if (fiche?.url_td?.url) return [fiche.url_td];
  return [];
}

function buListOf(port) {
  const list = (port?.urls_bu || []).filter((rec) => rec?.url);
  if (list.length) return list;
  const href = buUrlOf(port);
  return href ? [{ url: href }] : [];
}

function tdUrlOf(fiche) {
  return fiche?.url_td?.url || (fiche?.sources_td || [])[0]?.url || "";
}

function buUrlOf(port) {
  if (typeof port?.url_bu === "string") return port.url_bu;
  return port?.url_bu?.url || (port?.source_urls || [])[0] || "";
}

/** Source link: readable title on the first line, domain underneath. */
function SourceLink({ href, testId, pathTestId }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      data-testid={testId}
      className="min-w-0 block text-[13px] leading-[18px] text-m-accent-fg hover:underline underline-offset-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-m-accent rounded-sm"
      title={pathHint(href) || href}
    >
      <span className="block truncate" data-testid={pathTestId}>{sourceTitle(href)}</span>
      <span className="block text-[12px] leading-4 text-m-fg3 truncate">{hostOf(href)}</span>
    </a>
  );
}

function TdRow({ rec, testId, pathTestId, selectable, kept, onToggle, keepTestId }) {
  const href = rec?.url || "";
  const both = rec?.from_arm === "both";
  return (
    <div className="flex items-start justify-between gap-3 min-w-0">
      {selectable ? (
        <label className="flex items-start gap-2 min-w-0 flex-1">
          <input
            type="checkbox"
            data-testid={keepTestId}
            checked={Boolean(kept)}
            onChange={onToggle}
            className="mt-1 shrink-0 accent-m-accent"
          />
          <SourceLink href={href} testId={testId} pathTestId={pathTestId} />
        </label>
      ) : (
        <SourceLink href={href} testId={testId} pathTestId={pathTestId} />
      )}
      <div className="flex items-center gap-2 shrink-0 mt-0.5">
        {both && (
          <span className="text-[11px] leading-4 text-m-fg3" title={rec.bothLabel}>{rec.bothLabel}</span>
        )}
        <a href={href} target="_blank" rel="noreferrer" className="text-m-fg3 hover:text-m-fg" aria-label={hostOf(href)}>
          <ExternalLink size={14} strokeWidth={1.75} />
        </a>
      </div>
    </div>
  );
}

/** Registry tier chip (status pattern: glyph + colour + label), or "Not yet verified". */
function RegistryBadge({ port, t }) {
  const { tier, label, short } = registryBadge(port, t);
  return (
    <span
      key={tier}
      className={`tier-chip tier-chip-in ${tier === "none" ? "tier-chip--none" : ""}`}
      style={tierStyle(tier)}
      data-testid={`poe-fiche-tier-${tier}`}
      title={(port?.registry?.reasons || [])[0] || label}
    >
      {/* Static SVG built by tierGlyphSvg(); no user content inside. */}
      <span className="tier-glyph" dangerouslySetInnerHTML={{ __html: tierGlyphSvg(tier) }} />
      {short}
    </span>
  );
}

/** Official evidence of a port (registry.official_evidence): source domain, excerpt collapsed. */
function OfficialEvidence({ evidence, port, t }) {
  if (!evidence?.length) return null;
  return (
    <div className="mt-1.5 space-y-1" data-testid="poe-fiche-evidence">
      {evidence.map((e) => {
        const { lead, trail, segments } = snippetSegments(e.snippet, evidenceTerms(port, e), evidenceMarkOptions(e));
        return (
          <details key={e.url} className="m-details" data-testid="poe-fiche-evidence-item">
            <summary className="flex items-center gap-1.5 text-[12px] leading-4 text-m-fg3 hover:text-m-fg2">
              <ChevronRight size={12} strokeWidth={1.75} className="m-disclosure shrink-0" aria-hidden="true" />
              <span className="truncate">
                {t("poeEvidenceTitle")}: <a
                  href={e.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-m-accent-fg hover:underline underline-offset-2"
                  title={e.url}
                  onClick={(ev) => ev.stopPropagation()}
                >
                  {e.domain}
                </a>
              </span>
            </summary>
            <p className="m-details-body mt-1 ml-[18px] pl-2 border-l border-m-line-strong text-[12px] leading-4 text-m-fg2 break-words">
              {lead ? "… " : ""}
              {segments.map((s, i) => (s.mark
                ? <mark key={i} className="m-mark">{s.text}</mark>
                : <React.Fragment key={i}>{s.text}</React.Fragment>))}
              {trail ? " …" : ""}
            </p>
          </details>
        );
      })}
    </div>
  );
}

/** "How we checked": telemetry of the last Verify run, read from its payload only. */
function VerifyTelemetry({ verify, t }) {
  const ns = verify?.nemotron_status || {};
  const mem = verify?.memory || {};
  const row = (label, value, testId, mono) => (
    <React.Fragment key={testId}>
      <dt className="text-m-fg3">{label}</dt>
      <dd className={`min-w-0 truncate text-m-fg ${mono ? "m-code" : "m-num"}`} data-testid={testId} title={value}>{value}</dd>
    </React.Fragment>
  );
  return (
    <div className="rounded-[10px] border border-m-line bg-m-panel px-3 py-2.5" data-testid="poe-fiche-telemetry">
      <p className="text-[12px] leading-4 font-medium text-m-fg2">{t("telemetryTitle")}</p>
      <dl className="mt-2 grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 text-[12px] leading-4">
        {row(t("telemetryZetaris"), telemetryWord(verify?.zetaris_mode, t), "poe-telemetry-zetaris")}
        {row(
          t("telemetryMemory"),
          `${mem.recalled ?? 0} ${t("telemetryRecalled")}, ${mem.reinforced ?? 0} ${t("telemetryReinforced")}, ${mem.created ?? 0} ${t("telemetryCreated")}`,
          "poe-telemetry-memory",
        )}
        {row(t("telemetryModel"), ns.model || "—", "poe-telemetry-model", true)}
        {row(t("telemetryProvider"), telemetryWord(ns.provider, t), "poe-telemetry-provider")}
        {row(t("telemetryRun"), verify?.run_id || "—", "poe-telemetry-run", true)}
        {ns.fallback_reason && ns.provider && ns.provider !== "nightshift"
          ? row(t("telemetryFallback"), fallbackReasonText(ns.fallback_reason, t), "poe-telemetry-fallback")
          : null}
      </dl>
    </div>
  );
}

/** Section heading: 12 px medium, sentence case; the optional count is tabular. */
function SectionHeading({ children, count }) {
  return (
    <p className="mb-1.5 text-[12px] leading-4 font-medium text-m-fg2">
      {children}
      {count != null ? <span className="m-num text-m-fg3"> {count}</span> : null}
    </p>
  );
}

/**
 * Review sheet for a VLIZ polygon — same gesture as ProjectList:
 * Review (variant=page): every TD + every BU per port.
 * Map (sidebar): one TD URL + one BU per PoE. No Generate button.
 *
 * V2: each port's badge comes from its registry tier (PR #34); "Verify" runs
 * POST /poe/verify and merges the result (see poeRegistry.mergeVerifyIntoFiche).
 */

export default function ZoneFiche({
  t, lang, fiche, loading, onFlyToPort, variant = "sidebar",
  choices, onChoice, onVerify, verifyState,
}) {
  // Hook avant les retours anticipés : React exige des appels inconditionnels.
  const [openPort, setOpenPort] = useState(null);
  if (loading) {
    return (
      <section className="px-4 py-3 border-b border-m-line font-ui" data-testid="poe-zone-fiche-loading">
        <p className="text-[12px] leading-4 text-m-fg3">{t("poeFicheLoading")}</p>
      </section>
    );
  }
  if (!fiche) return null;
  const selectable = variant === "page" && typeof onChoice === "function";
  const tdMap = choices?.td || {};
  const ports = fiche.ports || [];
  const tdSources = tdListOf(fiche);
  const td = tdUrlOf(fiche);
  const tdBoth = fiche?.url_td?.from_arm === "both" || (fiche?.sources_td || [])[0]?.from_arm === "both";
  const showAllTd = variant === "page";
  const portsMax = variant === "page" ? "max-h-[45vh]" : "";
  const unclos = fiche.unclos && typeof fiche.unclos === "object" ? fiche.unclos : null;
  const unclosKey = unclos?.code ? `poeUnclos_${unclos.code}` : "";
  const sourceCount = tdSources.length;
  const summaryBits = [
    `${ports.length} ${t(ports.length === 1 ? "poeSheetPortOne" : "poeSheetPorts")}`,
    sourceCount ? `${sourceCount} ${t(sourceCount === 1 ? "poeSheetSource" : "poeSheetSources")}` : null,
  ].filter(Boolean);
  return (
    <ErrorBoundary>
      <section key={fiche.mrgid} className="m-enter px-4 py-4 border-b border-m-line space-y-4 font-ui text-[13px] leading-[18px] text-m-fg" data-testid="poe-zone-fiche">
      {/* Name → one-line summary → Verify */}
      <div>
        <p className="text-[15px] leading-5 font-medium text-m-fg" data-testid="poe-fiche-zone-label">
          {zoneDisplayName(fiche, t)}
        </p>
        <p className="mt-0.5 text-[12px] leading-4 text-m-fg3 m-num">
          {summaryBits.join(" · ")}
          {fiche.confidence_avg != null ? (
            <> · {t("poeSheetAvg")} <span data-testid="poe-fiche-score" className="text-m-fg2">{fiche.confidence_avg}</span></>
          ) : null}
        </p>
        {variant === "page" && fiche.fiche_scope === "union" ? (
          <p className="mt-1 text-[12px] leading-4 text-m-fg3" data-testid="poe-fiche-union-hint">
            {t("reviewUnionHint")}
          </p>
        ) : null}
      </div>
      {typeof onVerify === "function" ? (
        <div>
          <button
            type="button"
            onClick={onVerify}
            disabled={Boolean(verifyState?.running)}
            data-testid="poe-fiche-verify"
            aria-busy={Boolean(verifyState?.running)}
            className={`m-btn w-full ${fiche.verify ? "m-btn-secondary" : "m-btn-primary"}`}
          >
            {verifyState?.running ? (
              <>
                <svg
                  className="animate-spin h-3.5 w-3.5"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                {t("poeVerifying")}
              </>
            ) : (
              t(fiche.verify ? "poeVerifyAgain" : "poeVerify")
            )}
          </button>
          {verifyState?.error ? (
            <p className="mt-1.5 text-[12px] leading-4 text-m-danger-fg break-words" data-testid="poe-fiche-verify-error">
              {t("poeVerifyFailed")}: {verifyState.error}
            </p>
          ) : (
            <p className="mt-1.5 text-[12px] leading-4 text-m-fg3 text-center">
              {fiche.verify
                ? `${t("poeVerifiedWith")} ${telemetryWord(fiche.verify?.nemotron_status?.provider, t, { inSentence: true })}, Zetaris ${telemetryWord(fiche.verify?.zetaris_mode, t, { inSentence: true })}`
                : t("poeVerifyHint")}
            </p>
          )}
        </div>
      ) : null}
      {fiche.verify ? <VerifyTelemetry verify={fiche.verify} t={t} /> : null}

      <div data-testid="poe-fiche-sources-td">
        <SectionHeading count={showAllTd && tdSources.length > 1 ? tdSources.length : null}>
          {t("poeSourcesTd")}
        </SectionHeading>
        {showAllTd ? (
          tdSources.length ? (
            <ul className="space-y-1.5" data-testid="poe-fiche-td-list">
              {tdSources.map((rec, i) => (
                <li key={rec.url}>
                  <TdRow
                    rec={{ ...rec, bothLabel: t("poeSourceBoth") }}
                    testId={i === 0 ? "poe-fiche-td-url" : `poe-fiche-td-url-${i}`}
                    pathTestId={i === 0 ? "poe-fiche-td-path" : undefined}
                    selectable={selectable}
                    kept={tdMap[rec.url] === "keep"}
                    keepTestId={i === 0 ? "poe-fiche-td-keep" : `poe-fiche-td-keep-${i}`}
                    onToggle={() => onChoice({
                      target: "td",
                      url: rec.url,
                      action: tdMap[rec.url] === "keep" ? "clear" : "keep",
                    })}
                  />
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-[12px] leading-4 text-m-fg3">{t("poeFicheEmptyTd")}</p>
          )
        ) : td ? (
          <div className="flex items-start justify-between gap-3 min-w-0">
            <SourceLink href={td} testId="poe-fiche-td-url" pathTestId="poe-fiche-td-path" />
            <div className="flex items-center gap-2 shrink-0 mt-0.5">
              {tdBoth && (
                <span className="text-[11px] leading-4 text-m-fg3">{t("poeSourceBoth")}</span>
              )}
              <a href={td} target="_blank" rel="noreferrer" className="text-m-fg3 hover:text-m-fg" aria-label={hostOf(td)}>
                <ExternalLink size={14} strokeWidth={1.75} />
              </a>
            </div>
          </div>
        ) : (
          <p className="text-[12px] leading-4 text-m-fg3">{t("poeFicheEmptyTd")}</p>
        )}
      </div>

      <div data-testid="poe-fiche-ports">
        <SectionHeading count={ports.length}>
          {t("poeFichePorts")}
          {variant === "page" ? (
            <span className="font-normal text-m-fg3"> — {t("reviewPortsPreview")}</span>
          ) : null}
        </SectionHeading>
        {ports.length === 0 ? (
          <p className="text-[12px] leading-4 text-m-fg3">{t("poeFicheNoPorts")}</p>
        ) : (
          <div className={`divide-y divide-m-line-soft border-t border-m-line-soft ${portsMax} overflow-y-auto`}>
            {ports.map((p) => {
              const href = buUrlOf(p);
              const bus = showAllTd ? buListOf(p) : (href ? [{ url: href }] : []);
              const canFly = p.lat != null && p.lon != null && onFlyToPort;
              const pid = p.port_id || p.id || p.name;
              const score = p.confidence;
              const notes = registryNotes(p, t);
              const verdict = verdictLabel(p, t);
              const isOpen = openPort === pid;
              return (
                <div
                  key={pid || p.name}
                  data-testid={`poe-fiche-port-${pid || p.name}`}
                  className="py-2.5"
                >
                  <div className="flex items-start justify-between gap-3">
                    <button
                      type="button"
                      disabled={!canFly}
                      onClick={() => canFly && onFlyToPort({
                        id: pid, lat: p.lat, lon: p.lon, name: p.name,
                      })}
                      className="min-w-0 flex-1 text-left disabled:cursor-default rounded-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-m-accent"
                      title={canFly ? p.name : undefined}
                    >
                      <p className="text-[13px] leading-[18px] font-medium text-m-fg truncate">{p.name}</p>
                    </button>
                    {score != null ? (
                      <button
                        type="button"
                        onClick={() => setOpenPort(isOpen ? null : pid)}
                        aria-expanded={isOpen}
                        title={t("poeWhy")}
                        data-testid={`poe-fiche-port-why-${pid || p.name}`}
                        className="m-num shrink-0 inline-flex items-center gap-1 text-[13px] leading-[18px] text-m-fg2 hover:text-m-fg rounded-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-m-accent"
                      >
                        <span className="text-[12px] text-m-fg3">{t("poeScore")}</span> {score}
                        <ChevronRight size={12} strokeWidth={1.75} className={`transition-transform duration-150 ${isOpen ? "rotate-90" : ""}`} aria-hidden="true" />
                      </button>
                    ) : p.city ? (
                      <span className="text-[12px] leading-4 text-m-fg3 truncate">{p.city}</span>
                    ) : null}
                  </div>
                  <div className="mt-1.5 flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0 flex-wrap">
                      <RegistryBadge port={p} t={t} />
                      {verdict ? (
                        <span
                          key={verdict.key}
                          className={`tier-chip-in inline-flex items-center gap-1 text-[12px] leading-4 ${verdict.key === "pass" ? "text-m-fg2" : "text-m-fg3"}`}
                          data-testid={`poe-fiche-verdict-${verdict.key}`}
                        >
                          {verdict.key === "pass" ? <Check size={12} strokeWidth={2} aria-hidden="true" /> : null}
                          {verdict.text}
                        </span>
                      ) : null}
                    </div>
                    {bus.length ? (
                      <div
                        className="flex flex-wrap items-center justify-end gap-2 min-w-0 shrink-0"
                        data-testid="poe-fiche-port-bu-list"
                      >
                        {bus.map((rec, i) => (
                          <a
                            key={rec.url}
                            href={rec.url}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1 text-m-fg3 hover:text-m-fg shrink-0"
                            data-testid={i === 0 ? "poe-fiche-port-bu" : `poe-fiche-port-bu-${i}`}
                            title={rec.url}
                            aria-label={hostOf(rec.url)}
                          >
                            {showAllTd && bus.length > 1 ? (
                              <span className="text-[12px] leading-4 text-m-accent-fg">{hostOf(rec.url)}</span>
                            ) : null}
                            <ExternalLink size={14} strokeWidth={1.75} />
                          </a>
                        ))}
                      </div>
                    ) : (
                      <span className="sr-only" data-testid="poe-fiche-port-bu-empty" />
                    )}
                  </div>
                  {notes.map((n) => (
                    <p
                      key={n.key}
                      className="mt-1 text-[12px] leading-4 text-m-fg3"
                      data-testid={`poe-fiche-note-${n.key}`}
                    >
                      {n.text}
                    </p>
                  ))}
                  {/* Without official evidence, the run's first reason says why the tier is what it is. */}
                  {!(p.registry?.official_evidence || []).length && (p.registry?.reasons || [])[0] ? (
                    <p className="mt-1 text-[12px] leading-4 text-m-fg3" data-testid="poe-fiche-reason">
                      {p.registry.reasons[0]}
                    </p>
                  ) : null}
                  <OfficialEvidence evidence={p.registry?.official_evidence} port={p} t={t} />
                  {isOpen && (
                    <ConfidenceBreakdown
                      parts={p.confidence_parts}
                      reasons={p.confidence_reasons}
                      reasonsEn={p.reasons_en}
                      lang={lang}
                      t={t}
                    />
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {unclos?.code ? (
        <div data-testid="poe-fiche-unclos" className="rounded-[10px] border border-m-line bg-m-panel px-3 py-2.5">
          <p className="text-[12px] leading-4 font-medium text-m-fg2">{t("poeUnclosTitle")}</p>
          <p className="mt-1 text-[12px] leading-4 text-m-fg2">
            {t(unclosKey) !== unclosKey ? t(unclosKey) : (unclos.label || unclos.code)}
          </p>
        </div>
      ) : null}
      </section>
    </ErrorBoundary>
  );
}
