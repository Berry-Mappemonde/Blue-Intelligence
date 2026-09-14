# Cartographic tracks diagnostic — 14 September 2026

Wave 0 of the plan `docs/PLAN_IMPLEMENTATION_FILIERES_CARTO.md`.
No secret. Reading of the public Seamap `style.json` and the NOAA ENC
Direct MapServer.

## M14 — Seamap / Seascape depth attribute

**Yes.** The style `https://tiles.openwaters.io/seamap/style.json`
loads `seascape-vector` (Open Waters CDN, not the VPS).

| Style layer | Source | `source-layer` | Useful attribute |
|-------------|--------|----------------|----------------|
| `depth-areas` | `seascape-vector` | `depare` | `drval1` (filter `unsurveyed` = `!has drval1`) |
| `contour-lines` | `seascape-vector` | `contours` | present; exact property to confirm at paint |
| `soundings` | `seascape-vector` | `soundings` | point soundings |
| `depth-shading` | `seascape-dem` | — | DEM raster, **no** per-pixel attribute on the client |

Consequence: **M15 is possible** — MapLibre fill on `depare`
where `drval1` < skipper threshold (2 / 5 / 10 m). This is **not** an
S-52 engine. Seascape stays on the CDN (outside the VPS budget).

## H1 — NOAA ENC Direct (API, US waters)

MapServer: `https://gis.charttools.noaa.gov/arcgis/rest/services/encdirect`

Already wired for offices: `FUNCTN=2` (harbour / approach /
coastal / berthing).

Layers useful for lights / buoys (points):

| Service | id | Name |
|---------|----|-----|
| `enc_harbour` | 11 | Harbor.Light_point |
| `enc_harbour` | 6 | Harbor.Buoy_Lateral_point |
| `enc_harbour` | 4–8 | other buoys |
| `enc_harbour` | 1–3 | beacons |
| `enc_approach` | 13 | Approach.Light_point |
| `enc_approach` | 6–10 | buoys |
| `enc_coastal` | 10 | Coastal.Light_point |
| `enc_coastal` | 4–7 | buoys |
| `enc_berthing` | 6 | Berthing.Light_point |

No obvious `DEPARE` / vector isobath layer under these
names in the public MapServer queried. US isobaths remain
outside the V1 API (we do not download S-57 cells).

## S0 — CDSE vs CMEMS account

**Yes** (2026-09-14, operator Berry). CMEMS remains the climatology
login (`scripts/climatology/cmems_auth.py`). CDSE
(`dataspace.copernicus.eu`) is a **different** portal, different
password, stored in `scripts/satellite/.env` (gitignored).

See `scripts/satellite/README.md`. No secret in git.
