# Blue Intelligence — PRD

## Original Problem Statement
OSINT mapping application with two pipelines: (1) scraper of maritime customs Ports of Entry (PoE, Top-Down approach by worldwide VLIZ EEZs) and (2) scraper of marine conservation projects funded by foundations. React (Leaflet) + FastAPI + MongoDB.

**Massive 2026-08 refactor**: both pipelines shared into a Core architecture, hybrid extraction cascade to preserve TinyFish credits, ML bootstrapping (weak supervision) on existing data, Bottom-Up validation.

**ABSOLUTE CONSTRAINT**: data in the database (4,463 projects + 1,171+ PoE) is a treasure (training set) — no purge, non-destructive upsert everywhere.

## Core architecture (refactor 2026-08-26)
- `llm_core.py` — Universal LLM adapter: Gemini REST cascade (if a key) → Emergent (gemini-2.5-flash) → OpenRouter (gpt-4o-mini JSON mode) with auto fallback. Marine gatekeeper (local ML → LLM → heuristic), strict JSON PoE extraction, grounded search (Gemini google_search or OpenRouter :online with annotations).
- `geo_core.py` — Nominatim geocoding (1.1 s rate-limit + cache) → GeoNames, port-name variants, semantic re-ranking of candidates, snap_to_ocean/land mask, shapely point-in-EEZ, IsolationForest/DBSCAN.
- `dedup_core.py` — Haversine <500 m + fuzzy >60% (raw/normalised/sorted-token ratio), >90% alone. Non-destructive merge_docs, upsert_with_dedup.
- `extract_core.py` — Cascade N1 (httpx + trafilatura/PyMuPDF, free) → N2 (Readability/BS4) → N3 (TinyFish, 120 s cap, opt-in). Regex SERP filter, page metadata, selective depth=2 (links /annuaire, /contacts, /clearance).
- `rag_core.py` — 500-char sentence-aligned chunking, sentence-transformers all-MiniLM-L6-v2 (installed, TF-IDF fallback), top_chunks/select_context, semantic monitoring (content_changed ≥0.95 = skip), rerank_candidates.
- `ml_core.py` — TF-IDF+LogReg gatekeeper trained on 4,462 DB projects (acc 1.0), PoE anomaly scan (IsolationForest zone offsets + Haversine DBSCAN, additive flags), NER dataset export (5,634 rows, PORT_NAME/PROJECT_NAME/LOCATION).
- `osm_validate.py` — Bottom-Up Overpass validation (harbour/marina/customs/border_control/seamark) → osm_confidence 0-1, without touching name/coords. Accessible `.fr` mirror.
- `ai.py` / `geo.py` — back-compat wrappers to llm_core/geo_core.
- `pipeline.py` (Projects Swarm) — N1 crawler discovery first, TinyFish N3 last resort; extraction via cascade + RAG (>6,000 chars); dedup via dedup_core.
- `poe.py` — MD5 + semantic monitoring, Level-2 Retry Query (customs organisation), N1/N2 cascade + 1 TinyFish max/zone, RAG >15,000 chars, non-destructive upsert storage (preserves osm_*, anomalies).
- `ml_routes.py` — /api/ml/status, /train/gatekeeper, /gatekeeper/predict, /anomalies/scan+report, /ner/export-dataset.
- `poe_routes.py` — + /api/poe/validate-osm (start/status/cancel).

## Environment
- Keys (backend/.env): EMERGENT_LLM_KEY, OPENROUTER_API_KEY, TINYFISH_API_KEY, GEONAMES_USERNAME=[REDACTED]. No direct Gemini key. <!-- pragma: allowlist secret -->
- sentence-transformers + torch CPU installed (~2 GB — deploy image size impact).
- SearXNG blocked from the pod → OpenRouter :online fallback operational.
- Basemap: Esri Dark/Light Gray Canvas (CARTO watermarked “API KEY REQUIRED”).

## Data (restored 2026-08-26)
- projects: 4,463 (GeoJSON import), poe_ports: 1,171+ (1,169 restored — the export only contained the geocoded ones out of 1,864), eez_zones: 285 (165 backfilled “ia”).
- Restore: /app/scripts/restore_data.py + POST /api/import/geojson.

## What's been implemented (history)
- [before fork] Complete app: Projects Swarm, EEZ PoE, marinas, formalities UI, batch hub, “Missing project?” crowdsourcing, GeoJSON exports.
- [2026-08-26] Full Core refactor (ticket steps 1-3), DB restore, Esri tiles switch, 25/25 tests (pytest) + testing-agent validation (non-destructiveness proven by field-by-field Mongo diff).
- [2026-08-26 evening] Spec-compliance iteration + 4 features (testing agent 16/16 + 5/5 frontend flows):
  - Local trained spaCy NER (F1=0.968, 5,041 train) — POST /api/ml/train/ner, POST /api/ml/ner/extract, no-LLM fallback in extract_ports_llm. Model: backend/models/ner_spacy/.
  - UNCLOS qualification of the 120 EEZs without PoE (sovereign_entry 69, uninhabited 14, overlapping_claim 25, joint_regime 12) — POST /api/poe/qualify-unclos, blue “§ Legal status (UNCLOS)” block in the zone popup. Automatically cleared ($unset) when a zone gains ports.
  - Map badges: PoE popup shows OSM confidence (green ≥0.5 / amber / grey ∅) + red spatial-anomaly badge (data-testid: poe-osm-badge, poe-anomaly-badge, zone-unclos-block).
  - Full Overpass OSM validation launched on the 1,171 PoE (resumable via only_unchecked; killed by any backend hot-reload — re-run POST /api/poe/validate-osm {"only_unchecked":true}).
  - Compliance: per-country caps removed (no more ports[:25], coerce 150), 10k truncation removed (60k/source + RAG), multilingual query matrix 16 languages (localized_query), SERP regex widened (brochures/tourism/luggage/VTS/duty-free), ms-marco Cross-Encoder for geocode re-ranking (bi-encoder fallback), PDF 60 pages.

- [2026-08-26 night] SERP classifier + auto resume (testing agent 17/17 + 35/36 regression):
  - SERP classifier (ml_core): TF-IDF char n-grams on URL + LogReg, weak supervision (195 real source URLs vs synthetic tourist negatives), acc=0.987/f1=0.983. Endpoints POST /api/ml/train/serp, POST /api/ml/serp/predict {"url"}. Wired into the PoE pipeline via poe.rank_candidates_ml (sort before download + drop score<0.1 if ≥3 alternatives), called after serp_filter and after the Level-2 retry.
  - Auto job resume: state persisted in db.jobs (_id='osm_validation', desired/params/resumed), poe_routes._start_osm_task + schedule_job_resume() (20 s delay) called at server.py startup. Honours params.only_unchecked. Validated E2E (simulated kill → resume → desired=false) + “resume unnecessary” case.
  - OSM validation COMPLETE: 1,171/1,171 PoE checked, 678 high confidence (≥0.5), 154 with no OSM tag within 3 km.
  - Reusable regression tests: tests/test_serp_ml_resume.py (fast, no LLM cost).

- [2026-09-10] Science mode (6th mode, violet #a78bfa) — oceanographic datasets placed on the map + link to their portal sheet:
  - Sources (structured APIs only — no LLM, no scraping): Sextant/SISMER + ODATIS sub-portal via GeoNetwork 4 Elasticsearch JSON API (`/geonetwork/{srv|ODATIS}/api/search/records/_search`, native GeoJSON geom), SeaDataNet EDMED via SPARQL (WKT on the dct:spatial node), active Argo floats via the Ifremer ERDDAP index (`ArgoFloats-index`, last profile per WMO, fleetmonitoring.euro-argo.eu link).
  - Backend: services/science_build.py (GeoJSON/WKT bbox + antimeridian, “world” bbox detection → sheet kept but not placed, non-destructive upsert `_id={source}:{native_id}`), routers/science.py (geojson/count/build/status/cancel/runs/export/import), science_items + science_runs collections (rules snapshot → Runs tab).
  - Catalogue rules: science.catalog_max_records (2000, hard ES cap 10000), science.argo_window_days (30 d).
  - Frontend: SciencePanel (search, source filter, datasets/Argo legend), useScienceLayer (organisation/summary/DOI/WMO/cycle popup + portal-sheet button), ScienceCard console (checkable sources), Review not wired (placeholder), science.geojson export/import.
  - Tests: tests/test_science.py (unit, injected fetchers — antimeridian bbox, EDMED dedup, last Argo profile, per-source error isolation, re-run 100% updated) + tests/test_depth.py (EMODnet parser + cache).
  - Complements 2026-09-10 (evening): approach depth `GET /api/depth` (EMODnet Bathymetry REST, `depth_samples` cache, marina/anchorage popups); togglable WMS layers (shaded bathymetry `mean_multicolour`, substrate `seabed_substrate_1m`, cables `telecablesactual`+`powercables`); SeaDataNet CSR campaign tracks (SPARQL `https://sparql.ifremer.fr/csr/query`, `hasTrack` WKT subsampled to 160 points, `science.csr_max_records`=500 rule). EDMERP (3,628 European projects) has **no** geometry (`dct:spatial` = 0): not mapped; organisations and study areas remain those of catalogue sheets + CSR.

- [2026-09-13] Climatology mode (7th mode, teal #2dd4bf) — sourced monthly atlas, not a forecast:
  - Phrase: **BI shows the atlas. NAVIGUIDE uses it.** `kind: "climatology"` everywhere. Two distinct kinds: getWind/getWave/getCurrent stay NRT/ANFC.
  - Backend: `GET /api/climatology/{meta,point,crossings,wind|wave|current|cyclones.geojson}`. `null` on land / missing snapshot / NaN. Snapshots in `backend/data/climatology/` (IBTrACS v04r01 committed; CMEMS wind/swell/current generated on the Mac). `export_meta` extended (`period`, `month`, `source_ids`, `doi`).
  - Rules: `climatology.*` family (18) — `kind_is_climatology`, `no_llm_for_numbers`, `wave_stat` laws (forbidden to label a mean as P90), written periods.
  - Frontend: `data-testid="mode-toggle-climatology"` button, ClimatologyPanel (1–12 slider, Wind/Swell/Current/Cyclones filters), `climatology-raster@250` / `climatology-vector@260` panes (`pointer-events: none`), useClimatologyLayer only if `mode === "climatology"`. Review / Gold not wired (C8, same as Science).
  - NAVIGUIDE: EEZ/WPI pills off UI (data still fetchable); simulation ETA by month; isochrone MOST_LIKELY + current + P90 no-go + crossings; weather agent cites an IBTrACS integer. No 8th “Climatology” pill.
  - Out of V1: GFS/IFS/ICON/AIFS, Review/Gold, hourly cubes on the VPS, StormGlass as mode source.

## Spec compliance (Untitled document (6).md)
- ✅ 23/25 items fully compliant (SERP classifier now done).
- ⚠️ Partial: NLP query translation (static 16-language matrix instead of local opus-mt); PoE crowdsourcing with a law link (the existing module covers projects).

## Prioritised backlog
- P1: PoE crowdsourcing (skipper proposal + statute link + auto verification).
- P2: local opus-mt for dynamic query translation; OSM confidence filter on the map; projects ↔ customs cross-link; re-import of the ~695 ungeocoded PoE (needs a full backup); EEZ geometry simplification at low zoom (map perf); split of server.py/marinas.py (>700 lines, tech debt).

## Testing notes
- Fast regression: `cd /app/backend && python3 -m pytest tests/ -p no:randomly` (test_ner_unclos_osm.py = 16 non-destructive tests).
- FORBIDDEN: /api/deploy clear_db=true, generate-batch without a limit. Any .py write under /app/backend kills background jobs (uvicorn --reload).
