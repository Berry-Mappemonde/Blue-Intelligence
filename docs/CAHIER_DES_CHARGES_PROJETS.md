# Specification — Marine conservation projects

Scoping document for the **Projects** mode of Blue Intelligence.
It rereads the code, the PRD, the architecture, the GeoJSON seed, the Formalities (PoE) specification,
and the **review of 7 September 2026** (32 Berry-Mappemonde comments on v1.0).

Written in plain language: it is the contract of what we are looking for, and what we refuse.

Version **2.0** — 7 September 2026. **Complete** document + **implementation plan** (phases, files, API, acceptance tests).

**Contents**

1. In one sentence
2. Why this work exists
3. What we want to obtain
4. What we do not want
5. Vocabulary
6. The two strategies
7. Rules
8. Sources and tools
9. The code — where each piece lives
10. S_ocean score
11. Hard constraints
12. Acceptance criteria
13. Current state and gaps
14. Implementation plan
15. Documents and conversations this specification inherits from
16. Who does what
17. Lifecycle of a project
18. The second deliverable: funder portals
19. Algorithm (discovery, sites, Follow the Money)
20. Data model
21. What the user sees
22. MasterSeeds inventory
23. Gatekeeper and taxonomy
24. Concrete examples
25. Acceptance tests
26. Risks
27. Out of scope
28. Annexes
29. Trace of the review comments (v1 → v2)

---

## 1. In one sentence

Find every marine conservation, restoration or protection project **actually carried out** (one page, one or more places, several possible funders), **funded by foundations**, **tied to a place in the world precise enough and theoretically accessible by boat**, put them on the map, and never stick onto it a terrestrial programme, a home page, an NGO headquarters, or an invented GPS.

This **excludes** projects that are too general, or that are not clearly located at one or more places accessible by boat. We are clearly doing **eco-tourism**: a skipper must be able to say “I can go see that”.

---

## 2. Why this work exists

Ocean foundations publish their actions on hundreds of sites. The v1 map (~4,463 points, ~861 funders) has already gathered that web. Many points are **not visitable**: headquarters in Washington, country centroid, hashed ocean rectangle, `snap_to_ocean` snap tens of kilometres from the real place.

Blue Intelligence maps them for the Berry-Mappemonde expedition and for eco-tourism: **where** to go, **who** funds, **which page** to read. A GPS is not the perimeter of an MPA.

The v1 stock remains a **treasure** (restoration, review, future Gold). Losing it is losing both.

---

## 3. What we want to obtain

Two deliverables, inseparable:

1. **The map of visitable sites.**
   A project may have **several points** (several actions of the same programme).
   Each point: site name, GPS of the **action place** (not the HQ), boat accessibility, URL, funder(s), description, S_ocean, `geo_source`.

2. **The funder portals.**
   MasterSeeds = the **~861 funders already discovered** (plus those Follow the Money will add), not only the original 21 curated portals. For each: name, listing URL if known, last scan, pages seen.

A project without a site precise enough is **not published**. It stays as a seed / review queue (`unlocated`). We do not snap toward “a nearby sea” to pretend.

---

## 4. What we do not want

- **Terrestrial or freshwater** projects (except accessible coastal estuary / mangrove / delta).
- Programmes that are **too general** (“protect the oceans”) without a named site.
- **Generic pages**: home, news, donations, jobs, shop.
- An **invented GPS**: `ocean_fallback_coords`, estimate in the middle of a basin, country centroid.
- A **registered office** (Paris, London, Washington, Monaco-city of the NGO) presented as the project.
- **`snap_to_ocean`** as a patch: the snapped point no longer means anything.
- A map that **overwrites** `projects` (`clear_db`, `DELETE /api/projects`). These functions **disappear**.
- TinyFish **Agent** as a daily engine (credits). Search and Fetch are the normal TinyFish tools.
- Inventing a title, a site, or a funder absent from the sources.

---

## 5. Vocabulary

| Word | Meaning here |
|------|--------------|
| **Project** | A marine action described on a URL, funded by one or more foundations. |
| **Site** | An action place **precise enough** and **accessible by boat** (bay, reef, MPA, marina, island, estuary). A project may have *n* sites. |
| **Accessible by boat** | A skipper can theoretically get there (sea, coast, harbour, coastal MPA). Not an office, not an inland city. |
| **Funder** | Organisation in `funders`. MasterSeed = the union of the ~861 already seen. |
| **Swarm** | Discovery + extraction. **No longer** writes the v1 map: only a **run**. |
| **v1 map** | Current `projects` collection. Treasure. Review, not purge. |
| **Run** | Isolated generation `project_run_*`, modelled on `poe_run_*`. Manual promotion afterwards. |
| **Snapped / fallback** | v1 defects. Forbidden in new publication. Review candidates, excluded from future Gold. |
| **Gold Dataset** | Does not exist yet (no mapping of this kind existed). We can **create** one: v1 **minus** snapped **minus** ocean fallback, after review. |
| **Review** | Operator UI: accept / reject / edit a site, promote a run. |
| **Configurable rules** | Gatekeeper thresholds, distances, ceilings: in `settings` / JSON, **not hard-coded** in the code. |

---

## 6. The two strategies

We do not choose. We make them work together.

### 6.1 Top-Down — from the portal to the pages

We start from a **funder** (the ~861, not only 21).

1. Listing URL if we have it; otherwise infer it from the `url` already in the database for this funder.
2. Discover project pages: HTTP crawler → TinyFish **Search / Fetch** (free, quotas) → Agent **only** if still 0.
3. `deeplink_pages` cache + **run** queue.
4. Extract, judge “is this a locatable project?”, find the **sites**.
5. Write into `project_run_projects`, never into `projects`.

### 6.2 Bottom-Up — from the URL / the v1 point to the site

We start from the stock:

- v1 map (including snapped / fallback: to review, not to republish as-is);
- DeepLinkCache;
- skipper reports;
- `failed` / `unlocated` queue.

For each seed: does the page describe **one or more places accessible by boat**? If yes, extract those sites. If no, `unlocated` — no GPS patch.

### 6.3 Cross-check

| | Top-Down | Bottom-Up |
|---|---|---|
| Start | a funder / listing | a URL or a v1 point |
| Question | which project pages? | which **visitable sites** on this page? |
| Product | URLs + extracts in a run | verdict + sites, or `unlocated` |
| Weakness | noise, homes | does not discover a new portal |
| Strength | finds the listings | capitalises the 4,463 and the 861 |

---

## 7. Rules

### 7.1 Golden rule

We publish only **marine actions funded by foundations**, with a URL, and **at least one site precise enough that a boat can get there**.

Consequences:

- Forest, mountain, inland lake: no.
- Estuary, mangrove, delta, coastal blue carbon: yes, if the place is named.
- World programme: **seek each action place**. Several points > a “global” centroid. No invented representative GPS.
- NGO headquarters: **never** a site. The geocoder must refuse them.
- About / donate / news page: no.
- `snap_to_ocean`: **forbidden** for publishing. We seek the real place, or we leave `unlocated`.
- `ocean_fallback_coords`: **forbidden** on the map and in a promoted run.

### 7.2 Sources

- Evidence = the project page (`url`) + the site pages it cites.
- Funders = those of the page / the seed, mergeable, never invented.
- OSM, Nominatim, GeoNames, MPA polygons: **help locate**, do not prove the project.
- Claude Haiku **may** serve (filter, place judge, second reader) if the budget is open. This is no longer reserved for PoE.
- TinyFish Search / Fetch: normal tools. Agent: last resort, counter, cap.

### 7.3 Geography

A published site has a GPS **of the action place**:

- already at sea, or on the shoreline / harbour (a few kilometres, **configurable** threshold, tight default ~15 km);
- the point stays **where the geocoder found it** — we do not slide it toward the water;
- too inland, HQ, (0,0), random ocean basin: `unlocated`;
- several sites = several geometries attached to the same `project_id`.

### 7.4 Map and runs

- `projects`: **no purge**. Non-destructive upsert at **promotion** only.
- Every crawl / swarm writes into `project_run_*`.
- `clear_db` and `DELETE /api/projects`: **removed** (API 410 / 400, no more Console checkbox).
- GeoJSON import: skip known URL, merge, no overwrite of v1 GPS except review.

### 7.5 Rules outside compiled code

ML thresholds (0.85 / 0.12), `min_marine_score`, `max_inland_km`, TinyFish Agent ceilings, `max_partner_orgs`: **`settings` + optionally `backend/data/project_rules.json`**. Changing a rule must not require a Python commit, only a setting.

---

## 8. Sources and tools

### 8.1 Evidence (pages)

| Tool | Role | What it is not |
|------|------|----------------|
| Project / site pages | Evidence of the project and the places | — |
| HTTP crawler N1 | Simple listings, free | JS pagination |
| TinyFish **Search** | Find listings and site pages | Not Agent |
| TinyFish **Fetch** | Page mirror (free, quota) | Not Agent |
| TinyFish **Agent** | JS / pagination if Search+Fetch+crawler = 0 | Daily engine |
| N1/N2/N3 cascade | Text (trafilatura ∥ Readability → Chromium → mirror) | Does not invent |
| OpenRouter | Extraction, grey-zone gatekeeper | — |
| **Claude** | Place judge / second reader, shared budget | Not mandatory |
| Local RAG | Long pages | Not a GPS |

### 8.2 Signals (seeds and control)

| Tool | Role | Caution |
|------|------|---------|
| v1 map | 4,463 projects, ~861 funders | Never overwrite it; snapped/fallback → review |
| Widened MasterSeeds | Union of v1 funders + 21 curated listings | Listing URL sometimes unknown: to discover |
| DeepLinkCache | URLs already seen | Homes possible |
| Reports | Skipper, `Community Report` | Same site contract |
| Nominatim / GeoNames | Named place | HQ and cities: to filter |
| MPA polygons (ex-`/api/mpa`) | Geocoding hint for an MPA name | Not project evidence; map layer still out of deliverable |
| `dedup_core` | URL, or name+distance | Merge all empty fields (`merge_docs`) |

### 8.3 Excluded from discovery

`CRAWL_BLACKLIST` (configurable): contact, about, donate, news, shop, jobs…

---

## 9. The code — where each piece lives

Today (to evolve, § 14):

| File | Current role | v2 target |
|------|--------------|-----------|
| `services/swarm_pipeline.py` | Discovers + **writes `projects`** | Discovers + writes **`project_run_*`**; no more snap / fallback |
| `routers/swarm.py` | deploy (`clear_db`), Force Extract | `clear_db` refused; Force Extract = same pipeline, gatekeeper, run |
| `routers/projects.py` | list, import, enrich, `DELETE` | `DELETE` → 410; enrich does not snap; sites[] |
| `static_data/seeds.py` | 21 portals | Loader of the ~861 (`data/master_seeds.json`) |
| `core/llm.py` | `extract_project`, gatekeeper | Multiple sites; thresholds read from settings; optional Claude |
| `core/geo.py` | `snap_to_ocean`, `ocean_fallback_coords` | Kept for other uses / debug; **Projects pipeline no longer calls them** |
| `core/tinyfish.py` | Agent + Search/Fetch | Search/Fetch first; capped Agent |
| `services/poe_runs.py` | Isolated-run model | **Copy** `project_runs.py` |

Frontend: `SwarmPanel`, `ProjectList`, `useProjectsLayer`, `ProjectsCard`, `ReportModal`, `AuditView`. Target: clear_db checkbox **gone**; review screen; one project = several markers.

---

## 10. S_ocean score

Bundle 0–1 (extractor or heuristic). The `min_marine_score` threshold cuts at **entry**. It does not rewrite v1.

New, distinct signal: **`site_ok`** (bool + reason) — is the place precise enough and accessible by boat? Without `site_ok`, no publication, even if S_ocean is high.

---

## 11. Hard constraints

1. **Treasure.** 4,463 projects + 1,171+ PoE: no purge.
2. **Visitable site.** No point without an action place accessible by boat.
3. **No GPS patch.** Neither snap, nor ocean fallback, nor HQ.
4. **Isolated runs.** The swarm does not touch `projects`.
5. **Purges removed.** No more `clear_db`, no more `DELETE /api/projects`.
6. **TinyFish Agent = scalpel.** Search/Fetch first.
7. **Claude allowed** for Projects if the budget is open.
8. **Configurable rules.** No magic 0.85 / 0.12 / 500 km in the source.
9. **Indicative** map. A point is not the MPA polygon.

---

## 12. Acceptance criteria

For a **funder**:

1. Portal sheet (name, listing or “listing unknown”, last scan).
2. Each published **site**: name, action-place GPS, URL, funders, not HQ, not snapped, not fallback.
3. Generic pages / programmes without a place: `unlocated` or `rejected`, not on the map.
4. A programme on 4 islands → up to 4 points, same `project_id`.
5. Popup: URL + place + S_ocean. The visitor understands where to go.
6. v1 has lost no document, except a rejection **written** in review.

For a **run**: `wrote_projects: false` until promotion; `sites` / `unlocated` / `rejected` counters; no call to `snap_to_ocean` or `ocean_fallback_coords`.

---

## 13. Current state and gaps

### Already there

- Top-Down swarm 21 seeds, crawler, fallback TinyFish Agent, DeepLinkCache, saturation.
- Gatekeeper ML → LLM → heuristic, JSON extraction, 9-family categories.
- Map, filters, report, enrich ↻ (re-text, **not** the GPS).
- GeoJSON import/export, 4,463 seed.
- Console test/full.

Seed breakdown (4,463): Research 890, Conservation 765, Policy 490, Other 474, MPA 402, Pollution 391, Coastal 389, Fisheries 361, Education 301. ~861 funders. ~43 `snapped` in the export GeoJSON (the `geo_source` field is not there: ocean fallback is visible in the database, not in the seed).

### v2 gaps (what the code must catch up)

| Gap | Target |
|-----|--------|
| Live write into `projects` | `project_run_*` + promotion |
| `clear_db` / `DELETE` | **Removed** |
| `ocean_fallback` / `snap_to_ocean` in the swarm | **No longer called**; inland → `unlocated` |
| 21 MasterSeeds | **~861 funders** |
| One point per project | **n sites** |
| Force Extract without gatekeeper | Same `_process_url` / run |
| Dedup = funders only | `merge_docs` |
| Hard-coded thresholds | `settings` / `project_rules.json` |
| Projects Claude “forbidden” | Allowed if budget |
| TinyFish Agent too early | Search/Fetch first |
| No review UI | Queue + promote |
| Frozen categories | Trainable later (**not a priority**) |
| Telemetry without `dataset` | `projects` field (cosmetic) |
| `/api/mpa` 410 | Reuse the polygons **behind the scenes** to geocode an MPA name |

---

## 14. Implementation plan

Four phases. We relaunch **no** world swarm on `projects` before phase B.

### Phase A — Stop breaking the contract (first)

Goal: the next Deploy click can no longer empty the database nor place a ghost islet.

| Task | Files | Detail |
|------|-------|--------|
| A1. Kill the purges | `routers/projects.py`, `routers/swarm.py`, `swarm_pipeline.py`, `ProjectsCard.js` | `DELETE /api/projects` → **410**. `clear_db=true` → **400**, ignored in `deploy`. Console checkbox removed. |
| A2. No more GPS patch | `swarm_pipeline.py`, `routers/swarm.py` | No longer call `snap_to_ocean` or `ocean_fallback_coords`. If no place GPS, or point too inland: `failed` stage `unlocated`. Coastal point: we **keep** the geocoded GPS (harbour land OK). |
| A3. Rules outside code | `config.py`, `routers/misc.py`, `core/llm.py`, `core/ml.py` | `project_rules` in settings: `gatekeeper_accept`, `gatekeeper_reject`, `min_marine_score`, `max_inland_km` (default 15), `allow_tinyfish_agent`, `max_partner_orgs`. `core` reads these keys. |
| A4. Tests | `tests/test_project_contract.py` | 410 on DELETE; 400 on clear_db; process_url / helper: inland → no insert; no import of `ocean_fallback` on the publish path. |

Exit criterion A: contract pytest green; the UI no longer offers “empty the database”.

### Phase B — Isolated runs (before any new crawl)

Copy Formalities. Harmonise run functions across modes (same fingerprint, same events, same Console).

| Task | Files | Detail |
|------|-------|--------|
| B1. Collections | `project_runs.py` (new), `main.py` indexes | `project_runs`, `project_run_projects` (1 line = 1 site or 1 project+sites[]), `project_run_events`. `wrote_projects: false`. |
| B2. Wire the swarm | `swarm_pipeline.py` | `deploy` takes `run_id`; insert → `project_run_projects`. No more `insert_one` into `projects`. |
| B3. API | `routers/project_runs.py` or `/api/projects/runs` | POST run, GET status/diff/report, POST promote (later, manual). |
| B4. Console | `ProjectsCard.js`, `FormalitiesCard` as model | Launch a run, not “Deploy onto the map”. |
| B5. Force Extract / reports | `swarm.py`, `projects.py` | Same pipeline, same run (or `enrich` run). Gatekeeper mandatory. |
| B6. `dataset: "projects"` | `telemetry()` | Stats alignment. |

Exit criterion B: a test run (3 seeds) fills `project_run_*`, `projects.count` unchanged.

### Phase C — Action places (business core)

| Task | Files | Detail |
|------|-------|--------|
| C1. `sites[]` schema | `llm.py` `extract_project` | JSON: `sites: [{name, location, lat, lon, evidence}]` + financeurs[]. A world programme → several sites or `sites: []` + `unlocated`. |
| C2. Place judge | `project_geocode.py` (new) | Refuse HQ (funder city, headquarters/siège words). Nominatim + GeoNames. Claude or OpenRouter: “is this toponym a visitable marine action place?”. MPA polygon if the name matches (geocoding, not map layer). |
| C3. Multi-points | `project_to_feature` / Leaflet layer | One `project_id`, *n* Features, or GeometryCollection. Popup: **site** name. |
| C4. TinyFish | `_discover` | Crawler → Search → Fetch; Agent if `allow_tinyfish_agent` and still 0. |
| C5. MasterSeeds 861 | script `scripts/export_master_seeds.py`, `data/master_seeds.json` | Distinct union of `funders` + 21 curated URLs, **without priority**. Listing URL: most frequent domain of this funder’s projects, or to discover. Ceiling `max_partner_orgs` = Follow the Money novelties only. |
| C6. Dedup | `_dedup_merge` | Call `merge_docs`. |

Exit criterion C: on a sample (Hope Spots, a multi-island programme, a Pew headquarters), sites published in the **run** are visitable; 0 HQ; 0 fallback.

### Phase D — Review, Gold, ML

| Task | Files | Detail |
|------|-------|--------|
| D1. Review queue | collection `project_review`, Review tab (`docs/CAHIER_DES_CHARGES_REVIEW.md`) | Queues: v1 `snapped`, `fallback`, `unlocated`, `hq_suspect`, run↔v1 mismatches. Actions: accept site, edit GPS, reject, **Gold** (accepted sheet on the map). |
| D2. Gold | export | v1 **minus** snapped **minus** fallback, **plus** review accepted. Serves the gatekeeper. |
| D3. Retrain the gatekeeper | `ml.py` | **After** D2, not before the first isolated run. The v1 model is biased; relaunching it now recopies headquarters. |
| D4. Categories | later | Train the `normalize_category` indices. **Not a priority** (the 9 families remain a display bonus). |

Exit criterion D: an operator can clean v1 without a Mongo script; an exportable Gold exists.

### Order and dependencies

```
A (safety) → B (runs) → C (sites + 861 seeds) → D (review / Gold / ML)
                ↑
         no map crawl before B
```

We do **not** implement a “snap bounded at 50 km”: the review decided, it is no longer a step.

### Implementation load (technical, not calendar)

- **A**: few files, low risk, unit tests suffice.
- **B**: reasonable copy of the PoE runs module (~same shape, other collection).
- **C**: the invasive piece (prompt, geocode, multi-point GeoJSON, seeds).
- **D**: mostly frontend + Mongo queue.

---

## 15. Documents and conversations this specification inherits from

- `docs/PRD.md`, `docs/ARCHITECTURE.md`, `README.md`.
- `docs/CAHIER_DES_CHARGES_POE.md` — same form; **run model** to copy.
- `seed/projects.geojson` — 4,463 features.
- Projects specification **v1.0** (7 Sep 2026) and **32** Berry-Mappemonde **comments** (same day) — § 29.

This **v2 specification prevails** over v1 and over the code as soon as there is a conflict.

---

## 16. Who does what

| Actor | Does | Does not |
|-------|------|----------|
| **Visitor** | Map, filters, URL, report | Swarm, review, purge |
| **Operator** | Isolated run, review, promotion, import | `clear_db`, Force All blindly |
| **Gatekeeper** | Marine page vs not | Invent a site |
| **Place judge** | Is this toponym visitable by boat? | Snap toward any sea |
| **Reviewer** | Decides snapped / HQ / unlocated, goldises a sample | Goldise the whole seed at once |
| **Pipeline** | Discovers, extracts, proposes sites in a run | Touch `projects` by itself |

---

## 17. Lifecycle of a project

```
URL (listing 861 / cache / report)
    → text (cascade, not a challenge)
        → marine gatekeeper
            → extracted sites (0..n)
                → each site geocoded (action place, not HQ)
                    → site_ok → written in the run
                    → else unlocated
                        → human review
                            → promoted to projects (n Features)
```

| State | Meaning | Where |
|-------|---------|-------|
| `cached` | URL seen | `deeplink_pages` |
| `unlocated` | Marine but no visitable site | run / `failed` |
| `rejected` | Not marine / generic page | `failed` gatekeeper |
| `run_site` | Proposed site | `project_run_projects` |
| `review` | Mismatch or v1 snapped/fallback | `project_review` |
| **map** | Promoted | `projects` (+ `sites[]`) |
| `reported` | Report | `reported_projects` |

Dedup: same URL, or same site (name+<500 m). `merge_docs` fusion + union of funders.

---

## 18. The second deliverable: funder portals

One sheet per funder (~861+):

| Field | Meaning |
|-------|---------|
| `name` | Name as seen in the database / page |
| `url` | Listing if known, otherwise inferred domain |
| `source` | `curated` · `v1` · `follow_the_money` — no rank among them |
| `last_scan` / `urls_found` | Discovery |
| `listing_kind` | `projects_index` · `unknown` · … |

Follow the Money **writes into this table** (no longer a parallel list hard-capped at 5). The settings ceiling avoids drift; it does not prevent integrating a foundation already seen in v1.

---

## 19. Algorithm (discovery, sites, Follow the Money)

### Listing (L)

Funder → project pages (crawler, Search, Fetch; Agent if 0 and allowed).

### Marine + sites (M)

Page → gatekeeper → extract `sites[]`.  
For each site: place judge → GPS or `unlocated`.

### Decision

| L | M (at least 1 site_ok) | Decision |
|---|------------------------|----------|
| yes | yes | sites in the run |
| yes | no | `unlocated` / `rejected` |
| no | yes | report / partner: same |
| no | no | ignored |

World programme: M = the **list of action places**, not “global”.

---

## 20. Data model

### v1 map (do not overwrite)

`projects`: today 1 document ≈ 1 point. Target: 1 project document + `sites: [{name, lat, lon, geo_source, site_ok}]`.  
GeoJSON export: **one Feature per site** (same `project_id`).

Fields to keep: `title`, `url`, `funders`, `description`, `s_ocean`, `category_group`, `image`.  
`snapped` / `geo_source=ocean-region-fallback`: review flags, no longer publication sources.

### Runs (to create)

| Collection | One line = |
|------------|------------|
| `project_runs` | one run (like `poe_runs`) |
| `project_run_projects` | one project/site of the run |
| `project_run_events` | micro-steps |
| `project_review` | review queue |

Reuse `run_fingerprint`, `events.RunRecorder`, `TaskState`.

### Elsewhere

`deeplink_pages`, `discovery_state`, `telemetry` (+ `dataset`), `failed`, `reported_projects`, `settings`, `geocode_cache`.

Files: `data/master_seeds.json`, `data/project_rules.json` (defaults), `seed/projects.geojson`.

---

## 21. What the user sees

**Visitor.** Cyan map, clusters, one marker **per site**, search, funder, category legend (bonus), list, report, popup (place + URL + S_ocean). No more “snapped” badge as quality: a v1 snapped is to review, not to boast.

**Operator.** Launch a **run**, logs, telemetry. No more “empty the database” checkbox. Review queue + promote. Import/export. Settings: thresholds, `max_inland_km`, Agent on/off, Claude budget.

Current gaps (= phase B/D): runs, review, multi-sites, 861-portal sheet.

---

## 22. MasterSeeds inventory

**Target: ~861 funders** from v1, not 21 rows.

The 21 curated listings and the ~840 v1 funders are **equal** in the queue (no more priority 1 / 2). The 21 mainly provide an already-known listing URL:

The Ocean Foundation, Oceana, Blue Marine Foundation, Fondation de la Mer, Pure Ocean, Fondation CMA CGM, IFREMER, Prince Albert II, Institut Paul Ricard, SHOM, CORDIS, Coral Reef Alliance, Mission Blue, Seacology, Ocean Conservancy, Pew, WWF Oceans, Packard, Rare Fish Forever, Fauna & Flora Oceans, WCS Marine.

The other ~840: name as in the database, listing URL = most frequent domain of their v1 projects (otherwise to discover via Search `"{name}" marine projects`).

SHOM / IFREMER: institutes — 0 project URL remains an honest success if there is no action listing.

---

## 23. Gatekeeper and taxonomy

Three stages, **thresholds in settings**:

1. Local ML if trained enough: accept / reject according to `gatekeeper_accept` / `gatekeeper_reject` (historical defaults 0.85 / 0.12).
2. OpenRouter or Claude (if budget).
3. Keyword heuristic + `min_marine_score`.

Retraining: **after** Gold (phase D), not to “unblock” a run.

Nine families: useful for display, **non-priority work**. Later: train the indices.

---

## 24. Concrete examples

**Hope Spot.** Each spot = a visitable site. Not the Mission Blue office.

**World programme on 4 reefs.** 4 sites, 1 project, 4 points. Not a “Pacific” point.

**Pew / Washington headquarters.** L = project pages; M refuses Washington; seeks the named MPA / coast; otherwise `unlocated`.

**Report “Coral Gardeners Moorea”.** Moorea site if the page says so. `Community Report` in `funders`.

**v1 snapped or fallback.** Invisible as a “good point”: review queue, excluded from Gold until accepted.

---

## 25. Acceptance tests

### Portal / funder

1. Sheet in the widened MasterSeeds.
2. Each map site: action GPS, URL, funders, `site_ok`.
3. 0 HQ, 0 fallback, 0 snap, 0 (0,0).
4. Multi-place programme: as many points as extracted sites.
5. v1 `projects` count not decreased without a written review.

### Run

1. `wrote_projects: false`.
2. No `snap_to_ocean` / `ocean_fallback_coords` call in the traces.
3. `clear_db` impossible (400).
4. Tests: `test_project_contract.py` + existing non-destructive suites (`>= 4463`).

### Forbidden

Relaunch a `full` on the map. Reintroduce a purge checkbox. “Just a little snap”.

```bash
cd backend && python3 -m pytest tests/test_project_contract.py tests/test_blue_intelligence.py tests/test_import_and_regression.py tests/test_zoom_and_new_features.py tests/test_refactor_core.py -q
```

---

## 26. Risks

| Risk | Counter-measure |
|------|-----------------|
| Purge | Functions **removed** (phase A) |
| GPS patch | No more call; review of dirty v1 |
| HQ | Place judge + headquarters-city list |
| World programme → 0 point | Extract *n* sites; honest `unlocated` > centroid |
| 861 seeds = huge crawl | Isolated runs, TTL, saturation |
| TinyFish Agent | Search/Fetch; flag off |
| Biased v1 ML | Do not retrain before Gold |
| MPAs misused | Geocode backstage only |
| Multi-points / map perf | `max_markers` unchanged; cluster |

---

## 27. Out of scope

- Formalities — `docs/CAHIER_DES_CHARGES_POE.md` (we **harmonise** only the runs).
- Route marinas / anchorages.
- MPA polygon layer **on the map** (geocode use is **inside** C2 scope).
- PoE crowdsourcing.
- Automatic run → map promotion.
- Project ↔ PoE crossing (P2 PRD).
- Category training (later).
- Directory of all marine NGOs outside v1 funders + reports + Follow the Money.

---

## 28. Annexes

### A. Telemetry

`SUCCESS` (sites in the run), `MERGED`, `REJECTED`, `UNLOCATED`, `FAILED`, `CANCELLED`. Field `dataset: "projects"`.

### B. Target API

| Method | Effect |
|--------|--------|
| `GET /api/projects` | Map (1 Feature / site) |
| `POST /api/projects/runs` | Isolated run |
| `POST /api/projects/runs/{id}/promote` | Manual, later |
| `POST /api/swarm/deploy` | Becomes a run; `clear_db` → 400 |
| `DELETE /api/projects` | **410** |
| `POST /api/report-project` | Queue + next run |

### C. v1 restoration

```bash
curl -X POST http://localhost:8001/api/import/geojson \
  -H "Content-Type: application/json" --data-binary @seed/projects.geojson
```

Skip of known URLs. Not a purge.

### D. Tests

Current: `test_blue_intelligence.py`, `test_import_and_regression.py`, `test_zoom_and_new_features.py`, `test_refactor_core.py`, `test_ml_jobs.py`.  
To add: `test_project_contract.py` (A), then run tests (B) on the `test_poe_*` model.

### E. Attribution

Foundation pages; OSM / Nominatim / GeoNames; MPAs as a hint if reused. Syntheses, not official texts.

---

## 29. Trace of the review comments (v1 → v2)

| # | Decision taken up |
|---|-------------------|
| 0, 6, 7 | Opening sentence, eco-tourism, boat, several funders |
| 1, 2, 5, 9, 14 | Abandonment of `snap_to_ocean` as publication |
| 3, 21 | Agent expensive; Search/Fetch first |
| 4, 15, 20 | Better geocode + Claude allowed |
| 8 | *n* sites for a world programme |
| 10, 16, 22 | Create `project_run_*`, harmonise the modes, before a new run |
| 11, 27, 24 | Gold to **create** (v1 − snapped − fallback); retrain **after** |
| 12, 13, 29 | MasterSeeds = ~861 funders |
| 17 | Remove purges (not merely hide them) |
| 18, 19 | No more fallback; no more HQ in geocode output |
| 23 | Telemetry `dataset`: cosmetic, field to add (B6) |
| 25 | MPA = geocoding hint (C2) |
| 26 | Review UI rather than a bounded snap (D1) |
| 28 | Enrich ↻ = re-text today; GPS is revisited in C/D, not by snap |
| 30 | Configurable thresholds (A3) |
| 31 | Categories: keep, train later, not a priority |

---

The **numbers** (15 km, 0.85 / 0.12, 500 m, ceilings…) no longer live only here: catalogue `backend/data/run_rules.json`, principle and interval in `docs/REGLES_PARAMETRES.md`. A run records the snapshot in `params.rules`.

*End of the v2 specification. Any rule evolution is done first here, then in the catalogue / the code. Implementation follows § 14, phase A first.*
