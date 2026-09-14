# Implementation plan — Cartographic tracks (control, map, hydro, satellite)

Framing document. It puts back in order a pile of useful but
**mixed** ideas: OSM ontology, SHOM/NOAA, Review / Gold, versioned
GeoJSON, geocoding, VLM, Seamap, tippecanoe, EMODnet, NOAA ENC,
IENC, GEBCO, Sentinel.

Written in plain language: this is the contract of what we seek, and
of what we refuse. Each brick has **one job**. We do not stick a
second one on it.

Version **1.0** — 14 September 2026.

Inherits from: `README.md` (Seamap basemaps, exports, catalogue),
`docs/CATALOGUE_SEAMARK.md`, `docs/CONTRATS_MODES.md`,
`docs/CONTRATS_REVIEW_PAR_MODE.md`, `docs/CAHIER_DES_CHARGES_REVIEW.md`,
`docs/PLAN_IMPLEMENTATION_CLIMATOLOGIE.md`,
`docs/PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md`,
`docs/hackathon-nebius-nvidia.md`, `infra/vps/seamap/README.md`.

**Contents**

1. In one sentence
2. Why this work exists
3. What we want to achieve
4. What we do not want
5. Vocabulary
6. The four tracks (putting things in order)
7. Blue Intelligence / NAVIGUIDE simulator split
8. Current state and gaps
9. Track 1 — Control (objects and evidence)
10. Track 2 — Map (basemap + overlays + warning)
11. Track 3 — Official hydrography (API, not S-57 files)
12. Track 4 — Satellite (Berry corridor pilots)
13. Build order
14. Files touched
15. Recipe
16. Risks
17. Out of scope
18. Documents this plan inherits

---

## 1. In one sentence

Separate **four jobs** that do not overlap: (1) **control**
an extracted object against a reference and a human review,
(2) **display** Seamap + our overlays + EMODnet with a real
“NOT FOR NAVIGATION”, (3) **extend** the official objects already
wired **by API**, (4) **pilot** Sentinel on the Berry corridor
in Science mode — without ever turning Blue Intelligence into an
S-101 encoder or NAVIGUIDE into an ECDIS.

---

## 2. Why this work exists

The bricks are already there. What is missing is **not confusing
them**.

Today we have:

- a `seamark:*` catalogue and a tag audit;
- SHOM (SMCFAC / BUISGL) and NOAA ENC Direct **already** glued onto
  harbour offices;
- Review / Gold (human queue);
- versioned GeoJSON + sha256 + a weekly PMTiles **published but
  never displayed**;
- `geo.py` (Nominatim ∥ GeoNames);
- `vision_msg.py` + NIM / Nemotron (document judge);
- Seamap (OSM + PMTiles + MapLibre) as the “Nautical chart” basemap;
- EMODnet as WMS **and** as a point, **only** in Science mode;
- a “Not suitable for navigation” banner, **not** an
  acceptance window.

If we mix these roles, we head into bad implementations:

| Confusion | What it would produce |
|-----------|------------------------|
| OSM catalogue = S-101 encoder | A hydrographic product we are not |
| SHOM/NOAA = source to copy as-is | A sketch pontoon promoted to “official” |
| `geo.py` = image registration | A pixel georeferencer we do not need |
| VLM = shift pixels | A vision use outside the contract (and outside the VPS) |
| EMODnet WMS = Science only | A useful basemap hidden from other modes |
| GEBCO = harbour depth | A number too coarse for a basin |
| Sentinel = nautical chart | A satellite image presented as a sounding |

NAVIGUIDE (prod and simulator) is an **SADP**: pleasure-craft
decision support. Blue Intelligence is a **geospatial base + map**.
Neither is an ECDIS. This plan keeps that boundary.

---

## 3. What we want to achieve

Four deliverables, **in this dependency order** (not four
parallel projects that ignore each other).

1. **Control.** A BI object (pontoon, office, light, extracted
   depth area) has an **identity**, a **control reference**
   if one exists (SHOM / NOAA / OSM catalogue), and goes through
   **Review / Gold** before entering a certified run.
2. **Map.** Seamap remains the basemap. On top: weekly
   tippecanoe overlay, EMODnet WMS **also outside Science**, safety
   contour if the tiles carry a depth, **acceptance
   window** “NOT FOR NAVIGATION” (the banner is not enough).
3. **Official hydro by API.** Extend NOAA ENC Direct (US lights,
   buoys, contours) **via the ArcGIS API already used**, never
   via S-57 files. GEBCO only **offshore**, for
   NAVIGUIDE. IENC / VNF **out of scope**.
4. **Sentinel pilots.** Berry corridor only. Coastline +
   intertidal + simple SDB, OSM-shaped GeoJSON export, display in
   **Science mode** with the same warning. Compute **off the VPS**.

Split sentence (like climatology):

**Blue Intelligence shows, controls and versions. The NAVIGUIDE
simulator uses it for the film, without inventing a second map.**

---

## 4. What we do not want

- Encode or export **S-101** / ingest **S-57 files**.
- Register an image (sketch, Sentinel, PDF) with `geo.py` or a VLM.
- Make the VLM a bathymetry or georeferencing engine.
- Silent Gold, Gold without a click, Gold that changes the map without
  “Show the review” (`docs/CONTRATS_REVIEW_PAR_MODE.md` §0 and §8).
- Review / Gold of Science and Climatology modes in V1 (C8).
- **Vector** EMODnet contours on the VPS (GDAL + too much
  compute).
- GEBCO as an approach depth for a harbour.
- IENC / VNF (rivers) in the current scope.
- ACOLITE / CoastSat / ICESat-2 **on the VPS** (4 vCores, 8 GB,
  ~26 GB already taken by Seamap).
- Presenting a Sentinel product as a nautical chart.
- An 8th BI mode. Science absorbs the satellite pilots.
- Copying Seamap / OpenCPN GPL C++. We consume the CC-BY
  `style.json` and we rewrite.

---

## 5. Vocabulary

| Word | Meaning here |
|-----|----------|
| **Track** | A chain with a single job. Four tracks, not a “carto” catch-all. |
| **Control** | Compare an extracted object to a reference **already published**, then to a human eye. |
| **Reference** | SHOM WFS, NOAA ENC Direct, Marine Regions, `seamark:*` catalogue. Not an LLM. |
| **SMCFAC** | S-57 object “small craft facility” (pontoon / pleasure-craft facility). The SHOM WFS serves it as a **point**. |
| **BUISGL** | Building. `FUNCTN=2` = harbour-office building. |
| **250 m overlay** | Glue SHOM/NOAA onto OSM **by distance alone**, not by name (`find_building`). |
| **Review / Gold** | Human queue → Gold click → **certified run**. The map shows it only if “Show the review” is checked. |
| **Versioned GeoJSON** | **Intermediate** format: `metadata.version` = `YYYY-MM-DD.<sha25612>`. Not a chart, not an ENC. |
| **Gazetteer** | Directory of **toponyms** (where is this name?). Seed = `geo.py`. |
| **VLM judge** | Yes / no on a **mention** (“is this a navigation rule?”). Not a pixel registration. |
| **Seamap** | Open Waters vector basemap (OSM + PMTiles + MapLibre). Stack of the “Nautical chart” basemap. |
| **tippecanoe overlay** | PMTiles of **our** 7 exports, built every Monday. Layer **on top of** Seamap, not instead of it. |
| **Light S-52** | Colour a safety contour if a depth attribute exists. Not an S-52 engine. |
| **SDB** | Satellite-derived bathymetry (Stumpf formula). Research product, not a sounding. |
| **Intertidal** | Zone uncovered at low tide. MNDWI / CoastSat draw it; it is not an ENC. |
| **CDSE** | Copernicus Data Space Ecosystem (Sentinel images). **Another account** than CMEMS (sea models). |
| **Berry corridor** | Band along the official route. Sole scope of the Sentinel pilots. |

---

## 6. The four tracks (putting things in order)

```
  1. CONTROL                          2. MAP
  object + evidence + human           basemap + overlay + warning
  ┌─────────────────────┐             ┌──────────────────────────┐
  │ OSM catalogue       │             │ Seamap (OSM+PMTiles+ML)  │
  │   = export target   │             │ + tippecanoe overlay     │
  │ SHOM / NOAA         │             │ + EMODnet WMS (all       │
  │   = reference       │────────────▶│   modes, not only        │
  │ Review / Gold       │  GeoJSON    │   Science)               │
  │   = human queue     │  + sha256   │ + safety contour         │
  │ geo.py              │             │ + NOT FOR NAV window     │
  │   = gazetteer       │             └──────────────────────────┘
  │ VLM                 │
  │   = mention judge   │
  └─────────────────────┘
            │
            │  versioned exports (same contract)
            ▼
  3. OFFICIAL HYDRO                   4. SATELLITE (pilots)
  API only                            Berry corridor, off VPS
  ┌─────────────────────┐             ┌──────────────────────────┐
  │ NOAA ENC Direct     │             │ Sentinel-2 via CDSE      │
  │   lights / buoys /  │             │ ACOLITE + MNDWI/CoastSat │
  │   contours  (US)    │             │ SDB Stumpf ± ICESat-2    │
  │ GEBCO offshore      │             │ vs EMODnet (error)       │
  │ EMODnet: WMS+point  │             │ OSM-shaped GeoJSON       │
  │ IENC/VNF: NO        │             │ → Science mode only      │
  │ S-57 / S-101: NO    │             └──────────────────────────┘
  └─────────────────────┘
```

The arrows are **contracts**, not code copies. Versioned GeoJSON
is the **only** format that crosses the four tracks.

---

## 7. Blue Intelligence / NAVIGUIDE simulator split

Same spirit as “BI shows the atlas. NAVIGUIDE uses it”
(`docs/PLAN_IMPLEMENTATION_CLIMATOLOGIE.md` §6). Here:

```
              Versioned GeoJSON + sha256
              (+ PMTiles overlay on Monday)
                         │
          ┌──────────────┴──────────────┐
          ▼                             ▼
  Blue Intelligence              NAVIGUIDE simulator
  7 modes + Review/Gold          Leaflet film (stage 1)
  Seamap MapLibre basemap        pills already there
  overlay + EMODnet + modal      same /bi/* exports
  Science = catalogues +         ici() : 0 or 1 object
    Sentinel pilots              localised, not the world
          │                             │
          │                      prod naviguide.fr
          │                      UNTOUCHED by this plan
          └─────────────────────────────┘
```

| Idea | Blue Intelligence | NAVIGUIDE simulator | Prod `naviguide.fr` |
|------|-------------------|----------------------|---------------------|
| OSM catalogue + audit | Export target, badges, Monday audit | Nothing to paint; tags already in the exports | Unchanged |
| SHOM / NOAA control | 250 m overlay + Review fiche | One Gold office in `ici()` / Briefing, not a US dump | Unchanged |
| Review / Gold | Indispensable queue; Map switch | Consumes the **certified run** (hackathon Gold step), never the raw dump as “official” | Unchanged |
| GeoJSON + sha256 | Intermediate + snapshots + `data-*` release | Fetch `/bi/export/*` already in place; check `metadata.version` | `/bi` proxy already there |
| Gazetteer (`geo.py`) | P / PoE / future Berry toponyms | Stop names, `ici()` pack | Unchanged |
| VLM judge | Formalities / MPA / enrich: “is this a rule?” | Nemotron Ultra **strikes** an unproven mention (hackathon briefing) — same question, other screen | Unchanged |
| Seamap basemap | Already the “Nautical chart” basemap | Leaflet + OpenSeaMap raster tiles (marks). **No** MapLibre/PMTiles in stage 1 | MapLibre + Seamap already |
| tippecanoe overlay | To **display** (today only published) | Later option: a “BI overlay” pill; GeoJSON first | Outside this plan |
| EMODnet WMS outside Science | Map switch, all modes | Science pills already planned (bathy / seabed / cables) | Outside this plan |
| NOT FOR NAV window | First use of sea basemap + Science satellite | First lighting of marks / Science | Outside this plan |
| Safety contour | If a depth attribute in Seamap | Useless on Leaflet raster; the simulator has no Seascape | Outside this plan |
| NOAA ENC lights/buoys | Harbour-offices mode / US layer, API | One light **near `ici()`** on a US leg | Outside this plan |
| GEBCO | Useless in harbour; do not paint on BI | Engine / no-go **offshore** (not a harbour pill) | Hand-drawn GEBCO zones already in the routing workspace |
| Sentinel | Science mode, banner, export | 0 or 1 **local** coastline in the pack, never the 8 catalogues | Unchanged |
| IENC / VNF | No | No | No |

**Simulator rule.** Stage 1 is Leaflet, without MapLibre, without
file import/export, prod untouched
(`docs/PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md`). This plan
**does not cancel** that. The simulator mainly benefits from the
**exports**, **Gold**, the **judge**, **EMODnet as pills**, and later
**one** satellite object in `ici()`. It does not receive Seamap
PMTiles nor the S-52 contour.

---

## 8. Current state and gaps

### Already in place (do not rebuild)

| Brick | Where | Real job today |
|--------|----|-------------------------|
| `backend/data/seamark_catalog.json` + `scripts/audit_tags.py` | Catalogue + report | What the pipelines **read** in OSM |
| `capitainerie_world.py` | SHOM WFS + NOAA ENC Direct `FUNCTN=2` | Office overlay, not an encoder |
| `review_queue.py` / `review_gold.py` / Review tab | Human queue | Formalities furthest along; Marinas too “pre-Gold”; Harbour offices / MPA Gold too wide or missing |
| `export_meta.py` + `POST /api/export/snapshot` | GeoJSON + sha25612 | Stable intermediate |
| `.github/workflows/weekly-data-build.yml` | 7 GeoJSON → tippecanoe → `data-*` release | Archive **published**, overlay **not loaded** in the frontend |
| `backend/app/core/geo.py` | Nominatim ∥ GeoNames | Geocoding of **names**, not images |
| `vision_msg.py` + `review_doc_picker.py` | JPEG → NIM / Claude | Judge of Formalities **documents** |
| Seamap VPS mirror | `infra/vps/seamap/` | ~26 GB basemap, Monday cron |
| Nautical banner | `MapView.js` `data-testid="nautical-disclaimer"` | Always visible if sea basemap; **no** acceptance click |
| EMODnet WMS | `useScienceWms.js` | **`mode === "science"` only** |
| EMODnet point | `GET /api/depth` | Marina / anchorage popups |
| Simulator | `useToggleLayers.js` | BI GeoJSON + OpenSeaMap raster + climatology stub |

### Holes (what this plan fills)

| Hole | Track |
|------|---------|
| PMTiles `blue-intelligence-*.pmtiles` never referenced in the frontend | 2 |
| EMODnet WMS locked to Science mode | 2 |
| No acceptance window (banner only) | 2 |
| No local safety contour (we rely on the Seamap style) | 2 |
| “Show the review”: i18n ready, **Map button missing** | 1 |
| Harbour-office / MPA Gold: contract written, code too wide or incomplete | 1 |
| Catalogue `candidat` types (lights, rocks, anchorages) not yet in a pipeline | 1 |
| NOAA ENC: only `FUNCTN=2` (offices), not lights / buoys / contours | 3 |
| GEBCO: hand-drawn zones in routing, not a grid | 3 |
| Sentinel / CDSE / ACOLITE / CoastSat / ICESat-2: **zero code** | 4 |
| CDSE vs CMEMS account: **to verify** (human + secrets) | 4 |

---

## 9. Track 1 — Control (objects and evidence)

This is the track **already started**. We name it so we stop asking
it to be a map or an encoder.

### 9.1 OSM catalogue → BI fields (OpenSeaMap export target)

**Job.** State in black and white which tags we read, which are
`candidat`, and produce a GeoJSON **in the OSM /
OpenSeaMap vocabulary** (`leisure=marina`, `seamark:type=…`). This is
**not** an S-101 encoder.

**Already there.** `docs/CATALOGUE_SEAMARK.md`, `seamark_catalog.json`,
`audit_tags.py` (Monday, in the weekly workflow). Marina badges via
`SERVICE_TAG_QUESTIONS`.

**To do.**

| Id | Work | Criterion |
|----|---------|---------|
| C1 | Promote to `exploite` the tags a pipeline actually reads (anchorages `anchorage` / `mooring` as soon as `anchorage_build.py` keeps them) | Audit: no more “candidat even though the dump carries them” |
| C2 | Document the **inverse mapping**: slim BI field → export OSM tag (e.g. Avitaillement badge → `fuel=yes` / `seamark:small_craft_facility:category=fuel`) | A table in the catalogue; a test on a fixture |
| C3 | When a satellite pilot exports (`natural=coastline`, `seamark:type=depth_area`), **add those keys** to the catalogue **before** the first dump | No tag outside the catalogue without a `candidat` entry |

**Forbidden.** Generate S-101 attributes (`DRVAL1`, `CATSCF`…)
from OSM. The allowed direction is OSM → BI fields → OSM GeoJSON.
SHOM/NOAA remain a **control layer**, not the export target.

### 9.2 SHOM / NOAA as a control reference

**Job.** A pontoon read from a sketch, a website or an OSM tag
**is not** an SMCFAC. An OSM office **is not** a BUISGL
`FUNCTN=2` until the 250 m overlay has glued the same building.

**Already there.** Harbour offices: world OSM → SHOM `buisgl_point` +
`smcfac_point` → NOAA ENC Direct `FUNCTN=2` (points + centroids).
Review fiche: keep / detach the overlay. Marinas: OSM dump
only; SHOM documented in `marina_build.py`, not wired.

**To do.**

| Id | Work | Criterion |
|----|---------|---------|
| C4 | On the **Marina** fiche, show whether an SMCFAC / CATHAF exists at ≤ 250 m: “published reference” vs “OSM only”. **No** automatic basin merge | The reviewer sees both points; Gold does not require the SMCFAC (a marina is not a decree) |
| C5 | Keep NOAA / SHOM **orphan** visible (already the case for harbour offices): an office without OSM remains a candidate, not a map truth | Existing identity test unchanged |
| C6 | Do not extend `merge_km` beyond 0.25 km | `find_building` contract |

**Test sentence.** A pontoon extracted from text, with no SMCFAC and no
`leisure=marina` tag, **cannot** be Gold as a marina.

### 9.3 Review / Gold — indispensable queue

**Job.** The human eye. Without this queue, tracks 2–4 paint
raw data.

The code and contracts exist (`CAHIER_DES_CHARGES_REVIEW.md`,
`CONTRATS_REVIEW_PAR_MODE.md`). This plan **does not invent** a
“Culture Review” beside them: it is **the same** Review tab.

**To do (gaps already written, to code).**

| Id | Work | Criterion |
|----|---------|---------|
| C7 | Map button **Show the review** (i18n `reviewShowReview` already there) | Gold alone does not change the map; checked = certified run |
| C8 | Harbour offices: no more default `gold_on: true`; Gold after **building** acceptance | Meta-contract §0 test sentence |
| C9 | MPA: list of `visit_url` candidates; Gold refuses `visit_url == manager_url` | Contract §6 |
| C10 | Marinas: OSM ≠ automatic pre-Gold | Contract §4.5 |

Science / Climatology / Sentinel pilots: **no** V1 Review
queue. The banner + the acceptance window carry the warning.

### 9.4 Versioned GeoJSON + sha256 — intermediate format

**Job.** Carry a dataset from one track to another **without** losing
date, fingerprint and warning.

**Already there.** `versioned_fc()`, immutable snapshots, Monday release
with `SHA256SUMS-*.txt`.

**To do.**

| Id | Work | Criterion |
|----|---------|---------|
| C11 | Every **new** dataset (NOAA lights, Sentinel coastline, depth_area) goes through `versioned_fc()` | Same `metadata` as the 7 exports |
| C12 | The Monday workflow **adds** the new exports if they are public (else a separate release, same sha256 discipline) | `gh release create` fails if the tag exists: immutability |

### 9.5 Gazetteer (`geo.py`) — seed, not an image registration

**Job.** “Where is this **name**?” Nominatim ∥ GeoNames, Mongo
cache, space tests afterwards (haven vs VLIZ polygon).

**To do (later, after C7–C10).**

| Id | Work | Criterion |
|----|---------|---------|
| C13 | Extract a `toponyms` table (name, lat/lon, source, `mrgid` if EEZ) fed by geocoding successes + VLIZ names | A name already seen does not consume quota again |
| C14 | `project_geocode.py` (Projects spec) if it becomes necessary: **place judge**, always via `geocode_name` | No new HTTP client “image → GPS” |

**Forbidden.** Use `snap_to_ocean` to “glue” a Sentinel
coastline. The satellite has its own GPS (track 4).

### 9.6 VLM — mention judge, not pixels

**Job.** On a page, a PDF, a screenshot: “is this sentence a
**navigation rule** (VHF, anchoring ban, port of
entry, draft) or tourism?”

**Already there.** `vision_msg.py` sends JPEGs; Formalities uses it
to **choose the right PDF**, not to read a chart.

**To do.**

| Id | Work | Criterion |
|----|---------|---------|
| C15 | A JSON judge `navigation_rule: true\|false` + `quote` (excerpt) wired to `complete_json_cascade`, role `judge` | Fixture: “VHF 09 at the entrance” → true; “restaurant with sea view” → false |
| C16 | Wiring: marina / harbour-office enrichment (do not invent a VHF), MPA visit candidates, later simulator Briefing (Ultra strikes) | Empty field if false; we do not write a fake channel |

**Forbidden.** Ask the VLM for the corners of an image, a homography,
or a depth.

---

## 10. Track 2 — Map (basemap + overlays + warning)

This is the **most visible** workshop, and the smallest in code.
Seamap **remains** the basemap: OSM + PMTiles + MapLibre
(`useNauticalBasemap.js`, mirror `infra/vps/seamap/`).

### 10.1 Weekly tippecanoe overlay

**Already there.** Every Monday 05:00 UTC, tippecanoe builds
`blue-intelligence-$STAMP.pmtiles` (projects, marinas, anchorages,
harbour offices, MPAs, PoE, route) and publishes it on the GitHub
`data-$STAMP` release.

**To do.**

| Id | Work | Criterion |
|----|---------|---------|
| M1 | Serve the overlay: URL of the **latest** release (or nginx copy `/tiles/bi-overlay/current.pmtiles` if we want to avoid GitHub at runtime) | A `REACT_APP_BI_OVERLAY_URL` variable |
| M2 | MapLibre layer **on top of** the Seamap style (source `pmtiles://…`, layers per tippecanoe `-L`) | Seamap basemap visible; overlay switchable off |
| M3 | “BI data (week)” switch in the map chrome, **all modes**, default **on** once the sea basemap is accepted | `data-testid="overlay-bi-toggle"` |
| M4 | Pane / z-index: overlay **above** Seamap GL (190), **below** the route (380) and the clusters | Extend `layerOrder.js` + jest test |
| M5 | Simulator: **do not** port PMTiles in stage 1. GeoJSON pills are enough. Note M1–M4 as a **later** simulator stage | Stage 1 Leaflet intact |

Disk budget: the tippecanoe overlay is **small** (points + route),
unrelated to the 26 GB Seamap. VPS copy possible without aggressive
`KEEP`.

### 10.2 EMODnet WMS outside Science mode

**Already there.** Three layers (bathy, substrate, cables), panes 250 / 310
/ 370, persistence `bi.scienceWms`. The hook refuses everything if
`mode !== "science"`.

**To do.**

| Id | Work | Criterion |
|----|---------|---------|
| M6 | Remove the `mode === "science"` guard; the hook depends only on `enabled` | WMS lightable in Marinas / Formalities / etc. |
| M7 | Move (or **duplicate**) the three buttons out of `SciencePanel` alone: shared map chrome (next to dark / light / sea basemap) | Test: Marinas mode + bathy ON → `mean_multicolour` tiles |
| M8 | Z-index conflict with climatology (also 250): EMODnet bathy **under** the atlas if Climatology mode | Adjust `SCIENCE_WMS_PANES` / `PANES` and the order test |
| M9 | Simulator: Science pills already in the hackathon briefing (Bathymetry / Seabed / Cables). Wire the **same** WMS URLs as `useScienceWms.js` | Not a VPS proxy; tiles at EMODnet |

The `GET /api/depth` point sounding **stays** in marina /
anchorage popups (already outside Science). We do not move it.

### 10.3 “NOT FOR NAVIGATION” acceptance window

**Already there.** Bottom banner if `nauticalActive`. Texts
`seaMapDisclaimerTitle` / `Body`. `basemaps.sea.notForNavigation`.

**To do.**

| Id | Work | Criterion |
|----|---------|---------|
| M10 | **Blocking** modal on first visit to the sea basemap **or** when lighting a WMS / overlay / satellite layer: title, body, checkbox “I understand: not suitable for navigation”, Accept button | Without acceptance: sea basemap refused (dark/light fallback), WMS off |
| M11 | Persistence `localStorage` `bi.notForNav.accepted` + date + text `content_sha256` (if the text changes, we ask again) | Reload: no more modal, **banner kept** |
| M12 | Same gesture in the simulator when lighting Marks or Science WMS (`naviguide-simulator`) | `data-testid="not-for-nav-modal"` |
| M13 | Exports keep `disclaimer` / `disclaimer_fr` (already) | No JSON contract change |

The banner **stays**. The window is the **acceptance**. Both
coexist.

### 10.4 Safety contour (light S-52)

**Condition.** Only if Seamap / Seascape tiles expose a
queryable depth attribute (exact name to confirm in the
mirror `style.json`: often a raster bathymetry layer
**without** a per-pixel attribute on the client).

**Do first: a diagnosis, not a paint.**

| Id | Work | Criterion |
|----|---------|---------|
| M14 | Read the Seamap `style.json` (mirror or CDN): list layers whose `source-layer` / `paint` speak of depth / contour / DEPARE | Note in this folder or `docs/audits/`: **attribute yes/no** |
| M15 | **If yes**: MapLibre expression — skipper threshold (default **2 m**, adjustable 2 / 5 / 10); fill or contour line **above** the basemap, under the BI overlay | Visual test + `data-testid="safety-isobath"` |
| M16 | **If no** (likely case: Seascape stays on CDN, raster): **do not** invent a contour. Keep EMODnet WMS + `GET /api/depth`. Document the refusal here | A sentence in the basemap README |

**Forbidden.** Recode S-52 (IALA symbols, lights sectors, ECDIS
safety contour). We colour **one** limit, we do not write an ECDIS.

---

## 11. Track 3 — Official hydrography (API, not S-57 files)

### 11.1 NOAA ENC Direct — extend what is already wired

**Coverage.** US waters only. Same MapServer:

`https://gis.charttools.noaa.gov/arcgis/rest/services/encdirect`

**Already there.** Harbour / approach / coastal / berthing layers,
`FUNCTN=2` only (`NOAA_ENC_LAYERS` in
`capitainerie_world.py`).

**To do.**

| Id | Work | Criterion |
|----|---------|---------|
| H1 | Inventory of public `layer_id`s: lights (`LIGHTS`), buoys / beacons (`BOY*`, `BCN*`), contours / DEPARE if the service exposes them as GeoJSON | Table in `docs/` or comment + bbox `query` test |
| H2 | Tiled fetch (same discipline as the harbour-office overlay): upsert `noaa:{service}:{layer}:{fid}`, slim GeoJSON via `versioned_fc` | NOAA licence + disclaimer already cited |
| H3 | Display: optional **US** layer, not worldwide. BI: switch in Harbour offices **or** map chrome. Simulator: only if `ici()` is in a US bbox | Zero objects outside the ENC Direct bbox |
| H4 | Control (track 1): an OSM light `seamark:type=light` **near** a NOAA LIGHTS = same 250 m gesture as the office | No 500 m `same_site` merge |

**Forbidden.** Download S-57 `.000` cells. Parse an ENC.
Encode S-101.

### 11.2 EMODnet — stay on WMS + point

Already wired. The jump to **vector** contours needs
GDAL and a cube too large for the VPS. **Refused** (see §4).

If one day we want vector: compute **off the VPS**, versioned
GeoJSON snapshot, served like climatology. Not in this plan.

### 11.3 GEBCO — offshore, for NAVIGUIDE

**Job.** **Offshore** no-go / isochrone. Useless for a harbour
(resolution too coarse; EMODnet + OSM + `GET /api/depth`
win at the quay).

**Already there.** Hand-drawn rectangular zones in
`naviguide/.../bathymetry.py` (routing workspace). Not in BI.

**To do (simulator / engine, not the BI map).**

| Id | Work | Criterion |
|----|---------|---------|
| H5 | GEBCO grid **precomputed off the VPS** (like climatology snapshots), point lookup for the isochrone / `ici().depth_offshore` | `null` near coasts (threshold to write, e.g. 20 M from shore) |
| H6 | **Do not** paint GEBCO on Blue Intelligence | No GEBCO layer in `layerOrder.js` |

Prod `naviguide.fr`: outside this plan (same rule as simulator
stage 1). We prepare the lookup in the simulator / the **copied**
routing workspace, we do not glue the two repos.

### 11.4 IENC / VNF

Interesting for **rivers**. Out of scope: the Berry route and
the 7 modes are **maritime**. One line in §17 is enough. No
ticket, no prototype.

---

## 12. Track 4 — Satellite (Berry corridor pilots)

**Job.** See the error of an **estimated** coastline / depth,
compare it to EMODnet, export it as OSM-shaped GeoJSON,
display it in **Science** with the banner. This is not an ENC.

**Scope.** Only the corridor of `backend/data/route.geojson`
(buffer to fix, e.g. 30 M). Not the world.

**Compute.** Operator Mac or offline machine. The VPS **serves**
the GeoJSON, like climatology snapshots.

### 12.0 CDSE account (human blocker)

CMEMS (wind, swell, current, climatology) **is not** CDSE
(Sentinel-2 images).

| Id | Work | Criterion |
|----|---------|---------|
| S0 | Check the Copernicus account: do we have a **CDSE** access (dataspace.copernicus.eu) distinct from the CMEMS login already used by `scripts/climatology/cmems_auth.py`? | Note in `scripts/satellite/README.md`: yes/no + who owns the login. **No secret in git** |

Without S0, we do not write a downloader.

### 12.1 Proposed chain (off VPS)

| Step | Tool | Output |
|-------|-------|--------|
| S1 | Sentinel-2 L1C/L2A on scenes that cover the corridor (CDSE STAC) | Dated scenes, sha256 list |
| S2 | ACOLITE (coastal atmospheric correction) | Reflectances |
| S3 | MNDWI and/or CoastSat | `natural=coastline` polyline + intertidal polygon |
| S4 | Stumpf SDB **if** an ICESat-2 ATL03/ATL24 track crosses the scene | `seamark:type=depth_area` (shallow classes, not a 1 m DTM) |
| S5 | Compare to EMODnet (`depth_sample` + WMS) | Fields `error_m`, `n`, DOI / date of both products |
| S6 | `versioned_fc()` → `coastline.geojson` / `depth_areas.geojson` | `metadata.disclaimer` mandatory |
| S7 | Science mode: “Satellite (pilot)” filter + same WMS buttons + banner / M10 modal | Review **off** (placeholder) |

**Forbidden.** Register the image with the VLM. Invent a depth
without ICESat-2 **and** without saying so (`null` + `method: "stumpf-uncalibrated"`
if we still display a trial — by default we **do not display**).

### 12.2 What the simulator does with it

The hackathon briefing: Science = **0 or 1 localised dataset** in the
`ici()` pack, not the whole catalogues. A pilot coastline enters
`ici().science` **if** the boat is in the corridor **and**
if an export exists. Else `null`. Nano narrates; Ultra does not take
a satellite coast for an ENC.

---

## 13. Build order

No calendar in days. The order is **technical**: first what
unlocks display and the Review contract, then the NOAA API,
then satellite (blocked by S0).

### Wave 0 — Diagnosis (no secret, little code)

| Id | Deliverable |
|----|----------|
| M14 | Seamap depth attribute: yes / no |
| S0 | CDSE account: yes / no |
| H1 | List of useful ENC Direct layers (lights, buoys, DEPARE) |

### Wave 1 — Visible map (track 2) + Review switch

Depends on M14 only for M15 (else we skip M15–M16).

| Id | Deliverable | Where |
|----|----------|-----|
| M10–M13 | Acceptance window + banner kept | BI + simulator |
| M6–M8 | EMODnet WMS all modes | BI |
| M9 | EMODnet WMS as Science pills | simulator |
| M1–M4 | tippecanoe overlay on Seamap | BI |
| C7 | Show the review | BI Map |
| M15 | Contour **if** M14 positive | BI |

**Wave 1 recipe.** Sea basemap → modal → accept → banner. Light
bathy in Marinas mode. See this week’s overlay. Gold without
“Show the review”: map unchanged.

### Wave 2 — Control (track 1, gaps already contracted)

| Id | Deliverable |
|----|----------|
| C8–C10 | Harbour-office / MPA / marina Gold per contract |
| C4 | Neighbouring SMCFAC on Marina fiche |
| C1–C3 | Catalogue: `exploite` / export mapping / satellite keys as `candidat` |
| C15–C16 | “Navigation rule?” judge |

**Wave 2 recipe.** CONTRATS §0 test sentence green for each
kind. A VHF invented by the `false` judge is not written.

### Wave 3 — Extended NOAA + offshore GEBCO (track 3)

| Id | Deliverable |
|----|----------|
| H2–H4 | US lights / buoys by API, 250 m overlay vs OSM |
| H5–H6 | Offshore GEBCO lookup in the **simulator / routing**, not on BI |

**Wave 3 recipe.** Mediterranean bbox: 0 NOAA objects. Chesapeake
bbox: at least one light or buoy. Point 5 M from a harbour:
GEBCO `null`. Point in mid-Atlantic: a depth.

### Wave 4 — Sentinel pilots (track 4)

Blocked by S0 = yes.

| Id | Deliverable |
|----|----------|
| S1–S6 | `scripts/satellite/` scripts off VPS + 1–2 Berry scenes + exports |
| S7 | Science display |
| `ici().science` | 0 or 1 line if the boat is on it |

**Wave 4 recipe.** One scene, one GeoJSON with `metadata.version`,
error vs EMODnet written, banner visible, no Review Gold.

Waves 1 and 2 can **advance in parallel** (map vs
Review). Wave 4 does not start before S0. Wave 3 can
overlap 2 (same overlay pattern as harbour offices).

---

## 14. Files touched

### Wave 1 (map + Review switch)

| File | Role |
|---------|------|
| `frontend/src/components/map/NotForNavModal.js` | **New** — modal |
| `frontend/src/components/MapView.js` | Modal + banner |
| `frontend/src/components/map/useScienceWms.js` | No more `mode === "science"` guard |
| `frontend/src/components/map/useBiOverlay.js` | **New** — PMTiles overlay |
| `frontend/src/components/map/layerOrder.js` | Overlay pane + possibly contour |
| `frontend/src/components/map/__tests__/layerOrder.test.js` | Freeze the order |
| `frontend/src/App.js` / map chrome | WMS + overlay buttons outside SciencePanel |
| `frontend/src/i18n.js` | Modal / overlay / contour keys |
| `frontend/src/components/Header.js` or Map chrome | “Show the review” switch (C7) |
| `infra/vps/seamap/` or `deploy-app.sh` | Option: `REACT_APP_BI_OVERLAY_URL` |
| `naviguide-simulator/src/components/` | Modal + EMODnet WMS (M9, M12) |

### Wave 2 (control)

| File | Role |
|---------|------|
| `backend/app/services/review_gold.py` | No more automatic pre-Gold |
| `backend/app/services/review_queue.py` | MPA candidates; neighbouring marina SMCFAC |
| `frontend/src/components/review/*` | Fiches aligned to contract |
| `backend/data/seamark_catalog.json` + `docs/CATALOGUE_SEAMARK.md` | C1–C3 |
| `backend/app/core/judge.py` + tests | C15 |
| `backend/tests/test_review*.py` / `test_capitaineries.py` | §0 test sentences |

### Wave 3 (NOAA / GEBCO)

| File | Role |
|---------|------|
| `backend/app/services/capitainerie_world.py` or `noaa_enc.py` | H2 (new module **if** the file outgrows the office) |
| `backend/app/routers/` | US lights / buoys export |
| `naviguide-simulator` / routing copy | H5 GEBCO lookup |
| `backend/tests/test_capitaineries.py` | NOAA patterns to extend |

### Wave 4 (satellite)

| File | Role |
|---------|------|
| `scripts/satellite/README.md` | S0 + Mac recipe |
| `scripts/satellite/*.py` | CDSE STAC, exports; **not** ACOLITE shipped in the VPS image |
| `backend/app/services/science_build.py` / router | Ingest the pilot GeoJSON (`source: sentinel-pilot`) |
| `frontend/src/components/SciencePanel.js` | Satellite filter |
| `naviguide-simulator/src/engine/ici.js` | Local science field |

**Forbidden to touch** (this plan): prod `naviguide/naviguide-app/`,
`infra/vps/sync-from-atlas.sh`, NetCDF cubes on the VPS.

---

## 15. Recipe

**Global** recipe once the four waves are done. Each wave
has its own in §13.

1. Sea basemap: modal → accept → banner still there.
2. Marinas mode: light EMODnet bathy **without** going through Science.
3. This week’s overlay visible; export `metadata.version` =
   stamp of the `data-*` release.
4. Harbour-office Gold: Map unchanged while “Show the
   review” is unchecked.
5. Marina fiche: an SMCFAC at 200 m displays as **control**,
   not as identity.
6. Judge: VHF quote → `true`; restaurant ad → `false`.
7. Chesapeake: NOAA light or buoy. Bay of Biscay: **zero** NOAA.
8. Mid-Atlantic: GEBCO answers in the simulator. In a harbour:
   `null`.
9. Science + pilot: coastline + `error_m` vs EMODnet + banner.
   Review tab = placeholder.
10. Prod `blueintelligence.online` / `naviguide.fr`: this plan does
    **not** deploy them on its own. Wave 1–2 = BI PR. Wave 3–4
    simulator = `naviguide-simulator/` PR only.

---

## 16. Risks

| Risk | Mitigation |
|--------|------------|
| Seascape without attribute → contour impossible | M14 first; else EMODnet + depth point |
| GitHub release unreachable for the overlay | VPS copy `current.pmtiles` (small) |
| EMODnet WMS everywhere: perf / readability | Default **off**; `pointer-events: none` panes already |
| Confusing CDSE and CMEMS | Blocking S0; two READMEs |
| ACOLITE too heavy | Never on the VPS; 1–2 scenes |
| Gold too easy (OSM ⇒ Gold) | C8–C10 before displaying more NOAA objects |
| Presenting SDB as a sounding | `kind` / `method` / disclaimer; Review off |
| Extending NOAA worldwide | ENC Direct bbox filter; Mediterranean test = 0 |
| Gluing GEBCO onto a harbour | `null` under the coastal threshold |
| VLM “that sees the map” | Prompt + tests: textual mention only |

---

## 17. Out of scope

- **S-101** encoder / decoder or reading **S-57** files.
- **IENC / VNF** (inland navigation).
- **Vector** EMODnet contours on the VPS.
- GEBCO as a harbour layer or BI basemap.
- Image georeferencing (sketch, chart PDF, Sentinel) by VLM
  or by `geo.py`.
- Full **S-52** engine (symbols, light sectors, ECDIS
  safety contour).
- Review / Gold Science, Climatology, Sentinel pilots (V1).
- Modify `naviguide.fr` (prod) or merge simulator ↔ prod.
- Rivers, lakes, outside the corridor for Sentinel.
- StormGlass / Windy / paid charts as a source.

---

## 18. Documents this plan inherits

| Document | What we keep from it |
|----------|-------------------|
| `README.md` | Seamap basemap, sha256 exports, catalogue, warning |
| `docs/CATALOGUE_SEAMARK.md` | OSM → BI fields; audit; no invention |
| `docs/CONTRATS_MODES.md` | 7 modes; Science = structured APIs; geocoding = names |
| `docs/CONTRATS_REVIEW_PAR_MODE.md` | Gold meta-contract; “Show the review”; no Science/Climat |
| `docs/CAHIER_DES_CHARGES_REVIEW.md` | Formalities human queue |
| `docs/PLAN_IMPLEMENTATION_CLIMATOLOGIE.md` | BI shows / NAVIGUIDE uses; off VPS; honest `null` |
| `docs/PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md` | Leaflet; prod untouched; pills; `ici()` |
| `docs/hackathon-nebius-nvidia.md` | Gold + Tavily + Ultra; Science = 0 or 1 local; disclaimer |
| `infra/vps/seamap/README.md` | PMTiles mirror; Monday cron; no Seamap GPL |
| `.github/workflows/weekly-data-build.yml` | Overlay already built |

In case of conflict:

- **object of a mode** → `CONTRATS_MODES.md`;
- **Gold / map** → `CONTRATS_REVIEW_PAR_MODE.md` §0 and §8;
- **sea basemap / overlay** → this plan, wave 1;
- **simulator vs prod** → stage 1 plan (Leaflet, prod untouched);
- **S-101 / S-57 / pixel registration** → §4 of this plan (refused).
