#!/usr/bin/env tsx
/**
 * Cartographie la structure et l'arborescence de CruisersWiki via l'API MediaWiki.
 * Utilise FlareSolverr (priorité 1) ou Proxy/TinyFish pour contourner Cloudflare.
 *
 * Usage: npm run cruiserswiki:structure
 * Prérequis: FlareSolverr (docker run -d -p 8191:8191 ghcr.io/flaresolverr/flaresolverr)
 *            ou SCRAPE_DO_API_KEY ou TINYFISH_API_KEY en fallback.
 */
import dotenv from "dotenv";
import { writeFileSync } from "fs";
import { join } from "path";
import { cruisersWikiFetch } from "../lib/cruiserswiki-fetch";

dotenv.config();

const API = "https://www.cruiserswiki.org/api.php";
const DELAY_MS = 300;

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

function parseApiResponse(res: { text: string; status: number }): any {
  const trimmed = res.text.trim();
  if (trimmed.startsWith("<") || trimmed.includes("Just a moment") || trimmed.includes("cloudflare")) {
    throw new Error(
      "Cruisers Wiki bloque (Cloudflare). Lancez FlareSolverr: docker run -d -p 8191:8191 ghcr.io/flaresolverr/flaresolverr"
    );
  }
  const data = JSON.parse(res.text);
  if (data?.error) throw new Error(`API: ${data.error.info ?? data.error.code ?? JSON.stringify(data.error)}`);
  return data;
}

async function fetchCategorySubcats(categoryTitle: string): Promise<string[]> {
  const result: string[] = [];
  let cmcontinue: string | undefined;
  do {
    const params = new URLSearchParams({
      action: "query",
      list: "categorymembers",
      cmtitle: categoryTitle,
      cmtype: "subcat",
      cmlimit: "500",
      format: "json",
      origin: "*",
    });
    if (cmcontinue) params.set("cmcontinue", cmcontinue);
    const res = await cruisersWikiFetch(`${API}?${params}`, true);
    const data = parseApiResponse(res);
    const members = data.query?.categorymembers ?? [];
    for (const m of members) {
      const title = m.title ?? "";
      if (title.startsWith("Category:")) result.push(title);
    }
    cmcontinue = data.continue?.cmcontinue;
    if (cmcontinue) await sleep(DELAY_MS);
  } while (cmcontinue);
  return result;
}

async function fetchCategoryInfo(titles: string[]): Promise<Map<string, { pages: number; subcats: number }>> {
  const map = new Map<string, { pages: number; subcats: number }>();
  for (let i = 0; i < titles.length; i += 50) {
    const batch = titles.slice(i, i + 50);
    const params = new URLSearchParams({
      action: "query",
      prop: "categoryinfo",
      titles: batch.join("|"),
      format: "json",
      origin: "*",
    });
    const res = await cruisersWikiFetch(`${API}?${params}`, true);
    const data = parseApiResponse(res);
    const pages = data.query?.pages ?? {};
    for (const p of Object.values(pages)) {
      const page = p as { title?: string; categoryinfo?: { pages?: number; subcats?: number } };
      if (!page?.title) continue;
      const ci = page?.categoryinfo ?? {};
      map.set(page.title, {
        pages: ci.pages ?? 0,
        subcats: ci.subcats ?? 0,
      });
    }
    if (i + 50 < titles.length) await sleep(DELAY_MS);
  }
  return map;
}

function extractRegionsFromWikitext(wikitext: string): string[] {
  const regions: string[] = [];
  const linkRe = /\[\[([^\]|#]+)(?:\|[^\]]*)?\]\]/g;
  let m: RegExpExecArray | null;
  const seen = new Set<string>();
  while ((m = linkRe.exec(wikitext)) !== null) {
    const title = m[1].trim();
    if (title && !title.startsWith("Category:") && !title.startsWith("File:") && !seen.has(title)) {
      seen.add(title);
      regions.push(title);
    }
  }
  return regions.slice(0, 30);
}

async function fetchWorldCruisingGuidesRegions(): Promise<string[]> {
  const params = new URLSearchParams({
    action: "query",
    titles: "World_Cruising_Guides",
    prop: "revisions",
    rvprop: "content",
    rvslots: "main",
    format: "json",
    origin: "*",
  });
  const res = await cruisersWikiFetch(`${API}?${params}`, true);
  const data = parseApiResponse(res);
  const pages = data.query?.pages ?? {};
  const page = Object.values(pages)[0] as { revisions?: { 0?: { slots?: { main?: { "*"?: string } } } } };
  const content = page?.revisions?.[0]?.slots?.main?.["*"] ?? "";
  return extractRegionsFromWikitext(content);
}

async function runStructureScript(): Promise<void> {
  console.log("[CruisersWiki Structure] Démarrage (FlareSolverr + API MediaWiki)...");
  console.log("[CruisersWiki Structure] Prérequis: FlareSolverr ou Proxy/TinyFish");

  const categories: { name: string; pageCount: number; subcategoryCount: number }[] = [];
  let totalPortPages = 0;
  let totalMarinaPages = 0;

  const rootCats = ["Category:Ports", "Category:Marinas", "Category:Anchorages", "Category:Countries"];
  const allSubcatTitles: string[] = [];

  for (const root of rootCats) {
    console.log("[CruisersWiki Structure] Liste sous-catégories de", root, "...");
    const subcats = await fetchCategorySubcats(root);
    allSubcatTitles.push(...subcats);
    await sleep(DELAY_MS);
  }

  if (allSubcatTitles.length === 0) {
    console.warn("[CruisersWiki Structure] Aucune sous-catégorie trouvée. Vérifiez FlareSolverr.");
  }

  console.log("[CruisersWiki Structure] Récupération des comptages (categoryinfo)...");
  const infoMap = await fetchCategoryInfo(allSubcatTitles);

  for (const title of allSubcatTitles) {
    const ci = infoMap.get(title) ?? { pages: 0, subcats: 0 };
    categories.push({
      name: title,
      pageCount: ci.pages,
      subcategoryCount: ci.subcats,
    });
    if (title.includes("Ports")) totalPortPages += ci.pages;
    if (title.includes("Marinas")) totalMarinaPages += ci.pages;
  }

  console.log("[CruisersWiki Structure] Récupération des régions (World_Cruising_Guides)...");
  let topLevelRegions: string[] = [];
  try {
    topLevelRegions = await fetchWorldCruisingGuidesRegions();
  } catch (e) {
    console.warn("[CruisersWiki Structure] World_Cruising_Guides:", (e as Error).message);
  }

  const structureSummary =
    `CruisersWiki (MediaWiki) : ${categories.length} sous-catégories (Ports, Marinas, Anchorages par pays). ` +
    `Total Ports: ${totalPortPages}, Marinas: ${totalMarinaPages}. ` +
    `Régions: ${topLevelRegions.slice(0, 8).join(", ")}${topLevelRegions.length > 8 ? "..." : ""}.`;

  const output = {
    categories: categories.sort((a, b) => b.pageCount - a.pageCount),
    totalPortPages,
    totalMarinaPages,
    topLevelRegions,
    structureSummary,
  };

  const outPath = join(process.cwd(), "cruiserswiki-structure.json");
  writeFileSync(outPath, JSON.stringify(output, null, 2), "utf-8");
  console.log("[CruisersWiki Structure] Terminé. Résultat:", outPath);
  console.log(JSON.stringify(output, null, 2).slice(0, 400) + "...");
}

runStructureScript().catch((e) => {
  console.error("[CruisersWiki Structure] Erreur:", e);
  process.exit(1);
});
