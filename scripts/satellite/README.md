# Pilotes Sentinel — corridor Berry (hors VPS)

Filière 4 du plan `docs/PLAN_IMPLEMENTATION_FILIERES_CARTO.md`.
Le VPS **sert** un GeoJSON versionné. Il ne télécharge pas d’images,
n’exécute pas ACOLITE / CoastSat / ICESat-2.

## S0 — Compte CDSE (bloquant humain)

CMEMS (vent, houle, courant, climatologie —
`scripts/climatology/cmems_auth.py`) **n’est pas** CDSE
(images Sentinel-2, `dataspace.copernicus.eu`).

| Question | Réponse (à remplir par l’opérateur) |
|----------|-------------------------------------|
| Accès CDSE distinct du login CMEMS ? | **non vérifié** (aucun secret dans git, 2026-09-14) |
| Qui possède le login ? | — |

Sans S0 = oui, **pas de downloader**. Ce dossier n’en contient pas.

## Recette Mac (opérateur)

1. Confirmer S0.
2. Télécharger 1–2 scènes Sentinel-2 qui couvrent le corridor
   `backend/data/route.geojson` (buffer ~30 M) via le STAC CDSE.
3. ACOLITE + MNDWI / CoastSat **en local**.
4. Comparer à EMODnet (`GET /api/depth` + WMS). Noter `error_m`.
5. Produire un GeoJSON OSM-shaped (`natural=coastline` et, si ICESat-2,
   `seamark:type=depth_area`).
6. Tamponner :

```bash
python3 scripts/satellite/export_pilot.py \
  --in ~/Desktop/coastline-raw.geojson \
  --out backend/data/satellite/coastline.geojson
```

7. Importer dans Blue Intelligence (mode Science, source `sentinel-pilot`)
   via `POST /api/import/science.geojson`. **Pas** dans la moisson
   `SOURCES`. Review / Gold : off (placeholder).

Interdit : recaler l’image avec un VLM ou `geo.py`. Présenter le SDB
comme un sondage. Tourner ACOLITE sur le VPS.
