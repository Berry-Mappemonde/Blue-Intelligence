# Archive — Blue-Intelligence (swarm TypeScript)

**Source :** [NAVIGUIDE-for-Berry-Mappemonde/Blue-Intelligence](https://github.com/NAVIGUIDE-for-Berry-Mappemonde/Blue-Intelligence)  
**Commit :** `4d922cd` (2026-03-30, « Update README.md »)  
**Statut :** référence uniquement — le mode Projets de ce monorepo a déjà
dépassé ce swarm (904 MasterSeeds vs 78 ici, Mongo, cascade N1/N2/N3).

Le `README.md` de ce dossier est le README **d’origine** du dépôt TS.

## Pourquoi c’est là

Le trésor n’est pas le swarm projets (déjà refondu). C’est **l’OSINT des
guides de croisière** et quelques briques autour.

| Chemin | Intérêt pour Blue-Intelligence-Map |
|--------|-------------------------------------|
| `docs/WAYBACK_CDX.md`, `lib/wayback-phase2.ts`, `lib/wayback-phase3*.ts` | Inventaire massif d’archives Internet Archive (pas juste un miroir d’URL déjà connue) |
| `docs/CRUISERSWIKI_SCRAPING.md`, `lib/cruiserswiki-fetch.ts` | Contourner Cloudflare (FlareSolverr → Scrape.do → Playwright) |
| `docs/VISION_EXTRACTION_NAUTICALS_HYBRIDE.md`, `lib/nautical-extraction-pack.ts` | Extraire ports / mouillages / dangers **sans LLM en production** |
| `docs/EXTRACTION_PACK_WORKFLOW.md`, `tests/`, `scripts/validate-extraction-pack.ts` | Boucle gold : affiner des regex hors prod |
| `server.ts` | APIs nauticals + sync **Kartverket** (Norvège) et **Hidrografico** (Portugal) |
| `src/App.tsx` | Calque Nauticals + popups (référence UI) |
| `data/DeepLinkCacheProjectsPages.json` | **9 171 URLs** de pages projets (import one-shot possible après audit Mongo) |
| `data/DeepLinkCacheProjectsLists.json` | 78 listes de découverte |
| `data/MasterSeeds.json` | 78 portails — noyau historique, à comparer aux 904 actuels |
| `lib/domainScoring.ts` | Prioriser les sites qui donnent de vrais projets (score de Wilson) |
| `lib/semanticDedup.ts` | Dédup par similarité de phrases (TensorFlow.js) |
| `cruiserswiki-structure.json`, `scripts/cruiserswiki-structure-agent.ts` | Cartographie des catégories wiki (ports / marinas Méditerranée) |
| `env.example` | Modèle de variables (TinyFish, Claude, FlareSolverr) — sans secrets |
| `env/wayback-cdx.public.env.example` | Réglages CDX **non secrets** (renommé : le dépôt ignore `*.env`) |
| `lib/gshhg-*.ts`, `data/gshhg/` | Masque terrestre NOAA (Map utilise déjà `global_land_mask`) |

## Non copié

Bases SQLite vides, `node_modules`, `package-lock.json`, logos `public/`,
config Vite. Le déploiement Node/PM2 (`docs/DEPLOIEMENT-VPS-OVH.md`) est
gardé comme doc historique seulement.
