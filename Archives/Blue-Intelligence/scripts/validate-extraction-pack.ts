#!/usr/bin/env npx tsx
/**
 * Valide un pack d'extraction contre un fichier « gold » (URL → include attendu, coords optionnelles).
 * Usage:
 *   npx tsx scripts/validate-extraction-pack.ts --gold data/extraction-gold.example.json [--pack data/nautical-extraction-pack.default.json]
 *
 * La base SQLite doit contenir wayback_best_captures avec les URLs du gold (sinon entrée ignorée avec avertissement).
 *
 * Voir docs/EXTRACTION_PACK_WORKFLOW.md
 */
import Database from "better-sqlite3";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import {
  applyExtractionPack,
  loadExtractionPack,
  type NauticalExtractionPack,
} from "../lib/nautical-extraction-pack.ts";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, "..");

interface GoldEntry {
  url: string;
  include: boolean;
  lat?: number;
  lng?: number;
}

function parseArgs() {
  const argv = process.argv.slice(2);
  let gold = "";
  let packPath: string | null = null;
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--gold" && argv[i + 1]) gold = argv[++i];
    if (argv[i] === "--pack" && argv[i + 1]) packPath = argv[++i];
  }
  return { gold, packPath };
}

function approxEq(a: number | null | undefined, b: number | undefined, eps = 0.02): boolean {
  if (a == null || b == undefined) return true;
  return Math.abs(a - b) <= eps;
}

function main() {
  const { gold, packPath } = parseArgs();
  if (!gold) {
    console.error("Usage: --gold path/to/gold.json [--pack path/to/pack.json]");
    process.exit(1);
  }
  const goldResolved = path.isAbsolute(gold) ? gold : path.join(root, gold);
  if (!fs.existsSync(goldResolved)) {
    console.error("Fichier gold introuvable:", goldResolved);
    process.exit(1);
  }
  const raw = JSON.parse(fs.readFileSync(goldResolved, "utf8")) as { entries: GoldEntry[] };
  const entries = raw.entries;
  if (!Array.isArray(entries)) {
    console.error("gold.json doit contenir { entries: [...] }");
    process.exit(1);
  }

  const packFile = packPath
    ? path.isAbsolute(packPath)
      ? packPath
      : path.join(root, packPath)
    : null;
  const pack: NauticalExtractionPack = packFile ? loadExtractionPack(packFile) : loadExtractionPack();

  const dbPath = path.join(root, "blue_intelligence.db");
  if (!fs.existsSync(dbPath)) {
    console.error("Base introuvable:", dbPath);
    process.exit(1);
  }
  const db = new Database(dbPath, { readonly: true });
  const stmt = db.prepare("SELECT content FROM wayback_best_captures WHERE url = ?");

  let tp = 0,
    fp = 0,
    tn = 0,
    fn = 0;
  let coordOk = 0,
    coordCheck = 0;
  let skipped = 0;

  for (const e of entries) {
    const row = stmt.get(e.url) as { content: string } | undefined;
    if (!row) {
      console.warn("[skip] Pas de wikitext en base pour", e.url);
      skipped++;
      continue;
    }
    const r = applyExtractionPack(row.content, { sourceUrl: e.url }, pack);
    const predIn = r.include;
    if (e.include && predIn) tp++;
    else if (e.include && !predIn) fn++;
    else if (!e.include && predIn) fp++;
    else tn++;

    if (e.include && predIn && (e.lat != null || e.lng != null)) {
      coordCheck++;
      if (approxEq(r.lat, e.lat) && approxEq(r.lng, e.lng)) coordOk++;
    }
  }
  db.close();

  const n = tp + fp + tn + fn;
  const accuracy = n ? (tp + tn) / n : 0;
  console.log(JSON.stringify({ tp, fp, tn, fn, skipped, accuracy, coordOk, coordCheck, packVersion: pack.version }, null, 2));
}

main();
