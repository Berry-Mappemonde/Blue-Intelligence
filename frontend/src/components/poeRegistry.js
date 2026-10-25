/**
 * Registry evidence (PR #34) and POST /poe/verify results, shared by the sidebar
 * fiche (ZoneFiche) and the map popup (zonePopup) so both show the same badge and
 * the same score for a port.
 *
 * port.registry = {tier, label, validation, matches, official_evidence,
 *                  coord_mismatch, first_port_of_entry, reasons}
 * tier1 / tier2 need official-source evidence; tier_registered is a UN/LOCODE or
 * World Port Index match only; tier3 is neither. No registry: not verified yet.
 */

// One colour per tier, used by the sidebar badge and the popup so both match.
// tier_registered (registry match only) has its own colour, apart from tier3.
export const TIER_COLOR = {
  tier1: "#4ade80",
  tier2: "#5eead4",
  tier_registered: "#a78bfa",
  tier3: "#fbbf24",
  none: "#94a3b8",
};

/** Inline badge style for a tier: coloured text, faint border and background. */
export function tierStyle(tier) {
  const color = TIER_COLOR[tier] || TIER_COLOR.none;
  return { color, borderColor: `${color}66`, backgroundColor: `${color}1a` };
}

/** {tier, label} for a port: the i18n label of its registry tier, or "Not yet verified". */
export function registryBadge(port, t) {
  const registry = port?.registry;
  const tier = registry?.tier;
  if (!tier) return { tier: "none", label: t("poeTierNone") };
  const key = `poeTier_${tier}`;
  const label = t(key) !== key ? t(key) : (registry.label || tier);
  return { tier: TIER_COLOR[tier] ? tier : "none", label };
}

/** Closest same-name registry entry beyond the match distance, or null. */
export function closestCoordMismatch(port) {
  const list = (port?.registry?.coord_mismatch || []).filter((m) => m?.distance_km != null);
  if (!list.length) return null;
  return list.reduce((a, b) => (b.distance_km < a.distance_km ? b : a));
}

/** Short notes under the badge: coordinate mismatch and the WPI first-port-of-entry field. */
export function registryNotes(port, t) {
  const notes = [];
  const mismatch = closestCoordMismatch(port);
  if (mismatch) {
    const source = mismatch.source === "wpi" ? "WPI" : "UN/LOCODE";
    notes.push({
      key: "coord",
      text: `${t("poeCoordMismatch")} ${Number(mismatch.distance_km).toFixed(1)} km (${source} ${mismatch.code || ""})`.trim(),
    });
  }
  const fpoe = port?.registry?.first_port_of_entry;
  if (fpoe === "Yes" || fpoe === "No") {
    notes.push({ key: "wpi", text: t(`poeWpiFpoe_${fpoe}`) });
  }
  return notes;
}

/** Popup (inline HTML) version of the badge. `esc` escapes HTML. */
export function registryBadgeHtml(port, t, esc) {
  const { tier, label } = registryBadge(port, t);
  const { color, borderColor, backgroundColor } = tierStyle(tier);
  return `<span data-testid="poe-popup-tier-${esc(tier)}" style="font-family:'JetBrains Mono',monospace;font-size:8px;color:${color};border:1px solid ${borderColor};background:${backgroundColor};padding:0 4px;border-radius:2px;">${esc(label)}</span>`;
}

function portKey(name) {
  return String(name || "")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/['’`]/g, "")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

/**
 * The fiche with a /poe/verify result merged in. The response lists ports as
 * validated_ports + non_validated_ports (not `ports`); each is matched to the
 * fiche's port by name and brings its registry evidence and the run's confidence.
 * Ports only the run returned are appended. `verify` holds the run's telemetry.
 */
export function mergeVerifyIntoFiche(fiche, result) {
  const verified = [...(result?.validated_ports || []), ...(result?.non_validated_ports || [])];
  const byKey = new Map(verified.map((p) => [portKey(p.name), p]));
  const used = new Set();
  const ports = (fiche?.ports || []).map((p) => {
    const key = portKey(p.name);
    const v = byKey.get(key);
    if (!v) return p;
    used.add(key);
    return {
      ...p,
      registry: v.registry ?? p.registry,
      verdict: v.verdict ?? p.verdict,
      confidence: v.confidence ?? p.confidence,
      // The stored breakdown described the stored score; the run's reasons describe its own.
      confidence_parts: v.confidence != null ? null : p.confidence_parts,
      confidence_reasons: v.confidence != null ? (v.reasons_en || []) : p.confidence_reasons,
      reasons_en: v.confidence != null ? (v.reasons_en || []) : p.reasons_en,
      lat: p.lat ?? v.lat,
      lon: p.lon ?? v.lon,
    };
  });
  verified.forEach((v) => {
    if (used.has(portKey(v.name))) return;
    ports.push({
      ...v,
      source_urls: (v.sources || []).map((s) => s?.url).filter(Boolean),
      confidence_reasons: v.reasons_en || [],
    });
  });
  const scores = ports.map((p) => p.confidence).filter((c) => typeof c === "number");
  return {
    ...fiche,
    ports,
    confidence_avg: scores.length
      ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length)
      : fiche?.confidence_avg,
    verify: {
      run_id: result?.run_id,
      trace_name: result?.trace_name,
      nemotron_status: result?.nemotron_status || null,
      memory: result?.memory || null,
      zetaris_mode: result?.zetaris_mode || null,
      error: result?.error || null,
    },
  };
}
