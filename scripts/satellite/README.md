# Pilotes Sentinel — corridor Berry (hors VPS)

Filière 4 du plan `docs/PLAN_IMPLEMENTATION_FILIERES_CARTO.md`.
Le VPS **sert** un GeoJSON versionné. Il ne télécharge pas d’images,
n’exécute pas ACOLITE / CoastSat / ICESat-2.

## S0 — Compte CDSE (confirmé le 2026-09-14)

CMEMS (vent, houle, courant, climatologie —
`scripts/climatology/cmems_auth.py`) **n’est pas** CDSE
(images Sentinel-2, `dataspace.copernicus.eu`).

| Question | Réponse |
|----------|---------|
| Accès CDSE distinct du login CMEMS ? | **oui** |
| Qui possède le login ? | Compte dataspace.copernicus.eu de l’opérateur Berry |

Les identifiants vont dans `scripts/satellite/.env` (gitignoré).
Modèle : `scripts/satellite/.env.example`.
**Aucun mot de passe dans git.**

```bash
# Sur le Mac, dans le dossier du projet :
cp scripts/satellite/.env.example scripts/satellite/.env
# Puis remplir CDSE_USERNAME et CDSE_PASSWORD (mot de passe entre quotes).

python3 scripts/satellite/check_login.py
python3 scripts/satellite/search_stac.py --limit 2
```

`search_stac.py` **liste** 1–2 scènes autour de La Rochelle (buffer 30 M).
Il ne télécharge pas les fichiers images (trop lourds, à faire plus tard
sur le Mac).

## Suite (S1 → S7)

1. S1 — Télécharger 1–2 scènes Sentinel-2 listées (Mac, hors VPS).
2. S2 — ACOLITE en local (correction atmosphérique côtière).
3. S3 — MNDWI / CoastSat → trait de côte.
4. S4 — Profondeur seulement si une trace ICESat-2 croise la scène.
5. S5 — Comparer à EMODnet (`GET /api/depth` + WMS). Noter `error_m`.
6. S6 — Tamponner le GeoJSON :

```bash
python3 scripts/satellite/export_pilot.py \
  --in ~/Desktop/coastline-raw.geojson \
  --out backend/data/satellite/coastline.geojson
```

7. S7 — Importer dans Blue Intelligence (mode Science, source
   `sentinel-pilot`) via `POST /api/import/science.geojson`.
   **Pas** dans la moisson `SOURCES`. Review / Gold : off.

Interdit : recaler l’image avec un VLM ou `geo.py`. Présenter le SDB
comme un sondage. Tourner ACOLITE sur le VPS.
