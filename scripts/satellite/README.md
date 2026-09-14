# Wave 4 — Mac step-by-step guide (Sentinel)

Do this **on your Mac**, not on the server. One step at a time.
If a command prints an error, stop and reread that step’s
“If it blocks” box.

Images are heavy (~1 GB each). We start with **one** scene.

---

## Before you start (once)

1. Open **Terminal** (Spotlight: type `Terminal`, Enter).
2. Go to the project folder. Change the path if yours is elsewhere:

```bash
cd ~/Documents/Blue-Intelligence-Map
```

3. Create the secret file (if it does not exist yet):

```bash
cp scripts/satellite/.env.example scripts/satellite/.env
```

4. Open it:

```bash
open -e scripts/satellite/.env
```

5. Fill it in, **password in quotes**:

```
CDSE_USERNAME=your.email@example.com
CDSE_PASSWORD='your-password'
```

Save. This file is **not** sent to Git.

6. Check the login:

```bash
python3 scripts/satellite/check_login.py
```

You should read `CDSE : connexion OK`. Otherwise the password or the
account is wrong (CDSE = dataspace.copernicus.eu, not CMEMS).

---

## Step 1 — Download **one** L1C photo (S1)

ACOLITE needs **L1C** (raw image). **L2A** (already ESA-corrected)
is rejected: *Level-2A data not supported*.

**Why not use the “readier” ESA L2A?** ESA corrects mainly for land
(fields, forests). Over water that correction is often poor. ACOLITE
starts from L1C and corrects for the coast. So we do not skip ACOLITE:
it is not extra time for nothing. A L2A zip already on the Desktop
can stay there; do not point ACOLITE at it.

First refresh the list (`MSIL1C` scenes):

```bash
python3 scripts/satellite/search_stac.py --limit 2 --out scripts/satellite/scenes_la_rochelle.json
```

The `id` values must contain `MSIL1C`, not `MSIL2A`.

Then download **one** scene. This can take 10 to 40 minutes
depending on your connection.

```bash
python3 scripts/satellite/download_scenes.py --limit 1
```

The zip lands on the Desktop: `~/Desktop/sentinel-pilot/`.
A `download_receipt.json` file gives the `sha256` (S1 proof).

To see only whether the catalogue answers, without downloading:

```bash
python3 scripts/satellite/download_scenes.py --limit 1 --dry-run
```

**If it blocks.** Disk space: you need ~2 GB free (one zip +
unzip). Apple menu → Settings → General → Storage.

Then unzip the zip (double-click). You get a `.SAFE` folder.

---

## Step 2 — Clean sky and haze (S2, ACOLITE)

ACOLITE is a **separate** program. It does not run inside Blue Intelligence.

1. Install Python 3 if needed: [python.org/downloads](https://www.python.org/downloads/).
2. In Terminal:

```bash
cd ~
git clone https://github.com/acolite/acolite
cd acolite
python3 -m pip install -r requirements.txt
python3 launch_acolite.py
```

3. In ACOLITE:
   - **Input**: the **L1C** `.SAFE` folder from step 1
     (the name contains `MSIL1C`). Not the `MSIL2A` folder.
   - Output: e.g. `~/Desktop/sentinel-pilot/acolite`
   - Leave the **DSF** algorithm. ACOLITE writes L2R on its own.
   - Start. Wait for the end (often 15–40 min). The first run
     may download tables (LUT).

**If the log says** `Level-2A data not supported`: you pointed at
an L2A `.SAFE`. Rerun step 1 (L1C search + download) and change Input.

You should see GeoTIFF or NetCDF files in the ACOLITE output folder,
with green and SWIR bands (e.g. `rhos_561`, `rhos_1614`).
A folder that only contains `*_log_file.txt` and `*_settings_user.txt`
means the computation did not run.

---

## Step 3 — Coastline (S3, MNDWI)

Water is darker in SWIR than in green. We compute:

`MNDWI = (green − SWIR) / (green + SWIR)`

Then we keep the water / land **edge**.

**Simple path (QGIS, beginner)**

1. Install [QGIS](https://qgis.org) (Mac).
2. Open the two ACOLITE bands (green and SWIR).
3. Raster → Raster calculator:

```
("vert" - "swir") / ("vert" + "swir")
```

4. Extraction → Contour, threshold `0`.
5. Export as GeoJSON on the Desktop, e.g.
   `~/Desktop/sentinel-pilot/coastline-raw.geojson`.

One line (or a few lines) is enough. This is **not** a nautical chart.

---

## Step 4 — Depth only if ICESat-2 (S4)

```bash
cd ~/Documents/Blue-Intelligence-Map
python3 scripts/satellite/check_icesat2.py
```

- Message *“we do not invent a depth”*: **skip S4**.
  No `seamark:type=depth_area`. Go to step 5 with the coastline only.
- Message *“S4 is possible”* (this is the case around La Rochelle):
  ICESat-2 tracks **exist**. We compute depth **only**
  when the ATL24/ATL03 file is downloaded and aligned. Until then:
  coastline only, no invented sounding.

---

## Step 5 — Compare to EMODnet (S5)

```bash
python3 scripts/satellite/compare_emodnet.py \
  --in ~/Desktop/sentinel-pilot/coastline-raw.geojson \
  --out ~/Desktop/sentinel-pilot/coastline-emodnet.geojson
```

The script queries the EMODnet DTM. If there is **no** estimated
depth (normal case without S4), it records EMODnet and **does not
invent** a sounding.

---

## Step 6 — Stamp the file (S6)

```bash
python3 scripts/satellite/export_pilot.py \
  --in ~/Desktop/sentinel-pilot/coastline-emodnet.geojson \
  --out backend/data/satellite/coastline.geojson \
  --dataset sentinel-coastline
```

The file gets `natural=coastline`, `source=sentinel-pilot`,
a version and a “not for navigation” warning.

If a depth area existed (S4 only):

```bash
python3 scripts/satellite/export_pilot.py \
  --in ~/Desktop/sentinel-pilot/depth-raw.geojson \
  --out backend/data/satellite/depth_areas.geojson \
  --dataset sentinel-depth
```

---

## Step 7 — See it in Blue Intelligence (S7)

1. Start the site locally (as usual).
2. Enter (warning modal).
3. **Science** mode.
4. Gear → **Import GeoJSON** (admin account).
5. Choose `backend/data/satellite/coastline.geojson`.
6. Filter **Satellite (pilot)**.

Review stays **off** for this set. This is not Gold.
It is **not** mixed into the Sextant / Argo harvest.

From the command line (if the backend is already running):

```bash
curl -s -X POST http://127.0.0.1:8001/api/import/science.geojson \
  -H 'Content-Type: application/json' \
  --data-binary @backend/data/satellite/coastline.geojson
```

---

## What we never do

- Snap the image with a VLM or `geo.py`.
- Invent a depth without ICESat-2.
- Present this line as a navigation chart.
- Run ACOLITE or the download **on the VPS**.

---

## Already done here (do not redo)

- CDSE account verified (S0).
- Old L2A list in `scenes_la_rochelle.json`: **regenerate**
  with `search_stac.py` (L1C) before ACOLITE.
- Science filter `sentinel-pilot` in the app.
