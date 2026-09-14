# Diagnostic filières carto — 14 septembre 2026

Vague 0 du plan `docs/PLAN_IMPLEMENTATION_FILIERES_CARTO.md`.
Aucun secret. Lecture du `style.json` public Seamap et du MapServer
NOAA ENC Direct.

## M14 — Attribut de profondeur Seamap / Seascape

**Oui.** Le style `https://tiles.openwaters.io/seamap/style.json`
charge `seascape-vector` (CDN Open Waters, pas le VPS).

| Layer style | Source | `source-layer` | Attribut utile |
|-------------|--------|----------------|----------------|
| `depth-areas` | `seascape-vector` | `depare` | `drval1` (filtre `unsurveyed` = `!has drval1`) |
| `contour-lines` | `seascape-vector` | `contours` | présents ; propriété exacte à confirmer au paint |
| `soundings` | `seascape-vector` | `soundings` | sondes ponctuelles |
| `depth-shading` | `seascape-dem` | — | raster DEM, **pas** d’attribut par pixel côté client |

Conséquence : **M15 est possible** — aplat MapLibre sur `depare`
où `drval1` < seuil skipper (2 / 5 / 10 m). Ce n’est **pas** un
moteur S-52. Seascape reste sur CDN (hors budget VPS).

## H1 — NOAA ENC Direct (API, eaux US)

MapServer : `https://gis.charttools.noaa.gov/arcgis/rest/services/encdirect`

Déjà branché pour les bureaux : `FUNCTN=2` (harbour / approach /
coastal / berthing).

Layers utiles pour feux / bouées (points) :

| Service | id | Nom |
|---------|----|-----|
| `enc_harbour` | 11 | Harbor.Light_point |
| `enc_harbour` | 6 | Harbor.Buoy_Lateral_point |
| `enc_harbour` | 4–8 | autres bouées |
| `enc_harbour` | 1–3 | beacons |
| `enc_approach` | 13 | Approach.Light_point |
| `enc_approach` | 6–10 | bouées |
| `enc_coastal` | 10 | Coastal.Light_point |
| `enc_coastal` | 4–7 | bouées |
| `enc_berthing` | 6 | Berthing.Light_point |

Pas de couche `DEPARE` / isobathe vectorielle évidente sous ces
noms dans le MapServer public interrogé. Les isobathes US restent
hors V1 API (on ne télécharge pas de cellules S-57).

## S0 — Compte CDSE vs CMEMS

**Oui** (2026-09-14, opérateur Berry). CMEMS reste le login
climatologie (`scripts/climatology/cmems_auth.py`). CDSE
(`dataspace.copernicus.eu`) est un **autre** portail, autre mot
de passe, stocké dans `scripts/satellite/.env` (gitignoré).

Voir `scripts/satellite/README.md`. Pas de secret dans git.
