/**
 * Phase 2 : Analyse des fréquences de modification (2005–2026)
 * - 2.1 Historique par page : depuis wayback_cdx_raw (url, timestamp, digest)
 * - 2.2 Détection de changements : digest différent entre captures successives
 * - 2.3 Métriques : nombre de modifications, intervalle moyen
 * - 2.4 Score de priorité : haute (souvent modifiée) / basse (stable)
 * - 2.5 Stockage : modification_count, modification_frequency, avg_modification_interval_days
 *
 * Lit uniquement depuis wayback_cdx_raw (remplie par Phase 1). Pas de requêtes CDX.
 * Déclenché via POST /api/nauticals/wayback-phase2
 */

import type Database from "better-sqlite3";

interface CdxCapture {
  url: string;
  timestamp: string;
  digest: string;
}

/** Parse timestamp YYYYMMDDhhmmss en Date. */
function parseTimestamp(ts: string): number {
  return new Date(
    ts.slice(0, 4) + "-" + ts.slice(4, 6) + "-" + ts.slice(6, 8) + "T" + ts.slice(8, 10) + ":" + ts.slice(10, 12) + ":" + ts.slice(12, 14) + "Z"
  ).getTime();
}

/** Seuil minimal (jours) pour compter un changement de digest. Changements plus rapprochés = ignorés. */
const MIN_CHANGE_INTERVAL_DAYS = parseInt(process.env.WAYBACK_MIN_CHANGE_INTERVAL_DAYS || "7", 10);

/** Calcule les métriques par URL : nb modifications, intervalle moyen (jours). Ne compte que les changements séparés d'au moins MIN_CHANGE_INTERVAL_DAYS. */
function computeModificationMetrics(captures: CdxCapture[]): Map<string, { count: number; avgIntervalDays: number }> {
  const byUrl = new Map<string, CdxCapture[]>();
  for (const c of captures) {
    const list = byUrl.get(c.url) || [];
    list.push(c);
    byUrl.set(c.url, list);
  }

  const result = new Map<string, { count: number; avgIntervalDays: number }>();
  for (const [url, list] of byUrl) {
    list.sort((a, b) => a.timestamp.localeCompare(b.timestamp));
    let count = 0;
    const intervals: number[] = [];
    for (let i = 1; i < list.length; i++) {
      if (list[i].digest !== list[i - 1].digest) {
        const diff = (parseTimestamp(list[i].timestamp) - parseTimestamp(list[i - 1].timestamp)) / (1000 * 60 * 60 * 24);
        if (diff >= MIN_CHANGE_INTERVAL_DAYS) {
          count++;
          intervals.push(diff);
        }
      }
    }
    const avgIntervalDays = intervals.length > 0 ? intervals.reduce((a, b) => a + b, 0) / intervals.length : 0;
    result.set(url, { count, avgIntervalDays });
  }
  return result;
}

/** Score de priorité : haute (souvent modifiée) / moyenne / basse (stable). */
function computePriorityScore(count: number, avgIntervalDays: number): "high" | "medium" | "low" {
  if (count >= 5 && avgIntervalDays <= 365) return "high";
  if (count >= 2 || (count >= 1 && avgIntervalDays <= 730)) return "medium";
  return "low";
}

export interface Phase2Result {
  capturesTotal: number;
  urlsProcessed: number;
  highPriority: number;
  mediumPriority: number;
  lowPriority: number;
  errors: string[];
}

/** Phase 2 : analyse des fréquences de modification et mise à jour des entrées. Lit depuis wayback_cdx_raw. */
export async function runWaybackPhase2(db: Database.Database): Promise<Phase2Result> {
  const result: Phase2Result = { capturesTotal: 0, urlsProcessed: 0, highPriority: 0, mediumPriority: 0, lowPriority: 0, errors: [] };

  const updateStmt = db.prepare(
    "UPDATE nauticals SET modification_count = ?, modification_frequency = ?, avg_modification_interval_days = ? WHERE id = ?"
  );

  const rows = db
    .prepare(
      `SELECT id, source_id, source_url FROM nauticals WHERE source = 'cruiserswiki_wayback' AND source_url IS NOT NULL`
    )
    .all() as { id: number; source_id: string; source_url: string }[];

  /** Normalise l'URL pour matcher CDX (enlève trailing slash, www, http→https, lowercase). */
  function normUrl(u: string): string {
    let s = (u.startsWith("http") ? u : `https://${u}`).replace(/\/$/, "").toLowerCase();
    s = s.replace(/^https?:\/\/(www\.)?/, "https://");
    return s;
  }

  const urlToRow = new Map<string, { id: number }>();
  for (const r of rows) {
    const n = normUrl(r.source_url);
    urlToRow.set(n, { id: r.id });
  }

  const rawRows = db
    .prepare("SELECT url, timestamp, digest FROM wayback_cdx_raw ORDER BY url, timestamp")
    .all() as { url: string; timestamp: string; digest: string | null }[];

  if (rawRows.length === 0) {
    result.errors.push("wayback_cdx_raw is empty. Run sync with refreshCdx: true first.");
    const fallbackStmt = db.prepare(
      "UPDATE nauticals SET modification_count = 0, modification_frequency = 'low', avg_modification_interval_days = 0 WHERE source = 'cruiserswiki_wayback' AND id = ?"
    );
    for (const r of rows) fallbackStmt.run(r.id);
    result.urlsProcessed = rows.length;
    result.lowPriority = rows.length;
    return result;
  }

  const captures: CdxCapture[] = rawRows.map((r) => ({
    url: r.url,
    timestamp: r.timestamp,
    digest: r.digest ?? "",
  }));

  result.capturesTotal = captures.length;

  const metrics = computeModificationMetrics(captures);

  for (const [cdxUrl, { count, avgIntervalDays }] of metrics) {
    const key = normUrl(cdxUrl);
    const row = urlToRow.get(key);
    if (!row) continue;

    const freq = computePriorityScore(count, avgIntervalDays);
    updateStmt.run(count, freq, Math.round(avgIntervalDays * 10) / 10, row.id);

    result.urlsProcessed++;
    if (freq === "high") result.highPriority++;
    else if (freq === "medium") result.mediumPriority++;
    else result.lowPriority++;
  }

  return result;
}
