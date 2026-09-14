import { createRequire } from "module";

// Polyfill Node 20's removed util.isNullOrUndefined before any other module loads.
// Some TensorFlow-related dependencies still call util.isNullOrUndefined.
const require = createRequire(import.meta.url);
const util = require("util");
if (typeof (util as any).isNullOrUndefined !== "function") {
  (util as any).isNullOrUndefined = (v: any) => v === null || v === undefined;
}

import crypto from "crypto";
import express from "express";
import { createServer as createViteServer } from "vite";
import Database from "better-sqlite3";
import dotenv from "dotenv";
import path from "path";
import { fileURLToPath } from "url";
import fs from "fs";
import { JSDOM } from "jsdom";
import { Readability } from "@mozilla/readability";
import TurndownService from "turndown";
import Anthropic from "@anthropic-ai/sdk";
import { isInland as isInlandGSHHG, distanceToCoastKm } from "./lib/gshhg-landmask";
import { initializeDomainScoring, getDomainScoringEngine } from "./lib/domainScoring";
import { embedTexts, cosineSimilarity, serializeEmbedding, parseEmbedding } from "./lib/semanticDedup";
import { runWaybackPhase2, type Phase2Result } from "./lib/wayback-phase2";
import { enrichWaybackPhase3 } from "./lib/wayback-phase3";
import { runWaybackPhase3Agent } from "./lib/wayback-phase3-agent";
import {
  cruisersWikiFetch as libCruisersWikiFetch,
  isCruisersWikiValidJson,
  getCruisersWikiProxyBase,
} from "./lib/cruiserswiki-fetch";
import {
  getMemoizedExtractionPack,
  applyExtractionPack,
  parseCoordFromWikitext,
} from "./lib/nautical-extraction-pack";


process.on('uncaughtException', (err) => {
  console.error('Uncaught Exception:', err);
});
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const DATA_DIR = path.join(__dirname, "data");

// Load .env from project root (explicit path so it works regardless of cwd)
const envPath = path.join(__dirname, ".env");
const envLocalPath = path.join(__dirname, ".env.local");
const result = dotenv.config({ path: envPath, quiet: true });
dotenv.config({ path: envLocalPath, override: true, quiet: true });

// Fix BOM: if env key has BOM prefix (e.g. from Windows/editor), copy to correct key
if (result.parsed) {
  for (const key of Object.keys(result.parsed)) {
    const cleanKey = key.replace(/^\uFEFF/, "");
    if (cleanKey !== key) {
      process.env[cleanKey] = result.parsed![key];
    }
  }
}

const db = new Database("blue_intelligence.db");

// Initialize database
db.exec(`
  CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    url TEXT UNIQUE,
    description TEXT,
    funder TEXT,
    lat REAL,
    lng REAL,
    relevance_score REAL,
    category TEXT,
    status TEXT,
    image_url TEXT,
    start_date TEXT,
    end_date TEXT,
    title_embedding TEXT,
    description_embedding TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )
`);

try {
  db.exec(`ALTER TABLE projects ADD COLUMN image_url TEXT`);
} catch (e) {
  // Column might already exist, ignore error
}

try {
  db.exec(`ALTER TABLE projects ADD COLUMN start_date TEXT`);
  db.exec(`ALTER TABLE projects ADD COLUMN end_date TEXT`);
} catch (e) {
  // Columns might already exist, ignore error
}

// Migration: Allow null URLs
try {
  const info = db.prepare("PRAGMA table_info(projects)").all();
  const urlCol = info.find((c: any) => c.name === 'url');
  if (urlCol && urlCol.notnull === 1) {
    console.log("[Migration] Making url column nullable...");
    db.transaction(() => {
      db.exec(`
        CREATE TABLE projects_new (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          title TEXT NOT NULL,
          url TEXT UNIQUE,
          description TEXT,
          funder TEXT,
          lat REAL,
          lng REAL,
          relevance_score REAL,
          category TEXT,
          status TEXT,
          image_url TEXT,
          start_date TEXT,
          end_date TEXT,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO projects_new (id, title, url, description, funder, lat, lng, relevance_score, category, status, image_url, start_date, end_date, created_at)
        SELECT id, title, url, description, funder, lat, lng, relevance_score, category, status, image_url, start_date, end_date, created_at FROM projects;
        DROP TABLE projects;
        ALTER TABLE projects_new RENAME TO projects;
      `);
    })();
  }
} catch (e) {
  console.error("[Migration] Failed to migrate projects table:", e);
}

db.exec(`
  CREATE TABLE IF NOT EXISTS telemetry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    engine TEXT NOT NULL,
    target_url TEXT NOT NULL,
    status TEXT NOT NULL,
    projects_found INTEGER DEFAULT 0,
    duration_ms INTEGER NOT NULL,
    error_message TEXT,
    raw_response TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )
`);

try {
  db.exec(`ALTER TABLE telemetry ADD COLUMN raw_response TEXT`);
} catch (e) { }

try {
  db.exec(`ALTER TABLE projects ADD COLUMN s_ocean_score REAL`);
} catch (e) { }

try {
  db.exec(`ALTER TABLE projects ADD COLUMN title_embedding TEXT`);
} catch (e) { }

try {
  db.exec(`ALTER TABLE projects ADD COLUMN description_embedding TEXT`);
} catch (e) { }

db.exec(`
  CREATE TABLE IF NOT EXISTS failed_extractions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_url TEXT NOT NULL,
    project_url TEXT UNIQUE NOT NULL,
    error_message TEXT,
    error_type TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )
`);

db.exec(`
  CREATE TABLE IF NOT EXISTS nauticals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    source_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    caution TEXT,
    lat REAL NOT NULL,
    lng REAL NOT NULL,
    zone_ref TEXT,
    country TEXT,
    objtype TEXT,
    source_url TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )
`);
try {
  db.exec(`ALTER TABLE nauticals ADD COLUMN image_url TEXT`);
} catch (_) {}
try {
  db.exec(`ALTER TABLE nauticals ADD COLUMN wayback_timestamp TEXT`);
} catch (_) {}
try {
  db.exec(`ALTER TABLE nauticals ADD COLUMN wayback_url TEXT`);
} catch (_) {}
try {
  db.exec(`ALTER TABLE nauticals ADD COLUMN modification_count INTEGER`);
} catch (_) {}
try {
  db.exec(`ALTER TABLE nauticals ADD COLUMN modification_frequency TEXT`);
} catch (_) {}
try {
  db.exec(`ALTER TABLE nauticals ADD COLUMN avg_modification_interval_days REAL`);
} catch (_) {}
try {
  db.exec(`ALTER TABLE nauticals ADD COLUMN last_update_attempt_at TEXT`);
} catch (_) {}
try {
  db.exec(`ALTER TABLE nauticals ADD COLUMN live_fetched_at TEXT`);
} catch (_) {}
try {
  db.exec(`ALTER TABLE failed_extractions ADD COLUMN error_type TEXT`);
} catch (_) {}

db.exec(`
  CREATE TABLE IF NOT EXISTS wayback_cdx_cache (
    url TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    cached_at TEXT NOT NULL
  )
`);
db.exec(`
  CREATE TABLE IF NOT EXISTS wayback_cdx_raw (
    url TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    digest TEXT,
    cached_at TEXT NOT NULL,
    PRIMARY KEY (url, timestamp)
  )
`);
try {
  db.exec(`ALTER TABLE wayback_cdx_raw ADD COLUMN digest TEXT`);
} catch (_) {}

db.exec(`
  CREATE TABLE IF NOT EXISTS wayback_best_captures (
    url TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    wayback_url TEXT NOT NULL,
    content_type TEXT NOT NULL,
    content TEXT NOT NULL,
    fetched_at TEXT NOT NULL
  )
`);

// Migration: rendre lat/lng nullables pour cruiserswiki_wayback (pages sans coordonnées)
try {
  const info = db.prepare("PRAGMA table_info(nauticals)").all() as { name: string; notnull: number }[];
  const latCol = info.find((c) => c.name === "lat");
  if (latCol && latCol.notnull === 1) {
    console.log("[Migration] Making nauticals lat/lng nullable for Wayback...");
    db.transaction(() => {
      db.exec(`
        CREATE TABLE nauticals_new (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          source TEXT NOT NULL,
          source_id TEXT UNIQUE NOT NULL,
          title TEXT NOT NULL,
          description TEXT,
          caution TEXT,
          lat REAL,
          lng REAL,
          zone_ref TEXT,
          country TEXT,
          objtype TEXT,
          source_url TEXT,
          image_url TEXT,
          wayback_timestamp TEXT,
          wayback_url TEXT,
          modification_count INTEGER,
          modification_frequency TEXT,
          avg_modification_interval_days REAL,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO nauticals_new (id, source, source_id, title, description, caution, lat, lng, zone_ref, country, objtype, source_url, image_url, wayback_timestamp, wayback_url, modification_count, modification_frequency, avg_modification_interval_days, created_at)
        SELECT id, source, source_id, title, description, caution, lat, lng, zone_ref, country, objtype, source_url, image_url, wayback_timestamp, wayback_url, modification_count, modification_frequency, avg_modification_interval_days, created_at FROM nauticals;
        DROP TABLE nauticals;
        ALTER TABLE nauticals_new RENAME TO nauticals;
      `);
    })();
  }
} catch (e) {
  console.error("[Migration] Failed to migrate nauticals table:", e);
}

function inferErrorType(errorMessage: string | null | undefined): string {
  if (!errorMessage) return "unknown";
  const m = errorMessage.toLowerCase();
  if (m.includes("http 404") || m.includes("404")) return "404";
  if (m.includes("content too short") || m.includes("empty") || m.includes("no content") || m.includes("no results")) return "empty_page";
  if (m.includes("marine") || m.includes("gatekeeper") || m.includes("relevance")) return "gatekeeper";
  if (m.includes("parse") || m.includes("json") || m.includes("failed to parse")) return "parse_error";
  if (m.includes("fetch") || m.includes("network") || m.includes("econnrefused") || m.includes("timeout")) return "network";
  return "unknown";
}

// --- ETL: Structural Memory (MasterSeeds + DeepLinkCache) ---
function ensureDataDir() {
  if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
}

function loadMasterSeeds(): { name: string; url: string }[] {
  ensureDataDir();
  const p = path.join(DATA_DIR, "MasterSeeds.json");
  if (!fs.existsSync(p)) return [];
  try {
    const data = JSON.parse(fs.readFileSync(p, "utf-8"));
    return Array.isArray(data) ? data : [];
  } catch {
    return [];
  }
}

function loadDeepLinkCache(filename: string): { urls: string[] } {
  ensureDataDir();
  const p = path.join(DATA_DIR, filename);
  if (!fs.existsSync(p)) return { urls: [] };
  try {
    const data = JSON.parse(fs.readFileSync(p, "utf-8"));
    return { urls: Array.isArray(data?.urls) ? data.urls : [] };
  } catch {
    return { urls: [] };
  }
}

function saveDeepLinkCache(filename: string, urls: string[]) {
  ensureDataDir();
  const p = path.join(DATA_DIR, filename);
  const existing = loadDeepLinkCache(filename);
  const merged = [...new Set([...existing.urls, ...urls])];
  fs.writeFileSync(p, JSON.stringify({ urls: merged, updated_at: new Date().toISOString() }, null, 2));
}

function appendToDeepLinkCache(filename: string, newUrls: string[]) {
  const existing = loadDeepLinkCache(filename);
  saveDeepLinkCache(filename, [...existing.urls, ...newUrls]);
}

/** Vide les fichiers DeepLinkCache (listes + pages) sous `data/`. Ne modifie pas MasterSeeds.json. */
function clearDeepLinkCacheFiles(): void {
  ensureDataDir();
  const stamp = new Date().toISOString();
  for (const name of ["DeepLinkCacheProjectsLists.json", "DeepLinkCacheProjectsPages.json"]) {
    const p = path.join(DATA_DIR, name);
    fs.writeFileSync(p, JSON.stringify({ urls: [], updated_at: stamp }, null, 2));
  }
}

const GOAL_PROMPT = `
### Objective
L'agent doit uniquement naviguer, gérer la pagination (cliquer sur "Suivant" ou "Charger plus") et identifier les liens vers les fiches individuelles.

### Instructions
1. Navigate to the project directory or listing page.
2. If there is pagination (e.g., "Next", "Page 2", numbers), you MUST visit every page.
3. If there is a "Load More" button or infinite scroll, you MUST trigger it repeatedly until ALL projects are visible. Keep clicking until the button disappears.
4. Identify the links to the individual project detail pages.
5. DO NOT extract detailed data (no descriptions, no coordinates). ONLY extract the URLs.
6. If the page shows "no content", "404", "not found", or empty results: try the parent page or main listing (e.g. /grants/ instead of /grants/slug-123/).
7. Prefer filtered views that return content (e.g. category "ocean" or "marine") over unfiltered pages with mixed content.

### Output Format
Return ONLY a clean JSON array of strings representing the absolute URLs of the projects.
Example: ["https://example.com/project1", "https://example.com/project2"]
`;

const EXTRACT_PROMPT = `
### Objective
L'agent doit lire la page du projet et extraire les informations détaillées. Base de données UNIQUEMENT pour projets MARINS/OCÉAN (conservation marine, océans, mers, côtes, espèces marines, récifs coralliens).

### Instructions
1. Read the project details on the page.
2. Extract: title, description, funder, latitude, longitude, category, status, image_url, start_date, end_date.
3. marine_relevance (0-1): 1=clairement marin/océan, 0=pas marin. Si projet terrestre/freshwater/général sans lien océan → 0.
4. location_type: "coastal" si près de la mer, "inland" si en terres (loin des côtes), "unknown" si incertain.
5. Si coordonnées suggèrent un lieu INLAND, être TRÈS strict: marine_relevance >= 0.9 uniquement si lien océan explicite.

### Output Format
Return ONLY a valid JSON object:
{
  "title": "string",
  "url": "string",
  "description": "string",
  "funder": "string",
  "lat": number,
  "lng": number,
  "category": "string",
  "status": "string",
  "image_url": "string",
  "start_date": "string",
  "end_date": "string",
  "marine_relevance": number,
  "location_type": "coastal" | "inland" | "unknown"
}
`;

type GatekeeperConfig = { marine_threshold?: number; inland_threshold?: number; coast_distance_km?: number };
type ExtractionConfig = { concurrency?: number; claudeGatekeeperModel?: string; claudeExtractModel?: string; claudeScoringModel?: string };
type AgentConfig = { maxConcurrentAgents?: number };
type TaskConfig = { gatekeeper?: GatekeeperConfig; extraction?: ExtractionConfig; agent?: AgentConfig };
const agentQueue: { url: string; proxy?: string; mode?: "discover" | "extract"; useTinyFish?: boolean; config?: TaskConfig }[] = [];
let activeAgents = 0;
let maxConcurrentAgents = 2; // Surchargé par config.agent.maxConcurrentAgents au deploy

// Store active runs for SSE proxying and cancellation
let agentCounter = 0;
let extractCounter = 0;
const activeRuns = new Map<string, { streamingUrl: string, logs: any[], aborted?: boolean, status?: string, targetUrl?: string, mode?: string, agentLabel?: string }>();
const activeExtractRuns = new Map<string, { targetUrl: string; status: string; agentLabel: string }>();
let hybridExtractCounter = 0;
const activeHybridExtractions = new Map<string, { targetUrl: string; agentLabel: string; totalUrls: number }>();

// When true, GET /api/agent/active-runs returns [] until next deploy (prevents stale poll data)
// Start stopped so hard reload / server restart shows clean state (no ghost agents)
let swarmStopped = true;

// Mesure du temps de processus (deploy → dernière tâche terminée)
let deployStartTime: number | null = null;

// Extraction hybride en arrière-plan (ne bloque pas le slot TinyFish)
let extractingCount = 0;

// --- File d'extraction globale : un pool de workers partagé par toutes les découvertes TinyFish ---
interface QueuedExtraction {
  projectUrl: string;
  targetUrl: string;
  taskConfig?: TaskConfig;
}
const globalExtractQueue: QueuedExtraction[] = [];
let globalExtractConcurrency = 2;
const pendingByTarget = new Map<string, { total: number; success: number; processed: number; startTime: number; rawResponse?: string | null }>();
let globalExtractWorkersStarted = false;

function startGlobalExtractWorkers() {
  if (swarmStopped) return;
  if (globalExtractWorkersStarted) return;
  globalExtractWorkersStarted = true;
  const workerCount = globalExtractConcurrency;
  for (let w = 0; w < workerCount; w++) {
    (async () => {
      while (!swarmStopped) {
        const item = globalExtractQueue.shift();
        if (!item) {
          await new Promise((r) => setTimeout(r, 200));
          continue;
        }
        const { projectUrl, targetUrl, taskConfig } = item;
        try {
          const host = (() => { try { return new URL(projectUrl).hostname; } catch { return projectUrl.slice(0, 30); } })();
          broadcastLog({ key: "etl_fetch", host });
          const { markdown, method, imageUrls } = await fetchMarkdown(projectUrl);
          if (swarmStopped) { globalExtractQueue.unshift(item); break; }
          const projectData = await extractProjectData(markdown, projectUrl, taskConfig?.extraction, imageUrls);
          const gatekeeper = passesMarineGatekeeper(projectData, taskConfig?.gatekeeper);
          let saved = 0;
          if (!gatekeeper.pass) {
            console.log(`[Gatekeeper] REJECTED ${projectUrl}: ${gatekeeper.reason}`);
            if (!swarmStopped) {
              try {
                const errType = "gatekeeper";
                db.prepare(`
                  INSERT INTO failed_extractions (target_url, project_url, error_message, error_type)
                  VALUES (?, ?, ?, ?)
                  ON CONFLICT(project_url) DO UPDATE SET
                    error_message = excluded.error_message,
                    error_type = excluded.error_type,
                    created_at = CURRENT_TIMESTAMP
                `).run(targetUrl, projectUrl, gatekeeper.reason!, errType);
              } catch (dbErr) { }
            }
          } else if (!swarmStopped) {
            const relevanceScore = typeof projectData.marine_relevance === "number" ? projectData.marine_relevance : 0.95;
            broadcastLog({ key: "etl_claude_extract", title: (projectData.title || "?").slice(0, 40) });
            const upsertResult = await upsertProject({
              title: projectData.title || "Unknown",
              url: projectData.url || projectUrl,
              description: projectData.description || "",
              funder: projectData.funder || "Unknown",
              lat: projectData.lat || 0,
              lng: projectData.lng || 0,
              category: projectData.category || "Marine Conservation",
              status: projectData.status || "Active",
              image_url: projectData.image_url || "",
              start_date: projectData.start_date || null,
              end_date: projectData.end_date || null,
              relevance_score: relevanceScore,
              s_ocean_score: projectData.s_ocean_score ?? 0.75,
            });
            try {
              db.prepare(`DELETE FROM failed_extractions WHERE project_url = ?`).run(projectUrl);
            } catch (e) { }
            if (upsertResult !== "skipped") {
              broadcastLog({ key: "etl_saved", title: (projectData.title || "?").slice(0, 35) });
              saved = 1;
            }
          }
          const pending = pendingByTarget.get(targetUrl);
          if (pending) {
            pending.processed++;
            pending.success += saved;
          }
        } catch (err: any) {
          console.error(`[Extraction] Error processing ${projectUrl}:`, err.message);
          if (!swarmStopped) {
            try {
              const errType = inferErrorType(err.message);
              db.prepare(`
                INSERT INTO failed_extractions (target_url, project_url, error_message, error_type)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(project_url) DO UPDATE SET
                  error_message = excluded.error_message,
                  error_type = excluded.error_type,
                  created_at = CURRENT_TIMESTAMP
              `).run(targetUrl, projectUrl, err.message, errType);
            } catch (dbErr) { }
          }
          const pending = pendingByTarget.get(targetUrl);
          if (pending) pending.processed++;
        }
        extractingCount--;
        const pending = pendingByTarget.get(targetUrl);
        if (pending && pending.processed === pending.total) {
          const duration = Math.round(performance.now() - pending.startTime);
          recordTelemetry("tinyfish", targetUrl, "SUCCESS", pending.success, duration, null, pending.rawResponse ?? null);
          broadcastLog({ key: pending.success === 1 ? "etl_extract_one" : "etl_extract_many", n: pending.success });
          pendingByTarget.delete(targetUrl);
        }
        checkSwarmComplete();
      }
    })();
  }
}

function checkSwarmComplete() {
  if (deployStartTime && activeAgents === 0 && agentQueue.length === 0 && extractingCount === 0) {
    const elapsedSec = ((Date.now() - deployStartTime) / 1000).toFixed(1);
    broadcastLog({ key: "etl_swarm_done", sec: elapsedSec });
    console.log(`[Swarm] Process completed in ${elapsedSec}s`);
    deployStartTime = null;
  }
}

/** Extract-only: Readability + Claude pipeline (no TinyFish). Used for Pages cache URLs. */
async function runExtractOnly(projectUrl: string, taskConfig?: TaskConfig): Promise<number> {
  if (swarmStopped) return 0;
  extractCounter++;
  const extractId = `extract-${extractCounter}`;
  const label = `Readability.js ${extractCounter}`;
  activeExtractRuns.set(extractId, { targetUrl: projectUrl, status: "RUNNING", agentLabel: label });
  try {
    const host = (() => { try { return new URL(projectUrl).hostname; } catch { return projectUrl.slice(0, 30); } })();
    broadcastLog({ key: "etl_fetch", host });
    const { markdown, method, imageUrls } = await fetchMarkdown(projectUrl);
    const projectData = await extractProjectData(markdown, projectUrl, taskConfig?.extraction, imageUrls);
    if (swarmStopped) return 0;
    const gatekeeper = passesMarineGatekeeper(projectData, taskConfig?.gatekeeper);
    if (!gatekeeper.pass) {
      broadcastLog({ key: "etl_gatekeeper_rejected", host });
      console.log(`[Gatekeeper] REJECTED ${projectUrl}: ${gatekeeper.reason}`);
      return 0;
    }
    const relevanceScore = typeof projectData.marine_relevance === "number" ? projectData.marine_relevance : 0.95;
    broadcastLog({ key: "etl_claude_extract", title: (projectData.title || "?").slice(0, 40) });
    const upsertResult = await upsertProject({
      title: projectData.title || "Unknown",
      url: projectData.url || projectUrl,
      description: projectData.description || "",
      funder: projectData.funder || "Unknown",
      lat: projectData.lat || 0,
      lng: projectData.lng || 0,
      category: projectData.category || "Marine Conservation",
      status: projectData.status || "Active",
      image_url: projectData.image_url || "",
      start_date: projectData.start_date || null,
      end_date: projectData.end_date || null,
      relevance_score: relevanceScore,
      s_ocean_score: projectData.s_ocean_score ?? 0.75,
    });
    if (upsertResult !== "skipped") {
      broadcastLog({ key: "etl_saved", title: (projectData.title || "?").slice(0, 35) });
    }
    return upsertResult !== "skipped" ? 1 : 0;
  } catch (err: any) {
    console.error(`[Extract] Error for ${projectUrl}:`, err.message);
    throw err;
  } finally {
    activeExtractRuns.delete(extractId);
  }
}

function processQueue() {
  while (!swarmStopped && agentQueue.length > 0) {
    const task = agentQueue[0];
    const mode = task.mode || "discover";
    const useTinyFish = task.useTinyFish === true;
    const atAgentLimit = activeAgents >= maxConcurrentAgents;
    const atTinyFishLimit = (mode === "discover" || useTinyFish) && activeRuns.size >= maxConcurrentAgents;
    if (atAgentLimit || atTinyFishLimit) break;
    activeAgents++;
    agentQueue.shift();
    const shortUrl = task.url.length > 45 ? task.url.slice(0, 42) + "…" : task.url;
    if (mode === "extract") {
      broadcastLog({ key: "etl_extract_only", url: shortUrl });
    }
    (async () => {
      try {
        if (mode === "extract" && useTinyFish) {
          await runTinyFishAgent(task.url, task.proxy, 0, "extract", task.config);
        } else if (mode === "extract") {
          await runExtractOnly(task.url, task.config);
        } else {
          await runTinyFishAgent(task.url, task.proxy, 0, "discover", task.config);
        }
      } catch (error) {
        console.error(`Agent failed for ${task.url}:`, error);
      } finally {
        activeAgents--;
        processQueue();
        checkSwarmComplete();
      }
    })();
  }
}

// --- Dédoublonnage (Follow the Money: 500m, near-identical description) ---
const DEDUP_TITLE_SIMILARITY = 0.85;
const DEDUP_DESC_SIMILARITY = 0.85;
const DEDUP_COORD_KM = 0.5; // 500m per target pipeline

function normalizeText(s: string): string {
  return (s || "").toLowerCase().trim().replace(/\s+/g, " ");
}

function textSimilarity(a: string, b: string, maxLen?: number): number {
  // Fallback similarity: token-based Jaccard. Used when embeddings are not available.
  const na = normalizeText(a);
  const nb = normalizeText(b);
  if (!na || !nb) return na === nb ? 1 : 0;
  let sa = na,
    sb = nb;
  if (maxLen) {
    sa = sa.slice(0, maxLen);
    sb = sb.slice(0, maxLen);
  }
  if (sa === sb) return 1;
  const wa = new Set(sa.split(/\s+/).filter(Boolean));
  const wb = new Set(sb.split(/\s+/).filter(Boolean));
  const inter = [...wa].filter((w) => wb.has(w)).length;
  const union = wa.size + wb.size - inter;
  return union > 0 ? inter / union : 0;
}

async function computeEmbeddingsForProject(project: {
  title: string;
  description?: string;
}): Promise<{ titleEmbedding: number[]; descriptionEmbedding: number[] | null }> {
  try {
    await new Promise<void>((r) => setImmediate(r));
    const title = normalizeText(project.title);
    const description = project.description ? normalizeText(project.description) : "";
    const texts = [title];
    if (description) texts.push(description);
    const embeddings = await embedTexts(texts);
    return {
      titleEmbedding: embeddings[0] ?? [],
      descriptionEmbedding: description ? embeddings[1] ?? null : null,
    };
  } catch (err: any) {
    console.warn("[Embeddings] TensorFlow unavailable, using fallback dedup:", err?.message || err);
    return { titleEmbedding: [], descriptionEmbedding: null };
  }
}

const updateEmbeddingsStmt = db.prepare(`
  UPDATE projects SET title_embedding = ?, description_embedding = ? WHERE id = ?
`);

async function findDuplicateProject(project: {
  title: string;
  description: string;
  lat: number;
  lng: number;
  title_embedding?: number[];
  description_embedding?: number[] | null;
}): Promise<{ id: number; url: string } | null> {
  const { title, description, lat, lng } = project;
  const { titleEmbedding, descriptionEmbedding } =
    project.title_embedding && project.description_embedding !== undefined
      ? {
        titleEmbedding: project.title_embedding,
        descriptionEmbedding: project.description_embedding ?? null,
      }
      : await computeEmbeddingsForProject({ title, description });

  const delta = 0.02; // ~2km bounding box
  const rows = selectCandidatesByCoords.all(
    lat - delta,
    lat + delta,
    lng - delta,
    lng + delta
  ) as { id: number; title: string; url: string; description: string; lat: number; lng: number; title_embedding?: string; description_embedding?: string }[];

  for (const row of rows) {
    const dist = haversineDistanceKm(lat, lng, row.lat, row.lng);
    if (dist > DEDUP_COORD_KM) continue;

    let candidateTitleEmb = parseEmbedding(row.title_embedding);
    let candidateDescEmb = parseEmbedding(row.description_embedding);

    // If the row lacks embeddings, compute and persist them for future runs.
    if (!candidateTitleEmb || (row.description && !candidateDescEmb)) {
      const { titleEmbedding: computedTitleEmb, descriptionEmbedding: computedDescEmb } =
        await computeEmbeddingsForProject({ title: row.title, description: row.description || "" });
      candidateTitleEmb = candidateTitleEmb || computedTitleEmb;
      candidateDescEmb = candidateDescEmb || computedDescEmb;
      try {
        updateEmbeddingsStmt.run(serializeEmbedding(candidateTitleEmb), serializeEmbedding(candidateDescEmb), row.id);
      } catch (e) {
        // ignore write failures
      }
    }

    const titleSim = cosineSimilarity(titleEmbedding, candidateTitleEmb);
    const hasDescriptionComparison = descriptionEmbedding && candidateDescEmb;
    const descSim = hasDescriptionComparison ? cosineSimilarity(descriptionEmbedding, candidateDescEmb) : 1;

    if (titleSim >= DEDUP_TITLE_SIMILARITY && descSim >= DEDUP_DESC_SIMILARITY) {
      return { id: row.id, url: row.url };
    }

    // Fallback to token-level similarity when embeddings are unavailable
    if ((!titleEmbedding.length || !candidateTitleEmb?.length) && (titleSim >= DEDUP_TITLE_SIMILARITY)) {
      const fallbackTitleSim = textSimilarity(title, row.title);
      const fallbackDescSim = textSimilarity(description, row.description || "", 200);
      if (fallbackTitleSim >= DEDUP_TITLE_SIMILARITY && fallbackDescSim >= DEDUP_DESC_SIMILARITY) {
        return { id: row.id, url: row.url };
      }
    }
  }

  return null;
}

function haversineDistanceKm(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLng = ((lng2 - lng1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

const selectCandidatesByCoords = db.prepare(`
  SELECT id, title, url, description, lat, lng, title_embedding, description_embedding FROM projects
  WHERE lat BETWEEN ? AND ? AND lng BETWEEN ? AND ?
`);

const updateProjectByIdStmt = db.prepare(`
  UPDATE projects SET
    title = ?, description = ?, funder = ?, lat = ?, lng = ?,
    category = ?, status = ?, image_url = ?, start_date = ?, end_date = ?,
    relevance_score = ?, s_ocean_score = ?,
    title_embedding = ?, description_embedding = ?
  WHERE id = ?
`);

const insertProjectStmt = db.prepare(`
  INSERT INTO projects (title, url, description, funder, lat, lng, category, status, relevance_score, image_url, start_date, end_date, s_ocean_score, title_embedding, description_embedding)
  VALUES (@title, @url, @description, @funder, @lat, @lng, @category, @status, @relevance_score, @image_url, @start_date, @end_date, @s_ocean_score, @title_embedding, @description_embedding)
  ON CONFLICT(url) DO UPDATE SET
    title = excluded.title,
    description = excluded.description,
    funder = excluded.funder,
    lat = excluded.lat,
    lng = excluded.lng,
    category = excluded.category,
    status = excluded.status,
    image_url = excluded.image_url,
    start_date = excluded.start_date,
    end_date = excluded.end_date,
    relevance_score = excluded.relevance_score,
    s_ocean_score = excluded.s_ocean_score,
    title_embedding = excluded.title_embedding,
    description_embedding = excluded.description_embedding
`);

type ProjectRow = {
  title: string;
  url?: string;
  description?: string;
  funder?: string | string[];
  lat: number;
  lng: number;
  category?: string;
  status?: string;
  image_url?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  relevance_score?: number;
  s_ocean_score?: number;
  title_embedding?: number[];
  description_embedding?: number[] | null;
};

function chooseBestValue(existing: any, incoming: any): any {
  if (incoming === undefined || incoming === null || incoming === "") return existing;
  if (existing === undefined || existing === null || existing === "") return incoming;
  if (typeof existing === "string" && typeof incoming === "string") {
    // Prefer longer text (more complete) when there is a difference
    return incoming.length > existing.length ? incoming : existing;
  }
  return incoming;
}

async function upsertProject(p: ProjectRow): Promise<"inserted" | "updated" | "skipped"> {
  if (swarmStopped) return "skipped"; // Stop all inserts when swarm is stopped
  if (!p || !p.title || p.lat === undefined || p.lng === undefined) return "skipped";
  const lat = parseFloat(String(p.lat));
  const lng = parseFloat(String(p.lng));
  if (isNaN(lat) || isNaN(lng)) return "skipped";

  const title = p.title;
  const description = p.description || "";
  const funder = Array.isArray(p.funder) ? p.funder.join(", ") : (p.funder || "");
  const projectUrl = p.url || `internal://${title.replace(/[^\w]/g, "-").toLowerCase()}-${lat}-${lng}`;

  const { titleEmbedding, descriptionEmbedding } = await computeEmbeddingsForProject({ title, description });

  const existingByUrl = db.prepare("SELECT id, title, description, funder FROM projects WHERE url = ?").get(projectUrl) as
    | { id: number; title: string; description: string; funder: string }
    | undefined;

  const mergedFunder = (existingByUrl?.funder || "")
    ? [...new Set([...(existingByUrl?.funder || "").split(",").map((f) => f.trim()).filter(Boolean), ...funder.split(",").map((f) => f.trim()).filter(Boolean)])].join(", ")
    : funder;

  const applyUpdate = (id: number, existing: any) => {
    updateProjectByIdStmt.run(
      chooseBestValue(existing.title, title),
      chooseBestValue(existing.description, description),
      mergedFunder,
      lat,
      lng,
      p.category || "General",
      p.status || "Active",
      p.image_url ?? null,
      p.start_date ?? null,
      p.end_date ?? null,
      p.relevance_score ?? 0.95,
      p.s_ocean_score ?? 0.75,
      serializeEmbedding(titleEmbedding),
      serializeEmbedding(descriptionEmbedding),
      id
    );
  };

  if (existingByUrl) {
    applyUpdate(existingByUrl.id, existingByUrl);
    return "updated";
  }

  const dup = await findDuplicateProject({
    title,
    description,
    lat,
    lng,
    title_embedding: titleEmbedding,
    description_embedding: descriptionEmbedding,
  });
  if (dup) {
    const existing = db.prepare("SELECT title, description, funder FROM projects WHERE id = ?").get(dup.id) as
      | { title: string; description: string; funder: string }
      | undefined;
    applyUpdate(dup.id, existing || {});
    return "updated";
  }

  insertProjectStmt.run({
    title,
    url: projectUrl,
    description,
    funder,
    lat,
    lng,
    category: p.category || "General",
    status: p.status || "Active",
    image_url: p.image_url ?? null,
    start_date: p.start_date ?? null,
    end_date: p.end_date ?? null,
    relevance_score: p.relevance_score ?? 0.95,
    s_ocean_score: p.s_ocean_score ?? 0.75,
    title_embedding: serializeEmbedding(titleEmbedding),
    description_embedding: serializeEmbedding(descriptionEmbedding),
  });
  const row = db.prepare("SELECT id FROM projects WHERE url = ?").get(projectUrl) as { id: number } | undefined;

  // DOMAIN SCORING: Record project for domain reliability tracking
  try {
    const domainEngine = getDomainScoringEngine();
    domainEngine.recordProject(projectUrl, true);
  } catch (err) {
    console.warn(`[DomainScoring] Failed to record domain metrics: ${err}`);
  }

  const feature = {
    type: "Feature",
    geometry: { type: "Point", coordinates: [lng, lat] },
    properties: {

      id: row?.id,
      title,
      url: projectUrl,
      description,
      funder,
      relevance_score: p.relevance_score ?? 0.95,
      s_ocean_score: p.s_ocean_score ?? 0.75,
      category: p.category,
      status: p.status,
      image_url: p.image_url,
      start_date: p.start_date,
      end_date: p.end_date,
    },
  };
  broadcastNewProject(feature);
  return "inserted";
}

async function insertManyProjects(projects: any[]): Promise<number> {
  let count = 0;
  for (const p of projects) {
    const result = await upsertProject(p);
    if (result !== "skipped") count++;
  }
  return count;
}

async function saveProjects(projects: any[]): Promise<number> {
  console.log(`[Database] saveProjects called with ${projects.length} items`);
  const savedCount = await insertManyProjects(projects);
  console.log(`[Database] Saved ${savedCount} projects to database`);
  return savedCount;
}

function recordTelemetry(engine: string, targetUrl: string, status: string, projectsFound: number, durationMs: number, errorMessage: string | null = null, rawResponse: string | null = null) {
  db.prepare(`
    INSERT INTO telemetry (engine, target_url, status, projects_found, duration_ms, error_message, raw_response)
    VALUES (?, ?, ?, ?, ?, ?, ?)
  `).run(engine, targetUrl, status, projectsFound, durationMs, errorMessage, rawResponse);
}

function parseProjectsData(projectsData: any) {
  console.log(`[Parser] Parsing data of type: ${typeof projectsData}`);
  let projects = projectsData;

  // If it's a string, try to parse it as JSON first
  if (typeof projects === 'string') {
    try {
      const parsed = JSON.parse(projects);
      if (typeof parsed === 'object' && parsed !== null) {
        projects = parsed;
      }
    } catch (e) {
      // Not a valid JSON object string, continue
    }
  }

  // Extract string from result/output wrapper if present
  if (typeof projects === 'object' && projects !== null && !Array.isArray(projects)) {
    if (typeof projects.result === 'string') {
      projects = projects.result;
    } else if (typeof projects.output === 'string') {
      projects = projects.output;
    }
  }

  if (typeof projects === 'string') {
    try {
      // Try to find JSON block
      const jsonMatch = projects.match(/```json\s*([\s\S]*?)\s*```/) || projects.match(/```\s*([\s\S]*?)\s*```/);
      const cleaned = jsonMatch ? jsonMatch[1] : projects.trim();

      // Remove any leading/trailing non-JSON characters if no block found
      let jsonStr = cleaned;
      if (!jsonMatch) {
        const start = cleaned.indexOf('[');
        const end = cleaned.lastIndexOf(']');
        const startObj = cleaned.indexOf('{');
        const endObj = cleaned.lastIndexOf('}');

        if (start !== -1 && end !== -1 && (start < startObj || startObj === -1)) {
          jsonStr = cleaned.substring(start, end + 1);
        } else if (startObj !== -1 && endObj !== -1) {
          jsonStr = cleaned.substring(startObj, endObj + 1);
        }
      }

      console.log(`[Parser] Attempting to parse JSON string: ${jsonStr.substring(0, 100)}...`);
      projects = JSON.parse(jsonStr);
    } catch (e) {
      console.error("Failed to parse string result:", typeof projects === 'string' ? projects.substring(0, 200) : projects);
      projects = [];
    }
  }

  if (!Array.isArray(projects) && projects !== null && typeof projects === 'object') {
    console.log(`[Parser] Data is object, extracting array. Keys: ${Object.keys(projects).join(', ')}`);
    if (projects.type === "FeatureCollection" && Array.isArray(projects.features)) {
      projects = projects.features;
    } else if (projects.projects && Array.isArray(projects.projects)) {
      projects = projects.projects;
    } else if (projects.result && Array.isArray(projects.result)) {
      projects = projects.result;
    } else if (projects.features && Array.isArray(projects.features)) {
      projects = projects.features;
    } else {
      projects = [projects];
    }
  }

  if (!Array.isArray(projects)) {
    console.warn("[Parser] Could not find array in data");
    return [];
  }

  console.log(`[Parser] Normalizing ${projects.length} items`);
  // Map GeoJSON features or normalize flat objects
  return projects.map((p: any) => {
    let normalized = p;
    if (p.type === "Feature" && p.properties && p.geometry) {
      normalized = {
        ...p.properties,
        lat: p.geometry.coordinates?.[1],
        lng: p.geometry.coordinates?.[0]
      };
    }

    // Normalize lat/lng keys
    if (normalized.latitude !== undefined && normalized.lat === undefined) normalized.lat = normalized.latitude;
    if (normalized.longitude !== undefined && normalized.lng === undefined) normalized.lng = normalized.longitude;

    return normalized;
  });
}

import { htmlToMarkdown } from "mdream";
import FirecrawlApp from "@mendable/firecrawl-js";

const turndownService = new TurndownService();

/** Extract image URLs from HTML (og:image, twitter:image, first content img). Used as fallback when Claude returns empty. */
function extractImageUrlsFromHtml(html: string, baseUrl: string): string[] {
  const urls: string[] = [];
  try {
    const doc = new JSDOM(html, { url: baseUrl });
    const document = doc.window.document;
    const metaOg = document.querySelector('meta[property="og:image"]');
    const metaTwitter = document.querySelector('meta[name="twitter:image"], meta[property="twitter:image"]');
    const firstImg = document.querySelector('article img, main img, [role="main"] img, .content img, .project img, .hero img, img[src*="project"], img[src*="hero"], img');
    if (metaOg?.getAttribute("content")) {
      const href = metaOg.getAttribute("content")!.trim();
      if (href.startsWith("http")) urls.push(href);
      else urls.push(new URL(href, baseUrl).href);
    }
    if (metaTwitter?.getAttribute("content")) {
      const href = metaTwitter.getAttribute("content")!.trim();
      if (href.startsWith("http")) urls.push(href);
      else urls.push(new URL(href, baseUrl).href);
    }
    if (firstImg?.getAttribute("src")) {
      const href = firstImg.getAttribute("src")!.trim();
      if (href.startsWith("http")) urls.push(href);
      else urls.push(new URL(href, baseUrl).href);
    }
    return [...new Set(urls)];
  } catch {
    return [];
  }
}

async function fetchMarkdown(url: string): Promise<{ markdown: string, method: string, imageUrls?: string[] }> {
  let html = "";
  try {
    // Niveau 1: Local & Gratuit (Readability)
    const res = await fetch(url, {
      headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' }
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    html = await res.text();

    const doc = new JSDOM(html, { url });
    const reader = new Readability(doc.window.document);
    const article = reader.parse();

    if (article && article.textContent.length > 500) {
      const markdown = turndownService.turndown(article.content);
      const imageUrls = extractImageUrlsFromHtml(html, url);
      return { markdown, method: 'Readability', imageUrls };
    } else {
      throw new Error('Content too short or empty (JS-heavy)');
    }
  } catch (err: any) {
    console.log(`[Web Reading] Readability failed for ${url} (${err.message}), switching to Mdream...`);

    try {
      // Niveau 2: Mdream
      if (html) {
        const markdown = await htmlToMarkdown(html);
        if (markdown && markdown.length > 500) {
          const imageUrls = extractImageUrlsFromHtml(html, url);
          return { markdown, method: 'Mdream', imageUrls };
        }
      }
      throw new Error('Mdream result too short or empty');
    } catch (mdreamErr: any) {
      console.log(`[Web Reading] Mdream failed for ${url} (${mdreamErr.message}), switching to fallbacks...`);

      // Niveau 3: Firecrawl
      if (process.env.FIRECRAWL_API_KEY) {
        try {
          console.log(`[Web Reading] Trying Firecrawl for ${url}...`);
          const firecrawl = new FirecrawlApp({ apiKey: process.env.FIRECRAWL_API_KEY });
          const scrapeResult = await firecrawl.scrape(url, { formats: ['markdown'] }) as any;
          if (!scrapeResult.success) {
            throw new Error(scrapeResult.error || "Firecrawl scrape failed");
          }
          return { markdown: scrapeResult.markdown || "", method: 'Firecrawl' };
        } catch (firecrawlErr: any) {
          console.log(`[Web Reading] Firecrawl failed for ${url} (${firecrawlErr.message})`);
        }
      }

      // Niveau 4: Scrape.do
      const scrapeDoKey = process.env['SCRAPE.DO_API_KEY'] || process.env.SCRAPE_DO_API_KEY;
      if (scrapeDoKey) {
        try {
          console.log(`[Web Reading] Trying Scrape.do for ${url}...`);
          const scrapeRes = await fetch(`http://api.scrape.do?token=${scrapeDoKey}&url=${encodeURIComponent(url)}`);
          if (!scrapeRes.ok) throw new Error(`Scrape.do HTTP ${scrapeRes.status}`);
          const scrapeHtml = await scrapeRes.text();
          const markdown = await htmlToMarkdown(scrapeHtml);
          if (markdown && markdown.length > 500) {
            const imageUrls = extractImageUrlsFromHtml(scrapeHtml, url);
            return { markdown, method: 'Scrape.do', imageUrls };
          }
          throw new Error('Scrape.do result too short or empty');
        } catch (scrapeErr: any) {
          console.log(`[Web Reading] Scrape.do failed for ${url} (${scrapeErr.message})`);
        }
      }

      // Niveau 5: Jina Reader
      if (process.env.JINA_READER_API_KEY) {
        try {
          console.log(`[Web Reading] Trying Jina Reader for ${url}...`);
          const jinaRes = await fetch(`https://r.jina.ai/${url}`, {
            headers: { 'Authorization': `Bearer ${process.env.JINA_READER_API_KEY}` }
          });
          if (!jinaRes.ok) throw new Error(`Jina HTTP ${jinaRes.status}`);
          const markdown = await jinaRes.text();
          if (markdown && markdown.length > 500) {
            return { markdown, method: 'Jina Reader' };
          }
          throw new Error('Jina Reader result too short or empty');
        } catch (jinaErr: any) {
          console.log(`[Web Reading] Jina Reader failed for ${url} (${jinaErr.message})`);
          throw new Error(`All extraction methods failed. Last error: ${jinaErr.message}`);
        }
      }
      throw new Error(`All extraction methods failed. No API keys available for fallback.`);
    }
  }
}

const DEFAULT_GATEKEEPER = {
  marine_threshold: 0.75,
  inland_threshold: 0.9,
  coast_distance_km: 0, // 0 = comportement original (GSHHG point-in-polygon). >0 = tolérer projets à X km de la côte
};

/** Gatekeeper: reject projects not genuinely related to marine/ocean conservation. Stricter when inland or far from coast. */
function passesMarineGatekeeper(
  projectData: any,
  config?: { marine_threshold?: number; inland_threshold?: number; coast_distance_km?: number }
): { pass: boolean; reason?: string } {
  const marineRelevance = typeof projectData.marine_relevance === "number" ? projectData.marine_relevance : 0;
  const lat = parseFloat(projectData.lat) || 0;
  const lng = parseFloat(projectData.lng) || 0;
  const locationType = projectData.location_type || "unknown";
  const cfg = { ...DEFAULT_GATEKEEPER, ...config };
  const marineThreshold = cfg.marine_threshold ?? DEFAULT_GATEKEEPER.marine_threshold;
  const inlandThreshold = cfg.inland_threshold ?? DEFAULT_GATEKEEPER.inland_threshold;
  const coastKm = cfg.coast_distance_km ?? 0;

  let inland: boolean;
  if (coastKm > 0) {
    const dist = distanceToCoastKm(lat, lng);
    inland = dist > coastKm;
  } else {
    const coordsInland = isInlandGSHHG(lat, lng);
    inland = coordsInland || locationType === "inland";
  }

  const threshold = inland ? inlandThreshold : marineThreshold;
  if (marineRelevance < threshold) {
    return {
      pass: false,
      reason: inland
        ? (coastKm > 0
          ? `Gatekeeper: projet à >${coastKm} km de la côte (${lat.toFixed(2)}, ${lng.toFixed(2)}), marine_relevance=${marineRelevance.toFixed(2)} < ${threshold}`
          : `Gatekeeper: projet situé en terres (${lat.toFixed(2)}, ${lng.toFixed(2)}), marine_relevance=${marineRelevance.toFixed(2)} < ${threshold}`)
        : `Gatekeeper: marine_relevance=${marineRelevance.toFixed(2)} < ${threshold}`,
    };
  }
  return { pass: true };
}

/** Stage 1: Claude Haiku - Quick gatekeeper filter */
async function gatekeeperOnly(markdown: string, url: string, modelOverride?: string): Promise<{ pass: boolean; marine_relevance: number; location_type: string }> {
  const apiKey = process.env.CLAUDE_API_KEY || process.env.ANTHROPIC_API_KEY;
  if (!apiKey) throw new Error("CLAUDE_API_KEY (or ANTHROPIC_API_KEY) is not configured");
  const client = new Anthropic({ apiKey });
  const model = modelOverride || CLAUDE_GATEKEEPER_MODEL;
  const excerpt = markdown.slice(0, 4000);
  const response = await client.messages.create({
    model,
    max_tokens: 128,
    temperature: 0,
    messages: [{
      role: "user",
      content: `URL: ${url}\n\nIs this page about OCEAN/MARINE conservation? Return ONLY valid JSON: { "marine_relevance": 0-1, "location_type": "coastal"|"inland"|"unknown" }. 0=not marine, 1=clearly marine. No markdown, no explanation.\n\nExcerpt:\n${excerpt}`
    }],
  });
  const textBlock = (response.content as any[]).find((b: any) => b.type === "text");
  const raw = (textBlock?.text || "{}").trim();
  const jsonMatch = raw.match(/\{[\s\S]*\}/);
  const data = JSON.parse(jsonMatch ? jsonMatch[0] : "{}");
  const mr = typeof data.marine_relevance === "number" ? data.marine_relevance : 0.5;
  const lt = data.location_type || "unknown";
  const gk = passesMarineGatekeeper({ marine_relevance: mr, location_type: lt, lat: 0, lng: 0 });
  return { pass: gk.pass, marine_relevance: mr, location_type: lt };
}

const CLAUDE_EXTRACT_MODEL = process.env.CLAUDE_EXTRACT_MODEL || "claude-sonnet-4-5-20250929";
const CLAUDE_GATEKEEPER_MODEL = process.env.CLAUDE_GATEKEEPER_MODEL || "claude-haiku-4-5-20251001";
const EXTRACT_CONCURRENCY = Math.max(1, Math.min(20, parseInt(process.env.EXTRACT_CONCURRENCY || "2", 10)));

/** Run async tasks with limited concurrency (worker pool). */
async function runWithConcurrency<T>(
  items: T[],
  concurrency: number,
  fn: (item: T, index: number) => Promise<number>,
  shouldAbort?: () => boolean
): Promise<number> {
  if (items.length === 0) return 0;
  let nextIndex = 0;
  const results: number[] = new Array(items.length);
  const workers = Array(Math.min(concurrency, items.length))
    .fill(null)
    .map(async () => {
      while (true) {
        if (shouldAbort?.()) return;
        const i = nextIndex++;
        if (i >= items.length) return;
        try {
          results[i] = await fn(items[i], i);
        } catch {
          results[i] = 0;
        }
      }
    });
  await Promise.all(workers);
  return results.reduce((a, b) => a + (b || 0), 0);
}

/** Stage 2: Claude Sonnet - Analysis, geocoding, coastal snapping. Description < 250 chars */
async function extractAndGeocode(markdown: string, url: string, modelOverride?: string, imageUrls?: string[]): Promise<any> {
  const apiKey = process.env.CLAUDE_API_KEY || process.env.ANTHROPIC_API_KEY;
  if (!apiKey) throw new Error("CLAUDE_API_KEY (or ANTHROPIC_API_KEY) is not configured");
  const client = new Anthropic({ apiKey });
  const model = modelOverride || CLAUDE_EXTRACT_MODEL;
  const response = await client.messages.create({
    model,
    max_tokens: 1024,
    temperature: 0,
    messages: [{
      role: "user",
      content: `Extract marine conservation project from this page. URL: ${url}

RULES:
- description: answer why, what, how, when, where in < 250 characters.
- If coordinates (lat,lng) are INLAND (Paris, Geneva, US Midwest), apply COASTAL SNAPPING: recalculate to nearest maritime/coastal point.
- marine_relevance 0-1, location_type coastal|inland|unknown
- image_url: extract a representative project image. Prefer: terrain photos, project photos, maps of the area. Accept maps as illustration. EXCLUDE logos and icons. Use absolute URLs. Examples: https://example.com/project-photo.jpg or https://cdn.example.org/map-region.png. Empty string only if no image found.
${imageUrls && imageUrls.length > 0 ? `\nAvailable images from page metadata (use the most relevant): ${imageUrls.slice(0, 5).join(", ")}` : ""}

Return ONLY valid JSON (no markdown, no explanation):
{"title":"string","url":"string","description":"string","funder":"string","lat":number,"lng":number,"category":"string","status":"string","image_url":"string","start_date":"string","end_date":"string","marine_relevance":number,"location_type":"coastal|inland|unknown"}

Markdown:
${markdown.slice(0, 12000)}`
    }],
  });
  const textBlock = (response.content as any[]).find((b: any) => b.type === "text");
  const raw = (textBlock?.text || "{}").trim();
  const jsonMatch = raw.match(/\{[\s\S]*\}/);
  const data = JSON.parse(jsonMatch ? jsonMatch[0] : "{}");
  if (data.marine_relevance === undefined) data.marine_relevance = 0.95;
  if (data.location_type === undefined) data.location_type = "unknown";
  if ((!data.image_url || data.image_url.trim() === "") && imageUrls && imageUrls.length > 0) {
    data.image_url = imageUrls[0];
  }
  return data;
}

/** Stage 3: Claude Sonnet - S_ocean scoring */
async function scoreSOcean(projectData: any, modelOverride?: string): Promise<number> {
  const apiKey = process.env.CLAUDE_API_KEY || process.env.ANTHROPIC_API_KEY;
  if (!apiKey) throw new Error("CLAUDE_API_KEY (or ANTHROPIC_API_KEY) is not configured");
  const client = new Anthropic({ apiKey });
  const model = modelOverride || CLAUDE_EXTRACT_MODEL;
  const response = await client.messages.create({
    model,
    max_tokens: 64,
    temperature: 0,
    messages: [{
      role: "user",
      content: `Score this marine project 0-1 (S_ocean): technicality, source reliability, oceanic localization. Return ONLY valid JSON: { "s_ocean_score": number }. No markdown, no explanation.\n\nProject: ${projectData.title}\n${projectData.description?.slice(0, 200) || ""}\nURL: ${projectData.url || ""}\nCoords: ${projectData.lat}, ${projectData.lng}`
    }],
  });
  const textBlock = (response.content as any[]).find((b: any) => b.type === "text");
  const raw = (textBlock?.text || "{}").trim();
  const jsonMatch = raw.match(/\{[\s\S]*\}/);
  const data = JSON.parse(jsonMatch ? jsonMatch[0] : "{}");
  return typeof data.s_ocean_score === "number" ? Math.max(0, Math.min(1, data.s_ocean_score)) : 0.75;
}

/** Full 3-stage pipeline: Haiku gatekeeper → Sonnet extract+coastal snapping → Sonnet S_ocean */
async function extractProjectData(markdown: string, url: string, extractionConfig?: ExtractionConfig, imageUrls?: string[]) {
  const gatekeeperModel = extractionConfig?.claudeGatekeeperModel || CLAUDE_GATEKEEPER_MODEL;
  const extractModel = extractionConfig?.claudeExtractModel || CLAUDE_EXTRACT_MODEL;
  const gatekeeper = await gatekeeperOnly(markdown, url, gatekeeperModel);
  if (!gatekeeper.pass) {
    throw new Error(`Gatekeeper rejected: marine_relevance=${gatekeeper.marine_relevance}`);
  }
  const projectData = await extractAndGeocode(markdown, url, extractModel, imageUrls);
  projectData.marine_relevance = gatekeeper.marine_relevance;
  projectData.location_type = gatekeeper.location_type;
  const scoringModel = extractionConfig?.claudeScoringModel || extractionConfig?.claudeExtractModel || CLAUDE_EXTRACT_MODEL;
  projectData.s_ocean_score = await scoreSOcean(projectData, scoringModel);
  if (!projectData.url || projectData.url.trim() === "") projectData.url = url;
  return projectData;
}

function parseUrlsData(projectsData: any): string[] {
  console.log(`[Parser] Parsing URLs data of type: ${typeof projectsData}`);
  let projects = projectsData;

  if (typeof projects === 'string') {
    try {
      const parsed = JSON.parse(projects);
      if (typeof parsed === 'object' && parsed !== null) {
        projects = parsed;
      }
    } catch (e) { }
  }

  if (typeof projects === 'object' && projects !== null && !Array.isArray(projects)) {
    if (typeof projects.result === 'string') projects = projects.result;
    else if (typeof projects.output === 'string') projects = projects.output;
  }

  if (typeof projects === 'string') {
    try {
      const jsonMatch = projects.match(/```json\s*([\s\S]*?)\s*```/) || projects.match(/```\s*([\s\S]*?)\s*```/);
      const cleaned = jsonMatch ? jsonMatch[1] : projects.trim();

      let jsonStr = cleaned;
      if (!jsonMatch) {
        const start = cleaned.indexOf('[');
        const end = cleaned.lastIndexOf(']');
        if (start !== -1 && end !== -1) {
          jsonStr = cleaned.substring(start, end + 1);
        }
      }

      projects = JSON.parse(jsonStr);
    } catch (e) {
      console.error("Failed to parse string result:", typeof projects === 'string' ? projects.substring(0, 200) : projects);
      projects = [];
    }
  }

  if (!Array.isArray(projects) && projects !== null && typeof projects === 'object') {
    if (projects.urls && Array.isArray(projects.urls)) projects = projects.urls;
    else if (projects.result && Array.isArray(projects.result)) projects = projects.result;
    else projects = [projects];
  }

  if (!Array.isArray(projects)) return [];

  return projects.filter(p => typeof p === 'string');
}

async function runTinyFishAgent(targetUrl: string, proxy?: string, retryCount = 0, mode: 'discover' | 'extract' = 'discover', taskConfig?: TaskConfig) {
  if (swarmStopped) return 0;
  const startTime = performance.now();
  console.log(`[TinyFish] Starting agent for: ${targetUrl} (Attempt ${retryCount + 1}, Mode: ${mode})`);
  let runId = "";
  /** Affiché avant l’appel API pour que la console liste TinyFish avant Readability. */
  let pendingRunId: string | null = null;
  try {
    const apiKey = process.env.TINYFISH_API_KEY;
    if (!apiKey) throw new Error("TINYFISH_API_KEY is not configured");

    pendingRunId = crypto.randomUUID();
    activeRuns.set(pendingRunId, {
      streamingUrl: "",
      logs: [],
      status: "STARTING",
      targetUrl,
      mode,
      agentLabel: "TinyFish",
    });

    // 1. Launch TinyFish Run
    const response = await fetch("https://agent.tinyfish.ai/v1/automation/run-async", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": apiKey,
      },
      body: JSON.stringify({
        url: targetUrl,
        goal: mode === 'extract' ? EXTRACT_PROMPT : GOAL_PROMPT,
        max_steps: 60
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`[TinyFish] API Error Response (${response.status}):`, errorText);
      throw new Error(`TinyFish API Error: ${errorText}`);
    }

    const runData = await response.json();
    const safeRunData = { ...runData };
    if (safeRunData.error === null) delete safeRunData.error;
    if (process.env.DEBUG_TINYFISH) {
      console.log(`[TinyFish] Initial Run Data:`, JSON.stringify(safeRunData));
    }

    if ((!runData.id && !runData.run_id) || (runData.error && runData.error !== null)) {
      console.error(`[TinyFish] Failed to start run for ${targetUrl}. Full Response:`, JSON.stringify(runData));
      const errorMsg = typeof runData.error === 'object' ? JSON.stringify(runData.error) : runData.error;
      throw new Error(errorMsg || `TinyFish failed to start run. Response: ${JSON.stringify(runData)}`);
    }
    runId = runData.id || runData.run_id;
    const streamingUrl = runData.streamingUrl || runData.streaming_url;

    console.log(`[TinyFish] Run started: ${runId} for ${targetUrl}. Status: ${runData.status || 'UNKNOWN'}`);
    if (runData.error) console.log(`[TinyFish] Note: Run started with non-fatal error key: ${runData.error}`);

    if (pendingRunId) {
      activeRuns.delete(pendingRunId);
      pendingRunId = null;
    }
    if (swarmStopped) return 0; // Don't increment or register if we stopped
    agentCounter++;
    const label = `TinyFish ${agentCounter}`;
    activeRuns.set(runId, { streamingUrl, logs: [], status: runData.status || "PENDING", targetUrl, mode, agentLabel: label });
    const shortUrl = targetUrl.length > 50 ? targetUrl.slice(0, 47) + "…" : targetUrl;
    broadcastLog({ key: "swarm_dispatched", label, url: shortUrl });
    broadcastLog({ key: "swarm_browsing", label, modeKey: mode === "extract" ? "extract" : "discovery", url: shortUrl });

    // 3. Poll for completion (or we could use SSE, but for the backend poll is safer for DB update)
    let status = runData.status || "PENDING";
    let result = null;
    let pendingStartTime = Date.now();
    const PENDING_TIMEOUT_MS = 120000; // 2 minutes: free slot if TinyFish never starts
    let lastPendingLog = 0;

    while (status === "RUNNING" || status === "PENDING") {
      // Check if run was aborted
      const currentRun = activeRuns.get(runId);
      if (!currentRun || currentRun.aborted) {
        console.log(`[TinyFish] Run ${runId} was aborted or removed. Stopping poll.`);
        break;
      }

      // Safety timeout for PENDING state
      const timeInPending = Date.now() - pendingStartTime;
      if (status === "PENDING" && (timeInPending > PENDING_TIMEOUT_MS)) {
        console.error(`[TinyFish] Run ${runId} timed out in PENDING state after ${Math.round(timeInPending / 1000)}s. Freeing slot.`);
        activeRuns.delete(runId);
        throw new Error("Agent timed out while waiting to start (PENDING state too long). Slot freed for next task.");
      }
      // Log PENDING at most every 30s to avoid spam
      if (status === "PENDING" && (Date.now() - lastPendingLog > 30000)) {
        lastPendingLog = Date.now();
        console.log(`[TinyFish] Run ${runId} still PENDING (${Math.round(timeInPending / 1000)}s). Timeout in ${Math.round((PENDING_TIMEOUT_MS - timeInPending) / 1000)}s.`);
      }

      await new Promise(resolve => setTimeout(resolve, 5000));
      try {
        const statusRes = await fetch(`https://agent.tinyfish.ai/v1/runs/${runId}`, {
          headers: { "X-API-Key": apiKey }
        });

        if (!statusRes.ok) {
          console.error(`[TinyFish] Failed to fetch status for run ${runId}. Status: ${statusRes.status}`);
          continue; // Try again next loop
        }

        const statusData = await statusRes.json();
        status = statusData.status;

        // Update streaming URL if it was missing and is now available
        if (currentRun && !currentRun.streamingUrl && (statusData.streamingUrl || statusData.streaming_url)) {
          activeRuns.set(runId, {
            ...currentRun,
            streamingUrl: statusData.streamingUrl || statusData.streaming_url,
            status: status
          });
        } else if (currentRun) {
          activeRuns.set(runId, { ...currentRun, status: status });
        }

        if (status !== "RUNNING" && status !== "PENDING") {
          console.log(`[TinyFish] Run ${runId} status: ${status}`);
        }

        if (status === "COMPLETED") {
          broadcastLog({ key: "swarm_complete", label, modeKey: mode === "extract" ? "extract" : "discovery" });
          const safeStatusData = { ...statusData };
          if (safeStatusData.error === null) delete safeStatusData.error;
          if (safeStatusData.steps) delete safeStatusData.steps;
          if (safeStatusData.goal) delete safeStatusData.goal;
          if (safeStatusData.result) delete safeStatusData.result;
          if (safeStatusData.output) delete safeStatusData.output;
          console.log(`[TinyFish] Run ${runId} COMPLETED. Data:`, JSON.stringify(safeStatusData));
          result = statusData.result || statusData.output;
          // Retirer immédiatement de l'UI : les anciens agents ne s'affichent plus
          activeRuns.delete(runId);
        } else if (status === "FAILED") {
          const safeStatusData = { ...statusData };
          if (safeStatusData.steps) delete safeStatusData.steps;
          if (safeStatusData.goal) delete safeStatusData.goal;
          if (safeStatusData.result) delete safeStatusData.result;
          if (safeStatusData.output) delete safeStatusData.output;
          console.error(`[TinyFish] Run ${runId} FAILED. Data:`, JSON.stringify(safeStatusData));
          const errorMsg = typeof statusData.error === 'object' && statusData.error !== null
            ? (statusData.error.message || JSON.stringify(statusData.error))
            : statusData.error;
          throw new Error(errorMsg || "TinyFish run failed");
        }
      } catch (pollError: any) {
        console.error(`[TinyFish] Error polling status for run ${runId}:`, pollError.message);
        // Don't throw here, let the loop continue and potentially timeout if it's a transient network error
      }
    }

    let projectsFound = 0;
    let rawResponse = "";
    if (result) {
      rawResponse = typeof result === 'string' ? result : JSON.stringify(result);
      console.log(`[TinyFish] Received result for ${targetUrl}`);

      if (mode === 'extract') {
        if (swarmStopped) return 0;
        try {
          // Parse the JSON result directly
          let projectData = result;
          if (typeof result === 'string') {
            const jsonMatch = result.match(/```json\s*([\s\S]*?)\s*```/) || result.match(/```\s*([\s\S]*?)\s*```/);
            const cleaned = jsonMatch ? jsonMatch[1] : result.trim();
            projectData = JSON.parse(cleaned);
          }
          if (projectData.marine_relevance === undefined) projectData.marine_relevance = 0.5;
          if (projectData.location_type === undefined) projectData.location_type = "unknown";

          if (swarmStopped) return 0;
          const gatekeeper = passesMarineGatekeeper(projectData, taskConfig?.gatekeeper);
          if (!gatekeeper.pass) {
            console.log(`[Gatekeeper] REJECTED (extract mode) ${targetUrl}: ${gatekeeper.reason}`);
            if (!swarmStopped) {
              try {
                const errType = "gatekeeper";
                db.prepare(`
                  INSERT INTO failed_extractions (target_url, project_url, error_message, error_type)
                  VALUES (?, ?, ?, ?)
                  ON CONFLICT(project_url) DO UPDATE SET
                    error_message = excluded.error_message,
                    error_type = excluded.error_type,
                    created_at = CURRENT_TIMESTAMP
                `).run(targetUrl, targetUrl, gatekeeper.reason!, errType);
              } catch (dbErr) { }
            }
            throw new Error(gatekeeper.reason);
          }

          const relevanceScore = typeof projectData.marine_relevance === "number" ? projectData.marine_relevance : 0.95;
          const upsertResult = await upsertProject({
            title: projectData.title || 'Unknown',
            url: projectData.url || targetUrl,
            description: projectData.description || '',
            funder: projectData.funder || 'Unknown',
            lat: projectData.lat || 0,
            lng: projectData.lng || 0,
            category: projectData.category || 'Marine Conservation',
            status: projectData.status || 'Active',
            image_url: projectData.image_url || '',
            start_date: projectData.start_date || null,
            end_date: projectData.end_date || null,
            relevance_score: relevanceScore,
            s_ocean_score: projectData.s_ocean_score ?? 0.75,
          });

          try {
            db.prepare(`DELETE FROM failed_extractions WHERE project_url = ?`).run(targetUrl);
          } catch (e) { }

          projectsFound = upsertResult !== "skipped" ? 1 : 0;
          if (upsertResult !== "skipped") {
            broadcastLog({ key: "etl_saved", title: (projectData.title || "?").slice(0, 35) });
          }
          broadcastLog({ key: projectsFound === 1 ? "etl_extract_one" : "etl_extract_many", n: projectsFound });
          console.log(`[TinyFish] Extraction mode finished successfully for ${targetUrl}`);
        } catch (err: any) {
          console.error(`[TinyFish] Error parsing extraction result for ${targetUrl}:`, err.message);
          try {
            const errType = inferErrorType(err.message);
            db.prepare(`
              INSERT INTO failed_extractions (target_url, project_url, error_message, error_type)
              VALUES (?, ?, ?, ?)
              ON CONFLICT(project_url) DO UPDATE SET
                error_message = excluded.error_message,
                error_type = excluded.error_type,
                created_at = CURRENT_TIMESTAMP
            `).run(targetUrl, targetUrl, err.message, errType);
          } catch (e) { }
          throw new Error(`Failed to parse extraction result: ${err.message}`);
        }
      } else {
        const urls = parseUrlsData(result);
        const currentRunAfterDiscover = activeRuns.get(runId);
        if (swarmStopped || currentRunAfterDiscover?.aborted) {
          console.log(`[TinyFish] Run ${runId} stopped before extraction. Skipping hybrid extraction.`);
          activeRuns.delete(runId);
          return;
        }
        globalExtractConcurrency = Math.max(1, Math.min(20, taskConfig?.extraction?.concurrency ?? EXTRACT_CONCURRENCY));
        broadcastLog({ key: "etl_cache_updated", n: urls.length });
        broadcastLog({ key: "etl_pipeline", n: urls.length, c: globalExtractConcurrency });
        console.log(`[TinyFish] Discovered ${urls.length} URLs for ${targetUrl}. Pushing to global extraction queue...`);
        appendToDeepLinkCache("DeepLinkCacheProjectsLists.json", [targetUrl]);
        if (urls.length > 0) appendToDeepLinkCache("DeepLinkCacheProjectsPages.json", urls);

        activeRuns.delete(runId);
        if (urls.length === 0) {
          recordTelemetry("tinyfish", targetUrl, "SUCCESS", 0, Math.round(performance.now() - startTime), null, rawResponse);
          return;
        }
        if (swarmStopped) {
          console.log(`[TinyFish] Swarm stopped before queuing ${urls.length} extractions for ${targetUrl}`);
          return;
        }
        pendingByTarget.set(targetUrl, { total: urls.length, success: 0, processed: 0, startTime, rawResponse });
        extractingCount += urls.length;
        for (const projectUrl of urls) {
          globalExtractQueue.push({ projectUrl, targetUrl, taskConfig });
        }
        startGlobalExtractWorkers();
        return;
      }
    }

    const duration = Math.round(performance.now() - startTime);
    recordTelemetry('tinyfish', targetUrl, 'SUCCESS', projectsFound, duration, null, rawResponse);
    activeRuns.delete(runId);
  } catch (error: any) {
    console.error(`[TinyFish] Error for ${targetUrl}:`, error.message);
    const duration = Math.round(performance.now() - startTime);

    if (pendingRunId) {
      activeRuns.delete(pendingRunId);
      pendingRunId = null;
    }

    // Auto-retry once with standard profile if it failed early or timed out
    if (retryCount < 1 && !error.message.includes("aborted")) {
      console.log(`[TinyFish] Retrying ${targetUrl} due to error...`);
      if (runId) activeRuns.delete(runId);
      return runTinyFishAgent(targetUrl, proxy, retryCount + 1, mode, taskConfig);
    }

    recordTelemetry('tinyfish', targetUrl, 'ERROR', 0, duration, error.message);
    if (runId) activeRuns.delete(runId);
    throw error;
  }
}

// --- Kartverket (Den norske los) OGC API ---
const KARTVERKET_BASE = "https://dnl.kartverket.no/api/ogc/v1";
const PAGE_SIZE = 100;

function decodeHtmlEntities(s: string | null | undefined): string {
  if (s == null || typeof s !== "string") return "";
  return s
    .replace(/&oslash;/gi, "ø")
    .replace(/&aelig;/gi, "æ")
    .replace(/&aring;/gi, "å")
    .replace(/&Oslash;/g, "Ø")
    .replace(/&AElig;/g, "Æ")
    .replace(/&Aring;/g, "Å")
    .replace(/&nbsp;/g, " ")
    .replace(/&ndash;/g, "–")
    .replace(/&ldquo;/g, '"')
    .replace(/&rdquo;/g, '"')
    .replace(/&lsquo;/g, "'")
    .replace(/&rsquo;/g, "'")
    .trim();
}

async function fetchKartverketCollection(
  collection: "sailingdirections" | "place"
): Promise<{ source: string; source_id: string; title: string; description: string | null; caution: string | null; lat: number; lng: number; zone_ref: string | null; country: string; objtype: string | null; source_url: string }[]> {
  const source = collection === "sailingdirections" ? "kartverket_sailing" : "kartverket_place";
  const country = "Norway";
  const items: { source: string; source_id: string; title: string; description: string | null; caution: string | null; lat: number; lng: number; zone_ref: string | null; country: string; objtype: string | null; source_url: string }[] = [];
  let offset = 0;
  let hasMore = true;
  while (hasMore) {
    const url = `${KARTVERKET_BASE}/collections/dennorskelos/${collection}/items?limit=${PAGE_SIZE}&offset=${offset}&f=json`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Kartverket ${collection} fetch failed: ${res.status}`);
    const data = await res.json();
    const features = data.features ?? [];
    for (const f of features) {
      const props = f.properties ?? {};
      const geom = f.geometry;
      if (!geom || geom.type !== "Point" || !Array.isArray(geom.coordinates) || geom.coordinates.length < 2) continue;
      const [lng, lat] = geom.coordinates;
      const sourceId = props.id ?? f.id ?? `${collection}-${offset}-${items.length}`;
      let title = "";
      let description: string | null = null;
      let caution: string | null = null;
      if (collection === "sailingdirections") {
        title = decodeHtmlEntities(props.title_en ?? props.title_no ?? props.title ?? "");
        description = decodeHtmlEntities(props.description_en ?? props.description_no ?? null) || null;
        caution = decodeHtmlEntities(props.caution_en ?? props.caution_no ?? null) || null;
      } else {
        title = decodeHtmlEntities(props.title ?? props.title_en ?? props.title_no ?? "");
        const descEn = decodeHtmlEntities(props.description_en ?? props.description_no ?? null);
        const anchEn = decodeHtmlEntities(props.anchorage_en ?? props.anchorage_no ?? null);
        description = [descEn, anchEn].filter(Boolean).join("\n\n") || null;
        caution = null;
      }
      if (!title) title = sourceId;
      items.push({
        source,
        source_id: sourceId,
        title,
        description,
        caution,
        lat,
        lng,
        zone_ref: props.county ?? props.municipality ?? null,
        country,
        objtype: props.objtype ?? null,
        source_url: `https://dnl.kartverket.no/api/ogc/v1/collections/dennorskelos/${collection}/items/${sourceId}`,
      });
    }
    const returned = features.length;
    offset += returned;
    hasMore = returned >= PAGE_SIZE;
  }
  return items;
}

type NauticalInsert = { source: string; source_id: string; title: string; description: string | null; caution: string | null; lat: number; lng: number; zone_ref: string | null; country: string; objtype: string | null; source_url: string };

/** Insert pour cruiserswiki_wayback : lat/lng optionnels (pages sans coordonnées conservées) */
type NauticalInsertWayback = Omit<NauticalInsert, "lat" | "lng"> & { lat: number | null; lng: number | null; wayback_timestamp: string; wayback_url: string };

async function fetchHidrograficoAton(): Promise<NauticalInsert[]> {
  const items: NauticalInsert[] = [];
  let offset = 0;
  const limit = 100;
  let hasMore = true;
  while (hasMore) {
    const url = `https://api-features.hidrografico.pt/collections/aton/items?limit=${limit}&offset=${offset}&f=json`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Hidrografico aton fetch failed: ${res.status}`);
    const data = await res.json();
    const features = data.features ?? [];
    for (const f of features) {
      const props = f.properties ?? {};
      const geom = f.geometry;
      if (!geom || geom.type !== "Point" || !Array.isArray(geom.coordinates) || geom.coordinates.length < 2) continue;
      const [lng, lat] = geom.coordinates;
      const sourceId = `hidrografico_aton_${f.id ?? offset}-${items.length}`;
      const title = props.title ?? props.no_nac ?? sourceId;
      const desc = [props.desc, props.rmks, props.ch_abr].filter(Boolean).join(" · ") || null;
      items.push({
        source: "hidrografico_aton",
        source_id: sourceId,
        title: String(title),
        description: desc,
        caution: null,
        lat,
        lng,
        zone_ref: props.pos_WGS84 ?? null,
        country: "Portugal",
        objtype: "AtoN",
        source_url: `https://api-features.hidrografico.pt/collections/aton/items?f=html`,
      });
    }
    offset += features.length;
    hasMore = features.length >= limit;
  }
  return items;
}

function polygonCentroid(coords: number[][][]): [number, number] {
  let sumX = 0, sumY = 0, n = 0;
  for (const ring of coords) {
    for (const p of ring) {
      if (p.length >= 2) { sumX += p[0]; sumY += p[1]; n++; }
    }
  }
  return n > 0 ? [sumX / n, sumY / n] : [0, 0];
}

async function fetchNoaaAnchorages(): Promise<NauticalInsert[]> {
  const items: NauticalInsert[] = [];
  let offset = 0;
  const limit = 1000;
  let hasMore = true;
  while (hasMore) {
    const url = `https://coast.noaa.gov/arcgis/rest/services/Hosted/Anchorages/FeatureServer/0/query?where=1%3D1&outFields=anchoragename,location,anchoragetype,codefederalregulations&outSR=4326&f=geojson&resultOffset=${offset}&resultRecordCount=${limit}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`NOAA Anchorages fetch failed: ${res.status}`);
    const data = await res.json();
    const features = data.features ?? [];
    for (const f of features) {
      const props = f.properties ?? {};
      const geom = f.geometry;
      if (!geom || geom.type !== "Polygon" || !Array.isArray(geom.coordinates)) continue;
      const [lng, lat] = polygonCentroid(geom.coordinates);
      const sourceId = `noaa_anchor_${f.id ?? offset}-${items.length}`;
      const title = props.anchoragename ?? props.location ?? sourceId;
      const desc = [props.location, props.anchoragetype, props.codefederalregulations].filter(Boolean).join(" · ") || null;
      items.push({
        source: "noaa_anchor",
        source_id: sourceId,
        title: String(title),
        description: desc,
        caution: null,
        lat,
        lng,
        zone_ref: props.location ?? null,
        country: "USA",
        objtype: "anchorage",
        source_url: `https://coast.noaa.gov/arcgis/rest/services/Hosted/Anchorages/FeatureServer/0`,
      });
    }
    offset += features.length;
    hasMore = features.length >= limit;
  }
  return items;
}

const UK_AIMS_BASE = "https://environment.data.gov.uk/geoservices/datasets/d94b1866-b001-4a53-bb91-4016d05b48b8/ogc/features/v1/collections/AIMS_Aid_to_Navigation_Point/items";

async function fetchAimsAton(): Promise<NauticalInsert[]> {
  const items: NauticalInsert[] = [];
  let startIndex = 0;
  const limit = 500;
  let hasMore = true;
  while (hasMore) {
    const url = `${UK_AIMS_BASE}?f=application%2Fgeo%2Bjson&limit=${limit}&startIndex=${startIndex}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`UK AIMS fetch failed: ${res.status}`);
    const data = await res.json();
    const features = data.features ?? [];
    for (const f of features) {
      const props = f.properties ?? {};
      const geom = f.geometry;
      if (!geom || geom.type !== "Point" || !Array.isArray(geom.coordinates) || geom.coordinates.length < 2) continue;
      const [lng, lat] = geom.coordinates;
      const sourceId = `aims_aton_${props.asset_id ?? f.id ?? startIndex}-${items.length}`;
      const title = props.asset_name && props.asset_name !== "Not Available" ? props.asset_name : `${props.asset_sub_type ?? "AtoN"} (${props.asset_id ?? "?"})`;
      const desc = [props.asset_sub_type, props.water_management_area, props.local_authority, props.water_course_name].filter(Boolean).join(" · ") || null;
      items.push({
        source: "aims_aton",
        source_id: sourceId,
        title: String(title),
        description: desc,
        caution: null,
        lat,
        lng,
        zone_ref: props.local_authority ?? props.water_management_area ?? null,
        country: "UK",
        objtype: props.asset_sub_type ?? "AtoN",
        source_url: "https://environment.data.gov.uk/spatialdata/aims-aid-to-navigation/ogc/features/v1",
      });
    }
    startIndex += features.length;
    hasMore = features.length >= limit;
  }
  return items;
}

// --- Cruisers Wiki (API MediaWiki, pas TinyFish) ---
const CRUISERSWIKI_API = "https://www.cruiserswiki.org/api.php";
const CRUISERSWIKI_DELAY_MS = 300;

const CRUISERSWIKI_HEADERS: Record<string, string> = {
  "User-Agent": "BlueIntelligence/1.0 (Maritime OSINT; +https://github.com/blue-intelligence)",
  "Accept": "application/json",
};

/** Instance Playwright partagée pendant le sync Cruisers Wiki */
let cruisersWikiBrowser: Awaited<ReturnType<typeof import("playwright").chromium.launch>> | null = null;

/** Fetch via Playwright (stealth si dispo). Retourne null si échec. */
async function cruisersWikiFetchViaPlaywright(url: string): Promise<{ text: string; status: number } | null> {
  if (!cruisersWikiBrowser) return null;
  try {
    const page = await cruisersWikiBrowser.newPage();
    const response = await page.goto(url, { waitUntil: "networkidle", timeout: 25000 });
    await page.close();
    if (!response) return null;
    const text = await response.text();
    return { text, status: response.status() };
  } catch {
    return null;
  }
}

/** Fetch Cruisers Wiki. Ordre: FlareSolverr → Proxy → Playwright → TinyFish → Direct. */
async function cruisersWikiFetch(url: string, useTinyFish = false): Promise<{ text: string; status: number }> {
  return libCruisersWikiFetch(url, useTinyFish, {
    extraFetcher: cruisersWikiFetchViaPlaywright,
  });
}

/** Parse la réponse Cruisers Wiki ; gère 403, Cloudflare, et JSON invalide */
function parseCruisersWikiResponse(result: { text: string; status: number }): any {
  const { text, status } = result;
  const trimmed = text.trim();
  if (trimmed.startsWith("<") || trimmed.startsWith("<!")) {
    if (trimmed.includes("Just a moment") || trimmed.includes("cf-chl") || trimmed.includes("cloudflare")) {
      throw new Error("Cruisers Wiki bloque les requêtes serveur (Cloudflare). Lancez FlareSolverr (docker run -p 8191:8191 ghcr.io/flaresolverr/flaresolverr) ou ajoutez SCRAPE_DO_API_KEY dans .env.");
    }
    throw new Error(`Cruisers Wiki a renvoyé du HTML au lieu de JSON (${status})`);
  }
  let data: any;
  try {
    data = JSON.parse(text);
  } catch (e) {
    throw new Error(`Cruisers Wiki: réponse invalide (${text.slice(0, 100)}...)`);
  }
  if (status !== 200 || data?.error) {
    const errMsg = data?.error?.info ?? data?.error?.code ?? data?.message ?? text.slice(0, 150);
    const statusCode = status || 400;
    if (statusCode === 403) {
      const proxyBase = getCruisersWikiProxyBase();
      throw new Error(proxyBase
        ? `Proxy 403: ${errMsg} (vérifiez CRUISERSWIKI_PROXY_URL dans .env)`
        : "Cruisers Wiki 403 (Cloudflare). Lancez FlareSolverr ou ajoutez SCRAPE_DO_API_KEY dans .env.");
    }
    throw new Error(`Cruisers Wiki ${statusCode}: ${errMsg}`);
  }
  return data;
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

/** Liste les sous-catégories de Category:Ports (ex: Ports - Greece, Ports - Spain) */
async function fetchCruisersWikiPortSubcategories(): Promise<{ title: string; country: string }[]> {
  console.log("[Nauticals] Cruisers Wiki étape 1/3: liste des sous-catégories (Category:Ports)...");
  const result: { title: string; country: string }[] = [];
  let cmcontinue: string | undefined;
  do {
    const params = new URLSearchParams({
      action: "query",
      list: "categorymembers",
      cmtitle: "Category:Ports",
      cmtype: "subcat",
      cmlimit: "500",
      format: "json",
      origin: "*",
    });
    if (cmcontinue) params.set("cmcontinue", cmcontinue);
    const res = await cruisersWikiFetch(`${CRUISERSWIKI_API}?${params}`, true);
    const data = parseCruisersWikiResponse(res);
    const members = data.query?.categorymembers ?? [];
    for (const m of members) {
      const title = m.title ?? "";
      if (title.startsWith("Category:Ports - ")) {
        const country = title.replace("Category:Ports - ", "").trim();
        result.push({ title, country });
      }
    }
    cmcontinue = data.continue?.cmcontinue;
    if (cmcontinue) await sleep(CRUISERSWIKI_DELAY_MS);
  } while (cmcontinue);
  console.log("[Nauticals] Cruisers Wiki étape 1/3: TinyFish/Playwright a listé", result.length, "sous-catégories (pays)");
  return result;
}

/** Liste les pages d'une catégorie (ex: Vela Luka, Hydra) */
async function fetchCruisersWikiCategoryPages(categoryTitle: string): Promise<string[]> {
  const titles: string[] = [];
  let cmcontinue: string | undefined;
  do {
    const params = new URLSearchParams({
      action: "query",
      list: "categorymembers",
      cmtitle: categoryTitle,
      cmtype: "page",
      cmlimit: "500",
      format: "json",
      origin: "*",
    });
    if (cmcontinue) params.set("cmcontinue", cmcontinue);
    const res = await cruisersWikiFetch(`${CRUISERSWIKI_API}?${params}`, true);
    const data = parseCruisersWikiResponse(res);
    const members = data.query?.categorymembers ?? [];
    for (const m of members) {
      const t = m.title ?? "";
      if (t && !t.startsWith("Category:") && !t.startsWith("Template:")) titles.push(t);
    }
    cmcontinue = data.continue?.cmcontinue;
    if (cmcontinue) await sleep(CRUISERSWIKI_DELAY_MS);
  } while (cmcontinue);
  return titles;
}

/** Récupère le wikitext d'une page */
async function fetchCruisersWikiPageContent(pageTitle: string): Promise<string> {
  const params = new URLSearchParams({
    action: "query",
    titles: pageTitle,
    prop: "revisions",
    rvprop: "content",
    rvslots: "main",
    format: "json",
    origin: "*",
  });
  const res = await cruisersWikiFetch(`${CRUISERSWIKI_API}?${params}`); // pas TinyFish (bulk)
  const data = parseCruisersWikiResponse(res);
  const pages = data.query?.pages ?? {};
  const page = Object.values(pages)[0] as any;
  const content = page?.revisions?.[0]?.slots?.main?.["*"] ?? "";
  return content;
}

// --- Cruisers Wiki via Internet Archive (Wayback Machine) ---
const WAYBACK_CDX_URL = "https://web.archive.org/cdx/search/cdx";
const WAYBACK_BASE = "https://web.archive.org/web";
const WAYBACK_DELAY_MS = 120;
const WAYBACK_CONCURRENCY = 6;
const WAYBACK_USER_AGENT = "BlueIntelligence/1.0 (OSINT maritime; +https://github.com/blue-intelligence)";

const CDX_RETRIES = 3;
const CDX_CACHE_TTL_MS = 7 * 24 * 60 * 60 * 1000;

/** Lit le cache CDX si valide (TTL 7 jours). Retourne la dernière capture par URL (pour le fetch HTML). */
function getCachedCdxUrls(): { url: string; timestamp: string }[] | null {
  const row = db.prepare("SELECT cached_at FROM wayback_cdx_raw LIMIT 1").get() as { cached_at: string } | undefined;
  if (!row) return null;
  const cachedAt = new Date(row.cached_at).getTime();
  if (Date.now() - cachedAt > CDX_CACHE_TTL_MS) return null;
  const rows = db.prepare(
    "SELECT url, max(timestamp) as timestamp FROM wayback_cdx_raw GROUP BY url"
  ).all() as { url: string; timestamp: string }[];
  return rows.length > 0 ? rows : null;
}

/** Vide wayback_cdx_raw, wayback_cdx_cache et wayback_best_captures (avant refetch). */
function clearCdxCache(): void {
  db.prepare("DELETE FROM wayback_cdx_raw").run();
  db.prepare("DELETE FROM wayback_cdx_cache").run();
  db.prepare("DELETE FROM wayback_best_captures").run();
  clearCdxPerUrlCheckpoint();
}

/** Enregistre des captures dans wayback_cdx_raw (historique complet). Incrémental, ne supprime pas. */
function saveCdxRaw(entries: { url: string; timestamp: string; digest?: string }[]): void {
  if (entries.length === 0) return;
  const now = new Date().toISOString();
  const insert = db.prepare("INSERT OR REPLACE INTO wayback_cdx_raw (url, timestamp, digest, cached_at) VALUES (?, ?, ?, ?)");
  db.transaction(() => {
    for (const e of entries) insert.run(e.url, e.timestamp, e.digest ?? null, now);
  })();
}

/** Met à jour wayback_cdx_cache avec la dernière capture par URL (pour compat / affichage rapide). */
function saveCdxCache(entries: { url: string; timestamp: string }[]): void {
  const now = new Date().toISOString();
  const insert = db.prepare("INSERT OR REPLACE INTO wayback_cdx_cache (url, timestamp, cached_at) VALUES (?, ?, ?)");
  db.transaction(() => {
    db.prepare("DELETE FROM wayback_cdx_cache").run();
    for (const e of entries) insert.run(e.url, e.timestamp, now);
  })();
}

const CDX_PAGE_SIZE = 1000;
const CDX_PAGE_TIMEOUT_MS = 90000; // 90s (était 45s) pour pages lentes

/** URL CDX à requêter (direct ou via proxy si archive.org inaccessible). CDX_NO_PROXY=1 pour forcer direct. */
function getCdxFetchUrl(params: URLSearchParams): string {
  const cdxUrl = `${WAYBACK_CDX_URL}?${params}`;
  if (process.env.CDX_NO_PROXY === "1" || process.env.CDX_NO_PROXY === "true") return cdxUrl;
  const proxyBase = getCruisersWikiProxyBase();
  if (proxyBase) return `${proxyBase}${encodeURIComponent(cdxUrl)}`;
  return cdxUrl;
}

/** collapse CDX : digest = une capture par changement de contenu ; timestamp:6 = une capture par mois ; timestamp:8 = une capture par jour. */
const CDX_COLLAPSE = process.env.CDX_COLLAPSE || "timestamp:6";

/** Collapse pour inventaire d’URLs wildcard (per-URL) : urlkey ≈ une ligne par URL dans la plage. Voir CRUISERSWIKI_URL_SOURCE. */
const CDX_WILDCARD_COLLAPSE = process.env.CDX_WILDCARD_COLLAPSE?.trim() || "urlkey";

/** Parse corps JSON CDX (tableau de lignes avec en-têtes). Filtre pages wiki ports (hors Special/Category). */
function parseCdxJsonRows(data: unknown): { url: string; timestamp: string; digest?: string }[] {
  if (!Array.isArray(data) || data.length < 2) return [];
  const headers = data[0] as string[];
  const idxTs = headers.indexOf("timestamp");
  const idxOrig = headers.indexOf("original");
  const idxDig = headers.indexOf("digest");
  if (idxTs < 0 || idxOrig < 0) return [];
  const out: { url: string; timestamp: string; digest?: string }[] = [];
  for (let i = 1; i < data.length; i++) {
    const row = data[i] as string[];
    const u = row[idxOrig];
    const ts = row[idxTs];
    const digest = idxDig >= 0 ? row[idxDig] || undefined : undefined;
    if (u && ts && u.includes("/wiki/") && !u.includes("Special:") && !u.includes("Category:")) {
      out.push({ url: u, timestamp: ts, digest });
    }
  }
  return out;
}

function getCdxMode(): "bulk" | "per_url" {
  const m = (process.env.CDX_MODE || "bulk").toLowerCase().trim();
  return m === "per_url" ? "per_url" : "bulk";
}

/** Année CDX_FROM_YEAR ou défaut selon le mode (bulk: 2005, per_url: 2019). */
function getCdxFromYear(mode: "bulk" | "per_url"): number {
  const def = mode === "per_url" ? 2019 : 2005;
  const v = process.env.CDX_FROM_YEAR?.trim();
  if (v) {
    const n = parseInt(v, 10);
    if (!Number.isNaN(n) && n >= 1996 && n <= 2100) return n;
  }
  return def;
}

/** Mode per-URL : d’où vient la liste des pages — CDX wildcard (sans site live), MediaWiki, ou auto (CDX puis repli). */
function getCruisersWikiUrlSource(): "auto" | "cdx" | "mediawiki" {
  const v = (process.env.CRUISERSWIKI_URL_SOURCE || "auto").toLowerCase().trim();
  if (v === "mediawiki" || v === "mw") return "mediawiki";
  if (v === "cdx") return "cdx";
  return "auto";
}

/** Années pour parcourir le CDX wildcard lors de la découverte d’URLs (indépendant de CDX_FROM_YEAR pour les captures par URL). */
function getCdxUrlDiscoveryFromYear(): number {
  const v = process.env.CRUISERSWIKI_CDX_URL_FROM_YEAR?.trim();
  if (v) {
    const n = parseInt(v, 10);
    if (!Number.isNaN(n) && n >= 1996 && n <= 2100) return n;
  }
  return getCdxFromYear("per_url");
}

function getCdxUrlDiscoveryToYear(): number {
  const v = process.env.CRUISERSWIKI_CDX_URL_TO_YEAR?.trim();
  if (v) {
    const n = parseInt(v, 10);
    if (!Number.isNaN(n) && n >= 1996 && n <= 2100) return n;
  }
  return new Date().getFullYear();
}

const CDX_PER_URL_CHECKPOINT = path.join(DATA_DIR, "cdx_per_url_checkpoint.json");

function readCdxPerUrlCheckpoint(): { lastCompletedIndex: number } | null {
  try {
    const raw = fs.readFileSync(CDX_PER_URL_CHECKPOINT, "utf8");
    const j = JSON.parse(raw) as { lastCompletedIndex?: number };
    if (typeof j.lastCompletedIndex === "number" && j.lastCompletedIndex >= -1) return { lastCompletedIndex: j.lastCompletedIndex };
  } catch (_) {}
  return null;
}

function writeCdxPerUrlCheckpoint(lastCompletedIndex: number, total: number): void {
  try {
    fs.mkdirSync(path.dirname(CDX_PER_URL_CHECKPOINT), { recursive: true });
    fs.writeFileSync(
      CDX_PER_URL_CHECKPOINT,
      JSON.stringify({ lastCompletedIndex, total, updatedAt: new Date().toISOString() })
    );
  } catch (e) {
    console.warn("[Nauticals] CDX per-URL checkpoint write failed:", (e as Error)?.message);
  }
}

function clearCdxPerUrlCheckpoint(): void {
  try {
    if (fs.existsSync(CDX_PER_URL_CHECKPOINT)) fs.unlinkSync(CDX_PER_URL_CHECKPOINT);
  } catch (_) {}
}

/** Fetch une tranche CDX par plage de dates (from/to). collapse configurable via CDX_COLLAPSE. Ordre par défaut = chronologique (ancien→récent). */
async function fetchCdxPageByDateRange(from: string, to: string, offset: number): Promise<{ url: string; timestamp: string; digest?: string }[]> {
  const params = new URLSearchParams({
    url: "cruiserswiki.org/wiki/*",
    output: "json",
    filter: "statuscode:200",
    collapse: CDX_COLLAPSE,
    from,
    to,
    limit: String(CDX_PAGE_SIZE),
    offset: String(offset),
  });
  const fetchUrl = getCdxFetchUrl(params);
  const res = await fetch(fetchUrl, {
    headers: { "User-Agent": WAYBACK_USER_AGENT },
    signal: AbortSignal.timeout(CDX_PAGE_TIMEOUT_MS),
  });
  if (!res.ok) throw new Error(`CDX HTTP ${res.status}`);
  const data = (await res.json()) as unknown;
  return parseCdxJsonRows(data);
}

/** Une page CDX wildcard pour inventaire d’URLs (collapse urlkey ≈ une ligne par URL connue dans la plage). */
async function fetchCdxWildcardPageForUrlDiscovery(
  from: string,
  to: string,
  offset: number
): Promise<{ url: string; timestamp: string; digest?: string }[]> {
  const params = new URLSearchParams({
    url: "cruiserswiki.org/wiki/*",
    output: "json",
    filter: "statuscode:200",
    collapse: CDX_WILDCARD_COLLAPSE,
    from,
    to,
    limit: String(CDX_PAGE_SIZE),
    offset: String(offset),
  });
  const fetchUrl = getCdxFetchUrl(params);
  const res = await fetch(fetchUrl, {
    headers: { "User-Agent": WAYBACK_USER_AGENT },
    signal: AbortSignal.timeout(CDX_PAGE_TIMEOUT_MS),
  });
  if (!res.ok) throw new Error(`CDX HTTP ${res.status}`);
  const data = (await res.json()) as unknown;
  return parseCdxJsonRows(data);
}

/** Liste d’URLs wiki uniques via CDX wildcard (Internet Archive), sans appeler cruiserswiki.org. */
async function fetchWaybackUrlsFromCdxWildcard(): Promise<{ url: string }[]> {
  const fromY = getCdxUrlDiscoveryFromYear();
  const toY = getCdxUrlDiscoveryToYear();
  let maxPages = parseInt(process.env.CRUISERSWIKI_CDX_URL_MAX_PAGES || "5000", 10);
  if (Number.isNaN(maxPages) || maxPages <= 0) maxPages = 5000;
  const seen = new Set<string>();
  const out: { url: string }[] = [];
  console.log(
    "[Nauticals] Cruisers Wiki: liste d’URLs via CDX wildcard (collapse",
    CDX_WILDCARD_COLLAPSE + "), années",
    fromY,
    "→",
    toY,
    `(max ${maxPages} requêtes paginées)`
  );
  let totalPagesFetched = 0;
  for (let y = fromY; y <= toY; y++) {
    const from = String(y);
    const to = String(y);
    let offset = 0;
    while (true) {
      if (totalPagesFetched >= maxPages) {
        console.warn("[Nauticals] CDX wildcard: arrêt (CRUISERSWIKI_CDX_URL_MAX_PAGES=", maxPages, ")");
        break;
      }
      let rows: { url: string; timestamp: string; digest?: string }[];
      try {
        rows = await fetchCdxWildcardPageForUrlDiscovery(from, to, offset);
      } catch (e: any) {
        console.warn("[Nauticals] CDX wildcard année", y, "offset", offset, e?.message || e);
        break;
      }
      totalPagesFetched++;
      if (rows.length === 0) break;
      for (const r of rows) {
        if (!seen.has(r.url)) {
          seen.add(r.url);
          out.push({ url: r.url });
        }
      }
      if (rows.length < CDX_PAGE_SIZE) break;
      offset += CDX_PAGE_SIZE;
      await new Promise((r) => setTimeout(r, 600));
    }
    if (totalPagesFetched >= maxPages) break;
  }
  console.log("[Nauticals] CDX wildcard:", out.length, "URLs uniques,", totalPagesFetched, "requêtes CDX");
  return out;
}

/**
 * CDX pour une URL exacte : jusqu'à `limit` captures entre from et to (années ou YYYYMMDDhhmmss).
 * Sans sort=reverse côté API (souvent lent), on demande plus de lignes puis on trie par timestamp décroissant.
 */
async function fetchCdxCapturesForUrl(
  originalUrl: string,
  opts: { from: string; to: string; limit: number }
): Promise<{ url: string; timestamp: string; digest?: string }[]> {
  const useSortReverse = process.env.CDX_PER_URL_SORT_REVERSE === "1" || process.env.CDX_PER_URL_SORT_REVERSE === "true";
  const requestLimit = useSortReverse
    ? opts.limit
    : Math.min(300, Math.max(opts.limit * 25, Math.max(48, opts.limit)));
  const params = new URLSearchParams({
    url: originalUrl,
    output: "json",
    filter: "statuscode:200",
    from: opts.from,
    to: opts.to,
    limit: String(requestLimit),
  });
  const perUrlCollapse = process.env.CDX_PER_URL_COLLAPSE?.trim();
  if (perUrlCollapse && perUrlCollapse !== "none") params.set("collapse", perUrlCollapse);
  if (useSortReverse) params.set("sort", "reverse");

  const fetchUrl = getCdxFetchUrl(params);
  for (let attempt = 1; attempt <= CDX_RETRIES; attempt++) {
    try {
      const res = await fetch(fetchUrl, {
        headers: { "User-Agent": WAYBACK_USER_AGENT },
        signal: AbortSignal.timeout(CDX_PAGE_TIMEOUT_MS),
      });
      if (!res.ok) throw new Error(`CDX HTTP ${res.status}`);
      const data = (await res.json()) as unknown;
      let rows = parseCdxJsonRows(data);
      if (!useSortReverse) rows.sort((a, b) => b.timestamp.localeCompare(a.timestamp));
      const seen = new Set<string>();
      const deduped: { url: string; timestamp: string; digest?: string }[] = [];
      for (const r of rows) {
        if (seen.has(r.timestamp)) continue;
        seen.add(r.timestamp);
        deduped.push(r);
        if (deduped.length >= opts.limit) break;
      }
      return deduped;
    } catch (e) {
      if (attempt === CDX_RETRIES) throw e;
      await new Promise((r) => setTimeout(r, 5000 * attempt));
    }
  }
  return [];
}

/** Génère les tranches from/to : CDX_FROM_YEAR (bulk, défaut 2005) → année courante. Ordre chronologique (ancien → récent). */
function* getCdxDateRanges(): Generator<{ from: string; to: string; label: string }> {
  const now = new Date();
  const currentYear = now.getFullYear();
  const currentMonth = now.getMonth() + 1; // 1-12
  const startYear = getCdxFromYear("bulk");

  // Années passées : startYear → année courante - 1 (ordre chronologique)
  for (let y = startYear; y < currentYear; y++) {
    yield { from: String(y), to: String(y), label: String(y) };
  }
  // Année courante : par mois
  for (let m = 1; m <= currentMonth; m++) {
    const mm = String(m).padStart(2, "0");
    yield { from: `${currentYear}${mm}`, to: `${currentYear}${mm}`, label: `${currentYear}-${mm}` };
  }
}

/** Retourne la dernière capture par URL depuis wayback_cdx_raw (pour merge après resume). */
function getCdxUrlsFromRaw(): { url: string; timestamp: string }[] {
  const rows = db
    .prepare("SELECT url, max(timestamp) as timestamp FROM wayback_cdx_raw GROUP BY url")
    .all() as { url: string; timestamp: string }[];
  return rows;
}

/**
 * CDX mode per-URL : une requête CDX par page (liste des URLs via CDX wildcard et/ou MediaWiki selon CRUISERSWIKI_URL_SOURCE),
 * puis limit captures par URL (défaut 12), from/to années.
 * Checkpoint : data/cdx_per_url_checkpoint.json (effacé avec clearCdxCache).
 */
async function fetchWaybackCdxUrlsPerUrl(options?: {
  clearFirst?: boolean;
  resumeCdxPerUrlIndex?: number;
  cdxFromYear?: number;
  cdxPerUrlLimit?: number;
}): Promise<{ url: string; timestamp: string }[]> {
  if (options?.clearFirst) {
    clearCdxCache();
    console.log("[Nauticals] Cruisers Wiki Wayback CDX (per-URL): cache vidé");
  }

  const fromYear = options?.cdxFromYear ?? getCdxFromYear("per_url");
  const toYear = new Date().getFullYear();
  const from = String(fromYear);
  const to = String(toYear);
  const limit = options?.cdxPerUrlLimit ?? parseInt(process.env.CDX_PER_URL_LIMIT || "12", 10);
  const delayMs = Math.max(0, parseInt(process.env.CDX_PER_URL_DELAY_MS || "500", 10));
  const concurrency = Math.max(1, Math.min(8, parseInt(process.env.CDX_PER_URL_CONCURRENCY || "2", 10)));

  let startIndex = 0;
  if (typeof options?.resumeCdxPerUrlIndex === "number" && options.resumeCdxPerUrlIndex >= 0) {
    startIndex = options.resumeCdxPerUrlIndex;
  } else if (!options?.clearFirst) {
    const cp = readCdxPerUrlCheckpoint();
    if (cp && cp.lastCompletedIndex >= 0) startIndex = cp.lastCompletedIndex + 1;
  }

  const useProxy = !(process.env.CDX_NO_PROXY === "1" || process.env.CDX_NO_PROXY === "true") && !!getCruisersWikiProxyBase();
  if (process.env.CDX_NO_PROXY === "1" || process.env.CDX_NO_PROXY === "true") {
    console.log("[Nauticals] Cruisers Wiki Wayback CDX (per-URL): proxy désactivé (CDX_NO_PROXY)");
  } else if (useProxy) {
    console.log("[Nauticals] Cruisers Wiki Wayback CDX (per-URL): proxy activé");
  }

  console.log(
    "[Nauticals] Cruisers Wiki Wayback CDX (per-URL): liste des URLs… from=",
    from,
    "to=",
    to,
    "captures/URL≤",
    limit,
    "startIndex=",
    startIndex,
    "source=",
    getCruisersWikiUrlSource()
  );

  const urlRows = await fetchWaybackUrlsForPerUrlDiscovery();
  if (urlRows.length === 0) {
    throw new Error("CDX per-URL: aucune URL dans la liste (CDX wildcard + repli MediaWiki si auto)");
  }

  if (startIndex >= urlRows.length) {
    console.log("[Nauticals] Cruisers Wiki Wayback CDX (per-URL): startIndex ≥ total, rien à faire");
    const deduplicated = getCdxUrlsFromRaw();
    saveCdxCache(deduplicated);
    return deduplicated;
  }

  let totalRows = 0;
  for (let i = startIndex; i < urlRows.length; i += concurrency) {
    const batch = urlRows.slice(i, Math.min(i + concurrency, urlRows.length));
    const results = await Promise.all(
      batch.map(async ({ url }, j) => {
        const idx = i + j;
        try {
          const rows = await fetchCdxCapturesForUrl(url, { from, to, limit });
          if (rows.length > 0) saveCdxRaw(rows);
          totalRows += rows.length;
          if ((idx + 1) % 50 === 0 || idx + 1 === urlRows.length) {
            console.log(
              "[Nauticals] Cruisers Wiki Wayback CDX (per-URL):",
              idx + 1,
              "/",
              urlRows.length,
              "URLs,",
              totalRows,
              "lignes CDX brutes"
            );
          }
          return idx;
        } catch (e: any) {
          console.warn("[Nauticals] CDX per-URL skip", url.slice(0, 60), e?.message || e);
          return idx;
        }
      })
    );
    const lastDone = Math.max(...results);
    writeCdxPerUrlCheckpoint(lastDone, urlRows.length);
    if (i + concurrency < urlRows.length && delayMs > 0) await new Promise((r) => setTimeout(r, delayMs));
  }

  const deduplicated = getCdxUrlsFromRaw();
  saveCdxCache(deduplicated);
  console.log(
    "[Nauticals] Cruisers Wiki Wayback CDX (per-URL): terminé,",
    totalRows,
    "lignes insérées cette passe,",
    deduplicated.length,
    "URLs uniques"
  );
  return deduplicated;
}

type FetchWaybackCdxUrlOptions = {
  clearFirst?: boolean;
  resumeCdxFrom?: { from: string; to: string; offset: number };
  resumeCdxPerUrlIndex?: number;
  cdxMode?: "bulk" | "per_url";
  cdxFromYear?: number;
  cdxPerUrlLimit?: number;
};

/** Liste les URLs Cruisers Wiki archivées. Historique complet (pas de déduplication). Sauvegarde tout dans wayback_cdx_raw. Retourne la dernière capture par URL pour le fetch HTML. */
async function fetchWaybackCdxUrls(options?: FetchWaybackCdxUrlOptions): Promise<{ url: string; timestamp: string }[]> {
  const mode = options?.cdxMode ?? getCdxMode();
  if (mode === "per_url") {
    return fetchWaybackCdxUrlsPerUrl({
      clearFirst: options?.clearFirst,
      resumeCdxPerUrlIndex: options?.resumeCdxPerUrlIndex,
      cdxFromYear: options?.cdxFromYear,
      cdxPerUrlLimit: options?.cdxPerUrlLimit,
    });
  }

  const resume = options?.resumeCdxFrom;
  if (!resume) {
    if (options?.clearFirst) {
      clearCdxCache();
      console.log("[Nauticals] Cruisers Wiki Wayback CDX: cache vidé");
    }
  } else {
    console.log("[Nauticals] Cruisers Wiki Wayback CDX: reprise depuis", resume.from, "-", resume.to, "offset", resume.offset);
  }
  const useProxy = !(process.env.CDX_NO_PROXY === "1" || process.env.CDX_NO_PROXY === "true") && !!getCruisersWikiProxyBase();
  if (process.env.CDX_NO_PROXY === "1" || process.env.CDX_NO_PROXY === "true") {
    console.log("[Nauticals] Cruisers Wiki Wayback CDX: proxy désactivé (CDX_NO_PROXY)");
  } else if (useProxy) {
    console.log("[Nauticals] Cruisers Wiki Wayback CDX: proxy activé");
  }

  const urlToLatest = new Map<string, string>();
  let totalCaptures = 0;
  let foundResumeRange = false;

  for (const { from, to, label } of getCdxDateRanges()) {
    if (resume && !foundResumeRange) {
      if (from !== resume.from || to !== resume.to) continue;
      foundResumeRange = true;
    }
    let offset = resume && from === resume.from && to === resume.to ? resume.offset : 0;
    let page = offset > 0 ? Math.floor(offset / CDX_PAGE_SIZE) : 0;
    let hasMore = true;
    while (hasMore) {
      page++;
      for (let attempt = 1; attempt <= CDX_RETRIES; attempt++) {
        try {
          const entries = await fetchCdxPageByDateRange(from, to, offset);
          for (const e of entries) {
            totalCaptures++;
            const existing = urlToLatest.get(e.url);
            if (!existing || e.timestamp > existing) urlToLatest.set(e.url, e.timestamp);
          }
          if (entries.length > 0) {
            saveCdxRaw(entries);
            if (page === 1 || page % 2 === 0) {
              console.log("[Nauticals] Cruisers Wiki Wayback CDX:", label, "page", page, ", captures", totalCaptures, ", URLs uniques", urlToLatest.size);
            }
          }
          if (entries.length < CDX_PAGE_SIZE) hasMore = false;
          else offset += CDX_PAGE_SIZE;
          await new Promise((r) => setTimeout(r, 600));
          break;
        } catch (e) {
          if (attempt === CDX_RETRIES) {
            console.warn("[Nauticals] Cruisers Wiki Wayback CDX:", label, "page", page, "timeout après", CDX_RETRIES, "retries → skip page, offset", offset, "→", offset + CDX_PAGE_SIZE);
            offset += CDX_PAGE_SIZE;
            break;
          }
          console.log("[Nauticals] Cruisers Wiki Wayback CDX", label, "page", page, "timeout, retry", attempt, "/", CDX_RETRIES);
          await new Promise((r) => setTimeout(r, 5000 * attempt));
        }
      }
    }
  }

  const deduplicated = resume ? getCdxUrlsFromRaw() : Array.from(urlToLatest.entries()).map(([url, timestamp]) => ({ url, timestamp }));
  saveCdxCache(deduplicated);
  console.log("[Nauticals] Cruisers Wiki Wayback CDX: terminé,", totalCaptures, "captures en base,", deduplicated.length, "URLs uniques pour fetch HTML");
  return deduplicated;
}

/** Détecte une page Cloudflare (challenge, vérification navigateur). */
function isCloudflarePage(html: string): boolean {
  const lower = html.toLowerCase();
  return (
    lower.includes("checking your browser") ||
    lower.includes("just a moment") ||
    lower.includes("cf_chl_rt_tk") ||
    lower.includes("cf-browser-verification") ||
    (lower.includes("cloudflare") && lower.includes("ray id")) ||
    /access denied|ddos protection/i.test(lower)
  );
}

/** Vérifie si le HTML contient du vrai contenu wiki MediaWiki. */
function isValidWikiContent(html: string): boolean {
  if (!html || html.length < 200) return false;
  if (isCloudflarePage(html)) return false;
  const lower = html.toLowerCase();
  return (
    lower.includes("mw-content-text") ||
    lower.includes("mw-parser-output") ||
    lower.includes("firstheading") ||
    lower.includes("first_heading") ||
    lower.includes("{{coord") ||
    lower.includes("mediawiki")
  );
}

/** Retourne les timestamps pour une URL, du plus récent au plus ancien. */
function getCdxTimestampsForUrl(url: string): string[] {
  const rows = db
    .prepare("SELECT timestamp FROM wayback_cdx_raw WHERE url = ? ORDER BY timestamp DESC")
    .all(url) as { timestamp: string }[];
  return rows.map((r) => r.timestamp);
}

/** Retourne les timestamps pour une URL en essayant les variantes http/https, www. Déduplique et trie du plus récent au plus ancien. */
function getCdxTimestampsForUrlVariants(url: string): string[] {
  const variants = [
    url,
    url.replace(/^https:\/\//, "http://"),
    url.replace(/^https:\/\/www\./, "https://"),
    url.replace(/^http:\/\//, "https://"),
  ].filter((v, i, arr) => arr.indexOf(v) === i);
  if (variants.length === 0) return [];
  const placeholders = variants.map(() => "?").join(", ");
  const rows = db
    .prepare(`SELECT DISTINCT timestamp FROM wayback_cdx_raw WHERE url IN (${placeholders}) ORDER BY timestamp DESC`)
    .all(...variants) as { timestamp: string }[];
  return rows.map((r) => r.timestamp);
}

/** Extrait les coordonnées du HTML (meta geo, spans latitude/longitude, ou {{coord}} dans le source). */
function parseCoordFromHtml(html: string): { lat: number; lng: number } | null {
  const dom = new JSDOM(html);
  const doc = dom.window.document;
  const metaGeo = doc.querySelector('meta[name="geo.position"]');
  if (metaGeo) {
    const c = (metaGeo.getAttribute("content") || "").split(/[;,]/).map((s) => parseFloat(s.trim()));
    if (c.length >= 2 && !isNaN(c[0]) && !isNaN(c[1]) && Math.abs(c[0]) <= 90 && Math.abs(c[1]) <= 180) {
      return { lat: c[0], lng: c[1] };
    }
  }
  const metaIcbm = doc.querySelector('meta[name="ICBM"]');
  if (metaIcbm) {
    const c = (metaIcbm.getAttribute("content") || "").split(",").map((s) => parseFloat(s.trim()));
    if (c.length >= 2 && !isNaN(c[0]) && !isNaN(c[1]) && Math.abs(c[0]) <= 90 && Math.abs(c[1]) <= 180) {
      return { lat: c[0], lng: c[1] };
    }
  }
  const latSpan = doc.querySelector(".latitude");
  const lngSpan = doc.querySelector(".longitude");
  if (latSpan && lngSpan) {
    const lat = parseFloat(latSpan.textContent?.trim() || "");
    const lng = parseFloat(lngSpan.textContent?.trim() || "");
    if (!isNaN(lat) && !isNaN(lng) && Math.abs(lat) <= 90 && Math.abs(lng) <= 180) return { lat, lng };
  }
  const coord = parseCoordFromWikitext(html);
  if (coord) return coord;
  const degRe = /(\d+)[°º]\s*(\d+)[′']?\s*([NS])\s*(\d+)[°º]\s*(\d+)[′']?\s*([EW])/i;
  const m = html.match(degRe);
  if (m) {
    const degLat = parseFloat(m[1]) || 0;
    const minLat = parseFloat(m[2]) || 0;
    const ns = (m[3] || "").toUpperCase();
    const degLng = parseFloat(m[4]) || 0;
    const minLng = parseFloat(m[5]) || 0;
    const ew = (m[6] || "").toUpperCase();
    let lat = degLat + minLat / 60;
    let lng = degLng + minLng / 60;
    if (ns === "S") lat = -lat;
    if (ew === "W") lng = -lng;
    if (Math.abs(lat) <= 90 && Math.abs(lng) <= 180) return { lat, lng };
  }
  return null;
}

/** Extrait titre, description, caution du HTML MediaWiki. */
function parseWaybackHtmlContent(html: string): { title: string; description: string | null; caution: string | null } {
  const dom = new JSDOM(html);
  const doc = dom.window.document;
  const titleEl = doc.querySelector("#firstHeading") || doc.querySelector("h1") || doc.querySelector("title");
  const title = (titleEl?.textContent || "").replace(/\s*[-|].*$/, "").trim() || "Unknown";
  const content = doc.querySelector("#mw-content-text") || doc.querySelector(".mw-parser-output") || doc.body;
  const text = content?.textContent || "";
  const sectionRe = /(?:^|\n)\s*={2,}\s*(.+?)\s*={2,}\s*(?:\n|$)/g;
  const wanted = ["navigation", "entrance", "anchorages", "approach", "dangers", "warnings", "charts"];
  const sections: string[] = [];
  let caution: string | null = null;
  let m: RegExpExecArray | null;
  let lastEnd = 0;
  const blocks: { name: string; text: string }[] = [];
  while ((m = sectionRe.exec(text)) !== null) {
    if (blocks.length > 0) blocks[blocks.length - 1].text = text.slice(lastEnd, m.index).trim();
    blocks.push({ name: m[1].trim(), text: "" });
    lastEnd = m.index + m[0].length;
  }
  if (blocks.length > 0) blocks[blocks.length - 1].text = text.slice(lastEnd).trim();
  for (const b of blocks) {
    const n = b.name.toLowerCase();
    let t = b.text.replace(/\s+/g, " ").trim();
    if (t.length > 500) t = t.slice(0, 500) + "...";
    if (n.includes("danger") || n.includes("warning")) caution = t || caution;
    else if (wanted.some((w) => n.includes(w)) && t) sections.push(`${b.name}: ${t}`);
  }
  return {
    title,
    description: sections.length > 0 ? sections.join("\n\n") : null,
    caution: caution || null,
  };
}

const WAYBACK_FETCH_TIMEOUT_MS = 12000;

/** URL de fetch (direct ou via proxy). */
function getWaybackFetchUrl(url: string): string {
  const proxyBase = getCruisersWikiProxyBase();
  if (proxyBase) return `${proxyBase}${encodeURIComponent(url)}`;
  return url;
}

/** Récupère le HTML d'une capture Wayback. 1 retry sur échec réseau uniquement (pas sur contenu court). */
async function fetchWaybackHtml(url: string, timestamp: string): Promise<string | null> {
  const waybackUrl = `${WAYBACK_BASE}/${timestamp}/${url}`;
  const fetchUrl = getWaybackFetchUrl(waybackUrl);
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const res = await fetch(fetchUrl, {
        headers: { "User-Agent": WAYBACK_USER_AGENT },
        signal: AbortSignal.timeout(WAYBACK_FETCH_TIMEOUT_MS),
      });
      if (!res.ok) return null;
      return await res.text();
    } catch {
      if (attempt === 0) await new Promise((r) => setTimeout(r, 800));
    }
  }
  return null;
}

/** Récupère le HTML d'une capture Wayback avec validation. Si Cloudflare, essaie les captures plus anciennes jusqu'à trouver du contenu wiki valide. */
async function fetchWaybackHtmlWithValidation(
  url: string,
  initialTimestamp: string
): Promise<{ html: string; timestamp: string } | null> {
  const timestamps = getCdxTimestampsForUrl(url);
  const startIdx = timestamps.indexOf(initialTimestamp);
  const toTry = startIdx >= 0 ? timestamps.slice(startIdx) : [initialTimestamp, ...timestamps];
  for (const ts of toTry) {
    const html = await fetchWaybackHtml(url, ts);
    if (!html) continue;
    if (isValidWikiContent(html)) return { html, timestamp: ts };
    if (isCloudflarePage(html)) {
      if (process.env.DEBUG_WAYBACK) console.log("[Wayback] Cloudflare détecté pour", url, "ts", ts, "→ capture précédente");
      continue;
    }
    continue;
  }
  return null;
}

/** Extrait le wikitext de la page action=edit MediaWiki (textarea#wpTextbox1). Décode les entités HTML. */
function extractWikitextFromEditPage(html: string): string | null {
  const m = html.match(/<textarea[^>]*id="wpTextbox1"[^>]*>([\s\S]*?)<\/textarea>/i);
  if (!m) return null;
  let text = m[1]
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'");
  return text;
}

/** Récupère la dernière archive valable (wikitext) d'une page via Wayback. Essaie les timestamps du plus récent au plus ancien jusqu'à trouver du contenu valide (pas Cloudflare). Si saveToBestCaptures, enregistre dans wayback_best_captures. */
async function fetchWaybackWikitextForPage(sourceUrl: string, saveToBestCaptures = false): Promise<string | null> {
  const timestamps = getCdxTimestampsForUrlVariants(sourceUrl);
  const editUrl = sourceUrl.includes("?") ? `${sourceUrl}&action=edit` : `${sourceUrl}?action=edit`;
  for (const ts of timestamps) {
    const html = await fetchWaybackHtml(editUrl, ts);
    if (!html) continue;
    if (isCloudflarePage(html)) {
      if (process.env.DEBUG_WAYBACK) console.log("[Wayback] Cloudflare détecté pour", sourceUrl, "ts", ts, "→ capture précédente");
      continue;
    }
    const wikitext = extractWikitextFromEditPage(html);
    if (wikitext && wikitext.length > 100) {
      if (saveToBestCaptures) {
        const waybackUrl = `${WAYBACK_BASE}/${ts}/${sourceUrl}`;
        const now = new Date().toISOString();
        db.prepare(
          `INSERT OR REPLACE INTO wayback_best_captures (url, timestamp, wayback_url, content_type, content, fetched_at) VALUES (?, ?, ?, 'wikitext', ?, ?)`
        ).run(sourceUrl, ts, waybackUrl, wikitext, now);
      }
      return wikitext;
    }
  }
  return null;
}

/** Étapes 1+2 : pour chaque URL, trouve la dernière archive valable et stocke le wikitext dans wayback_best_captures. */
async function populateWaybackBestCaptures(entries: { url: string; timestamp?: string }[]): Promise<number> {
  const insertStmt = db.prepare(
    `INSERT OR REPLACE INTO wayback_best_captures (url, timestamp, wayback_url, content_type, content, fetched_at) VALUES (?, ?, ?, 'wikitext', ?, ?)`
  );
  const total = entries.length;
  let filled = 0;
  for (let i = 0; i < entries.length; i += WAYBACK_CONCURRENCY) {
    const batch = entries.slice(i, i + WAYBACK_CONCURRENCY);
    const results = await Promise.all(
      batch.map(async ({ url }) => {
        const sourceUrl = url.startsWith("http") ? url : `https://${url}`;
        const timestamps = getCdxTimestampsForUrlVariants(sourceUrl);
        const editUrl = sourceUrl.includes("?") ? `${sourceUrl}&action=edit` : `${sourceUrl}?action=edit`;
        for (const ts of timestamps) {
          const html = await fetchWaybackHtml(editUrl, ts);
          if (!html) continue;
          if (isCloudflarePage(html)) continue;
          const wikitext = extractWikitextFromEditPage(html);
          if (wikitext && wikitext.length > 100) {
            const waybackUrl = `${WAYBACK_BASE}/${ts}/${sourceUrl}`;
            const now = new Date().toISOString();
            insertStmt.run(sourceUrl, ts, waybackUrl, wikitext, now);
            return true;
          }
        }
        return false;
      })
    );
    filled += results.filter(Boolean).length;
    if ((i + batch.length) % 100 === 0 || i + batch.length >= total) {
      console.log("[Nauticals] Cruisers Wiki Wayback best captures:", Math.min(i + batch.length, total), "/", total, ", remplis:", filled);
    }
    if (i + WAYBACK_CONCURRENCY < total) await new Promise((r) => setTimeout(r, WAYBACK_DELAY_MS));
  }
  return filled;
}

/** Étape 3 : lit wayback_best_captures, applique le pack d'extraction, retourne NauticalInsertWayback[]. */
function nauticalsFromBestCaptures(): NauticalInsertWayback[] {
  const pack = getMemoizedExtractionPack();
  const rows = db
    .prepare("SELECT url, timestamp, wayback_url, content FROM wayback_best_captures")
    .all() as { url: string; timestamp: string; wayback_url: string; content: string }[];
  const items: NauticalInsertWayback[] = [];
  for (const row of rows) {
    const sourceUrl = row.url.startsWith("http") ? row.url : `https://${row.url}`;
    const applied = applyExtractionPack(row.content, { sourceUrl }, pack);
    if (!applied.include) continue;
    const slug = row.url.replace(/^https?:\/\/[^/]+\/wiki\//, "").replace(/\s+/g, "_");
    const title = decodeURIComponent(slug.replace(/_/g, " "));
    items.push({
      source: "cruiserswiki_wayback",
      source_id: `wayback_${slug}`,
      title,
      description: applied.description,
      caution: applied.caution,
      lat: applied.lat,
      lng: applied.lng,
      zone_ref: null,
      country: "Unknown",
      objtype: "port",
      source_url: sourceUrl,
      wayback_timestamp: row.timestamp,
      wayback_url: row.wayback_url,
    });
  }
  return items;
}

/** Récupère le HTML depuis Wayback via l'URL "closest" (*). Pas besoin de CDX. Retourne { html, timestamp } ou null. */
async function fetchWaybackHtmlClosest(originalUrl: string): Promise<{ html: string; timestamp: string } | null> {
  const waybackUrl = `${WAYBACK_BASE}/*/${originalUrl}`;
  const fetchUrl = getWaybackFetchUrl(waybackUrl);
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const res = await fetch(fetchUrl, {
        headers: { "User-Agent": WAYBACK_USER_AGENT },
        signal: AbortSignal.timeout(WAYBACK_FETCH_TIMEOUT_MS),
        redirect: "follow",
      });
      if (!res.ok) return null;
      const html = await res.text();
      if (!html || html.length < 200) return null;
      const finalUrl = res.url;
      const m = finalUrl.match(/\/web\/(\d{14})\//);
      const timestamp = m ? m[1] : "20240101000000";
      return { html, timestamp };
    } catch {
      if (attempt === 0) await new Promise((r) => setTimeout(r, 800));
    }
  }
  return null;
}

/** Liste les URLs des pages Ports via l'API MediaWiki (fallback quand CDX échoue). Nécessite proxy/FlareSolverr. */
async function fetchWaybackUrlsFromMediaWiki(): Promise<{ url: string }[]> {
  await launchCruisersWikiBrowser();
  const subcats = await fetchCruisersWikiPortSubcategories();
  const urls: { url: string }[] = [];
  for (const { title: catTitle } of subcats) {
    const pageTitles = await fetchCruisersWikiCategoryPages(catTitle);
    for (const pageTitle of pageTitles) {
      const slug = pageTitle.replace(/\s+/g, "_");
      const url = `https://www.cruiserswiki.org/wiki/${encodeURIComponent(slug)}`;
      urls.push({ url });
    }
    await sleep(CRUISERSWIKI_DELAY_MS);
  }
  return urls;
}

/** Liste des pages pour le mode per-URL : CDX wildcard (sans cruiserswiki.org), MediaWiki, ou auto (CDX puis repli). */
async function fetchWaybackUrlsForPerUrlDiscovery(): Promise<{ url: string }[]> {
  const src = getCruisersWikiUrlSource();
  if (src === "mediawiki") {
    console.log("[Nauticals] Liste d'URLs: MediaWiki uniquement (CRUISERSWIKI_URL_SOURCE=mediawiki)");
    return fetchWaybackUrlsFromMediaWiki();
  }
  if (src === "cdx") {
    console.log("[Nauticals] Liste d'URLs: CDX wildcard uniquement (CRUISERSWIKI_URL_SOURCE=cdx)");
    const rows = await fetchWaybackUrlsFromCdxWildcard();
    if (rows.length === 0) {
      throw new Error(
        "CDX wildcard: aucune URL (vérifier CRUISERSWIKI_CDX_URL_FROM_YEAR / TO_YEAR ou CRUISERSWIKI_CDX_URL_MAX_PAGES)"
      );
    }
    return rows;
  }
  try {
    const rows = await fetchWaybackUrlsFromCdxWildcard();
    if (rows.length > 0) {
      console.log("[Nauticals] Liste d'URLs: CDX wildcard OK (", rows.length, "URLs)");
      return rows;
    }
    console.warn("[Nauticals] CDX wildcard: 0 URL, repli MediaWiki…");
  } catch (e: any) {
    console.warn("[Nauticals] CDX wildcard URL list échoué:", e?.message || e);
  }
  console.log("[Nauticals] Repli MediaWiki pour la liste d'URLs…");
  return fetchWaybackUrlsFromMediaWiki();
}

/** Orchestration : CDX (cache ou fetch) → fallback MediaWiki si CDX vide → fetch HTML → parsing → NauticalInsertWayback[]. */
async function fetchWaybackCruisersWikiNauticals(options?: {
  refreshCdx?: boolean;
  resumeCdxFrom?: { from: string; to: string; offset: number };
  resumeCdxPerUrlIndex?: number;
  cdxMode?: "bulk" | "per_url";
  cdxFromYear?: number;
  cdxPerUrlLimit?: number;
}): Promise<NauticalInsertWayback[]> {
  console.log("[Nauticals] Cruisers Wiki Wayback étape 1/3: liste des URLs...");
  const skipCache =
    options?.refreshCdx || options?.resumeCdxFrom || typeof options?.resumeCdxPerUrlIndex === "number";
  let entries: { url: string; timestamp?: string }[] | null = skipCache ? null : getCachedCdxUrls();
  let useMediaWikiFallback = false;

  const clearCdxFirst =
    !!options?.refreshCdx &&
    !options?.resumeCdxFrom &&
    typeof options?.resumeCdxPerUrlIndex !== "number";

  if (entries && entries.length > 0) {
    console.log("[Nauticals] Cruisers Wiki Wayback: cache CDX valide,", entries.length, "URLs");
  } else {
    try {
      entries = await fetchWaybackCdxUrls({
        clearFirst: clearCdxFirst,
        resumeCdxFrom: options?.resumeCdxFrom,
        resumeCdxPerUrlIndex: options?.resumeCdxPerUrlIndex,
        cdxMode: options?.cdxMode,
        cdxFromYear: options?.cdxFromYear,
        cdxPerUrlLimit: options?.cdxPerUrlLimit,
      });
      console.log("[Nauticals] Cruisers Wiki Wayback CDX:", entries.length, "URLs uniques pour fetch HTML");
    } catch (e) {
      console.warn("[Nauticals] Cruisers Wiki Wayback CDX échoué, fallback MediaWiki API...");
      entries = await fetchWaybackUrlsFromMediaWiki();
      useMediaWikiFallback = true;
      console.log("[Nauticals] Cruisers Wiki Wayback (MediaWiki):", entries.length, "URLs");
    }
    if (!entries || entries.length === 0) {
      console.warn("[Nauticals] Cruisers Wiki Wayback CDX vide, fallback MediaWiki API...");
      entries = await fetchWaybackUrlsFromMediaWiki();
      useMediaWikiFallback = true;
      console.log("[Nauticals] Cruisers Wiki Wayback (MediaWiki):", entries.length, "URLs");
    }
    if (!entries || entries.length === 0) {
      throw new Error("Aucune URL Cruisers Wiki (CDX et MediaWiki ont échoué ou retourné 0)");
    }
  }

  let items: NauticalInsertWayback[] = [];
  if (useMediaWikiFallback) {
    const total = entries.length;
    for (let i = 0; i < entries.length; i += WAYBACK_CONCURRENCY) {
      const batch = entries.slice(i, i + WAYBACK_CONCURRENCY);
      const results = await Promise.all(
        batch.map(({ url }) =>
          fetchWaybackHtmlClosest(url).then((r) => {
            if (!r) return { url, timestamp: "", html: null };
            if (isCloudflarePage(r.html)) return { url, timestamp: "", html: null };
            return { url, timestamp: r.timestamp, html: r.html };
          })
        )
      );
      for (const { url, timestamp, html } of results) {
        if (!html || html.length < 200) continue;
        const coord = parseCoordFromHtml(html);
        const { title, description, caution } = parseWaybackHtmlContent(html);
        const slug = url.replace(/^https?:\/\/[^/]+\/wiki\//, "").replace(/\s+/g, "_");
        const waybackUrl = `${WAYBACK_BASE}/${timestamp}/${url}`;
        const sourceUrl = url.startsWith("http") ? url : `https://${url}`;
        items.push({
          source: "cruiserswiki_wayback",
          source_id: `wayback_${slug}`,
          title,
          description,
          caution,
          lat: coord?.lat ?? null,
          lng: coord?.lng ?? null,
          zone_ref: null,
          country: "Unknown",
          objtype: "port",
          source_url: sourceUrl,
          wayback_timestamp: timestamp,
          wayback_url: waybackUrl,
        });
      }
      if ((i + batch.length) % 100 === 0 || i + batch.length >= total) {
        console.log("[Nauticals] Cruisers Wiki Wayback:", Math.min(i + batch.length, total), "/", total);
      }
      if (i + WAYBACK_CONCURRENCY < total) await new Promise((r) => setTimeout(r, WAYBACK_DELAY_MS));
    }
  } else {
    console.log("[Nauticals] Cruisers Wiki Wayback étape 2/3: dernières archives valables (wayback_best_captures)...");
    await populateWaybackBestCaptures(entries);
    items = nauticalsFromBestCaptures();
  }
  const withCoords = items.filter((x) => x.lat != null && x.lng != null).length;
  console.log("[Nauticals] Cruisers Wiki Wayback étape 3/3: terminé,", items.length, "nauticals (dont", withCoords, "avec coord)");
  return items;
}

/** Lance Chromium avec stealth (contournement Cloudflare) ou fallback Playwright standard. */
async function launchCruisersWikiBrowser(): Promise<void> {
  if (cruisersWikiBrowser) return;
  try {
    const { chromium } = await import("playwright-extra");
    const StealthPlugin = (await import("puppeteer-extra-plugin-stealth")).default;
    chromium.use(StealthPlugin());
    cruisersWikiBrowser = await chromium.launch({ headless: true });
    console.log("[Nauticals] Cruisers Wiki: Playwright (stealth) lancé");
  } catch (e1) {
    try {
      const { chromium } = await import("playwright");
      cruisersWikiBrowser = await chromium.launch({ headless: true });
      console.log("[Nauticals] Cruisers Wiki: Playwright standard lancé (stealth non dispo)");
    } catch (e2) {
      console.log("[Nauticals] Cruisers Wiki: Playwright non disponible, fallback proxy/direct");
    }
  }
}

/** Vérifie si FlareSolverr est disponible. */
async function isFlareSolverrAvailable(): Promise<boolean> {
  try {
    const url = process.env.FLARESOLVERR_URL || "http://localhost:8191/v1";
    const base = url.replace(/\/v1.*$/, "") || "http://localhost:8191";
    const r = await fetch(base, { signal: AbortSignal.timeout(2000) });
    return true;
  } catch {
    return false;
  }
}

/** Orchestration : catégories → pages → parsing → NauticalInsert[] */
async function fetchCruisersWikiNauticals(): Promise<NauticalInsert[]> {
  const items: NauticalInsert[] = [];
  const fsOk = await isFlareSolverrAvailable();
  const proxyOk = !!getCruisersWikiProxyBase();
  console.log("[Nauticals] Cruisers Wiki: FlareSolverr", fsOk ? "disponible" : "non détecté", "| Proxy (Scrape.do)", proxyOk ? "configuré" : "non configuré");
  if (!fsOk) console.log("[Nauticals] Pour FlareSolverr: docker run -d -p 8191:8191 ghcr.io/flaresolverr/flaresolverr");
  await launchCruisersWikiBrowser();
  try {
  const subcats = await fetchCruisersWikiPortSubcategories();
  console.log("[Nauticals] Cruisers Wiki étape 2/3: liste des pages par catégorie (TinyFish/Playwright)...");
  let totalPagesListed = 0;
  const allPageTitles: { pageTitle: string; country: string }[] = [];
  for (const { title: catTitle, country } of subcats) {
    const pageTitles = await fetchCruisersWikiCategoryPages(catTitle);
    console.log("[Nauticals] Cruisers Wiki catégorie", country, ":", pageTitles.length, "pages listées");
    totalPagesListed += pageTitles.length;
    for (const pageTitle of pageTitles) allPageTitles.push({ pageTitle, country });
  }
  console.log("[Nauticals] Cruisers Wiki étape 2/3: TinyFish/Playwright a listé", totalPagesListed, "URLs pour Playwright (bulk)");
  console.log("[Nauticals] Cruisers Wiki étape 3/3: fetch contenu des pages (Playwright/Proxy, pas TinyFish)...");
  const extractionPack = getMemoizedExtractionPack();
  let processed = 0;
  for (const { pageTitle, country } of allPageTitles) {
      await sleep(CRUISERSWIKI_DELAY_MS);
      processed++;
      if (processed % 100 === 0 || processed === totalPagesListed) {
        console.log("[Nauticals] Cruisers Wiki bulk:", processed, "/", totalPagesListed, "pages");
      }
      try {
        const wikitext = await fetchCruisersWikiPageContent(pageTitle);
        const slug = pageTitle.replace(/\s+/g, "_");
        const sourceUrl = `https://www.cruiserswiki.org/wiki/${encodeURIComponent(slug)}`;
        const applied = applyExtractionPack(wikitext, { sourceUrl }, extractionPack);
        if (!applied.include) continue;
        if (applied.lat == null || applied.lng == null) continue;
        items.push({
          source: "cruiserswiki",
          source_id: `cruiserswiki_${slug}`,
          title: pageTitle,
          description: applied.description,
          caution: applied.caution,
          lat: applied.lat,
          lng: applied.lng,
          zone_ref: null,
          country,
          objtype: "port",
          source_url: sourceUrl,
        });
      } catch (e: any) {
        console.warn("[Nauticals] Cruisers Wiki skip", pageTitle, ":", e?.message);
      }
  }
  console.log("[Nauticals] Cruisers Wiki étape 3/3: terminé,", items.length, "nauticals extraits (avec coord)");
  return items;
  } finally {
    if (cruisersWikiBrowser) {
      await cruisersWikiBrowser.close();
      cruisersWikiBrowser = null;
    }
  }
}

/** Entier optionnel depuis le body sync (JSON number ou string). */
function parseSyncBodyInt(v: unknown): number | undefined {
  if (typeof v === "number" && Number.isFinite(v)) return Math.trunc(v);
  if (typeof v === "string" && v.trim() !== "") {
    const n = parseInt(v.trim(), 10);
    if (!Number.isNaN(n)) return n;
  }
  return undefined;
}

async function syncNauticalsFromAllSources(options?: {
  refreshCdx?: boolean;
  resumeCdxFrom?: { from: string; to: string; offset: number };
  resumeCdxPerUrlIndex?: number;
  cdxMode?: "bulk" | "per_url";
  cdxFromYear?: number;
  cdxPerUrlLimit?: number;
  refreshKartverket?: boolean;
  refreshWayback?: boolean;
  refreshCruiserswiki?: boolean;
}): Promise<{
  sailing: number;
  cruiserswiki: number;
  wayback: number;
  waybackPhase2?: Phase2Result;
  cruiserswikiError?: string;
  waybackError?: string;
}> {
  const insertStmt = db.prepare(`
    INSERT INTO nauticals (source, source_id, title, description, caution, lat, lng, zone_ref, country, objtype, source_url)
    VALUES (@source, @source_id, @title, @description, @caution, @lat, @lng, @zone_ref, @country, @objtype, @source_url)
  `);
  const insertWaybackStmt = db.prepare(`
    INSERT INTO nauticals (source, source_id, title, description, caution, lat, lng, zone_ref, country, objtype, source_url, wayback_timestamp, wayback_url)
    VALUES (@source, @source_id, @title, @description, @caution, @lat, @lng, @zone_ref, @country, @objtype, @source_url, @wayback_timestamp, @wayback_url)
  `);
  let sailingCount = 0;
  let cruiserswikiCount = 0;
  let waybackCount = 0;
  let cruiserswikiError: string | undefined;
  let waybackError: string | undefined;

  const kartverketExisting = (db.prepare("SELECT COUNT(*) as c FROM nauticals WHERE source = 'kartverket_sailing'").get() as { c: number }).c;
  if (kartverketExisting > 0 && !options?.refreshKartverket) {
    sailingCount = kartverketExisting;
    console.log("[Nauticals] Kartverket sailing: déjà en base,", sailingCount, "(skip fetch)");
  } else {
    try {
      const sailing = await fetchKartverketCollection("sailingdirections");
      db.prepare("DELETE FROM nauticals WHERE source = 'kartverket_sailing'").run();
      for (const row of sailing) insertStmt.run(row);
      sailingCount = sailing.length;
      console.log("[Nauticals] Kartverket sailing:", sailingCount);
    } catch (e: any) {
      console.error("[Nauticals] Kartverket fetch failed:", e?.message);
    }
  }

  let waybackPhase2: Phase2Result | undefined;
  const waybackExisting = (db.prepare("SELECT COUNT(*) as c FROM nauticals WHERE source = 'cruiserswiki_wayback'").get() as { c: number }).c;
  if (
    waybackExisting > 0 &&
    !options?.refreshWayback &&
    !options?.resumeCdxFrom &&
    typeof options?.resumeCdxPerUrlIndex !== "number"
  ) {
    waybackCount = waybackExisting;
    console.log("[Nauticals] Cruisers Wiki Wayback: déjà en base,", waybackCount, "(skip fetch)");
    const hasModFreq = (db.prepare("SELECT COUNT(*) as c FROM nauticals WHERE source = 'cruiserswiki_wayback' AND modification_frequency IS NOT NULL").get() as { c: number }).c;
    if (hasModFreq < waybackExisting) {
      console.log("[Nauticals] Cruisers Wiki Wayback Phase 2: analyse des fréquences (données existantes)...");
      waybackPhase2 = await runWaybackPhase2(db);
    }
  } else {
  try {
    const wayback = await fetchWaybackCruisersWikiNauticals({
      refreshCdx: options?.refreshCdx,
      resumeCdxFrom: options?.resumeCdxFrom,
      resumeCdxPerUrlIndex: options?.resumeCdxPerUrlIndex,
      cdxMode: options?.cdxMode,
      cdxFromYear: options?.cdxFromYear,
      cdxPerUrlLimit: options?.cdxPerUrlLimit,
    });
    db.prepare("DELETE FROM nauticals WHERE source = 'cruiserswiki_wayback'").run();
    for (const row of wayback) {
      insertWaybackStmt.run({
        ...row,
        lat: row.lat ?? null,
        lng: row.lng ?? null,
      });
    }
    waybackCount = wayback.length;
    console.log("[Nauticals] Cruisers Wiki Wayback Phase 1:", waybackCount);

    if (waybackCount > 0) {
      console.log("[Nauticals] Cruisers Wiki Wayback Phase 2: analyse des fréquences de modification...");
      waybackPhase2 = await runWaybackPhase2(db);
      console.log("[Nauticals] Cruisers Wiki Wayback Phase 2:", waybackPhase2);
    }
  } catch (e: any) {
    waybackError = e?.message ?? String(e);
    console.error("[Nauticals] Cruisers Wiki Wayback fetch failed:", waybackError);
  }
  }

  const cruiserswikiExisting = (db.prepare("SELECT COUNT(*) as c FROM nauticals WHERE source = 'cruiserswiki'").get() as { c: number }).c;
  if (cruiserswikiExisting > 0 && !options?.refreshCruiserswiki) {
    cruiserswikiCount = cruiserswikiExisting;
    console.log("[Nauticals] Cruisers Wiki: déjà en base,", cruiserswikiCount, "(skip fetch)");
  } else {
  try {
    const cruiserswiki = await fetchCruisersWikiNauticals();
    db.prepare("DELETE FROM nauticals WHERE source = 'cruiserswiki'").run();
    for (const row of cruiserswiki) insertStmt.run(row);
    cruiserswikiCount = cruiserswiki.length;
    console.log("[Nauticals] Cruisers Wiki:", cruiserswikiCount);
  } catch (e: any) {
    cruiserswikiError = e?.message ?? String(e);
    console.error("[Nauticals] Cruisers Wiki fetch failed:", cruiserswikiError);
  }
  }

  return { sailing: sailingCount, cruiserswiki: cruiserswikiCount, wayback: waybackCount, waybackPhase2, cruiserswikiError, waybackError };
}

// Log stream for frontend (informative process logs)
// Supports: broadcastLog("raw") or broadcastLog({ key: "etl_fetch", host: "x.com" })
const logStreamSubscribers: { res: express.Response }[] = [];
function broadcastLog(msg: string | Record<string, unknown>) {
  const payload = typeof msg === "string" ? { message: msg } : { ...msg };
  const line = JSON.stringify(payload) + "\n";
  for (let i = logStreamSubscribers.length - 1; i >= 0; i--) {
    try {
      logStreamSubscribers[i].res.write(`data: ${line}`);
    } catch (_) {
      logStreamSubscribers.splice(i, 1);
    }
  }
}

// NDJSON live feed: subscribers receive new projects as they're inserted
const projectStreamSubscribers: { res: express.Response }[] = [];
function broadcastNewProject(feature: object) {
  if (swarmStopped) return;
  const line = JSON.stringify(feature) + "\n";
  for (let i = projectStreamSubscribers.length - 1; i >= 0; i--) {
    try {
      projectStreamSubscribers[i].res.write(`data: ${line}`);
    } catch (_) {
      projectStreamSubscribers.splice(i, 1);
    }
  }
}

async function startServer() {
  const app = express();
  const PORT = 3000;

  initializeDomainScoring('data/domain-metrics.json');

  app.use(express.json());


  // CORS + frame-ancestors: permet au flux TinyFish (inspector) d'afficher l'app sans blocage
  app.use((_req, res, next) => {
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type");
    res.setHeader("Content-Security-Policy", "frame-ancestors 'self' https://tetra-streaming.tinyfish.io https://*.tinyfish.io");
    next();
  });
  app.options("*", (_req, res) => res.sendStatus(204));

  app.get("/favicon.ico", (_req, res) => {
    const svgPath = path.join(__dirname, "dist", "logo-blue-intelligence.svg");
    if (fs.existsSync(svgPath)) {
      res.setHeader("Content-Type", "image/svg+xml");
      res.sendFile(svgPath);
    } else {
      res.status(404).end();
    }
  });

  const CONFIRM_SECRET = process.env.BLUEINTEL_CONFIRM_CODE?.trim();
  const hasConfirmProtection = !!CONFIRM_SECRET;

  /** Normalise le code pour éviter les faux négatifs (Unicode, espaces invisibles, etc.) */
  function normalizeConfirmCode(s: string): string {
    return s
      .trim()
      .replace(/\r\n?|\n/g, "")
      .replace(/\uFEFF/g, "")
      .replace(/\u200B|\u200C|\u200D|\u2060/g, "")
      .normalize("NFC");
  }

  function requireConfirmCode(req: express.Request, res: express.Response): boolean {
    if (!hasConfirmProtection) return true;
    const raw = req.body?.confirmCode ?? "";
    const code = normalizeConfirmCode(typeof raw === "string" ? raw : String(raw));
    if (!code) {
      res.status(403).json({ error: "confirm_required", message: "Confirmation code required" });
      return false;
    }
    const secretNorm = normalizeConfirmCode(CONFIRM_SECRET!);
    const secretBuf = Buffer.from(secretNorm, "utf8");
    const codeBuf = Buffer.from(code, "utf8");
    if (secretBuf.length !== codeBuf.length || !crypto.timingSafeEqual(secretBuf, codeBuf)) {
      const DEBUG_API = process.env.DEBUG_API === "1" || process.env.DEBUG_API === "true";
      if (DEBUG_API) {
        console.log("[Confirm] Code invalide - longueur secret:", secretBuf.length, "code reçu:", codeBuf.length);
      }
      res.status(403).json({ error: "invalid_code", message: "Invalid confirmation code" });
      return false;
    }
    return true;
  }

  const DEBUG_API = process.env.DEBUG_API === "1" || process.env.DEBUG_API === "true";
  app.use((req, res, next) => {
    if (DEBUG_API && req.path.startsWith("/api/")) {
      const start = Date.now();
      res.on("finish", () => {
        const duration = Date.now() - start;
        if (res.statusCode >= 400 || duration > 500) {
          console.log(`[API] ${req.method} ${req.path} ${res.statusCode} ${duration}ms`);
        }
      });
    }
    next();
  });

  // API Routes
  app.get("/api/debug/db", (req, res) => {
    try {
      const projects = db.prepare("SELECT * FROM projects").all();
      const telemetry = db.prepare("SELECT * FROM telemetry").all();
      res.json({ projects, telemetry });
    } catch (error) {
      res.status(500).json({ error: String(error) });
    }
  });

  app.get("/api/config-check", (req, res) => {
    res.json({
      tinyfishKeySet: !!process.env.TINYFISH_API_KEY,
      claudeKeySet: !!(process.env.CLAUDE_API_KEY || process.env.ANTHROPIC_API_KEY),
      confirmRequired: hasConfirmProtection,
      envKeys: Object.keys(process.env).filter(k => k.includes('FISH') || k.includes('API') || k.includes('KEY') || k.includes('TINY') || k.includes('CLAUDE') || k.includes('ANTHROPIC'))
    });
  });

  /** Vérifie le code secret (ex: pour débloquer la couche Nautiques) */
  app.post("/api/verify-confirm-code", (req, res) => {
    if (!requireConfirmCode(req, res)) return;
    res.json({ ok: true });
  });

  /** Debug: voir ce que le serveur reçoit pour le code (sans exposer le contenu) */
  app.post("/api/debug/confirm-test", (req, res) => {
    const raw = req.body?.confirmCode;
    const code = normalizeConfirmCode(typeof raw === "string" ? raw : raw != null ? String(raw) : "");
    const secretNorm = CONFIRM_SECRET ? normalizeConfirmCode(CONFIRM_SECRET) : "";
    const secretLen = Buffer.from(secretNorm, "utf8").length;
    const codeLen = Buffer.from(code, "utf8").length;
    res.json({
      hasBody: !!req.body,
      bodyKeys: req.body ? Object.keys(req.body) : [],
      confirmCodeType: typeof raw,
      secretLength: secretLen,
      codeReceivedLength: codeLen,
      lengthsMatch: secretLen === codeLen,
      confirmRequired: hasConfirmProtection,
    });
  });

  app.get("/api/projects", (req, res) => {
    try {
      const projects = db.prepare("SELECT * FROM projects").all();

      const geojson = {
        type: "FeatureCollection",
        features: projects.map((p: any) => ({
          type: "Feature",
          geometry: {
            type: "Point",
            coordinates: [p.lng, p.lat],
          },
          properties: {
            id: p.id,
            title: p.title,
            url: p.url,
            description: p.description,
            funder: p.funder,
            relevance_score: p.relevance_score,
            s_ocean_score: p.s_ocean_score,
            category: p.category,
            status: p.status,
            image_url: p.image_url,
            start_date: p.start_date,
            end_date: p.end_date,
          },
        })),
      };

      res.json(geojson);
    } catch (error) {
      console.error("Error fetching projects:", error);
      res.status(500).json({ error: "Failed to fetch projects" });
    }
  });

  /** Vérification : stats par source, modification_frequency, Phase 3. */
  app.get("/api/nauticals/stats", (_req, res) => {
    try {
      const bySource = db.prepare(
        "SELECT source, COUNT(*) as count FROM nauticals GROUP BY source"
      ).all() as { source: string; count: number }[];
      const waybackByFreq = db.prepare(
        "SELECT modification_frequency, COUNT(*) as count FROM nauticals WHERE source = 'cruiserswiki_wayback' GROUP BY modification_frequency"
      ).all() as { modification_frequency: string | null; count: number }[];
      const waybackWithCoords = db.prepare(
        "SELECT COUNT(*) as count FROM nauticals WHERE source = 'cruiserswiki_wayback' AND lat IS NOT NULL AND lng IS NOT NULL"
      ).get() as { count: number };
      let phase3Stats: { lastUpdateAttempts: number; liveFetched: number } | null = null;
      try {
        const lastAttempt = db.prepare(
          "SELECT COUNT(*) as count FROM nauticals WHERE source = 'cruiserswiki_wayback' AND last_update_attempt_at IS NOT NULL"
        ).get() as { count: number };
        const liveFetched = db.prepare(
          "SELECT COUNT(*) as count FROM nauticals WHERE source = 'cruiserswiki_wayback' AND live_fetched_at IS NOT NULL"
        ).get() as { count: number };
        phase3Stats = { lastUpdateAttempts: lastAttempt.count, liveFetched: liveFetched.count };
      } catch (_) {}
      res.json({
        bySource,
        wayback: {
          byModificationFrequency: waybackByFreq,
          withCoords: waybackWithCoords.count,
          total: bySource.find((s) => s.source === "cruiserswiki_wayback")?.count ?? 0,
        },
        phase3: phase3Stats,
      });
    } catch (error) {
      console.error("Error fetching nauticals stats:", error);
      res.status(500).json({ error: "Failed to fetch stats" });
    }
  });

  app.get("/api/nauticals", (req, res) => {
    try {
      const rows = db.prepare("SELECT * FROM nauticals").all() as any[];
      const withCoords = rows.filter((n) => n.lat != null && n.lng != null && Math.abs(n.lat) <= 90 && Math.abs(n.lng) <= 180);
      const geojson = {
        type: "FeatureCollection",
        features: withCoords.map((n) => ({
          type: "Feature",
          geometry: { type: "Point", coordinates: [n.lng, n.lat] },
          properties: {
            id: n.id,
            title: n.title,
            description: n.description,
            caution: n.caution,
            source: n.source,
            source_id: n.source_id,
            zone_ref: n.zone_ref,
            country: n.country,
            objtype: n.objtype,
            source_url: n.source_url,
            image_url: n.image_url ?? null,
            wayback_url: n.wayback_url ?? null,
            modification_frequency: n.modification_frequency ?? null,
            modification_count: n.modification_count ?? null,
          },
        })),
      };
      res.json(geojson);
    } catch (error) {
      console.error("Error fetching nauticals:", error);
      res.status(500).json({ error: "Failed to fetch nauticals" });
    }
  });

  app.post("/api/nauticals/sync", async (req, res) => {
    if (!requireConfirmCode(req, res)) return;
    try {
      console.log("[Nauticals] Syncing from Kartverket + Wayback (Phase 1+2) + Cruisers Wiki...");
      const { sailing, cruiserswiki, wayback, waybackPhase2, cruiserswikiError, waybackError } = await syncNauticalsFromAllSources({
        refreshCdx: req.body?.refreshCdx,
        resumeCdxFrom: req.body?.resumeCdxFrom,
        resumeCdxPerUrlIndex: parseSyncBodyInt(req.body?.resumeCdxPerUrlIndex),
        cdxMode: req.body?.cdxMode === "per_url" || req.body?.cdxMode === "bulk" ? req.body.cdxMode : undefined,
        cdxFromYear: parseSyncBodyInt(req.body?.cdxFromYear),
        cdxPerUrlLimit: parseSyncBodyInt(req.body?.cdxPerUrlLimit),
        refreshKartverket: req.body?.refreshKartverket,
        refreshWayback: req.body?.refreshWayback,
        refreshCruiserswiki: req.body?.refreshCruiserswiki,
      });
      const total = sailing + cruiserswiki + wayback;
      console.log("[Nauticals] Synced:", total, "(Kartverket:", sailing, "| Wayback:", wayback, "| Cruisers Wiki:", cruiserswiki, ")");
      res.json({ status: "ok", sailing, cruiserswiki, wayback, waybackPhase2, total, cruiserswikiError, waybackError });
    } catch (error: any) {
      console.error("[Nauticals] Sync error:", error);
      res.status(500).json({ error: "Failed to sync nauticals", message: String(error?.message ?? error) });
    }
  });

  /** Phase 2 : analyse des fréquences de modification (2010–2016) → modification_count, modification_frequency. */
  app.post("/api/nauticals/wayback-phase2", async (req, res) => {
    if (!requireConfirmCode(req, res)) return;
    try {
      console.log("[Nauticals] Phase 2: analyse des fréquences de modification...");
      const result = await runWaybackPhase2(db);
      console.log("[Nauticals] Phase 2 terminé:", result);
      res.json({ status: "ok", ...result });
    } catch (error: any) {
      console.error("[Nauticals] Phase 2 error:", error);
      res.status(500).json({ error: "Failed to run wayback phase 2", message: String(error?.message ?? error) });
    }
  });

  /** Phase 3 : enrichissement via Claude (pays + coordonnées pour entrées sans lat/lng). */
  app.post("/api/nauticals/enrich-wayback-phase3", async (req, res) => {
    if (!requireConfirmCode(req, res)) return;
    try {
      const maxCoords = req.body?.maxCoords ?? 100;
      const dryRun = req.body?.dryRun === true;
      console.log("[Nauticals] Phase 3: enrichissement Claude (maxCoords:", maxCoords, ", dryRun:", dryRun, ")");
      const result = await enrichWaybackPhase3(db, { maxCoords, dryRun });
      console.log("[Nauticals] Phase 3 terminé:", result);
      res.json({ status: "ok", ...result });
    } catch (error: any) {
      console.error("[Nauticals] Phase 3 error:", error);
      res.status(500).json({ error: "Failed to enrich wayback phase 3", message: String(error?.message ?? error) });
    }
  });

  /** Phase 3 Agent : priorisation, fetch dernière archive valable (Wayback), fusion Claude, enrichissement. */
  app.post("/api/nauticals/wayback-phase3", async (req, res) => {
    if (!requireConfirmCode(req, res)) return;
    try {
      const maxUpdate = req.body?.maxUpdate ?? 20;
      const maxEnrichment = req.body?.maxEnrichment ?? 50;
      const forceRetry = req.body?.forceRetry === true;
      const includeEnrichment = req.body?.includeEnrichment !== false;
      console.log("[Nauticals] Phase 3 Agent: maxUpdate=", maxUpdate, ", maxEnrichment=", maxEnrichment, ", forceRetry=", forceRetry);
      const fetchPageContent = async (_pageTitle: string, sourceUrl: string): Promise<string | null> => {
        try {
          return await fetchWaybackWikitextForPage(sourceUrl, true);
        } catch {
          return null;
        }
      };
      const result = await runWaybackPhase3Agent(db, {
        fetchPageContent,
        maxUpdate,
        includeEnrichment,
        maxEnrichment,
        forceRetry,
      });
      console.log("[Nauticals] Phase 3 Agent terminé:", result);
      res.json({ status: "ok", ...result });
    } catch (error: any) {
      console.error("[Nauticals] Phase 3 Agent error:", error);
      res.status(500).json({ error: "Failed to run wayback phase 3 agent", message: String(error?.message ?? error) });
    }
  });

  /** Agent TinyFish : cartographie la structure et l'arborescence de CruisersWiki (catégories, comptage des pages). */
  const CRUISERSWIKI_STRUCTURE_GOAL = `
Map the structure and tree of cruiserswiki.org (MediaWiki). Start at Special:Categories.
1. List all main categories (e.g. Category:Ports, Category:Marinas, Category:Countries).
2. For each category that contains port/marina/anchorage pages, click into it and count: subcategoryCount, pageCount.
3. Navigate to World_Cruising_Guides and note the top-level regions/links.
4. Return a JSON object: { categories: [{ name, subcategoryCount, pageCount }], totalPortPages, totalMarinaPages, topLevelRegions, structureSummary }.
Return ONLY valid JSON, no other text.
`;
  app.post("/api/cruiserswiki/structure", async (req, res) => {
    if (!requireConfirmCode(req, res)) return;
    const apiKey = process.env.TINYFISH_API_KEY;
    if (!apiKey) {
      res.status(400).json({ error: "TINYFISH_API_KEY not configured" });
      return;
    }
    try {
      const response = await fetch("https://agent.tinyfish.ai/v1/automation/run-async", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
        body: JSON.stringify({
          url: "https://www.cruiserswiki.org/wiki/Special:Categories",
          goal: CRUISERSWIKI_STRUCTURE_GOAL,
          max_steps: 100,
          browser_profile: "stealth",
          proxy_config: { enabled: true, country_code: "US" },
        }),
      });
      if (!response.ok) {
        const errText = await response.text();
        res.status(response.status).json({ error: "TinyFish API error", details: errText });
        return;
      }
      const runData = (await response.json()) as { id?: string; run_id?: string; streaming_url?: string; streamingUrl?: string };
      const runId = runData.id || runData.run_id;
      const streamingUrl = runData.streaming_url || runData.streamingUrl;
      if (!runId) {
        res.status(500).json({ error: "No run ID in TinyFish response" });
        return;
      }
      console.log("[CruisersWiki Structure] TinyFish run started:", runId);
      res.json({ runId, streamingUrl, message: "Run started. Poll /api/agent/active-runs or use streaming_url to watch." });
    } catch (error: any) {
      console.error("[CruisersWiki Structure] Error:", error);
      res.status(500).json({ error: "Failed to start CruisersWiki structure agent", message: String(error?.message ?? error) });
    }
  });

  const NAUTICAL_IMAGE_GOAL = `Find a representative image of this maritime location: prefer views of port, coast, fjord, or map of the area. Accept maps as illustration. EXCLUDE logos and icons. Return ONLY the image URL (must start with http:// or https://). No other text, no markdown. Examples: https://upload.wikimedia.org/wikipedia/commons/thumb/0/0e/Oslo_City_Centre.jpg/500px-Oslo_City_Centre.jpg`;

  async function findImageUrlWithTinyFish(title: string, zoneRef: string | null, country: string | null): Promise<string | null> {
    const apiKey = process.env.TINYFISH_API_KEY;
    if (!apiKey) return null;
    const searchQuery = `${title} ${country || "maritime"}`;
    const searchUrl = `https://en.wikipedia.org/wiki/Special:Search?search=${encodeURIComponent(searchQuery)}`;
    const runWithRetry = async (attempt: number): Promise<string | null> => {
      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 120000);
        const response = await fetch("https://agent.tinyfish.ai/v1/automation/run-async", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
          body: JSON.stringify({ url: searchUrl, goal: NAUTICAL_IMAGE_GOAL, max_steps: 30 }),
          signal: controller.signal,
        });
        clearTimeout(timeout);
        if (!response.ok) return null;
        const runData = await response.json();
        const runId = runData.id || runData.run_id;
        if (!runId) return null;
        for (let poll = 0; poll < 60; poll++) {
          await new Promise((r) => setTimeout(r, 3000));
          const statusRes = await fetch(`https://agent.tinyfish.ai/v1/runs/${runId}`, { headers: { "X-API-Key": apiKey } });
          if (!statusRes.ok) continue;
          const statusData = await statusRes.json();
          const status = statusData.status;
          if (status === "COMPLETED") {
            const result = statusData.result || statusData.output;
            const text = typeof result === "string" ? result : JSON.stringify(result || "");
            const match = text.match(/(https?:\/\/[^\s"'<>)\]]+\.(?:jpg|jpeg|png|gif|webp)(?:\?[^\s"'<>)\]]*)?)/i);
            const url = match ? match[1].trim() : (text.match(/https?:\/\/upload\.wikimedia\.org[^\s"'<>)\]]+/) || [])[0]?.trim();
            if (url && (await validateImageUrl(url))) return url;
            return null;
          }
          if (status === "FAILED") return null;
        }
        return null;
      } catch {
        return null;
      }
    };
    let last: string | null = null;
    for (let attempt = 0; attempt < 2; attempt++) {
      last = await runWithRetry(attempt);
      if (last) return last;
      if (attempt < 1) await new Promise((r) => setTimeout(r, 2000));
    }
    return last;
  }

  const UA = "BlueIntelligence/1.0 (Maritime OSINT; https://naviguide.fr)";
  const WIKI_WIKICOMMONS_LOG = process.env.DEBUG_NAUTICALS_IMAGES === "true";

  /** Validates that URL returns an image (HEAD request, MIME type). */
  async function validateImageUrl(url: string): Promise<boolean> {
    try {
      const res = await fetch(url, { method: "HEAD", redirect: "follow" });
      if (!res.ok) return false;
      const ct = (res.headers.get("content-type") || "").toLowerCase();
      return ct.includes("image/");
    } catch {
      return false;
    }
  }

  /** Wikidata: récupère l'image P18 d'une entité Q */
  async function findImageFromWikidata(qId: string): Promise<string | null> {
    try {
      const url = `https://www.wikidata.org/w/api.php?action=wbgetclaims&entity=${qId}&property=P18&format=json&origin=*`;
      const res = await fetch(url, { headers: { "User-Agent": UA } });
      if (!res.ok) return null;
      const data = await res.json();
      const claims = data?.claims?.["P18"];
      const filename = claims?.[0]?.mainsnak?.datavalue?.value;
      if (!filename || typeof filename !== "string") return null;
      const encoded = encodeURIComponent(filename.replace(/ /g, "_"));
      const thumbUrl = `https://commons.wikimedia.org/w/index.php?title=Special:Redirect/file/${encoded}&width=400`;
      if (await validateImageUrl(thumbUrl)) return thumbUrl;
      return null;
    } catch {
      return null;
    }
  }

  /** Wikipedia: articles géolocalisés (rayon 10km max). Fallback Wikidata si pas de pageimage. */
  async function findImageFromWikipediaGeosearch(lat: number, lng: number): Promise<string | null> {
    try {
      const coord = `${lat}|${lng}`;
      const url = `https://en.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord=${encodeURIComponent(coord)}&gsradius=10000&gslimit=10&format=json&origin=*`;
      const res = await fetch(url, { headers: { "User-Agent": UA } });
      if (!res.ok) {
        if (WIKI_WIKICOMMONS_LOG) console.log("[Wikipedia geosearch] HTTP error:", res.status);
        return null;
      }
      const data = await res.json();
      const results = (data?.query?.geosearch ?? []).slice(0, 8);
      const pageIds = results.map((p: any) => p.pageid).filter(Boolean);
      if (pageIds.length === 0) {
        if (WIKI_WIKICOMMONS_LOG) console.log("[Wikipedia geosearch] No results for", coord);
        return null;
      }
      const imgRes = await fetch(`https://en.wikipedia.org/w/api.php?action=query&pageids=${pageIds.join("|")}&prop=pageimages|pageprops&pithumbsize=400&ppprop=wikibase_item&format=json&origin=*`, { headers: { "User-Agent": UA } });
      const imgData = await imgRes.json();
      const pages = imgData?.query?.pages ?? {};
      for (const pid of pageIds) {
        const thumb = pages[pid]?.thumbnail?.source;
        if (thumb && (thumb.startsWith("http://") || thumb.startsWith("https://"))) {
          if (await validateImageUrl(thumb)) return thumb;
        }
      }
      for (const pid of pageIds) {
        const qId = pages[pid]?.pageprops?.wikibase_item;
        if (qId) {
          const wdImg = await findImageFromWikidata(qId);
          if (wdImg) return wdImg;
        }
      }
      return null;
    } catch (e: any) {
      if (WIKI_WIKICOMMONS_LOG) console.log("[Wikipedia geosearch] Error:", e?.message);
      return null;
    }
  }

  /** Wikimedia Commons: images géolocalisées (namespace 6 = fichiers) */
  async function findImageFromCommonsGeosearch(lat: number, lng: number): Promise<string | null> {
    try {
      const coord = `${lat}|${lng}`;
      const url = `https://commons.wikimedia.org/w/api.php?action=query&generator=geosearch&ggsprimary=all&ggsnamespace=6&ggsradius=10000&ggscoord=${encodeURIComponent(coord)}&ggslimit=8&prop=imageinfo&iilimit=1&iiprop=url&iiurlwidth=400&format=json&origin=*`;
      const res = await fetch(url, { headers: { "User-Agent": UA } });
      if (!res.ok) {
        if (WIKI_WIKICOMMONS_LOG) console.log("[Commons geosearch] HTTP error:", res.status);
        return null;
      }
      const data = await res.json();
      const pages = data?.query?.pages ?? {};
      for (const pid of Object.keys(pages)) {
        const thumb = pages[pid]?.imageinfo?.[0]?.thumburl ?? pages[pid]?.imageinfo?.[0]?.url;
        if (thumb && (thumb.startsWith("http://") || thumb.startsWith("https://"))) {
          if (await validateImageUrl(thumb)) return thumb;
        }
      }
      if (WIKI_WIKICOMMONS_LOG && Object.keys(pages).length === 0) console.log("[Commons geosearch] No results for", coord);
      return null;
    } catch (e: any) {
      if (WIKI_WIKICOMMONS_LOG) console.log("[Commons geosearch] Error:", e?.message);
      return null;
    }
  }

  /** Titre contient des caractères norvégiens (ø, æ, å) */
  function hasNorwegianChars(title: string): boolean {
    return /[øæåØÆÅ]/.test(title);
  }

  /** Wikipedia: recherche par titre. Priorité no.wikipedia pour noms norvégiens. Variantes: country, fjord, port, zone_ref. */
  async function findImageFromWikipediaTitle(row: { title: string; zone_ref?: string | null; country?: string | null }): Promise<string | null> {
    const searchOnWiki = async (lang: "en" | "no" | "pt") => {
      const base = lang === "en" ? "https://en.wikipedia.org" : lang === "no" ? "https://no.wikipedia.org" : "https://pt.wikipedia.org";
      const zone = (row.zone_ref || "").trim();
      const country = row.country || "Norway";
      const queries = [
        `${row.title} ${country}`,
        `${row.title} fjord`,
        `${row.title} port`,
        zone ? `${row.title} ${zone}` : "",
        row.title,
      ].filter(Boolean);
      for (const searchQuery of queries) {
        if (!searchQuery.trim()) continue;
        const searchUrl = `${base}/w/api.php?action=query&list=search&srsearch=${encodeURIComponent(searchQuery)}&format=json&origin=*`;
        const searchRes = await fetch(searchUrl, { headers: { "User-Agent": UA } });
        const searchData = await searchRes.json();
        const results = (searchData?.query?.search ?? []).slice(0, 5);
        const pageIds = results.map((p: any) => p.pageid).filter(Boolean);
        if (pageIds.length === 0) continue;
        const imgRes = await fetch(`${base}/w/api.php?action=query&pageids=${pageIds.join("|")}&prop=pageimages|pageprops&pithumbsize=400&ppprop=wikibase_item&format=json&origin=*`, { headers: { "User-Agent": UA } });
        const imgData = await imgRes.json();
        const pages = imgData?.query?.pages ?? {};
        for (const pid of pageIds) {
          const thumb = pages[pid]?.thumbnail?.source;
          if (thumb && (thumb.startsWith("http://") || thumb.startsWith("https://"))) {
            if (await validateImageUrl(thumb)) return thumb;
          }
        }
        for (const pid of pageIds) {
          const qId = pages[pid]?.pageprops?.wikibase_item;
          if (qId) {
            const wdImg = await findImageFromWikidata(qId);
            if (wdImg) return wdImg;
          }
        }
        for (const hit of results) {
          const pageTitle = hit.title?.replace(/ /g, "_");
          if (!pageTitle) continue;
          const articleUrl = `${base}/wiki/${encodeURIComponent(pageTitle).replace(/%2F/g, "/")}`;
          try {
            const resFetch = await fetch(articleUrl, { headers: { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" } });
            if (!resFetch.ok) continue;
            const html = await resFetch.text();
            const urls = extractImageUrlsFromHtml(html, articleUrl);
            if (urls[0] && (await validateImageUrl(urls[0]))) return urls[0];
          } catch {
            /* skip */
          }
        }
      }
      return null;
    };
    if (hasNorwegianChars(row.title)) {
      const fromNo = await searchOnWiki("no");
      if (fromNo) return fromNo;
    }
    if (row.country === "Portugal") {
      const fromPt = await searchOnWiki("pt");
      if (fromPt) return fromPt;
    }
    const fromEn = await searchOnWiki("en");
    if (fromEn) return fromEn;
    return searchOnWiki("no");
  }

  /** Unsplash: recherche par mots-clés (pas de géolocalisation). Optionnel via UNSPLASH_ACCESS_KEY. */
  async function findImageFromUnsplash(query: string): Promise<string | null> {
    const key = process.env.UNSPLASH_ACCESS_KEY;
    if (!key) return null;
    try {
      const url = `https://api.unsplash.com/search/photos?query=${encodeURIComponent(query)}&per_page=5`;
      const res = await fetch(url, { headers: { Authorization: `Client-ID ${key}` } });
      if (!res.ok) return null;
      const data = await res.json();
      const img = data?.results?.[0]?.urls?.regular ?? data?.results?.[0]?.urls?.small;
      if (img && (await validateImageUrl(img))) return img;
      return null;
    } catch {
      return null;
    }
  }

  /** Pexels: recherche par mots-clés. Optionnel via PEXELS_API_KEY. */
  async function findImageFromPexels(query: string): Promise<string | null> {
    const key = process.env.PEXELS_API_KEY;
    if (!key) return null;
    try {
      const url = `https://api.pexels.com/v1/search?query=${encodeURIComponent(query)}&per_page=5`;
      const res = await fetch(url, { headers: { Authorization: key } });
      if (!res.ok) return null;
      const data = await res.json();
      const img = data?.photos?.[0]?.src?.medium ?? data?.photos?.[0]?.src?.small;
      if (img && (await validateImageUrl(img))) return img;
      return null;
    } catch {
      return null;
    }
  }

  type NauticalRow = { id: number; title: string; zone_ref: string | null; country: string | null; lat: number; lng: number };

  const NAUTICALS_IMAGES_BATCH = 100;
  const failedNauticalIds = new Set<number>();

  function sortNauticalsByPriority(rows: NauticalRow[]): NauticalRow[] {
    const major = /Oslo|Bergen|Trondheim|Stavanger|Kristiansand|Tromsø|havn|port/i;
    return [...rows].sort((a, b) => {
      const aMajor = major.test(a.title) || major.test(a.zone_ref || "");
      const bMajor = major.test(b.title) || major.test(b.zone_ref || "");
      if (aMajor && !bMajor) return -1;
      if (!aMajor && bMajor) return 1;
      return (a.zone_ref ? 0 : 1) - (b.zone_ref ? 0 : 1);
    });
  }

  app.post("/api/nauticals/fetch-images", async (req, res) => {
    if (req.body?.requireConfirm && !requireConfirmCode(req, res)) return;
    try {
      const reset = req.body?.reset === true || req.query?.reset === "1";
      if (reset) {
        db.prepare("UPDATE nauticals SET image_url = NULL").run();
        failedNauticalIds.clear();
      }
      let rows = db.prepare("SELECT id, title, zone_ref, country, lat, lng FROM nauticals WHERE image_url IS NULL OR image_url = ''").all() as NauticalRow[];
      const forceRetry = req.body?.retryFailed === true || req.query?.retry_failed === "1";
      if (forceRetry) failedNauticalIds.clear();
      rows = sortNauticalsByPriority(rows).filter((r) => !failedNauticalIds.has(r.id));
      const limit = Math.min(rows.length, NAUTICALS_IMAGES_BATCH);
      let fetched = 0;
      const updateStmt = db.prepare("UPDATE nauticals SET image_url = ? WHERE id = ?");
      const hasTinyFish = !!process.env.TINYFISH_API_KEY;
      for (let i = 0; i < limit; i++) {
        const row = rows[i];
        let imageUrl: string | null = null;
        imageUrl = await findImageFromWikipediaGeosearch(row.lat, row.lng);
        if (!imageUrl) imageUrl = await findImageFromCommonsGeosearch(row.lat, row.lng);
        if (!imageUrl) imageUrl = await findImageFromWikipediaTitle(row);
        if (!imageUrl) {
          const q = `${row.title} ${row.country || "coast"} port`;
          imageUrl = await findImageFromPexels(q) ?? await findImageFromUnsplash(q);
        }
        if (!imageUrl && hasTinyFish) imageUrl = await findImageUrlWithTinyFish(row.title, row.zone_ref, row.country);
        if (imageUrl) {
          updateStmt.run(imageUrl, row.id);
          fetched++;
        } else {
          failedNauticalIds.add(row.id);
        }
        await new Promise((r) => setTimeout(r, 150));
      }
      res.json({ status: "ok", processed: limit, fetched, remaining: rows.length - limit });
    } catch (error: any) {
      console.error("[Nauticals] Fetch images error:", error);
      res.status(500).json({ error: "Failed to fetch images", message: String(error?.message ?? error) });
    }
  });

  app.post("/api/nauticals/fetch-images-ai", async (req, res) => {
    if (!requireConfirmCode(req, res)) return;
    try {
      const rows = db.prepare("SELECT id, title, zone_ref, country, lat, lng FROM nauticals WHERE image_url IS NULL OR image_url = ''").all() as NauticalRow[];
      const limit = rows.length;
      let fetched = 0;
      const updateStmt = db.prepare("UPDATE nauticals SET image_url = ? WHERE id = ?");
      const hasTinyFish = !!process.env.TINYFISH_API_KEY;
      if (!hasTinyFish) {
        return res.status(400).json({ error: "TINYFISH_API_KEY required for AI image fetch" });
      }
      for (let i = 0; i < limit; i++) {
        const row = rows[i];
        let imageUrl = await findImageFromWikipediaGeosearch(row.lat, row.lng);
        if (!imageUrl) imageUrl = await findImageFromCommonsGeosearch(row.lat, row.lng);
        if (!imageUrl) imageUrl = await findImageFromWikipediaTitle(row);
        if (!imageUrl) {
          const q = `${row.title} ${row.country || "coast"} port`;
          imageUrl = await findImageFromPexels(q) ?? await findImageFromUnsplash(q);
        }
        if (!imageUrl) imageUrl = await findImageUrlWithTinyFish(row.title, row.zone_ref, row.country);
        if (imageUrl) {
          updateStmt.run(imageUrl, row.id);
          fetched++;
        }
        await new Promise((r) => setTimeout(r, 150));
      }
      res.json({ status: "ok", processed: limit, fetched });
    } catch (error: any) {
      console.error("[Nauticals] Fetch images AI error:", error);
      res.status(500).json({ error: "Failed to fetch images", message: String(error?.message ?? error) });
    }
  });

  function hasValidImageUrl(v: string | null | undefined): boolean {
    if (v == null) return false;
    const t = String(v).trim();
    if (t === "" || t === "null" || t === "undefined") return false;
    if (!t.startsWith("http://") && !t.startsWith("https://")) return false;
    if (t.length < 12) return false; // "https://x.co" minimum
    return true;
  }

  app.get("/api/projects/without-image", (req, res) => {
    try {
      const all = db.prepare("SELECT id, title, url, funder, image_url FROM projects ORDER BY id DESC").all() as { id: number; title: string; url: string; funder: string; image_url: string | null }[];
      const rows = all.filter((p) => !hasValidImageUrl(p.image_url)).map(({ id, title, url, funder }) => ({ id, title, url, funder, type: "project" as const }));
      res.json(rows);
    } catch (error) {
      console.error("Error fetching projects without image:", error);
      res.status(500).json({ error: "Failed to fetch" });
    }
  });

  app.get("/api/nauticals/without-image", (req, res) => {
    try {
      const all = db.prepare("SELECT id, title, zone_ref, source_url, image_url FROM nauticals").all() as { id: number; title: string; zone_ref: string | null; source_url: string | null; image_url: string | null }[];
      const rows = all.filter((n) => !hasValidImageUrl(n.image_url)).map(({ id, title, zone_ref, source_url }) => ({ id, title, zone_ref, url: source_url || "", funder: zone_ref || "", type: "nautical" as const }));
      res.json(rows);
    } catch (error) {
      console.error("Error fetching nauticals without image:", error);
      res.status(500).json({ error: "Failed to fetch" });
    }
  });

  app.get("/api/without-image", (req, res) => {
    try {
      const projects = db.prepare("SELECT id, title, url, funder, image_url FROM projects ORDER BY id DESC").all() as { id: number; title: string; url: string; funder: string; image_url: string | null }[];
      const nauticals = db.prepare("SELECT id, title, zone_ref, source_url, image_url FROM nauticals").all() as { id: number; title: string; zone_ref: string | null; source_url: string | null; image_url: string | null }[];
      const projRows = projects.filter((p) => !hasValidImageUrl(p.image_url)).map(({ id, title, url, funder }) => ({ id, title, url, funder, type: "project" as const }));
      const nautRows = nauticals.filter((n) => !hasValidImageUrl(n.image_url)).map(({ id, title, zone_ref, source_url }) => ({ id, title, url: source_url || "", funder: zone_ref || "", type: "nautical" as const }));
      res.json({ projects: projRows, nauticals: nautRows });
    } catch (error) {
      console.error("Error fetching without-image:", error);
      res.status(500).json({ error: "Failed to fetch" });
    }
  });

  app.get("/api/projects/image-stats", (req, res) => {
    try {
      const all = db.prepare("SELECT id, image_url FROM projects").all() as { id: number; image_url: string | null }[];
      const without = all.filter((p) => !hasValidImageUrl(p.image_url));
      const samples = without.slice(0, 5).map((p) => ({ id: p.id, image_url: p.image_url, repr: JSON.stringify(p.image_url) }));
      res.json({ total: all.length, withoutImage: without.length, samples });
    } catch (error) {
      console.error("Error fetching image stats:", error);
      res.status(500).json({ error: "Failed to fetch" });
    }
  });

  app.get("/api/projects/stream", (req, res) => {
    res.setHeader("Content-Type", "text/event-stream");
    res.setHeader("Cache-Control", "no-cache");
    res.setHeader("Connection", "keep-alive");
    projectStreamSubscribers.push({ res });
    req.on("close", () => {
      const idx = projectStreamSubscribers.findIndex((s) => s.res === res);
      if (idx >= 0) projectStreamSubscribers.splice(idx, 1);
    });
  });

  app.get("/api/logs/stream", (req, res) => {
    res.setHeader("Content-Type", "text/event-stream");
    res.setHeader("Cache-Control", "no-cache");
    res.setHeader("Connection", "keep-alive");
    logStreamSubscribers.push({ res });
    req.on("close", () => {
      const idx = logStreamSubscribers.findIndex((s) => s.res === res);
      if (idx >= 0) logStreamSubscribers.splice(idx, 1);
    });
  });

  app.get("/api/test-project", async (req, res) => {
    try {
      // Create a fake project
      const project = {
        title: "Coral Reef Restoration Maldives",
        description: "Project restoring coral reefs in Maldives waters",
        lat: 3.2,
        lng: 73.0,
      };

      // Force insertion even if the swarm is stopped (test mode)
      const oldSwarmStopped = swarmStopped;
      console.log("[Test] /api/test-project called (swarmStopped=", swarmStopped, ")");
      swarmStopped = false;
      const result = await upsertProject(project);
      swarmStopped = oldSwarmStopped;
      console.log("[Test] /api/test-project result=", result, "(swarmStopped restored to", swarmStopped, ")");

      res.setHeader("Content-Type", "application/json");
      res.send(JSON.stringify({ success: true, project, result, swarmStopped: oldSwarmStopped }));
    } catch (err: any) {
      console.error("[Test] /api/test-project error:", err);
      res.setHeader("Content-Type", "application/json");
      res.status(500).send(JSON.stringify({ success: false, error: String(err), stack: err?.stack }));
    }
  });

  app.get("/api/test-project-2", async (req, res) => {
    try {
      // Create a semantically similar project (same location)
      const project = {
        title: "Maldives Coral Reef Recovery",
        description: "Local coral reef recovery program in the Maldives",
        lat: 3.2,
        lng: 73.0,
        url: "https://example.com/project2",
        funder: "Ocean Protectors",
        category: "Marine",
        status: "Active",
      };

      // Force insertion even if the swarm is stopped (test mode)
      const oldSwarmStopped = swarmStopped;
      console.log("[Test] /api/test-project-2 called (swarmStopped=", swarmStopped, ")");
      swarmStopped = false;
      const result = await upsertProject(project);
      swarmStopped = oldSwarmStopped;
      console.log("[Test] /api/test-project-2 result=", result, "(swarmStopped restored to", swarmStopped, ")");

      // Query nearby records and compute similarity stats for debugging
      const candidates = db
        .prepare("SELECT id, title, url, description, lat, lng, title_embedding, description_embedding FROM projects WHERE abs(lat - ?) < 0.01 AND abs(lng - ?) < 0.01")
        .all(project.lat, project.lng) as Array<{
          id: number;
          title: string;
          url: string;
          description: string;
          lat: number;
          lng: number;
          title_embedding?: string;
          description_embedding?: string;
        }>;

      const { titleEmbedding: queryTitleEmb, descriptionEmbedding: queryDescEmb } = await computeEmbeddingsForProject({
        title: project.title,
        description: project.description,
      });

      const similarities = await Promise.all(
        candidates.map(async (c) => {
          let candidateTitleEmb = parseEmbedding(c.title_embedding);
          let candidateDescEmb = parseEmbedding(c.description_embedding);

          // If embeddings are missing, compute them for debug insight
          if (!candidateTitleEmb || (c.description && !candidateDescEmb)) {
            const computed = await computeEmbeddingsForProject({ title: c.title, description: c.description });
            candidateTitleEmb = candidateTitleEmb || computed.titleEmbedding;
            candidateDescEmb = candidateDescEmb || computed.descriptionEmbedding;
          }

          const titleSim = cosineSimilarity(queryTitleEmb, candidateTitleEmb);
          const hasDesc = queryDescEmb && candidateDescEmb;
          const descSim = hasDesc ? cosineSimilarity(queryDescEmb, candidateDescEmb) : null;
          return {
            id: c.id,
            url: c.url,
            title: c.title,
            description: c.description,
            titleSim,
            descSim,
          };
        })
      );

      res.setHeader("Content-Type", "application/json");
      res.send(JSON.stringify({ success: true, project, result, nearby: similarities }));
    } catch (err: any) {
      console.error("[Test] /api/test-project-2 error:", err);
      res.setHeader("Content-Type", "application/json");
      res.status(500).send(JSON.stringify({ success: false, error: String(err), stack: err?.stack }));
    }
  });

  app.get("/api/projects/ndjson", (req, res) => {
    res.setHeader("Content-Type", "application/x-ndjson");
    const projects = db.prepare("SELECT * FROM projects").all() as any[];
    for (const p of projects) {
      res.write(JSON.stringify({
        type: "Feature",
        geometry: { type: "Point", coordinates: [p.lng, p.lat] },
        properties: { id: p.id, title: p.title, url: p.url, description: p.description, funder: p.funder, relevance_score: p.relevance_score, s_ocean_score: p.s_ocean_score, category: p.category, status: p.status, image_url: p.image_url, start_date: p.start_date, end_date: p.end_date }
      }) + "\n");
    }
    res.end();
  });

  app.post("/api/projects/clear", (req, res) => {
    if (!requireConfirmCode(req, res)) return;
    try {
      swarmStopped = true;
      deployStartTime = null;
      agentQueue.length = 0;
      activeAgents = 0;
      agentCounter = 0;
      activeRuns.clear();
      activeExtractRuns.clear();
      activeHybridExtractions.clear();
      db.prepare("DELETE FROM projects").run();
      broadcastLog({ key: "etl_db_cleared" });
      res.json({ status: "ok", message: "All projects cleared" });
    } catch (error) {
      console.error("Error clearing projects:", error);
      res.status(500).json({ error: "Failed to clear projects" });
    }
  });

  app.post("/api/audit/clear", (req, res) => {
    if (!requireConfirmCode(req, res)) return;
    try {
      db.prepare("DELETE FROM telemetry").run();
      db.prepare("DELETE FROM failed_extractions").run();
      const includeDeepLinkCache = req.body?.includeDeepLinkCache === true;
      if (includeDeepLinkCache) {
        clearDeepLinkCacheFiles();
        broadcastLog({ key: "etl_deeplink_cache_cleared" });
      }
      broadcastLog({ key: "etl_audit_cleared" });
      res.json({
        status: "ok",
        message: includeDeepLinkCache
          ? "Audit cleared (telemetry + failed extractions) and DeepLink cache emptied"
          : "Audit data cleared (telemetry + failed extractions)",
        deepLinkCacheCleared: includeDeepLinkCache,
      });
    } catch (error) {
      console.error("Error clearing audit:", error);
      res.status(500).json({ error: "Failed to clear audit data" });
    }
  });

  app.get("/api/telemetry", (req, res) => {
    try {
      const telemetry = db.prepare("SELECT * FROM telemetry ORDER BY created_at DESC LIMIT 100").all();
      res.json(telemetry);
    } catch (error) {
      console.error("Error fetching telemetry:", error);
      res.status(500).json({ error: "Failed to fetch telemetry" });
    }
  });

  app.get("/api/failed-extractions", (req, res) => {
    try {
      const failed = db.prepare("SELECT * FROM failed_extractions ORDER BY created_at DESC").all() as any[];
      const updateStmt = db.prepare("UPDATE failed_extractions SET error_type = ? WHERE id = ?");
      const out = failed.map((f) => {
        let errType = f.error_type;
        if (!errType && f.error_message) {
          errType = inferErrorType(f.error_message);
          try {
            updateStmt.run(errType, f.id);
          } catch (_) {}
        }
        return { ...f, error_type: errType || f.error_type };
      });
      res.json(out);
    } catch (error) {
      console.error("Error fetching failed extractions:", error);
      res.status(500).json({ error: "Failed to fetch failed extractions" });
    }
  });


  // DOMAIN SCORING ENDPOINTS
  app.get("/api/domain-scoring/metrics", (req, res) => {
    try {
      const engine = getDomainScoringEngine();
      const minProjects = parseInt(req.query.minProjects as string) || 1;
      const metrics = engine.getSortedDomains(minProjects);
      res.json({
        total: metrics.length,
        metrics: metrics.map(m => ({
          domain: m.domain,
          totalProjects: m.totalProjects,
          validProjects: m.validProjects,
          reliabilityScore: parseFloat(m.reliabilityScore.toFixed(4)),
          lastUpdated: new Date(m.lastUpdated).toISOString(),
        })),
      });
    } catch (error) {
      console.error("Error fetching domain metrics:", error);
      res.status(500).json({ error: "Failed to fetch domain metrics" });
    }
  });

  app.get("/api/domain-scoring/top", (req, res) => {
    try {
      const engine = getDomainScoringEngine();
      const limit = parseInt(req.query.limit as string) || 10;
      const topDomains = engine.getTopDomains(limit);
      res.json({
        limit,
        domains: topDomains.map(m => ({
          domain: m.domain,
          totalProjects: m.totalProjects,
          validProjects: m.validProjects,
          reliabilityScore: parseFloat(m.reliabilityScore.toFixed(4)),
          weightedScore: parseFloat(engine.getWeightedScore(m.domain).toFixed(4)),
        })),
      });
    } catch (error) {
      console.error("Error fetching top domains:", error);
      res.status(500).json({ error: "Failed to fetch top domains" });
    }
  });

  app.get("/api/domain-scoring/domain/:domain", (req, res) => {
    try {
      const engine = getDomainScoringEngine();
      const { domain } = req.params;
      const metrics = engine.getDomainMetrics(domain);
      if (!metrics) {
        return res.status(404).json({ error: "Domain not found" });
      }
      res.json({
        domain: metrics.domain,
        totalProjects: metrics.totalProjects,
        validProjects: metrics.validProjects,
        reliabilityScore: parseFloat(metrics.reliabilityScore.toFixed(4)),
        weightedScore: parseFloat(engine.getWeightedScore(domain).toFixed(4)),
        lastUpdated: new Date(metrics.lastUpdated).toISOString(),
      });
    } catch (error) {
      console.error("Error fetching domain metrics:", error);
      res.status(500).json({ error: "Failed to fetch domain metrics" });
    }
  });

  app.post("/api/domain-scoring/reset", (req, res) => {
    try {
      const engine = getDomainScoringEngine();
      engine.resetMetrics();
      res.json({ status: "ok", message: "Domain metrics reset" });
    } catch (error) {
      console.error("Error resetting domain metrics:", error);
      res.status(500).json({ error: "Failed to reset domain metrics" });
    }
  });


  app.post("/api/agent/force-extract", async (req, res) => {
    if (!requireConfirmCode(req, res)) return;
    const { projectUrls, proxy, config } = req.body;

    if (!projectUrls || !Array.isArray(projectUrls) || projectUrls.length === 0) {
      return res.status(400).json({ error: "projectUrls array is required" });
    }
    const tinyfishKey = process.env.TINYFISH_API_KEY;
    if (!tinyfishKey) {
      return res.status(500).json({ error: "TINYFISH_API_KEY is required for force-extract (re-extraction uses TinyFish to handle PDFs and pages that Readability cannot parse)" });
    }

    const urlsToQueue: string[] = [];
    const skipped404: string[] = [];
    for (const url of projectUrls) {
      try {
        const headRes = await fetch(url, { method: "HEAD", redirect: "follow", signal: AbortSignal.timeout(5000) });
        if (headRes.status === 404) {
          skipped404.push(url);
          continue;
        }
      } catch (_) {
      }
      urlsToQueue.push(url);
    }

    swarmStopped = false;
    const taskConfig = config as TaskConfig | undefined;
    maxConcurrentAgents = Math.max(1, Math.min(10, taskConfig?.agent?.maxConcurrentAgents ?? 2));
    for (const url of urlsToQueue) {
      if (!agentQueue.find(t => t.url === url)) {
        agentQueue.push({ url, proxy, mode: 'extract', useTinyFish: true, config: taskConfig });
      }
    }
    processQueue();

    const msg = skipped404.length > 0
      ? `${urlsToQueue.length} queued, ${skipped404.length} skipped (404)`
      : `${urlsToQueue.length} agents deployed for forced extraction (TinyFish)`;
    res.json({ status: "QUEUED", message: msg, queued: urlsToQueue.length, skipped404: skipped404.length });
  });

  app.post("/api/failed-extractions/delete", (req, res) => {
    const { ids } = req.body;
    if (ids && Array.isArray(ids) && ids.length > 0) {
      const placeholders = ids.map(() => "?").join(",");
      db.prepare(`DELETE FROM failed_extractions WHERE id IN (${placeholders})`).run(...ids);
    }
    res.json({ status: "ok" });
  });

  app.get("/api/etl/seeds", (req, res) => {
    try {
      const seeds = loadMasterSeeds();
      res.json(seeds);
    } catch (e) {
      res.status(500).json({ error: "Failed to load MasterSeeds" });
    }
  });

  app.get("/api/etl/caches", (req, res) => {
    try {
      const lists = loadDeepLinkCache("DeepLinkCacheProjectsLists.json");
      const pages = loadDeepLinkCache("DeepLinkCacheProjectsPages.json");
      res.json({ lists: lists.urls, pages: pages.urls });
    } catch (e) {
      res.status(500).json({ error: "Failed to load caches" });
    }
  });

  app.post("/api/etl/swarm-deploy", async (req, res) => {
    if (!requireConfirmCode(req, res)) return;
    const { clearBeforeStart, testMode, proxy, config } = req.body || {};
    const tinyfishKey = process.env.TINYFISH_API_KEY;
    if (!tinyfishKey) {
      return res.status(500).json({ error: "TINYFISH_API_KEY is not configured" });
    }
    swarmStopped = false;
    deployStartTime = Date.now();
    maxConcurrentAgents = Math.max(1, Math.min(10, config?.agent?.maxConcurrentAgents ?? 2));
    globalExtractConcurrency = Math.max(1, Math.min(20, config?.extraction?.concurrency ?? EXTRACT_CONCURRENCY));
    globalExtractWorkersStarted = false;
    broadcastLog({ key: "etl_deploy_start" });
    agentQueue.length = 0;
    activeAgents = 0; // Reset so processQueue can start new tasks immediately
    agentCounter = 0;
    extractCounter = 0;
    hybridExtractCounter = 0;
    activeRuns.clear();
    activeExtractRuns.clear();
    activeHybridExtractions.clear();
    globalExtractQueue.length = 0;
    pendingByTarget.clear();
    if (clearBeforeStart) {
      db.prepare("DELETE FROM projects").run();
      broadcastLog({ key: "etl_db_cleared" });
    }

    const taskConfig = config as TaskConfig | undefined;

    const failedRows = db.prepare("SELECT id, target_url, project_url, error_message, error_type FROM failed_extractions").all() as any[];
    const toRetry = failedRows.filter((f) => {
      const errType = f.error_type || inferErrorType(f.error_message);
      return errType !== "404" && errType !== "empty_page";
    });
    if (toRetry.length > 0) {
      const byTarget = new Map<string, string[]>();
      for (const f of toRetry) {
        const t = f.target_url || f.project_url;
        if (!byTarget.has(t)) byTarget.set(t, []);
        byTarget.get(t)!.push(f.project_url);
      }
      const startTime = Date.now();
      for (const [targetUrl, projectUrls] of byTarget) {
        pendingByTarget.set(targetUrl, { total: projectUrls.length, success: 0, processed: 0, startTime, rawResponse: null });
      }
      extractingCount += toRetry.length;
      for (const f of toRetry) {
        globalExtractQueue.push({ projectUrl: f.project_url, targetUrl: f.target_url || f.project_url, taskConfig });
      }
      startGlobalExtractWorkers();
      broadcastLog({ key: "etl_failed_retry", n: toRetry.length });
    }

    const seeds = loadMasterSeeds();
    const lists = loadDeepLinkCache("DeepLinkCacheProjectsLists.json");
    const pages = loadDeepLinkCache("DeepLinkCacheProjectsPages.json");
    broadcastLog({ key: "etl_master_seeds", n: seeds.length });
    broadcastLog({ key: "etl_deeplink", lists: lists.urls.length, pages: pages.urls.length });
    const existingUrls = new Set(
      (db.prepare("SELECT url FROM projects WHERE url IS NOT NULL").all() as { url: string }[]).map(r => r.url)
    );
    const alreadySucceededUrls = new Set(
      (db.prepare("SELECT target_url FROM telemetry WHERE status = ?").all("SUCCESS") as { target_url: string }[]).map(r => r.target_url)
    );
    const discoverUrlsFull = [...new Set([
      ...seeds.map((s: { url: string }) => s.url),
      ...lists.urls
    ])].filter((u: string) => !alreadySucceededUrls.has(u));
    const skippedSeeds = seeds.length + lists.urls.length - discoverUrlsFull.length;
    if (skippedSeeds > 0) {
      broadcastLog({ key: "etl_seeds_skipped", n: skippedSeeds });
    }
    const discoverUrls = testMode
      ? seeds.filter((s: { url: string }) => !alreadySucceededUrls.has(s.url)).slice(0, Math.max(2, maxConcurrentAgents)).map((s: { url: string }) => s.url)
      : discoverUrlsFull;
    const extractUrls = pages.urls.filter((u: string) => !existingUrls.has(u));
    const toEnqueue: { url: string; proxy?: string; mode: "discover" | "extract"; config?: TaskConfig }[] = [];
    const discoverLimit = testMode ? Math.max(2, maxConcurrentAgents) : discoverUrls.length;
    const extractLimit = testMode ? 0 : extractUrls.length;
    for (let i = 0; i < Math.min(discoverUrls.length, discoverLimit); i++) {
      toEnqueue.push({ url: discoverUrls[i], proxy, mode: "discover", config: taskConfig });
    }
    for (let i = 0; i < Math.min(extractUrls.length, extractLimit); i++) {
      toEnqueue.push({ url: extractUrls[i], proxy, mode: "extract", config: taskConfig });
    }
    const nDiscover = toEnqueue.filter(t => t.mode === "discover").length;
    const nExtract = toEnqueue.filter(t => t.mode === "extract").length;
    broadcastLog({ key: "etl_queue", discover: nDiscover, extract: nExtract, total: toEnqueue.length });
    for (const t of toEnqueue) {
      agentQueue.push(t);
    }
    broadcastLog({ key: "etl_enqueued", n: toEnqueue.length });
    console.log(`[Swarm] Deploy: ${toEnqueue.length} tasks enqueued (${nDiscover} discover, ${nExtract} extract)`);
    processQueue();
    res.json({
      status: "QUEUED",
      message: `ETL Swarm deployed. ${toEnqueue.length} tasks enqueued (${discoverUrls.length} discover, ${extractUrls.length} extract available).`,
      enqueued: toEnqueue.length,
      discoverAvailable: discoverUrls.length,
      extractAvailable: extractUrls.length
    });
  });

  app.post("/api/agent/start", async (req, res) => {
    const { targetUrl, proxy, mode, config } = req.body;

    if (!targetUrl) {
      return res.status(400).json({ error: "targetUrl is required" });
    }
    if (swarmStopped) {
      return res.status(409).json({ error: "Swarm is stopped. Deploy first." });
    }

    const tinyfishKey = process.env.TINYFISH_API_KEY;
    if (!tinyfishKey) {
      return res.status(500).json({ error: "TINYFISH_API_KEY is not configured" });
    }

    const taskConfig = config as TaskConfig | undefined;
    const taskMode = mode === "extract" ? "extract" : "discover";
    if (!agentQueue.find(t => t.url === targetUrl)) {
      agentQueue.push({ url: targetUrl, proxy, mode: taskMode, config: taskConfig });
      processQueue();
    }

    res.json({ status: "QUEUED", message: `Agent deployed (${taskMode})` });
  });

  /** Ordre affichage console : TinyFish d’abord, Readability / hybrid ensuite, pool global en dernier. */
  function swarmRunDisplayOrder(run: { id: string; mode?: string; streamingUrl?: string | null; status?: string }): number {
    if (run.id === "global-extract") return 2;
    if (run.status === "STARTING") return 0;
    if (run.mode === "extract" && !run.streamingUrl) return 1;
    return 0;
  }

  app.get("/api/agent/active-runs", (req, res) => {
    const tinyFishRuns = swarmStopped ? [] : Array.from(activeRuns.entries())
      .filter(([, data]) => !data.aborted && (data.status === "RUNNING" || data.status === "PENDING" || data.status === "STARTING"))
      .map(([id, data]) => ({
        id,
        agentLabel: data.agentLabel || "TinyFish",
        streamingUrl: data.streamingUrl,
        status: data.status,
        targetUrl: data.targetUrl || null,
        mode: data.mode || "discover"
      }));
    const extractRuns = Array.from(activeExtractRuns.entries()).map(([id, data]) => ({
      id,
      agentLabel: data.agentLabel,
      streamingUrl: null,
      status: data.status,
      targetUrl: data.targetUrl,
      mode: "extract"
    }));
    const hybridRuns = Array.from(activeHybridExtractions.entries()).map(([id, data]) => ({
      id,
      agentLabel: data.agentLabel,
      streamingUrl: null,
      status: "RUNNING",
      targetUrl: data.targetUrl,
      mode: "extract",
      totalUrls: data.totalUrls
    }));
    const queueSize = globalExtractQueue.length;
    const pendingCount = Array.from(pendingByTarget.values()).reduce((s, p) => s + (p.total - p.processed), 0);
    const globalExtractRun = (queueSize > 0 || pendingCount > 0)
      ? [{
          id: "global-extract",
          agentLabel: `Extraction pool (${globalExtractConcurrency} workers)`,
          streamingUrl: null,
          status: "RUNNING",
          targetUrl: null,
          mode: "extract",
          queueSize,
          inProgress: pendingCount
        }]
      : [];
    const merged = [...tinyFishRuns, ...extractRuns, ...hybridRuns, ...globalExtractRun];
    merged.sort((a, b) => swarmRunDisplayOrder(a) - swarmRunDisplayOrder(b));
    res.json(merged);
  });

  app.get("/api/agent/stream/:runId", async (req, res) => {
    const { runId } = req.params;
    const run = activeRuns.get(runId);
    if (!run || !run.streamingUrl) {
      return res.status(404).json({ error: "Run or streaming URL not found" });
    }

    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

    const apiKey = process.env.TINYFISH_API_KEY;
    const sseResponse = await fetch(run.streamingUrl, {
      headers: { "X-API-Key": apiKey! }
    });

    if (!sseResponse.body) return res.end();

    const reader = sseResponse.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value);
      res.write(chunk);
    }
    res.end();
  });

  app.post("/api/agent/stop", async (req, res) => {
    broadcastLog({ key: "swarm_stop" });
    swarmStopped = true;
    deployStartTime = null;
    agentQueue.length = 0;
    agentCounter = 0;
    activeAgents = 0;
    extractingCount = 0;
    globalExtractQueue.length = 0;
    pendingByTarget.clear();
    globalExtractWorkersStarted = false;
    const apiKey = process.env.TINYFISH_API_KEY;
    for (const [runId, run] of activeRuns.entries()) {
      run.aborted = true;
      if (apiKey && runId) {
        try {
          await fetch(`https://agent.tinyfish.ai/v1/runs/${runId}/cancel`, {
            method: "POST",
            headers: { "X-API-Key": apiKey },
          });
        } catch (e) {
          console.warn(`[Swarm] Failed to cancel TinyFish run ${runId}:`, (e as Error).message);
        }
      }
    }
    activeRuns.clear();
    activeExtractRuns.clear();
    activeHybridExtractions.clear();
    res.json({ status: "STOPPED", message: "Agent queue cleared and active runs signaled to stop" });
  });

  app.get("/api/agent/status", (req, res) => {
    res.json({ activeAgents, queuedAgents: agentQueue.length });
  });

  app.get("/api/proxy-image", async (req, res) => {
    let imageUrl = req.query.url as string;
    if (!imageUrl) return res.status(400).send("No URL provided");

    // Handle relative URLs just in case
    if (imageUrl.startsWith('/')) {
      return res.status(400).send("Invalid relative URL. Must be absolute.");
    }

    try {
      const response = await fetch(imageUrl, {
        headers: {
          "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
          "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
          "Accept-Language": "en-US,en;q=0.9",
          "Referer": new URL(imageUrl).origin
        }
      });

      if (!response.ok) {
        console.error(`[Proxy Image] Failed to fetch ${imageUrl}: ${response.status} ${response.statusText}`);
        throw new Error("Failed to fetch image");
      }

      const contentType = response.headers.get("content-type");
      if (contentType) res.setHeader("Content-Type", contentType);

      // Cache for 24 hours
      res.setHeader("Cache-Control", "public, max-age=86400");

      const arrayBuffer = await response.arrayBuffer();
      res.end(Buffer.from(arrayBuffer));
    } catch (error) {
      console.error(`[Proxy Image] Error fetching ${imageUrl}:`, error);
      res.status(404).send("Image not found");
    }
  });

  // Vite middleware for development
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    app.use(express.static(path.join(__dirname, "dist")));
  }

  // --- DEDUPLICATION TEST FUNCTION ---
  async function runDedupTest() {
    console.log("[TEST] Running deduplication test...");

    const testProjects = [
      {
        title: "Coral Reef Restoration Maldives",
        description: "Project restoring coral reefs in Maldives waters",
        lat: 3.2,
        lng: 73.0,
        url: "https://example.com/project1",
        funder: "Blue Ocean Foundation",
        category: "Marine",
        status: "Active"
      },
      {
        title: "Coral Reef Restoration Maldives",
        description: "Project restoring coral reefs in Maldives waters",
        lat: 3.2001,
        lng: 73.0002,
        url: "https://example.com/project2",
        funder: "Ocean Protectors",
        category: "Marine",
        status: "Active"
      }
    ];

    const savedCount = await saveProjects(testProjects);
    console.log(`[TEST] Saved ${savedCount} projects (deduplicated)`);
  }
  // Uncomment to test manually
  // await runDedupTest();

  // Nettoyage au démarrage : supprime les anciennes sources non utilisées (Hidrografico, NOAA, UK AIMS, Kartverket Place)
  try {
    const del = db.prepare(
      "DELETE FROM nauticals WHERE source NOT IN ('kartverket_sailing', 'cruiserswiki', 'cruiserswiki_wayback')"
    ).run();
    if (del.changes > 0) {
      console.log("[Nauticals] Cache cleared:", del.changes, "legacy points removed");
    }
  } catch (e: any) {
    console.error("[Nauticals] Cleanup error:", e?.message);
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server running on http://localhost:${PORT}`);
  });
}

startServer();