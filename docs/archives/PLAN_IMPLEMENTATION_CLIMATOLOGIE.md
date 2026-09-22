> **Archivé le 22 septembre 2026 — réalisé.** Atlas livré. Mémoire : houle climatologique (« swell not shipped »). Index : [docs/README.md](../README.md).

# Implementation plan — Climatology mode (7th Blue Intelligence mode)

Framing and workshop document. It records the September 2026 decisions:
passage simulation by **historical climatology**, not by GFS/IFS forecast;
inspiration from the OpenCPN plugin `climatology_pi` (spirit and API, not the GPL code);
**seventh mode** on Blue Intelligence; data **invisible but everywhere** in
NAVIGUIDE, with fusion of the maps already in place.

Written in plain language: this is the contract of what we seek, and of what
we refuse.

Version **1.0** — 13 September 2026.

**Contents**

1. In one sentence
2. Why this work exists
3. What we want to achieve
4. What we do not want
5. Vocabulary
6. Blue Intelligence / NAVIGUIDE split
7. OpenCPN inspiration (what we copy, what we refuse)
8. Current state and gaps
9. Shared shell (7th mode + API + panes)
10. Product 1 — 10 m wind and roses
11. Product 2 — Swell P50 / P90
12. Product 3 — Surface current
13. Product 4 — Cyclone risk (IBTrACS)
14. Rules (`run_rules`)
15. JSON contracts
16. Build order
17. Files touched
18. Licences and attributions
19. Recipe
20. Risks
21. Out of scope
22. Documents and conversations this plan inherits

---

## 1. In one sentence

Give the skipper a **sourced monthly atlas** (wind as roses, swell P50/P90,
current, cyclone tracks) to **simulate passages** of the Berry-Mappemonde
circumnavigation, display it as Blue Intelligence’s **seventh mode**, and
**use it without painting it** in NAVIGUIDE.

---

## 2. Why this work exists

NAVIGUIDE is an SADP (pleasure-craft decision-support system), not an ECDIS.
An expedition leg often **lasts longer than the predictability** of a model
(7 to 10 useful days, 15–16 days degraded). Wiring an isochrone to the
00 UTC GFS/IFS run gives the illusion of an arrival to the nearest day.

Historical climatology (means, roses, percentiles, tracks) is the honest
tool for “which month, which route, which plausible duration”. Forecast
remains a **tactical** complement (0–10 day departure window), not the
simulation engine.

The current code already inverts the roles a little, and badly:

- `getWind.py` reads a Copernicus **L4 NRT** wind with ~48 h lag (assimilated
  observation, not a forecast);
- `getWave.py` / `getCurrent.py` query **analysis + 10-day forecast**
  products, but truncate to yesterday’s `time=-1`;
- isochrone routing (port 3010, not deployed) calls `climatology.py`: a
  **hand-drawn atlas** (rectangular zones, a single kn / ° pair), not a
  historical grid;
- map simulation is still **geometric** (polar + distance), without wind;
- Blue Intelligence has **no** weather layer.

---

## 3. What we want to achieve

Two deliverables, **the same data snapshot**, two ways to show it.

### Blue Intelligence — 7th mode `climatology`

A mode of the same rank as Projects, Marinas, Harbour offices, Formalities,
MPAs, Science: header button, own colour, panel, dedicated map.

Inside the mode (filters, like Sextant / Argo in Science):

| Filter | Content |
|--------|---------|
| Wind | 8-sector roses, % of time, mean kn, % calm, % gale, MOST_LIKELY and AVERAGE summaries |
| Swell | Hs P50 and Hs P90, period, direction; raster overlay |
| Current | Arrows toward where it sets (monthly surface mean) |
| Cyclones | IBTrACS tracks for the displayed month |

**January–December** slider. Popups with provenance (model / product, period,
licence, `sample_count`). Banner “not suitable for navigation”.

### NAVIGUIDE — invisible but everywhere

The **same** grids feed isochrones, simulation, weather agent. They are
**not** a mandatory map layer. We merge the maps already there
(route, simulation, Copernicus click, BI pills, polar) into **one** MapLibre.
Climatology, EEZ and WPI stay in the engine (queries, crossings, briefing)
and **do not need to be turned on** on the map — we can remove them from
the pill panel.

---

## 4. What we do not want

- A climatology overlay **on every** BI mode (it is not an EMODnet basemap).
- An 8th “Climatology” switch in NAVIGUIDE.
- Presenting a 1991–2020 mean as “tomorrow’s wind”.
- Blending several models (`best_match`) **without** writing the product name.
- Inventing a field: `null` on land, on a `NaN` pixel, if the sample is too thin.
- An LLM that produces a wind, an Hs or a “cyclone season” without a number.
- Copying OpenCPN’s GPL C++ (`climatology_pi`) or the `0xfeff` binary.
- Downloading hourly worldwide GRIB/NetCDF cubes **onto the VPS** (4 vCores,
  8 GB RAM, ~35 GB free after seamap).
- StormGlass, Windy, PredictWind, Meteomatics, OpenWeather as the mode’s source.
- Replacing `getWind` / `getWave` / `getCurrent` (NRT / departure forecast) with
  climatology: **two distinct `kind`s**.

---

## 5. Vocabulary

| Word | Meaning here |
|-----|----------|
| **Climatology** | Monthly statistics over a named period (e.g. 1993–2019). `kind: "climatology"`. |
| **Forecast (NWP / AI)** | GFS, IFS, ICON, AIFS… 7–16 day horizon. Outside V1 of the mode. |
| **Analysis / NRT** | Copernicus L4 current-wind product used by NAVIGUIDE. Recent observation, not the atlas. |
| **Reanalysis** | ERA5, WAVERYS, GLORYS12: homogeneous past, source of the grids. |
| **Rose / atlas** | 8 sectors: % of time, mean kn, % ≤ 3 kn (calm), % ≥ 34 kn (gale). |
| **MOST_LIKELY** | Dominant rose sector (recommended by OpenCPN for routing). |
| **AVERAGE** | Vector mean u/v (often weaker than the scalar kn). |
| **P50 / P90** | Hs percentiles: “typical” vs “1 year in 10 above”. The no-go uses P90. |
| **Snapshot** | Files precomputed **off the VPS**, versioned (`metadata` + sha256), only **served** in prod. |

---

## 6. Blue Intelligence / NAVIGUIDE split

```
                    climatology snapshot (offline)
                    wind-roses · swell P50/P90 · current · IBTrACS
                                    │
                 ┌──────────────────┴──────────────────┐
                 ▼                                     ▼
     Blue Intelligence                          NAVIGUIDE
     7th mode `climatology`                     engine, not the paint
     Header + panel + map                       isochrones, simulation,
     roses / raster / arrows / tracks           weather agent, crossings
                 │                                     │
                 │                          single merged map
                 │                          (route, sim, Copernicus click,
                 │                           useful BI pills)
                 │                          EEZ / WPI / atlas: in the
                 │                          code, not necessarily on screen
```

Split sentence: **BI shows the atlas. NAVIGUIDE uses it.**

---

## 7. OpenCPN inspiration (what we copy, what we refuse)

Repos: [rgleason/climatology_pi](https://github.com/rgleason/climatology_pi)
(maintenance), [seandepagnier/climatology_pi](https://github.com/seandepagnier/climatology_pi),
data [climatology_pi_data](https://github.com/seandepagnier/climatology_pi_data).
Manual: [opencpn-manuals…/climatology](https://opencpn-manuals.github.io/plugins/climatology/index.html).
Licence **GPL v3** — we re-read to understand, we **rewrite**.

OpenCPN already ships the wind / current / cyclone product: ~30-year
means compressed (~7 MB), month slider, roses (barbs = 5 kn, blue centre =
calm, red = gale), current arrows, tracks by basin, and three callbacks
for `weather_routing_pi` (`ClimatologyData`, `ClimatologyWindAtlasData`,
`CycloneTrackCrossings`). AVERAGE / MOST_LIKELY / CUMULATIVE_MAP modes.
**Swell is not shipped** (“swell and seastate not yet implemented”).

| We copy | We refuse |
|----------|-----------|
| Rose rather than a single arrow | Binary format `wind01.gz` / magic `0xfeff` |
| Calm ≤ 3 kn, gale ≥ 34 kn | GPL C++ code |
| MOST_LIKELY vs AVERAGE | Unisys tracks (we take IBTrACS) |
| `CycloneTrackCrossings` | Dropping currents &lt; 0.2 without naming it |
| Compressed snapshot, not a live cube | Processing 180 GB on the VPS |
| Interpolation between two months | Clouds, lightning, humidity, WOA bathymetry (Science / EMODnet handle those) |
| “Grain of salt” warning | Silent El Niño mean with no period written |

---

## 8. Current state and gaps

| Place | Today | Target |
|---------|-------------|-------|
| `frontend/src/App.js` + `Header.js` | 6 modes | 7th `climatology` |
| `layerOrder.js` | `basemap-gl`, `route`, `amp`, `formalities-escales` | + climatology raster/vector panes, **lit only** if `mode === "climatology"` |
| `getWind.py` | L4 NRT, `now-2j`, `time=-1` | Unchanged for the “recently observed” click |
| `getWave.py` / `getCurrent.py` | ANFC, last step from yesterday | Unchanged for 0–10 d departure; simulation = climo snapshot |
| `climatology.py` | Hand-drawn zones | Fallback if the grid is missing; never again the source |
| `isochrone.py` | Single `wind_at(lat, lon, month)` | MOST_LIKELY + current + P90 no-go + crossings |
| `SimulationPanel.jsx` | Geometry only | Consumes the leg’s month, **without** drawing the atlas |
| `MaritimeLayers.jsx` | EEZ, WPI, marks, 5 BI export pills | One merged map; EEZ / WPI / climo off UI if unused |
| Agent `meteo_agent.py` | Optional StormGlass + LLM | IBTrACS count for the month on the leg |

---

## 9. Shared shell (7th mode + API + panes)

To put in place **before** the four products. Without it, each product
reinvents the header and the metadata.

| Task | Files | Detail |
|-------|----------|--------|
| C0. Mode | `App.js`, `Header.js`, `i18n.js`, `README.md`, `CONTRATS_MODES.md` | `mode === "climatology"`. Own colour (neither Science violet nor Projects cyan). `data-testid="mode-toggle-climatology"`. Header comment: no more “Six-mode switch”. |
| C1. Panes | `layerOrder.js` + `layerOrder.test.js` | `climatology-raster@250`, `climatology-vector@260`, `pointer-events: none`. The test freezes the list. Lighting only in the 7th mode. |
| C2. HTTP | `backend/app/routers/climatology.py` | `GET /api/climatology/meta` ; `GET /api/climatology/point?lat=&lon=&month=` ; `GET /api/climatology/{wind\|wave\|current\|cyclones}.geojson?month=`. Every field `kind: "climatology"`. `null` on land. |
| C3. Metadata | `app/core/export_meta.py` | `version`, `content_sha256`, `license`, `disclaimer` / `disclaimer_fr`, plus `period`, `month`, `source_ids`, `doi`. |
| C4. Panel | `ClimatologyPanel.js` | Slider 1–12, Wind / Swell / Current / Cyclones filters, legend, attribution. Off on first display (except possibly wind, to decide at implementation). |
| C5. Map | `useClimatologyLayer.js` + `MapView.js` branch | Like `useScienceLayer`: only if `mode === "climatology"`. |
| C6. Rules | `run_rules.json` family `climatology.*` | See §14. Law = no disguised forecast, no LLM. |
| C7. Snapshot | `backend/data/climatology/` + snapshot export | Generated **off the VPS** (Mac). The server serves the files. |
| C8. Review | — | **No** Review / Gold / `RunSelector` in V1 (like Science: harvest or snapshot, not a Gold run). |

Exit criterion C: the 7th button changes the map and the panel; `meta` + `point`
return `kind`, `month`, `period`, licence; panes green in the test; the six
other modes show no rose.

### NAVIGUIDE — map fusion (same shell)

| Task | Files | Detail |
|-------|----------|--------|
| N1 | `climatology_query` on the `naviguide-api` side or reading BI snapshots | Point / crossings **without** a climatology MapLibre Source |
| N2 | `MaritimeLayers.jsx`, `Sidebar.jsx` | One map; remove EEZ, WPI, climatology pills from the UI (data still fetchable) |
| N3 | `isochrone.py`, `SimulationPanel` / `useLegContext` | Consume the month; no atlas layer |
| N4 | `meteo_agent.py` | IBTrACS number, not an invented season text |

---

## 10. Product 1 — 10 m wind and roses

### In one sentence

For each month, a **rose** (8 sectors, % of time, mean kn, % calm,
% gale) and two summaries (MOST_LIKELY, AVERAGE).

### Source

A monthly mean (ERA5 monthly CDS, or
`WIND_GLO_PHY_CLIMATE_L4_MY_012_003`) gives **arrows only**. OpenCPN
builds the atlas from SeaWinds **6 h**.

We stay on Copernicus (account already in `COPERNICUS_USERNAME`):

| Product | Dataset | Role |
|---------|---------|------|
| NRT (current code) | `cmems_obs-wind_glo_phy_nrt_l4_0.125deg_PT1H` | “Recently observed” click — outside this product |
| Hourly MY | `cmems_obs-wind_glo_phy_my_l4_0.25deg_PT1H` | **Source of the roses** (u/v 10 m, 1994 → month-3) |
| Monthly climatology | `WIND_GLO_PHY_CLIMATE_L4_MY_012_003` | AVERAGE-arrows net only (V0) |

PUM: [CMEMS-WIND-PUM-012-004-006](https://documentation.marine.copernicus.eu/PUM/CMEMS-WIND-PUM-012-004-006.pdf).

Direction: `atan2(-u, -v)` (where the wind comes from), already in `getWind.py`.
Stored mesh: 0.5°. Target period: `1994-01..2020-12`.

### Phases

**A — Offline pipeline (Mac)**

| Task | Files | Detail |
|-------|----------|--------|
| A1 | `scripts/climatology/gen_wind_atlas.py` | `copernicusmarine.subset` MY 0.25°, one calendar month × years 1994–2020, **6 h subsample**. kn = m/s × 1.94384. |
| A2 | same script | 8 sectors, calm/gale, optional 10 kn bins. Sector &lt; 2.5 % → 0. Cell too thinly sampled → `null`. |
| A3 | `backend/data/climatology/wind/wind-MM.npz` + `.atlas.json` | 12 documented files. Not the GPL binary. |
| A4 | `gen_wind_mean.py` (optional) | AVERAGE arrows from the climate product — visible V0, not the rose deliverable. |

Criterion A: 15°N, 25°W, March: dominant NE rose; calm/gale ∈ [0, 100];
`sample_count` &gt; 0 at sea; `null` over the Sahara.

**B — API** — `climatology_wind.py`: `atlas_at(lat, lon, month)`, bilinear
interpolation + between months. `point` fills `wind_atlas`. GeoJSON: 1° offshore,
0.5° if requested.

**C — BI map** — `useClimatologyWind.js`: roses on the vector pane
(length = %, barbs = 5 kn, blue/red centre). Popup: MOST_LIKELY **and**
AVERAGE, period, `sample_count`. Never “forecast wind”.

**D — NAVIGUIDE** — `wind_at` reads the atlas (`most_likely` by default). Zone
lookup = fallback. `isochrone.py`: `mode=most_likely\|average` recorded on the route.

---

## 11. Product 2 — Swell P50 / P90

### In one sentence

Two monthly Hs P50 and Hs P90 fields + period and direction: mode overlay,
isochrone no-go. OpenCPN never shipped this.

### Source

[GLOBAL_MULTIYEAR_WAV_001_032](https://data.marine.copernicus.eu/product/GLOBAL_MULTIYEAR_WAV_001_032/description)
(WAVERYS / MFWAM, 0.2°). PUM: [CMEMS-GLO-PUM-001-032](https://documentation.marine.copernicus.eu/PUM/CMEMS-GLO-PUM-001-032.pdf).

| Dataset | Content | Enough for P90? |
|---------|---------|-------------------|
| `cmems_mod_glo_wav_my_0.2deg-climatology_P1M-m` | **Mean** 1993–04/2019 of `VHM0`, `VTM02` | No |
| `cmems_mod_glo_wav_my_0.2deg_PT3H-i` | 3 h instantaneous + partitions | **Yes** — percentiles offline |

Variables: `VHM0`, `VTM02`, `VMDR`, `VHM0_SW1` / `VMDR_SW1` (same names as
`getWave.py`, different product). Forbidden to label a mean “P90”.

### Phases

**A0** — `gen_wave_mean.py`: climatology_P1M-m dataset, V0 overlay `stat: mean`.
**A1** — `gen_wave_pct.py`: for each month, PT3H all years, `nanpercentile`
50 and 90, `circmedian` for `VMDR`. One month at a time, never the worldwide cube in RAM.
**A2** — `wave-MM.npz`: `hs_p50`, `hs_p90`, `period`, `dir`, sea mask.

Criterion A: 40°S in July, `hs_p90` &gt; `hs_p50` &gt; 0; Andes = null.

**B / C** — API + mode raster (P50 / P90 buttons). Popup: “1 year in 10,
Hs &gt; X m this month (period 1993–2019)”.

**D** — `is_wave_hazard` if `hs_p90 > climatology.wave_nogo_m` (default 2.5 m,
already in `overWave`). `getWave.py` unchanged (departure forecast).

---

## 12. Product 3 — Surface current

### In one sentence

Twelve monthly surface u/v fields (1993–2016 mean), arrows toward where
it sets, drift in a calm and isochrone correction.

### Source (the simplest)

[GLOBAL_MULTIYEAR_PHY_001_030](https://data.marine.copernicus.eu/product/GLOBAL_MULTIYEAR_PHY_001_030/description)
(GLORYS12). PUM: [CMEMS-GLO-PUM-001-030](https://documentation.marine.copernicus.eu/PUM/CMEMS-GLO-PUM-001-030.pdf).

Already-climatological dataset:
`cmems_mod_glo_phy_my_0.083deg-climatology_P1M-m`

12 means 1993–2016, `uo` / `vo` / `thetao`, first level `depth ≈ 0.494 m`
(`minimum_depth=0.5`, `maximum_depth=1.0`, like `getCurrent.py`).

Do not confuse with `cmems_mod_glo_phy_anfc_0.083deg_PT1H-m` (click forecast).

Convention: `atan2(u, v)` — **toward where** it sets. Documented low threshold
(`climatology.current_min_kn`): below it, vector 0 **and** flag
`below_threshold`, not a silent null.

### Phases

**A** — `gen_current.py`: one surface subset, 12 steps. Option: 0.25° for the
map, 1/12° for the point.

Criterion A: 26°N, 80°W (Gulf Stream, February) &gt; 1 kn toward the NE; Sahara = null.

**B / C** — arrows on the vector pane of the BI **mode**, stackable with the roses.

**D** — after `move_position` on wind, add `current × time_step_h` in
`isochrone.py`. `getCurrent.py` unchanged.

---

## 13. Product 4 — Cyclone risk (IBTrACS)

### In one sentence

Historical tracks **since 1980**, filtered by month, plus `crossings` to
forbid an isochrone leg. Season **as a number**.

### Source

[IBTrACS v04r01](https://www.ncei.noaa.gov/products/international-best-track-archive),
CSV `ibtracs.since1980.list.v04r01.csv`.
[Columns](https://www.ncei.noaa.gov/sites/default/files/2025-09/IBTrACS_v04r01_column_documentation.pdf).
Licence: unrestricted redistribution (ERDDAP).

Columns: `SID`, `SEASON`, `BASIN` (NA, EP, WP, NI, SI, SP, SA), `ISO_TIME`,
`LAT`, `LON`, `TRACK_TYPE`, `USA_STATUS`, `USA_WIND` (kn, 1 min), `USA_PRES`,
`WMO_WIND` (10 min depending on basin — **document the mix**: `USA_WIND` else
`WMO_WIND`, field `wind_source`).

Filter: `TRACK_TYPE == main` (not `spur`). Antimeridian: split LineStrings
WP/SP that cross 180°.

Routing API (OpenCPN spirit):

`crossings(lat1, lon1, lat2, lon2, month, dayrange) → { count, storms[] }`

### Phases

**A** — `gen_cyclones.py`: one GeoJSON + index `{month: [sid…]}`.
Criterion A: September NA full; February NA empty; SP January–March full.

**B / C** — traces in BI mode, colour by `max_wind_kn`. Click: SID, year,
max kn, NCEI link.

**D** — isochrone: if `climatology.avoid_cyclone_tracks`, drop the step if
`crossings > 0`. Weather agent: integer for the month on the leg.

---

## 14. Rules (`run_rules`)

A number is not an opinion (`docs/REGLES_PARAMETRES.md`). Family
`climatology.*`.

| Id | Family | Default | Range | Phenomenon |
|----|---------|--------|------------|-----------|
| `climatology.wind_calm_kn` | geometry | 3 | 2–4 | Calm Beaufort 0–1 (OpenCPN) |
| `climatology.wind_gale_kn` | geometry | 34 | 34–41 | Gale Beaufort 8 |
| `climatology.wind_sectors` | law | 8 | — | 45° rose |
| `climatology.wind_min_sector_pct` | geometry | 2.5 | 1–5 | Sector noise |
| `climatology.wind_grid_deg` | budget | 0.5 | 0.25–1 | Atlas mesh |
| `climatology.wave_nogo_m` | geometry | 2.5 | 2.0–4.0 | `overWave` threshold |
| `climatology.wave_stat` | law | P90 = no-go, P50 = “typical” | — | Forbidden to label a mean P90 |
| `climatology.wave_period` | law | `1993-2019` | — | WAVERYS climo window; A1 may extend it if documented |
| `climatology.current_min_kn` | geometry | 0.15 | 0.05–0.30 | Noise vs useful drift |
| `climatology.current_depth_m` | law | 0.5 | — | First GLORYS level |
| `climatology.current_period` | law | `1993-2016` | — | PUM climatology dataset |
| `climatology.cyclone_first_year` | law | 1980 | — | since1980 file |
| `climatology.cyclone_dayrange` | geometry | 21 | 7–45 | Window around the route day |
| `climatology.cyclone_radius_nm` | geometry | 120 | 60–200 | Popup counter “near the leg” |
| `climatology.cyclone_min_kn` | geometry | 34 | 34–64 | Display at least tropical storm |
| `climatology.avoid_cyclone_tracks` | law | true in simulation | — | Isochrone constraint |

Non-overridable law: climatology `kind` ≠ forecast; no LLM for a
wind / an Hs / a cyclone counter.

---

## 15. JSON contracts

### Query point

```json
{
  "kind": "climatology",
  "month": 3,
  "period": "1991-2020",
  "provenance": {
    "wind": "CMEMS WIND MY L4 0.25°",
    "wave": "WAVERYS GLOBAL_MULTIYEAR_WAV_001_032",
    "current": "GLORYS12 GLOBAL_MULTIYEAR_PHY_001_030 climatology_P1M-m",
    "cyclone": "IBTrACS v04r01 since1980"
  },
  "coordinates": { "latitude": 15.24, "longitude": -42.85, "cell_selection": "sea" },
  "wind_atlas": {
    "sectors_deg": 45,
    "directions_from": [
      { "dir_deg": 45, "pct": 41, "speed_knots": 16.2 },
      { "dir_deg": 90, "pct": 22, "speed_knots": 14.0 }
    ],
    "calm_pct": 8,
    "gale_pct": 3,
    "most_likely": { "dir_deg": 45, "speed_knots": 16.2 },
    "vector_mean": { "dir_deg": 58, "speed_knots": 12.1 },
    "sample_count": 1840
  },
  "wave": {
    "hs_p50_m": 1.8,
    "hs_p90_m": 3.1,
    "period_s": 8.4,
    "dir_deg": 70
  },
  "current": {
    "speed_knots": 0.4,
    "direction_to_deg": 280
  },
  "cyclone": {
    "tracks_in_month": 12,
    "crossings_if_leg": null
  }
}
```

On land: `wind_atlas`, `wave`, `current` set to `null` (structure kept).

`most_likely` and `vector_mean` both stay **visible**: the vector
mean is the pilot-chart trap.

### Wind GeoJSON (mode grid)

`FeatureCollection` + `metadata` (`export_meta`): `model` / product, `month`,
`period`, `grid_spacing_deg`, licence. Points: MOST_LIKELY `wind_speed_knots`,
`wind_direction_from_deg`, `calm_pct`, `gale_pct`.

---

## 16. Build order

```
C0–C8  7th mode + empty API + panes + panel
   ├─ 4  Cyclones     (CSV, shortest to see on the map)
   ├─ 3  Current      (12 surface NetCDF)
   ├─ 1  Wind roses   (6 h subset × ~27 years, Mac)
   └─ 2  Swell P90    (3 h WAVERYS, the heaviest; V0 = P1M mean in parallel)
        └─ “OpenCPN-grade” isochrones when 1+2+3+4 are wired
N1–N4  NAVIGUIDE map fusion (can advance in parallel as soon as the point API responds)
```

Until product 1 is there, we do not claim to replace `climatology.py`.

0–10 d forecast (unlock CMEMS ANFC validity, GFS/IFS overlay):
**outside V1** of this mode. Another workshop, another `kind: "forecast"`.

---

## 17. Files touched

### Blue Intelligence

- `frontend/src/App.js`, `Header.js`, `i18n.js`, `MapView.js`
- `frontend/src/components/ClimatologyPanel.js` (new)
- `frontend/src/components/map/useClimatologyLayer.js` (new, or one hook per product)
- `frontend/src/components/map/layerOrder.js` + `__tests__/layerOrder.test.js`
- `backend/app/routers/climatology.py` (new)
- `backend/app/services/climatology_wind.py`, `_wave.py`, `_current.py`, `_cyclones.py`
- `backend/app/core/export_meta.py` (period / DOI fields)
- `backend/data/run_rules.json` + `docs/REGLES_PARAMETRES.md`
- `backend/data/climatology/` (git-lfs snapshots or `data-` release, to decide)
- `scripts/climatology/gen_*.py`
- `backend/tests/test_climatology_*.py`
- `README.md`, `docs/CONTRATS_MODES.md`

### NAVIGUIDE

- `naviguide/naviguide_workspace/naviguide_weather_routing/climatology.py`
- `naviguide/naviguide_workspace/naviguide_weather_routing/isochrone.py`
- `naviguide/naviguide-api/agents/meteo_agent.py`
- `naviguide/naviguide-app/src/components/MaritimeLayers.jsx`
- `naviguide/naviguide-app/src/components/Sidebar.jsx`
- `naviguide/naviguide-app/src/hooks/useLegContext.js` (leg month)
- `getWind.py` / `getWave.py` / `getCurrent.py`: **not** merged with the atlas

---

## 18. Licences and attributions

| Source | Licence | Credit |
|--------|---------|---------|
| CMEMS wind / wave / current | Copernicus Marine service licence | “Generated using E.U. Copernicus Marine Service Information” + product DOI |
| IBTrACS | Unrestricted redistribution | “IBTrACS v04r01, NOAA NCEI” |
| OpenCPN (idea only) | GPL v3 — we do not copy | No derived file |

7th-mode footer + `metadata.disclaimer_fr`: same phrases as `export_meta.py`
(not suitable for navigation, not a SOLAS document, METAREA / Navtex watch
unchanged).

---

## 19. Recipe

### Blue Intelligence (Climatology mode)

1. The 7th button shows the panel and the atlas map; the six other modes
   have no rose.
2. December, Atlantic 10–20°N: ENE/NE roses, not the single 18 kn / 050° of
   `climatology.py`.
3. P90 on, P50 off: roaring forties darker, summer Mediterranean calm.
4. Gulf Stream February: arrows &gt; 1 kn; Sahara: no current.
5. September slider, Caribbean: tangle of traces; March: almost empty.
6. Land click: wind / swell / current blocks at `null`.
7. CMEMS + IBTrACS attribution + navigation banner visible.

### NAVIGUIDE

1. No “climatology” / EEZ / WPI layer is required on screen for
   a simulation to give an ETA that **moves** with the month.
2. MOST_LIKELY isochrone ≠ AVERAGE on a trade-wind.
3. July 50°S isochrone more northerly as soon as P90 is wired.
4. Martinique→Azores `crossings` in September &gt; 0; in March = 0.
5. The weather agent cites an IBTrACS **integer**, not only “hurricane season”.
6. The Copernicus wind/wave/current click still speaks NRT / ANFC
   (different `kind`, product timestamp).

---

## 20. Risks

| Risk | Mitigation |
|--------|--------|
| 3 h WAVERYS / MY wind cube on the 8 GB VPS | Mac pipeline only; VPS = finished files |
| Confusing P1M mean and P90 | Mandatory `stat` field; test `p90 >= p50` |
| Confusing 48 h NRT and atlas | Two `kind`s, two endpoints |
| Wind `from` vs current `to` convention | Separate `atan2` tests; popup legend |
| Antimeridian (WP tracks, route) | Split LineStrings; never interpolate across Africa |
| Header too dense (7 buttons) | Short labels; icon only on a narrow viewport (to treat in UI) |
| OpenCPN GPL | Rewrite; licence review before merge |
| El Niño / climate change | Period written on screen; no “2027 truth” |
| Open-Meteo `best_match` | Outside V1; if one day forecast, model **named** |

---

## 21. Out of scope (V1)

- GFS / IFS / ICON / AIFS forecast and “this week” overlay **in the
  7th BI mode**. The **simulator** forecast workshop is
  [PLAN_IMPLEMENTATION_SIMULATION_B.md](./PLAN_IMPLEMENTATION_SIMULATION_B.md)
  (after
  [PLAN_IMPLEMENTATION_SIMULATION_A.md](./PLAN_IMPLEMENTATION_SIMULATION_A.md)).
- Unlocking `valid_time` of `getWave.py` / `getCurrent.py` (separate forecast
  workshop — B on the simulator side, not the NRT click).
- Self-hosting Open-Meteo, NOMADS GRIB ingestion.
- Review / Gold of Climatology mode.
- IBTrACS R34 radii, El Niño analogue years, 40+ kn wind bins.
- Full directional spectrum, Stokes, tidal currents.
- Clouds, lightning, humidity, precipitation (OpenCPN has them; this is not the
  V1 offshore skipper).
- 8th climatology pill in NAVIGUIDE.

---

## 22. Documents and conversations this plan inherits

- Product decisions (Sept. 2026): climatology first for passages;
  7th BI mode; NAVIGUIDE invisible + map fusion; four products opened.
- OpenCPN plugin `climatology_pi` (manual, `gendata/`, `ClimatologyOverlayFactory.h`)
  and `weather_routing_pi` (MOST_LIKELY, crossings).
- `docs/REGLES_PARAMETRES.md`, `docs/CONTRATS_MODES.md`, `docs/PRD.md`.
- `docs/archives/PLAN_IMPLEMENTATION_FILIERES_CARTO.md` — EMODnet / GEBCO / Science
  satellite: jobs distinct from the monthly atlas.
- `docs/archives/PLAN_IMPLEMENTATION_SIMULATION_A.md` — simulator-film ETA
  by month, fixed searoute line.
- `docs/archives/PLAN_IMPLEMENTATION_SIMULATION_B.md` — `kind: forecast` 0–10 d
  + Follow + one-leg isochrone, **inside** `naviguide-simulator/`.
- Code: `getWind.py`, `getWave.py`, `getCurrent.py`, `climatology.py`,
  `isochrone.py`, `useScienceWms.js`, `layerOrder.js`, `MaritimeLayers.jsx`,
  `export_meta.py`, `meteo_agent.py`.
- CMEMS PUM wind 012-004-006, waves 001-032, physics 001-030;
  IBTrACS v04r01; ERA5 monthly (rejected as the **sole** source of the roses).
