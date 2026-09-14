/**
 * Phase 3 — Agent IA de mise à jour
 * - Priorisation selon modification_frequency (Phase 2)
 * - Fetch dernière archive valable (Wayback action=edit) via callback injecté
 * - Extraction wikitext → coords, sections, descriptions
 * - Fusion Claude : ancien + nouveau → décision de garder
 * - Validation : coords plausibles
 * - Enrichissement : pays + lat/lng via Claude pour entrées sans coords
 *
 * Stratégie : haute=mensuelle (30j), moyenne=trimestrielle (90j), basse=annuelle (365j)
 * Déclenché via POST /api/nauticals/wayback-phase3
 */

import type Database from "better-sqlite3";
import Anthropic from "@anthropic-ai/sdk";
import { inferCountryFromWaybackUrl, suggestCoordsWithClaude } from "./wayback-phase3";
import {
  getMemoizedExtractionPack,
  parseCoordFromWikitext,
  parseDescriptionFromWikitextWithPack,
} from "./nautical-extraction-pack";

const PRIORITY_ORDER = ["high", "medium", "low"] as const;
const MIN_DAYS_BY_PRIORITY: Record<string, number> = {
  high: 30,
  medium: 90,
  low: 365,
};

/** Extrait page title depuis source_url (ex: .../wiki/Ports_-_Greece/Hydra → Ports_-_Greece/Hydra). */
function pageTitleFromSourceUrl(sourceUrl: string): string {
  const m = sourceUrl.match(/\/wiki\/(.+?)(?:\?|$)/);
  return m ? decodeURIComponent(m[1]) : sourceUrl.replace(/^https?:\/\/[^/]+\/wiki\//, "");
}

/** Claude : fusion ancien + nouveau contenu, retourne structure validée. */
async function claudeMerge(
  oldData: { title: string; description: string | null; caution: string | null; lat: number | null; lng: number | null; country: string },
  newWikitext: string
): Promise<{ lat: number | null; lng: number | null; description: string | null; caution: string | null; country: string } | null> {
  const apiKey = process.env.CLAUDE_API_KEY || process.env.ANTHROPIC_API_KEY;
  if (!apiKey) return null;
  const client = new Anthropic({ apiKey });
  try {
    const msg = await client.messages.create({
      model: "claude-sonnet-4-5-20250929",
      max_tokens: 1024,
      messages: [
        {
          role: "user",
          content: `You are merging maritime port data. OLD data (from Wayback archive) vs NEW wikitext (from live Cruisers Wiki).

OLD: title=${oldData.title}, lat=${oldData.lat}, lng=${oldData.lng}, country=${oldData.country}, description=${(oldData.description || "").slice(0, 300)}, caution=${(oldData.caution || "").slice(0, 200)}

NEW wikitext (excerpt): ${newWikitext.slice(0, 2000)}

Extract from NEW: coordinates ({{coord|...}}), description (Navigation, Anchorages, etc.), caution (Dangers, Warnings).
Merge rules: prefer NEW coords if valid; keep OLD if NEW coords seem wrong (e.g. land, wrong hemisphere). Prefer NEW description if longer/detailed.

Reply with JSON only: {"lat": number|null, "lng": number|null, "description": string|null, "caution": string|null, "country": string}`,
        },
      ],
    });
    const text = msg.content?.[0]?.type === "text" ? (msg.content[0] as { text: string }).text : "";
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    if (!jsonMatch) return null;
    const parsed = JSON.parse(jsonMatch[0]) as { lat?: number | null; lng?: number | null; description?: string | null; caution?: string | null; country?: string };
    const lat = parsed.lat != null && !isNaN(Number(parsed.lat)) ? Number(parsed.lat) : null;
    const lng = parsed.lng != null && !isNaN(Number(parsed.lng)) ? Number(parsed.lng) : null;
    if (lat != null && (Math.abs(lat) > 90 || isNaN(lat))) return null;
    if (lng != null && (Math.abs(lng) > 180 || isNaN(lng))) return null;
    return {
      lat,
      lng,
      description: typeof parsed.description === "string" ? parsed.description : null,
      caution: typeof parsed.caution === "string" ? parsed.caution : null,
      country: typeof parsed.country === "string" ? parsed.country : oldData.country || "Unknown",
    };
  } catch {
    return null;
  }
}

export interface Phase3AgentOptions {
  /** Fonction pour récupérer le wikitext d'une page (injectée depuis server). sourceUrl utilisé pour lookup CDX. */
  fetchPageContent: (pageTitle: string, sourceUrl: string) => Promise<string | null>;
  /** Nombre max de pages à tenter de mettre à jour (fetch Wayback). */
  maxUpdate?: number;
  /** Inclure l'enrichissement (pays + coords Claude) pour entrées sans coords. */
  includeEnrichment?: boolean;
  /** Nombre max d'enrichissements coords. */
  maxEnrichment?: number;
  /** Ignorer last_update_attempt_at (forcer retry). */
  forceRetry?: boolean;
}

export interface Phase3AgentResult {
  updateAttempted: number;
  updateSuccess: number;
  updateFailed: number;
  enrichmentCountry: number;
  enrichmentCoords: number;
  errors: string[];
}

export async function runWaybackPhase3Agent(
  db: Database.Database,
  options: Phase3AgentOptions
): Promise<Phase3AgentResult> {
  const maxUpdate = options.maxUpdate ?? 20;
  const includeEnrichment = options.includeEnrichment ?? true;
  const maxEnrichment = options.maxEnrichment ?? 50;
  const forceRetry = options.forceRetry ?? false;
  const result: Phase3AgentResult = { updateAttempted: 0, updateSuccess: 0, updateFailed: 0, enrichmentCountry: 0, enrichmentCoords: 0, errors: [] };

  try {
    db.exec(`ALTER TABLE nauticals ADD COLUMN last_update_attempt_at TEXT`);
  } catch (_) {}
  try {
    db.exec(`ALTER TABLE nauticals ADD COLUMN live_fetched_at TEXT`);
  } catch (_) {}

  const updateStmt = db.prepare(
    `UPDATE nauticals SET lat=?, lng=?, description=?, caution=?, country=?, last_update_attempt_at=?, live_fetched_at=? WHERE id=?`
  );
  const updateAttemptStmt = db.prepare(`UPDATE nauticals SET last_update_attempt_at=? WHERE id=?`);
  const updateCountryStmt = db.prepare(`UPDATE nauticals SET country=? WHERE id=?`);
  const updateCoordsStmt = db.prepare(`UPDATE nauticals SET lat=?, lng=? WHERE id=?`);

  const now = new Date().toISOString();
  const rows = db
    .prepare(
      `SELECT id, source_id, title, description, caution, lat, lng, country, source_url, modification_frequency, last_update_attempt_at
       FROM nauticals WHERE source = 'cruiserswiki_wayback' AND source_url IS NOT NULL
       ORDER BY CASE modification_frequency WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, id`
    )
    .all() as {
    id: number;
    title: string;
    description: string | null;
    caution: string | null;
    lat: number | null;
    lng: number | null;
    country: string;
    source_url: string;
    modification_frequency: string | null;
    last_update_attempt_at: string | null;
  }[];

  const extractionPack = getMemoizedExtractionPack();

  for (const row of rows) {
    if (result.updateAttempted >= maxUpdate) break;
    const freq = row.modification_frequency || "low";
    const minDays = MIN_DAYS_BY_PRIORITY[freq] ?? 365;
    if (!forceRetry && row.last_update_attempt_at) {
      const last = new Date(row.last_update_attempt_at).getTime();
      if (Date.now() - last < minDays * 24 * 60 * 60 * 1000) continue;
    }

    const pageTitle = pageTitleFromSourceUrl(row.source_url);
    result.updateAttempted++;
    updateAttemptStmt.run(now, row.id);

    const wikitext = await options.fetchPageContent(pageTitle, row.source_url);
    if (!wikitext || wikitext.length < 100) {
      result.updateFailed++;
      continue;
    }

    const coord = parseCoordFromWikitext(wikitext);
    const { description, caution } = parseDescriptionFromWikitextWithPack(wikitext, extractionPack.extraction);
    let merged = { lat: coord?.lat ?? row.lat, lng: coord?.lng ?? row.lng, description, caution, country: row.country || "Unknown" };
    const claudeResult = await claudeMerge(
      { title: row.title, description: row.description, caution: row.caution, lat: row.lat, lng: row.lng, country: row.country || "Unknown" },
      wikitext
    );
    if (claudeResult) {
      merged = {
        lat: claudeResult.lat ?? merged.lat,
        lng: claudeResult.lng ?? merged.lng,
        description: claudeResult.description ?? merged.description,
        caution: claudeResult.caution ?? merged.caution,
        country: claudeResult.country || merged.country,
      };
    }
    if (merged.lat != null && merged.lng != null && (Math.abs(merged.lat) > 90 || Math.abs(merged.lng) > 180)) {
      merged.lat = row.lat;
      merged.lng = row.lng;
    }
    updateStmt.run(merged.lat, merged.lng, merged.description, merged.caution, merged.country, now, now, row.id);
    result.updateSuccess++;
    await new Promise((r) => setTimeout(r, 500));
  }

  if (includeEnrichment) {
    const enrichRows = db
      .prepare(
        `SELECT id, title, description, country, source_url FROM nauticals WHERE source = 'cruiserswiki_wayback' AND (lat IS NULL OR lng IS NULL) LIMIT ?`
      )
      .all(maxEnrichment) as { id: number; title: string; description: string | null; country: string; source_url: string | null }[];

    for (const r of enrichRows) {
      let country = r.country || "Unknown";
      const inferred = inferCountryFromWaybackUrl(r.source_url || "");
      if (inferred && country === "Unknown") {
        updateCountryStmt.run(inferred, r.id);
        result.enrichmentCountry++;
        country = inferred;
      }
      const coord = await suggestCoordsWithClaude(r.title, r.description, country);
      if (coord) {
        updateCoordsStmt.run(coord.lat, coord.lng, r.id);
        result.enrichmentCoords++;
      }
      await new Promise((r) => setTimeout(r, 300));
    }
  }

  return result;
}
