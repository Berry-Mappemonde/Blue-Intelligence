#!/usr/bin/env python3
"""Construit un snapshot figé des réponses Overpass pour les 1169 ports d'entrée.

Réutilise ``overpass_around`` et les fonctions de cache de ``enrich_ci_osm.py``.
Format identique au cache CI_OSM_CACHE :
    {"version": 1, "ports": {port_id: {"lat": ..., "lon": ..., "elements": [...]}}}
Résumable : saute les ports déjà présents dans le snapshot.
Lit ``seed/ports_of_entry.geojson``. N'utilise pas Mongo.
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "backend" / "scripts"))

from enrich_ci_osm import _load_cache, _save_cache  # noqa: E402
from app.services.osm_validate import overpass_around  # noqa: E402

SEED = REPO / "seed" / "ports_of_entry.geojson"
SNAPSHOT = REPO / "backend" / "tests" / "fixtures" / "osm-ports.snapshot.json"
CONCURRENCY = 3


def load_ports() -> list[dict]:
    data = json.loads(SEED.read_text(encoding="utf-8"))
    feats = data["features"]
    ports = []
    for f in feats:
        p = f["properties"]
        lon, lat = f["geometry"]["coordinates"]
        ports.append(
            {
                "_id": p["id"],
                "name": p.get("name"),
                "lat": lat,
                "lon": lon,
            }
        )
    return ports


async def main() -> None:
    ports = load_ports()
    cache = _load_cache(SNAPSHOT) if SNAPSHOT.is_file() else {}
    todo = [
        p
        for p in ports
        if str(p["_id"]) not in cache
    ]
    print(f"{len(ports)} ports au total, {len(todo)} restants à interroger", flush=True)
    sem = asyncio.Semaphore(CONCURRENCY)
    done = len(cache)
    for port in todo:
        pid = str(port["_id"])
        async with sem:
            try:
                elements = await overpass_around(port["lat"], port["lon"])
            except Exception as exc:  # pas d'invention de données: on stocke vide
                print(
                    f"  {port['name']}: OVERPASS ECHEC {type(exc).__name__}: {exc}",
                    flush=True,
                )
                elements = []
        cache[pid] = {
            "lat": port.get("lat"),
            "lon": port.get("lon"),
            "elements": elements,
        }
        done += 1
        if done % 25 == 0 or done == len(ports):
            _save_cache(SNAPSHOT, cache)
            print(f"  {done}/{len(ports)} (dernier: {port['name']})", flush=True)
        await asyncio.sleep(0.4)  # politesse Overpass
    _save_cache(SNAPSHOT, cache)
    print(f"Termine: {len(cache)}/{len(ports)} ports dans {SNAPSHOT}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
