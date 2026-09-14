# Climatology snapshots — generated on the Mac, only served on the VPS

These scripts **must not** run on the VPS (4 vCores / 8 GB, ~35 GB
free). They write `backend/data/climatology/`:

| Script | Product | Output |
|--------|---------|--------|
| `gen_cyclones.py` | IBTrACS v04r01 since1980 | `cyclones/ibtracs_since1980.json` |
| `gen_current.py` | GLORYS12 climatology_P1M-m | `current/current-MM.npz` |
| `gen_wind_mean.py` | CMEMS wind climate P1M 1994–2020 | `wind/wind-MM.npz` (`stat: average`) |
| `gen_wind_atlas.py` | CMEMS wind MY L4 0.25° 6 h | `wind/wind-MM.npz` + roses |
| `gen_wave_mean.py` | WAVERYS climatology_P1M-m | `wave/wave-MM.npz` (`stat: mean`) |
| `gen_wave_pct.py` | WAVERYS PT3H, one month at a time | `wave/wave-MM.npz` (`hs_p50` / `hs_p90`) |

Mac prerequisites: a Copernicus account in `backend/.env`
(`COPERNICUS_USERNAME` / `COPERNICUS_PASSWORD`), `numpy`, `netCDF4` /
`xarray`, enough disk for **one month** at a time — never the worldwide
cube in RAM. Do not run this on the VPS.

### Roses — one command on the Mac

In Terminal (replace the path if your folder is elsewhere):

```bash
cd ~/Blue-Intelligence-Map
source backend/.venv/bin/activate
pip install copernicusmarine xarray netCDF4 numpy python-dotenv
bash scripts/climatology/gen_wind_atlas_mac.sh
```

If the Mac does not have a venv yet:

```bash
cd ~/Blue-Intelligence-Map
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install copernicusmarine xarray netCDF4 numpy python-dotenv
bash scripts/climatology/gen_wind_atlas_mac.sh
```

The 12 wind months often take **several hours**. `caffeinate`
prevents the Mac from sleeping. If it stops, rerun **the same
command**: the current month resumes at the next year. A month already
in rose form is skipped. If Copernicus hangs, the script kills that
year after 40 minutes and retries it on its own.

Hs P50/P90 (`gen_wave_pct_mac.sh`) is **heavier**: 3 h ×
1993–2019, one calendar month at a time, Hs histograms (never the
cube in RAM). Rerunning the same command resumes at the next year. A
month already in `p50_p90` is skipped — a P1M mean is not.

Hourly CMEMS wind comes in two datasets of the same product: 0.25° until
October 2009, then 0.125° until 2020. The script chains them and
stores a 0.5° grid. January–May 1994 do not exist: they are
skipped; that is not an error.

```bash
# Cyclones (free CSV, the shortest)
python3 scripts/climatology/gen_cyclones.py

# Current (12 surface NetCDFs — the simplest CMEMS)
python3 scripts/climatology/gen_current.py

# AVERAGE wind (monthly climatology — visible V0, not a rose)
python3 scripts/climatology/gen_wind_mean.py

# Wind roses — 12 months, on the Mac (not the VPS)
# Prevents sleep, resumes if the network drops.
bash scripts/climatology/gen_wind_atlas_mac.sh

# A single month (e.g. March, to check the trades)
python3 scripts/climatology/gen_wind_atlas.py --month 3

# Waves: P1M mean first (V0, do not label it P90), then percentiles
python3 scripts/climatology/gen_wave_mean.py --month 7
python3 scripts/climatology/gen_wave_pct.py --month 7

# Hs P50/P90 — 12 months, on the Mac (not the VPS)
# Prevents sleep, resumes if the network drops. Longer than the roses.
bash scripts/climatology/gen_wave_pct_mac.sh
```
