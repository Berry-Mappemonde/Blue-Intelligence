# Sentinel pilots — Berry corridor (off the VPS)

Stream 4 of the plan `docs/PLAN_IMPLEMENTATION_FILIERES_CARTO.md`.
The VPS **serves** a versioned GeoJSON. It does not download images
and does not run ACOLITE / CoastSat / ICESat-2.

## S0 — CDSE account (confirmed 2026-09-14)

CMEMS (wind, wave, current, climatology —
`scripts/climatology/cmems_auth.py`) **is not** CDSE
(Sentinel-2 images, `dataspace.copernicus.eu`).

| Question | Answer |
|----------|--------|
| Separate CDSE access from the CMEMS login? | **yes** |
| Who owns the login? | The Berry operator's dataspace.copernicus.eu account |

Credentials go in `scripts/satellite/.env` (gitignored).
Template: `scripts/satellite/.env.example`.
**No password in git.**

```bash
# On the Mac, in the project folder:
cp scripts/satellite/.env.example scripts/satellite/.env
# Then fill in CDSE_USERNAME and CDSE_PASSWORD (password in quotes).

python3 scripts/satellite/check_login.py
python3 scripts/satellite/search_stac.py --limit 2
```

`search_stac.py` **lists** 1–2 scenes around La Rochelle (30 M buffer).
It does not download the image files (too heavy; do that later
on the Mac).

## Next steps (S1 → S7)

1. S1 — Download 1–2 listed Sentinel-2 scenes (Mac, off the VPS).
2. S2 — ACOLITE locally (coastal atmospheric correction).
3. S3 — MNDWI / CoastSat → coastline.
4. S4 — Depth only if an ICESat-2 track crosses the scene.
5. S5 — Compare to EMODnet (`GET /api/depth` + WMS). Record `error_m`.
6. S6 — Stamp the GeoJSON:

```bash
python3 scripts/satellite/export_pilot.py \
  --in ~/Desktop/coastline-raw.geojson \
  --out backend/data/satellite/coastline.geojson
```

7. S7 — Import into Blue Intelligence (Science mode, source
   `sentinel-pilot`) via `POST /api/import/science.geojson`.
   **Not** in the `SOURCES` harvest. Review / Gold: off.

Forbidden: snapping the image with a VLM or `geo.py`. Present SDB
as a sounding. Running ACOLITE on the VPS.
