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

// Meridian status pattern: shape + colour + label, the same in the sidebar cards,
// the map popups and the legend. Colours live in index.css (--tier1 … --tier-none).
export const TIER_COLOR = {
  tier1: "#4fb67f",
  tier2: "#3cb5a8",
  tier_registered: "#9b87f5",
  tier3: "#8f8f8f",
  none: "#5e5e5e",
};
export const TIER_ORDER = ["tier1", "tier2", "tier_registered", "tier3"];

/**
 * Readable title of a source URL: the last path segment without its hash/date
 * prefix, extension and separators ("ca0e0347-bermuda_customs_guidelines.pdf" ->
 * "Bermuda customs guidelines (PDF)"); the host when the path is empty.
 */
export function sourceTitle(url) {
  try {
    const u = new URL(url);
    const segs = decodeURIComponent(u.pathname).split("/").filter(Boolean);
    let leaf = segs.pop() || "";
    const ext = (leaf.match(/\.([a-z0-9]{2,5})$/i) || [])[1] || "";
    if (ext) leaf = leaf.slice(0, -(ext.length + 1));
    leaf = leaf
      .replace(/^[0-9a-f]{6,}[-_]/i, "")
      .replace(/^\d{6,}[-_]/, "")
      .replace(/[-_.+]+/g, " ")
      .replace(/\s+/g, " ")
      .trim();
    if (!leaf || /^(index|default|home)$/i.test(leaf)) leaf = segs.pop() || u.hostname.replace(/^www\./, "");
    leaf = leaf.charAt(0).toUpperCase() + leaf.slice(1);
    const kind = /^(pdf|docx?|xlsx?|pptx?)$/i.test(ext) ? ` (${ext.toUpperCase()})` : "";
    return leaf + kind;
  } catch (_) {
    return String(url || "");
  }
}

// Entry terms highlighted in an evidence excerpt when the run did not record one
// (display only; the tier never depends on this list).
export const ENTRY_TERMS = [
  "first port of entry", "ports of entry", "port of entry", "port d'entrée", "ports d'entrée",
  "customs and immigration", "customs clearance", "clear customs", "customs", "immigration",
  "clearance", "douane", "dédouanement", "yacht reporting centre",
];
const PREFIX_RE = /^(port autonome d[e']?|port of|port de|port d'|porto d[eoa]|puerto de[l]?|harbou?r of|marina d[ei]|marina|luka|porto|puerto|port)\s+/iu;

/** Name variants of a port worth highlighting: the name, without its facility word, and the match recorded by the run. */
export function portNameVariants(port, evidence) {
  const names = [evidence?.name_found, port?.name].filter(Boolean).map((n) => String(n).trim());
  const bare = names.map((n) => n.replace(PREFIX_RE, "")).filter((n) => n && n.length > 2);
  return [...new Set([...names, ...bare])];
}

/** Cut a stored excerpt to word boundaries; `lead` / `trail` say where an ellipsis belongs. */
export function trimSnippet(snippet) {
  let text = String(snippet || "").replace(/\s+/g, " ").trim();
  let lead = false;
  let trail = false;
  if (text && !/^[\p{Lu}\p{N}("“'[«]/u.test(text)) {
    const i = text.indexOf(" ");
    if (i > 0 && i < 30) text = text.slice(i + 1);
    lead = true;
  }
  if (text && !/[.!?…)”"'»]$/u.test(text)) {
    const i = text.lastIndexOf(" ");
    if (i > 0 && text.length - i < 30) text = text.slice(0, i);
    trail = true;
  }
  return { text, lead, trail };
}

const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/['’]/g, "['’]");

/**
 * Excerpt as segments [{text, mark}] with the port name and the entry term marked.
 * Terms: the run's name_found / entry_term when present, else the name variants and
 * the ENTRY_TERMS list. Longest term first so "first port of entry" wins over "customs".
 */
export function snippetSegments(snippet, terms, { repeat = [] } = {}) {
  const { text, lead, trail } = trimSnippet(snippet);
  const list = [...new Set((terms || []).filter(Boolean).map((t) => String(t).trim()).filter((t) => t.length > 1))]
    .sort((a, b) => b.length - a.length);
  if (!text || !list.length) return { lead, trail, segments: [{ text, mark: false }] };
  const re = new RegExp(`(?<![\\p{L}\\p{N}])(?:${list.map(escapeRe).join("|")})(?![\\p{L}\\p{N}])`, "giu");
  const segments = [];
  const seen = new Set();
  const again = new Set(repeat.map((t) => String(t).toLowerCase().replace(/[’]/g, "'")));
  let last = 0;
  for (const m of text.matchAll(re)) {
    // Each term is marked once (names, generic entry terms); only the entry term the
    // run recorded is marked at every occurrence, so the excerpt stays readable.
    const key = m[0].toLowerCase().replace(/[’]/g, "'");
    if (seen.has(key) && !again.has(key)) continue;
    seen.add(key);
    if (m.index > last) segments.push({ text: text.slice(last, m.index), mark: false });
    segments.push({ text: m[0], mark: true });
    last = m.index + m[0].length;
  }
  if (last < text.length) segments.push({ text: text.slice(last), mark: false });
  return { lead, trail, segments };
}

/** Terms to mark for one evidence item of a port, and whether to mark each once. */
export function evidenceTerms(port, evidence) {
  const names = portNameVariants(port, evidence);
  return evidence?.entry_term ? [...names, evidence.entry_term] : [...names, ...ENTRY_TERMS];
}
export function evidenceMarkOptions(evidence) {
  return { repeat: evidence?.entry_term ? [evidence.entry_term] : [] };
}

// Telemetry values as words (display only; the raw value stays in the title).
export function telemetryWord(value, t) {
  const v = String(value || "").trim();
  if (!v) return "—";
  const key = `poeTelemetry_${v.toLowerCase().replace(/[^a-z0-9]+/g, "_")}`;
  return t(key) !== key ? t(key) : v;
}

/** "nightshift: offline; nvidia: not_configured" -> "Nightshift offline, NVIDIA not configured". */
export function fallbackReasonText(reason, t) {
  const raw = String(reason || "").trim();
  if (!raw) return "";
  const parts = raw.split(/;\s*/).map((part) => {
    const [name, state] = part.split(/:\s*/);
    if (!state) return part;
    return `${telemetryWord(name, t)} ${telemetryWord(state, t)}`;
  });
  return parts.join(", ");
}

/** Inline SVG glyph of a tier (12 px): filled disc + check, ring + check, half ring, dashed ring. */
export function tierGlyphSvg(tier) {
  const c = TIER_COLOR[tier] || TIER_COLOR.none;
  const check = (stroke) => `<path d="M3.9 6.2l1.5 1.5 2.9-3" fill="none" stroke="${stroke}" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>`;
  let body;
  if (tier === "tier1") body = `<circle cx="6" cy="6" r="5.25" fill="${c}"/>${check("#121212")}`;
  else if (tier === "tier2") body = `<circle cx="6" cy="6" r="4.75" fill="none" stroke="${c}" stroke-width="1.4"/>${check(c)}`;
  else if (tier === "tier_registered") body = `<circle cx="6" cy="6" r="4.75" fill="none" stroke="${c}" stroke-width="1.4"/><path d="M6 1.25a4.75 4.75 0 0 1 0 9.5z" fill="${c}"/>`;
  else if (tier === "tier3") body = `<circle cx="6" cy="6" r="4.75" fill="none" stroke="${c}" stroke-width="1.4" stroke-dasharray="2.2 1.9" stroke-linecap="round"/>`;
  else body = `<circle cx="6" cy="6" r="4.75" fill="none" stroke="${c}" stroke-width="1.4"/>`;
  return `<svg viewBox="0 0 12 12" width="12" height="12" aria-hidden="true" focusable="false">${body}</svg>`;
}

/** Inline chip style for a tier (kept for the review page): chip colour as a CSS variable. */
export function tierStyle(tier) {
  const color = TIER_COLOR[tier] || TIER_COLOR.none;
  return { "--tier-c": color };
}

/** {tier, label, short} for a port: its registry tier labels, or "Not yet verified". */
export function registryBadge(port, t) {
  const registry = port?.registry;
  const tier = registry?.tier;
  if (!tier) return { tier: "none", label: t("poeTierNone"), short: t("poeTierNone") };
  const key = `poeTier_${tier}`;
  const label = t(key) !== key ? t(key) : (registry.label || tier);
  const shortKey = `poeTierShort_${tier}`;
  const short = t(shortKey) !== shortKey ? t(shortKey) : label;
  return { tier: TIER_COLOR[tier] ? tier : "none", label, short };
}

/** Verdict of the last run in words, or null before any Verify. */
export function verdictLabel(port, t) {
  if (port?.verdict === "pass") return { key: "pass", text: t("poeVerdictPass") };
  if (port?.verdict === "flag" || port?.verdict === "retry") return { key: "flag", text: t("poeVerdictFlag") };
  return null;
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

/** Popup (inline HTML) version of the chip: glyph + short label, full label as title. */
export function registryBadgeHtml(port, t, esc) {
  const { tier, label, short } = registryBadge(port, t);
  const color = TIER_COLOR[tier] || TIER_COLOR.none;
  const cls = tier === "none" ? "tier-chip tier-chip--none" : "tier-chip";
  return `<span class="${cls}" style="--tier-c:${color}" title="${esc(label)}" data-testid="poe-popup-tier-${esc(tier)}"><span class="tier-glyph">${tierGlyphSvg(tier)}</span>${esc(short)}</span>`;
}

// Same rules as registry_check.port_key in the backend, so a /poe/verify port ("Port of
// St. George’s") matches its fiche port ("St. George's"). Both sides are tested against
// __tests__/portKeyCases.json, generated from the backend.
const POSSESSIVE = /['’‘`´]s(?![\p{L}\p{N}_])/giu;
const APOSTROPHES = /['’‘`´]/g;
// Leading facility words ("Port of X", "Porto de X", "Luka X"); one is removed.
const PORT_PREFIXES = [
  "port autonome de", "port autonome d", "pkk porti i", "porti i", "port of", "port de", "port d",
  "porto de", "porto do", "porto da", "puerto de", "puerto del", "harbour of", "harbor of",
  "marina de", "marina di", "marina", "luka", "porto", "puerto", "port", "the",
];
// Trailing facility words ("Bridgetown Port", "Anchorage Small Boat Harbor"); one is removed.
const PORT_SUFFIXES = [
  "small boat harbour", "small boat harbor", "deep water harbour", "deep water harbor",
  "harbour", "harbor", "port", "marina", "jetty", "terminal",
];
const PORT_TOKENS = { st: "saint", ste: "sainte", mt: "mount", ft: "fort", pt: "point" };

/** Casefold, strip accents and punctuation: "Luka Brčko" -> "luka brcko" (backend name_key). */
function nameKey(name) {
  return String(name || "")
    .normalize("NFKD")
    .replace(/\p{Mn}/gu, "")
    .toLowerCase()
    .replace(/ß/g, "ss")
    .replace(/ς/g, "σ")
    .replace(APOSTROPHES, "")
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim();
}

/** The first matching facility word removed, at the start or the end (backend _strip). */
function stripOnce(key, words, leading) {
  for (const word of words) {
    if (leading && key.startsWith(`${word} `)) return key.slice(word.length + 1);
    if (!leading && key.endsWith(` ${word}`)) return key.slice(0, -word.length - 1);
  }
  return key;
}

/** A port's name without facility words, St spelled out ("saint george"). */
export function portKey(name) {
  const key = nameKey(String(name || "").replace(POSSESSIVE, ""));
  const stripped = stripOnce(stripOnce(key, PORT_PREFIXES, true), PORT_SUFFIXES, false) || key;
  return stripped.split(" ").filter(Boolean).map((t) => PORT_TOKENS[t] || t).join(" ");
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
