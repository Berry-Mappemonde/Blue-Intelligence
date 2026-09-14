#!/usr/bin/env npx tsx
/**
 * Exporte un échantillon de wikitext depuis wayback_best_captures (SQLite).
 * Usage:
 *   npx tsx scripts/export-wayback-wikitext-sample.ts [--limit 50] [--seed 42] [--out samples.ndjson]
 *
 * Voir docs/EXTRACTION_PACK_WORKFLOW.md
 */
import Database from "better-sqlite3";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, "..");

function parseArgs() {
  const argv = process.argv.slice(2);
  let limit = 50;
  let seed = Date.now();
  let out = path.join(root, "data", "wayback-wikitext-sample.ndjson");
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--limit" && argv[i + 1]) limit = Math.max(1, parseInt(argv[++i], 10) || 50);
    if (argv[i] === "--seed" && argv[i + 1]) seed = parseInt(argv[++i], 10) || seed;
    if (argv[i] === "--out" && argv[i + 1]) out = argv[++i];
  }
  return { limit, seed, out };
}

/** PRNG déterministe (mulberry32) pour échantillon reproductible avec --seed */
function mulberry32(a: number) {
  return function () {
    let t = (a += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function shuffleInPlace<T>(arr: T[], rand: () => number) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
}

function main() {
  const { limit, seed, out } = parseArgs();
  const dbPath = path.join(root, "blue_intelligence.db");
  if (!fs.existsSync(dbPath)) {
    console.error("Base introuvable:", dbPath);
    process.exit(1);
  }
  const db = new Database(dbPath, { readonly: true });
  try {
    const rows = db
      .prepare(
        "SELECT url, timestamp, wayback_url, length(content) as content_len, content FROM wayback_best_captures"
      )
      .all() as { url: string; timestamp: string; wayback_url: string; content_len: number; content: string }[];
    if (rows.length === 0) {
      console.error("wayback_best_captures est vide.");
      process.exit(1);
    }
    const rand = mulberry32(seed);
    shuffleInPlace(rows, rand);
    const picked = rows.slice(0, Math.min(limit, rows.length));
    const lines = picked.map((r) =>
      JSON.stringify({
        url: r.url,
        timestamp: r.timestamp,
        wayback_url: r.wayback_url,
        content_len: r.content_len,
        content: r.content,
      })
    );
    fs.mkdirSync(path.dirname(out), { recursive: true });
    fs.writeFileSync(out, lines.join("\n") + "\n", "utf8");
    console.log("Exporté", picked.length, "lignes →", out, "| seed=", seed);
  } finally {
    db.close();
  }
}

main();
