/**
 * Pack d'extraction nauticals (regex / heuristiques versionnées).
 * Voir docs/VISION_EXTRACTION_NAUTICALS_HYBRIDE.md et docs/EXTRACTION_PACK_WORKFLOW.md
 */

import { readFileSync, existsSync } from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** Chemin du pack par défaut (repo root / data / …). */
export const DEFAULT_NAUTICAL_EXTRACTION_PACK_PATH = path.join(__dirname, "..", "data", "nautical-extraction-pack.default.json");

export interface NauticalExtractionPackFilter {
  /** Score minimum pour inclure la page dans nauticals (base 1 + bonus). */
  minRelevanceScore: number;
  /** Sous-chaînes (insensible à la casse) sur le slug wiki : exclusion si une correspond. */
  titleUrlBlacklist: string[];
  /** Si non vide : le slug doit contenir au moins une de ces sous-chaînes. */
  titleUrlWhitelist: string[];
  /** Mot-clé (wikitext en minuscules) → poids ajouté au score. */
  keywordWeights: Record<string, number>;
  /** Bonus par section « wanted » présente (titres == Section ==). */
  sectionPresenceBonus: number;
}

export interface NauticalExtractionPackExtraction {
  /** Sous-chaînes recherchées dans le titre de section (minuscules). */
  wantedSectionSubstrings: string[];
  /** Sections considérées comme caution (sous-chaîne dans le titre). */
  dangerSectionSubstrings: string[];
  maxSectionTextLength: number;
}

export interface NauticalExtractionPack {
  version: string;
  filter: NauticalExtractionPackFilter;
  extraction: NauticalExtractionPackExtraction;
}

export interface ExtractionPackContext {
  sourceUrl: string;
  /** Slug wiki sans domaine, ex. Ports_-_Greece/Hydra */
  pageSlug?: string;
}

export interface ApplyExtractionPackResult {
  include: boolean;
  score: number;
  lat: number | null;
  lng: number | null;
  description: string | null;
  caution: string | null;
  /** Raison d'exclusion ou détails debug */
  excludeReason?: string;
}

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

/** Valide minimalement la structure d'un pack JSON. */
export function parseNauticalExtractionPack(raw: unknown): NauticalExtractionPack {
  if (!isPlainObject(raw)) throw new Error("Extraction pack: root must be an object");
  const version = raw.version;
  if (typeof version !== "string" || !version.trim()) throw new Error("Extraction pack: missing version");

  const filter = raw.filter;
  if (!isPlainObject(filter)) throw new Error("Extraction pack: missing filter");

  const minRelevanceScore = filter.minRelevanceScore;
  if (typeof minRelevanceScore !== "number" || Number.isNaN(minRelevanceScore)) {
    throw new Error("Extraction pack: filter.minRelevanceScore must be a number");
  }

  const titleUrlBlacklist = filter.titleUrlBlacklist;
  const titleUrlWhitelist = filter.titleUrlWhitelist;
  if (!Array.isArray(titleUrlBlacklist) || !titleUrlBlacklist.every((x) => typeof x === "string")) {
    throw new Error("Extraction pack: filter.titleUrlBlacklist must be string[]");
  }
  if (!Array.isArray(titleUrlWhitelist) || !titleUrlWhitelist.every((x) => typeof x === "string")) {
    throw new Error("Extraction pack: filter.titleUrlWhitelist must be string[]");
  }

  const keywordWeights = filter.keywordWeights;
  if (!isPlainObject(keywordWeights)) throw new Error("Extraction pack: filter.keywordWeights must be an object");
  for (const [k, v] of Object.entries(keywordWeights)) {
    if (typeof v !== "number" || Number.isNaN(v)) throw new Error(`Extraction pack: keywordWeights["${k}"] must be a number`);
  }

  const sectionPresenceBonus = filter.sectionPresenceBonus;
  if (typeof sectionPresenceBonus !== "number" || Number.isNaN(sectionPresenceBonus)) {
    throw new Error("Extraction pack: filter.sectionPresenceBonus must be a number");
  }

  const extraction = raw.extraction;
  if (!isPlainObject(extraction)) throw new Error("Extraction pack: missing extraction");

  const wanted = extraction.wantedSectionSubstrings;
  const danger = extraction.dangerSectionSubstrings;
  const maxLen = extraction.maxSectionTextLength;
  if (!Array.isArray(wanted) || !wanted.every((x) => typeof x === "string")) {
    throw new Error("Extraction pack: extraction.wantedSectionSubstrings must be string[]");
  }
  if (!Array.isArray(danger) || !danger.every((x) => typeof x === "string")) {
    throw new Error("Extraction pack: extraction.dangerSectionSubstrings must be string[]");
  }
  if (typeof maxLen !== "number" || maxLen < 1) {
    throw new Error("Extraction pack: extraction.maxSectionTextLength must be a positive number");
  }

  return {
    version,
    filter: {
      minRelevanceScore,
      titleUrlBlacklist: titleUrlBlacklist.map((s) => s.toLowerCase()),
      titleUrlWhitelist: titleUrlWhitelist.map((s) => s.toLowerCase()),
      keywordWeights: Object.fromEntries(Object.entries(keywordWeights).map(([k, v]) => [k.toLowerCase(), v as number])),
      sectionPresenceBonus,
    },
    extraction: {
      wantedSectionSubstrings: wanted.map((s) => s.toLowerCase()),
      dangerSectionSubstrings: danger.map((s) => s.toLowerCase()),
      maxSectionTextLength: maxLen,
    },
  };
}

/** Slug wiki depuis une URL source Cruisers Wiki. */
export function pageSlugFromSourceUrl(sourceUrl: string): string {
  const m = sourceUrl.match(/\/wiki\/(.+?)(?:\?|$)/);
  const raw = m ? m[1] : sourceUrl.replace(/^https?:\/\/[^/]+\/wiki\//, "");
  try {
    return decodeURIComponent(raw).replace(/\s+/g, "_");
  } catch {
    return raw.replace(/\s+/g, "_");
  }
}

/** Parse {{coord|...}} → { lat, lng } ou null (logique historique server.ts). */
export function parseCoordFromWikitext(wikitext: string): { lat: number; lng: number } | null {
  /** Contenu entre {{coord| et }} (peut contenir plusieurs | pour lat|lng décimaux). */
  const coordRe = /\{\{[Cc]oord\s*\|([^}]*)\}\}/;
  const m = coordRe.exec(wikitext);
  if (!m) return null;
  const parts = m[1].split("|").map((p) => p.trim()).filter(Boolean);
  if (parts.length >= 2) {
    const a = parseFloat(parts[0]);
    const b = parseFloat(parts[1]);
    if (!isNaN(a) && !isNaN(b)) {
      if (Math.abs(a) <= 90 && Math.abs(b) <= 180) return { lat: a, lng: b };
      if (Math.abs(a) <= 180 && Math.abs(b) <= 90) return { lat: b, lng: a };
    }
  }
  if (parts.length >= 6) {
    const degLat = parseFloat(parts[0]) || 0;
    const minLat = parseFloat(parts[1]) || 0;
    const ns = (parts[2] || "").toUpperCase();
    const degLng = parseFloat(parts[3]) || 0;
    const minLng = parseFloat(parts[4]) || 0;
    const ew = (parts[5] || "").toUpperCase();
    const lat = degLat + minLat / 60;
    const lng = degLng + minLng / 60;
    if (ns === "S") return { lat: -lat, lng: ew === "W" ? -lng : lng };
    return { lat, lng: ew === "W" ? -lng : lng };
  }
  return null;
}

/** Liste des titres de sections (== Titre ==) en minuscules. */
function listSectionTitlesLower(wikitext: string): string[] {
  const sectionRe = /^==\s*(.+?)\s*==\s*$/gm;
  const out: string[] = [];
  let m: RegExpExecArray | null;
  while ((m = sectionRe.exec(wikitext)) !== null) {
    out.push(m[1].trim().toLowerCase());
  }
  return out;
}

/** Extrait description et caution selon le pack. */
export function parseDescriptionFromWikitextWithPack(
  wikitext: string,
  extraction: NauticalExtractionPackExtraction
): { description: string | null; caution: string | null } {
  const sectionRe = /^==\s*(.+?)\s*==\s*$/gm;
  const blocks: { name: string; text: string }[] = [];
  let m: RegExpExecArray | null;
  let lastEnd = 0;
  while ((m = sectionRe.exec(wikitext)) !== null) {
    if (blocks.length > 0) blocks[blocks.length - 1].text = wikitext.slice(lastEnd, m.index).trim();
    blocks.push({ name: m[1].trim(), text: "" });
    lastEnd = m.index + m[0].length;
  }
  if (blocks.length > 0) blocks[blocks.length - 1].text = wikitext.slice(lastEnd).trim();

  const sections: string[] = [];
  let caution: string | null = null;
  const maxLen = extraction.maxSectionTextLength;
  const wanted = extraction.wantedSectionSubstrings;
  const dangerSubs = extraction.dangerSectionSubstrings;

  for (const b of blocks) {
    const n = b.name.toLowerCase();
    let text = b.text
      .replace(/\{\{[^}]*\}\}/g, " ")
      .replace(/\[\[([^|\]]*\|)?([^\]]+)\]\]/g, "$2")
      .replace(/\s+/g, " ")
      .trim();
    if (text.length > maxLen) text = text.slice(0, maxLen) + "...";
    if (dangerSubs.some((d) => n.includes(d))) caution = text || caution;
    else if (wanted.some((w) => n.includes(w)) && text) sections.push(`${b.name}: ${text}`);
  }
  return {
    description: sections.length > 0 ? sections.join("\n\n") : null,
    caution: caution || null,
  };
}

function computeRelevanceScore(
  wikitext: string,
  slugLower: string,
  pack: NauticalExtractionPack
): { score: number; excludeReason?: string } {
  const { filter, extraction } = pack;

  for (const bl of filter.titleUrlBlacklist) {
    if (bl && slugLower.includes(bl)) {
      return { score: 0, excludeReason: `blacklist:${bl}` };
    }
  }

  if (filter.titleUrlWhitelist.length > 0) {
    const ok = filter.titleUrlWhitelist.some((w) => w && slugLower.includes(w));
    if (!ok) {
      return { score: 0, excludeReason: "whitelist:no_match" };
    }
  }

  let score = 1;
  const lower = wikitext.toLowerCase();
  for (const [kw, w] of Object.entries(filter.keywordWeights)) {
    if (kw && lower.includes(kw)) score += w;
  }

  if (filter.sectionPresenceBonus !== 0) {
    const titles = listSectionTitlesLower(wikitext);
    let bonusCount = 0;
    for (const t of titles) {
      if (extraction.wantedSectionSubstrings.some((w) => t.includes(w))) bonusCount++;
    }
    score += bonusCount * filter.sectionPresenceBonus;
  }

  if (score < filter.minRelevanceScore) {
    return { score, excludeReason: `below_min_score:${score}<${filter.minRelevanceScore}` };
  }

  return { score };
}

/**
 * Applique le pack : filtre de pertinence + extraction coords / description / caution.
 */
export function applyExtractionPack(wikitext: string, context: ExtractionPackContext, pack: NauticalExtractionPack): ApplyExtractionPackResult {
  const slug = (context.pageSlug ?? pageSlugFromSourceUrl(context.sourceUrl)).toLowerCase();
  const { score, excludeReason } = computeRelevanceScore(wikitext, slug, pack);

  const coord = parseCoordFromWikitext(wikitext);
  const { description, caution } = parseDescriptionFromWikitextWithPack(wikitext, pack.extraction);

  if (excludeReason) {
    return {
      include: false,
      score,
      lat: coord?.lat ?? null,
      lng: coord?.lng ?? null,
      description,
      caution,
      excludeReason,
    };
  }

  return {
    include: true,
    score,
    lat: coord?.lat ?? null,
    lng: coord?.lng ?? null,
    description,
    caution,
  };
}

/**
 * Charge un pack depuis un fichier JSON.
 * @param explicitPath chemin absolu ou relatif ; sinon env NAUTICAL_EXTRACTION_PACK_PATH ; sinon default repo file.
 */
export function loadExtractionPack(explicitPath?: string | null): NauticalExtractionPack {
  const fromEnv = typeof process !== "undefined" && process.env?.NAUTICAL_EXTRACTION_PACK_PATH?.trim();
  const p = explicitPath?.trim() || fromEnv || DEFAULT_NAUTICAL_EXTRACTION_PACK_PATH;
  const resolved = path.isAbsolute(p) ? p : path.join(process.cwd(), p);
  if (!existsSync(resolved)) {
    throw new Error(`Extraction pack file not found: ${resolved}`);
  }
  const raw = JSON.parse(readFileSync(resolved, "utf8")) as unknown;
  return parseNauticalExtractionPack(raw);
}

let memoPack: NauticalExtractionPack | null = null;

/** Charge le pack une fois (env NAUTICAL_EXTRACTION_PACK_PATH ou fichier default). */
export function getMemoizedExtractionPack(): NauticalExtractionPack {
  if (memoPack) return memoPack;
  memoPack = loadExtractionPack();
  return memoPack;
}

/** Réinitialise le cache (tests). */
export function resetExtractionPackMemo(): void {
  memoPack = null;
}
