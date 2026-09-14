# Architecture & code analysis — Blue Intelligence

This document presents (1) a file-by-file analysis of the code, (2) the
cleanup that was done, (3) the target layout and split that was applied.

---

## 1. Code analysis

### Backend (`backend/`, FastAPI + MongoDB)

| File | Role | Key functions / classes |
|------|------|-------------------------|
| `server.py` (~1,750 l.) | FastAPI entry point: settings, projects, GeoJSON import/export, marinas, anchorages, enrichment, Stripe donations, EEZ crossings, user manual | `get_settings`, `project_to_feature`, `/api/*` endpoints, `_run_marina_enrich_one`, `_run_project_enrich`, `_stripe`, in-memory states (`EnrichBatchState`, `ZeeComputeState`) |
| `llm_core.py` | **Single LLM adapter (OpenRouter)** — all AI completions | `ask_json`, `ask_text`, `gatekeeper_check`, `extract_project`, `extract_ports`, `llm_geocode`, `grounded_search`, `parse_json_flexible` |
| `pipeline.py` | Discovery/extraction swarm for marine projects (TinyFish SSE → HTTP crawler → Readability → LLM) | `Swarm` class (`deploy`, `stop`, `status`, workers), `pick_image` |
| `poe.py` | Sovereign [EEZ → Ports of Entry] pipeline: VLIZ referential, multilingual search, government whitelist, collect, extract, geocode, MD5/semantic monitoring | `build_referential`, `generate_zone_poe`, `build_whitelist`, `url_allowed`, `qualify_unclos`, `zone_to_item`, `ports_to_geojson` |
| `poe_routes.py` | Formalities-mode endpoints + automatic refresh + job resume | `TaskState`, `_auto_refresh_loop`, `/api/poe/*` endpoints |
| `marina_world.py` | Worldwide `leisure=marina` dump (Overpass tiles, `osm_id` identity, slim GeoJSON, Maps link) | `build_world_marinas`, `marinas_to_slim_geojson` |
| `marina_maps_place.py` | Google `/maps/place/` sheet signal (TinyFish Search or OSM tag, no Maps scrape) | `resolve_maps_places`, `is_google_place_url` |
| `anchorages.py` | Anchorage build (Overpass only, same corridors) | `build_anchorages`, `anchorages_to_geojson` |
| `enrichment.py` | Marina enrichment — OpenRouter → TinyFish → OSM tags chain, credit guardrail | `enrich_marina`, `enrich_via_openrouter`, `enrich_via_tinyfish`, `enrich_from_osm_tags`, `openrouter_check_credit` |
| `geo_core.py` | Unified geospatial: Nominatim → GeoNames geocoding (cache + rate-limit), land mask, coastal snap, point-in-EEZ, spatial anomalies | `geocode`, `geocode_port`, `haversine_km`, `is_ocean`, `snap_to_ocean`, `coast_distance_km` |
| `extract_core.py` | Parse cascade N1 (trafilatura/PyMuPDF) → N2 (Readability/BS4) → N3 (capped TinyFish), SERP filter, internal follow-ups | `extract_cascade`, `serp_filter`, `internal_followups` |
| `dedup_core.py` | Non-destructive spatio-textual dedup (Haversine < 500 m + fuzzy > 60%) | `is_duplicate`, `deduplicate_list`, `merge_docs`, `normalize_name` |
| `rag_core.py` | Local RAG: ~500-char chunking, cosine-similarity selection, semantic monitoring (sentence-transformers, TF-IDF fallback) | `select_context`, `content_changed`, `semantic_rerank` |
| `ml_core.py` | Local ML (weak supervision): TF-IDF+LogReg gatekeeper, SERP classifier, spaCy NER, IsolationForest/DBSCAN anomalies | `predict_relevance`, `predict_serp`, `extract_entities`, `train_*` |
| `ml_routes.py` | `/api/ml/*` endpoints (training, predictions, anomalies, NER) | `TRAIN_STATE`… states |
| `osm_validate.py` | Bottom-Up PoE validation via Overpass (`osm_confidence`) | `validate_ports` |
| `zee.py` | Official-route EEZ crossings (shapely intersection, 4 fallback levels) | `build_zee_crossings`, `crossings_to_summary`, `filter_french_territories` |
| `tinyfish_client.py` | TinyFish HTTP client (sync/async run + polling) | `tf_run_sync`, `tf_run_async`, `tf_get_run`, JSON schemas |
| `seeds.py` / `categories.py` | Static data: foundation MasterSeeds, category taxonomy | `MASTER_SEEDS`, `CATEGORY_GROUPS`, `normalize_category` |
| `tests/` | pytest suite (14 files) — most require the server running (`REACT_APP_BACKEND_URL`) | — |

### Frontend (`frontend/src/`, React CRA + Leaflet + Tailwind)

| File | Role |
|------|------|
| `index.js` / `App.js` | Bootstrap + global state (active mode, settings, swarm status, i18n) |
| `api.js` | axios client to `REACT_APP_BACKEND_URL/api` |
| `i18n.js` | EN/FR dictionaries |
| `components/MapView.js` | Leaflet map: project/marina/anchorage clusters, EEZ choropleth, popups, official route |
| `components/Header.js` | Mode switch (historical screenshot: 5 modes; the product contract is **7** — see README / `CONTRATS_MODES.md`), donations, language, theme |
| `components/ProjectList.js`, `MarinasPanel.js`, `FormalitiesPanel.js` | Per-mode side panels (search, filters, lists) |
| `components/AuditView.js` + `BatchHub.js` + `AgentConsole.js` | Operator console: KPIs, telemetry, batch triggers, live agent view |
| `components/SettingsPanel.js` | Cross-cutting settings (docs, import/export, map, API keys) |
| `components/Donations.js`, `ReportModal.js`, `SwarmPanel.js` | Stripe pot, project report, swarm status |

---

## 2. Cleanup done

### Removed (git history keeps them)

| Item | Reason |
|------|--------|
| `prototype_ai_studio/` | Google AI Studio prototype (Vite/TS) fully disconnected from the app |
| `.emergent/` | Internal Emergent platform tooling (pod cron/webhooks) |
| `test_reports/`, `test_result.md`, `backend_test.py` | Historical artefacts from the platform’s test iterations |
| `tests/` (root) | Legacy iteration tests, redundant with `backend/tests/` |
| `memory/test_credentials.md` | Obsolete environment notes (mentioned Emergent keys) |
| `package-lock.json` (root) | Orphan — no root `package.json` |
| `backend/ai.py`, `backend/geo.py` | Empty back-compat wrappers — merged into `llm_core.py` / `geo_core.py` |
| `backend/data/route.geojson.bak_antimeridian` | Backup file |
| `backend/data/cached_pdfs/`, `backend/data/.tld_cache/` | Runtime caches (now gitignored) |
| `emergentintegrations`, `litellm` (private wheel), `google-generativeai` & co, `openai`, `tiktoken` dependencies | No more Gemini/Emergent calls — Stripe migrated to the official `stripe` SDK |

### Moved

- `memory/PRD.md` → `docs/PRD.md`
- `design_guidelines.json` → `docs/design_guidelines.json`

---

## 3. Target layout (APPLIED)

The historical flat backend (18 modules at the same level, `server.py` ~1,750 l.)
was reorganised into the `app/` package — the route surface stayed
byte-identical (85/85 checked against `main`):

```
backend/
├── server.py                   # shim: `from app.main import app` (uvicorn server:app unchanged)
├── app/
│   ├── main.py                 # FastAPI assembly, middlewares, startup/shutdown
│   ├── config.py               # paths (DATA_DIR, MODELS_DIR, ROUTE_FILE), env, DEFAULT_SETTINGS
│   ├── db.py                   # Motor client + get_settings
│   ├── state.py                # shared singletons (swarm)
│   ├── routers/                # 1 file = 1 REST domain
│   │   ├── projects.py         #   /projects, /import|export geojson, /categories, enrich, /report-project
│   │   ├── swarm.py            #   /swarm/*, /stats, /telemetry, /failed/* (Force Extract)
│   │   ├── marinas.py          #   /marinas/*, /anchorages/*, unit + batch enrich
│   │   ├── formalities.py      #   /poe/* (ex poe_routes.py)
│   │   ├── ml.py               #   /api/ml/* (ex ml_routes.py)
│   │   ├── donations.py        #   /donations/*, /payments/*, Stripe webhook
│   │   └── misc.py             #   health, /settings, /manual, /route, /zee/*
│   ├── services/               # business logic (no FastAPI imports)
│   │   ├── swarm_pipeline.py   #   ex pipeline.py
│   │   ├── poe_pipeline.py     #   ex poe.py
│   │   ├── marina_build.py     #   corridor / SHOM (anchorages + helpers)
│   │   ├── marina_world.py     #   worldwide leisure=marina dump
│   │   ├── marina_maps_place.py #  /maps/place/ signal (TinyFish Search, no scrape)
│   │   ├── anchorage_build.py  #   ex anchorages.py
│   │   ├── marina_enrich.py    #   ex enrichment.py
│   │   ├── zee_crossings.py    #   ex zee.py
│   │   └── osm_validate.py
│   ├── core/                   # reusable cross-cutting bricks
│   │   ├── llm.py              #   ex llm_core.py (OpenRouter)
│   │   ├── geo.py              #   ex geo_core.py
│   │   ├── extract.py          #   ex extract_core.py
│   │   ├── dedup.py            #   ex dedup_core.py
│   │   ├── rag.py              #   ex rag_core.py
│   │   ├── ml.py               #   ex ml_core.py
│   │   ├── tinyfish.py         #   ex tinyfish_client.py
│   │   └── tasks.py            #   generic TaskState (replaces 4 duplicated classes)
│   └── static_data/            # seeds.py, categories.py
├── data/ · models/ · tests/
```

Functions that were split:

1. **`poe_pipeline.generate_zone_poe`** → orchestrator + 5 steps:
   `_skip_if_unchanged` (MD5/semantic monitoring), `_find_sources`
   (search + gatekeeper + Level-2 + bootstrapping), `_collect_texts`
   (N1/N2/N3 cascade), `_extract_and_geocode`, `_persist_zone`
   (non-destructive upsert);
2. **`server.py`** → 7 routers per domain (see above);
3. **Task states** (`TaskState`, `EnrichBatchState`, `ZeeComputeState`,
   `BuildState`) → a single `app/core/tasks.TaskState` class +
   `prune_tasks` / `new_task` helpers;
4. **Frontend**:
   - `MapView.js` (899 l. → ~300 l.): orchestrator + per-layer modules under
     `components/map/` (`constants.js`, `zonePopup.js`, `useRouteLayer.js`,
     `useProjectsLayer.js`, `useMarinasLayer.js`, `useAnchoragesLayer.js`,
     `useFormalitiesLayers.js`);
   - `BatchHub.js` (709 l. → 36 l.): dispatcher + 1 card per file under
     `components/audit/` (`CardShell.js`, `ProjectsCard.js`, `MarinasCard.js`,
     `FormalitiesCard.js`) — a card’s polling runs only while it is
     mounted.

## 4. Renames

### Visible features (applied)

| Before | After | Reason |
|--------|-------|--------|
| “Swarm Intelligence Audit” (header button) | **Console** (title: “Console de supervision” / “Operations Console”) | Shorter, describes the real function (supervision + triggers), without jargon |
| “Soutenir Blue Intelligence” button (Stripe donations) | **removed** | Stripe dropped — all donation/payment code was removed |
| “Moteur d'extraction” selector (Gemini/GPT/Claude/OpenRouter) | static **OpenRouter** badge | A single engine now |
| “Filtre par catégorie” dropdown (Projects mode) | **removed** | Redundant with the clickable legend, which already filters |
| “Rafraîchir” button (Marinas banner) | **removed** | The list refreshes automatically every 8 s |

### Code functions (proposal — apply over time)

| Current | Proposed | Reason |
|---------|----------|--------|
| `swarm_pipeline.Swarm.deploy` | `Swarm.start_discovery` | “deploy” sounds like infrastructure deployment |
| `poe_pipeline.generate_zone_poe` | `generate_ports_of_entry` | Spell out the produced object |
| `marina_enrich.enrich_via_tinyfish` | `scrape_official_site` | Describes the action, not the vendor |
| `core.llm.ask_json` / `ask_text` | `complete_json` / `complete_text` | Standard LLM completion vocabulary |
| `core.geo.snap_to_ocean` | unchanged | Name already exact |
| `routers/swarm._force_extract_one` | `force_extract_failed_url` | Clarify the target (failed URL) |
| `core.rag.select_context` | `select_relevant_chunks` | Describes the mechanism (chunk similarity) |
| `ia` / `ia_sans_source` state (EEZ statuses) | `generee` / `generee_sans_source` | “ia” is ambiguous; migrate data + UI in a dedicated pass |

## 5. Possible future evolutions

- Persist task states in a Mongo `jobs` collection so they survive
  restarts (already done for OSM validation);
- Extract LLM prompts into dedicated files (`app/core/prompts/`);
- Switch settings reads to a TTL cache to avoid a Mongo round-trip
  per request;
- Tunable rules catalogue: `data/run_rules.json` + `core/run_rules.py`
  (`params.rules` snapshot per run — see `docs/REGLES_PARAMETRES.md`).
