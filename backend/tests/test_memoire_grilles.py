"""Mémoire du masque terrestre et des grilles climatologiques.

Le masque 1 km ne doit plus résider en entier (933 Mo), une grille
mensuelle ne se recharge pas, le cache reste borné, et une requête
lourde laisse la boucle répondre.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import textwrap
import zipfile
from pathlib import Path

import numpy as np
import pytest
from numpy.lib import format as npformat

os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("DB_NAME", "bi_test_memoire_grilles")

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services import climatology_current as current_mod
from app.services import climatology_wave as wave_mod
from app.services import climatology_wind as wind_mod
from app.services import land_mask
from app.services.climatology_common import is_land


# Points vérifiés sur globe.is_land. La Nouvelle-Zélande et la côte de
# Miami ne tombent dans aucune boîte de repli : un retour aux boîtes
# les classerait tous les deux en mer.
_LAND = (
    (23.0, 5.0),          # Sahara
    (-33.0, -70.0),       # Andes
    (-41.3, 174.0),       # Île du Sud
    (-36.8, 174.7),       # Auckland
    (25.8, -80.2),        # Miami, terre
    (21.3, -157.8),       # Honolulu
    (-90.0, 0.0),         # pôle Sud, dernière ligne de la grille
    (51.5, -0.1),         # Londres
)
_SEA = (
    (15.0, -25.0),        # alizés
    (26.0, -80.0),        # Gulf Stream
    (-40.0, 10.0),        # 40°S
    (25.8, -80.1),        # large de Miami
    (0.0, 0.0),
    (90.0, 0.0),
    (0.0, 180.0),
    (0.0, -180.0),
)


def test_masque_compact_memes_reponses():
    land_mask.reset()
    before = land_mask.builds()
    for lat, lon in _LAND:
        assert is_land(lat, lon) is True, (lat, lon)
    for lat, lon in _SEA:
        assert is_land(lat, lon) is False, (lat, lon)
    assert land_mask.resident_bytes() < 8_000_000
    assert land_mask.builds() == before + 1


def test_masque_construit_une_seule_fois():
    land_mask.reset()
    before = land_mask.builds()
    assert land_mask.is_ocean(15.0, -25.0) is True
    assert land_mask.is_land(48.8, 2.3) is True
    assert land_mask.builds() == before + 1


def test_encodage_aligne_sur_les_octets_du_fichier():
    """Quelques cellules relues dans le npz, sans décompresser la grille."""
    path = land_mask.mask_path()
    assert path is not None
    state = land_mask._ensure()
    samples = (0, 1, state.nlat // 2, state.nlat - 1)
    lons = (0, 1, state.nlon // 2, state.nlon - 1)
    with zipfile.ZipFile(path) as archive:
        with archive.open("mask.npy") as raw:
            npformat.read_magic(raw)
            npformat.read_array_header_1_0(raw)
            for lat_i in samples:
                raw.seek(0)
                npformat.read_magic(raw)
                npformat.read_array_header_1_0(raw)
                raw.seek(lat_i * state.nlon, os.SEEK_CUR)
                row = raw.read(state.nlon)
                assert len(row) == state.nlon
                for lon_i in lons:
                    ocean = land_mask._ocean_scalar(state, lat_i, lon_i)
                    assert ocean is (row[lon_i] == 1), (lat_i, lon_i, row[lon_i], ocean)


def test_grille_mensuelle_non_rechargee_et_cache_borne():
    for mod, args in (
        (wind_mod, (3,)),
        (wave_mod, (3, wave_mod.wave_npz_path(3).stat().st_mtime)),
        (current_mod, (3,)),
    ):
        mod._load_month.cache_clear()
        assert mod._load_month.cache_parameters()["maxsize"] == 12
        first = mod._load_month(*args)
        assert first is not None
        misses = mod._load_month.cache_info().misses
        second = mod._load_month(*args)
        assert second is first
        info = mod._load_month.cache_info()
        assert info.misses == misses
        assert info.hits >= 1
        assert info.currsize <= 12
    wind_mod._load_month.cache_clear()
    loaded = wind_mod._load_month(1)
    assert loaded["u_mean"].dtype == np.float32
    assert loaded["sector_spd"].dtype == np.float32


def test_import_application_reste_sous_le_plafond():
    """Le process qui sert l'API ne doit plus monter d'un gigaoctet à l'import."""
    script = textwrap.dedent(
        """
        import os
        os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
        os.environ.setdefault("DB_NAME", "bi_test_memoire_grilles")
        os.environ.setdefault("SERVE_FRONTEND", "0")

        def rss_kb():
            with open("/proc/self/status") as fh:
                for line in fh:
                    if line.startswith("VmRSS:"):
                        return int(line.split()[1])
            raise SystemExit("rss")

        from app.main import app
        from app.services.climatology_common import is_land
        from app.services.land_mask import resident_bytes
        assert app.title
        assert is_land(23.0, 5.0) is True
        assert is_land(25.8, -80.1) is False
        assert resident_bytes() < 8_000_000
        print(rss_kb())
        """
    )
    env = os.environ.copy()
    env["MONGO_URL"] = "mongodb://127.0.0.1:27017"
    env["DB_NAME"] = "bi_test_memoire_grilles"
    env["SERVE_FRONTEND"] = "0"
    env["PYTHONPATH"] = str(BACKEND) + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(BACKEND),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    rss_kb = int(proc.stdout.strip().splitlines()[-1])
    # Avant : ~994 Mo dès l'import (masque 933 Mo). Le plafond laisse
    # la marge des imports, très en dessous de 1,5 Go.
    assert rss_kb < 250_000, rss_kb


def test_boucle_reactive_pendant_geojson_vent():
    async def _run():
        gaps = []
        task = asyncio.create_task(asyncio.to_thread(wind_mod.wind_geojson, 9, 1.0))
        loop = asyncio.get_running_loop()
        last = loop.time()
        while not task.done():
            await asyncio.sleep(0.05)
            now = loop.time()
            gaps.append(now - last)
            last = now
        fc = await task
        return fc, (max(gaps) if gaps else 0.0)

    fc, worst = asyncio.run(_run())
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) > 1000
    assert worst < 1.0, worst
