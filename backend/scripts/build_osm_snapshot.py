#!/usr/bin/env python3
"""Construit le cache Overpass pour les 1169 ports d'entrée.

Réutilise ``overpass_around``. Format identique au cache CI_OSM_CACHE :
    {"version": 1, "ports": {port_id: {"lat": ..., "lon": ..., "elements": [...]}}}
Résumable : saute les ports déjà présents dans le cache.
Lit ``seed/ports_of_entry.geojson``. N'utilise pas Mongo.

Sur une réponse Overpass réussie, stocke les elements (même une liste vide,
car une vraie réponse "rien trouve" est une reponse valide). Sur un echec,
ne stocke rien (le port reste manquant et est retry au prochain lancement).
Arrete de lancer de nouvelles requetes quand le budget est atteint
(verifie APRES avoir acquis le semaphore).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "backend" / "scripts"))

from app.services.osm_validate import overpass_around  # noqa: E402

SEED = REPO / "seed" / "ports_of_entry.geojson"
CONCURRENCY = 2
SAVE_EVERY = 1  # sauvegarde apres chaque port reussi
POLITE_DELAY_S = 0.5  # delai poli entre requetes Overpass


def load_ports() -> list[dict]:
    data = json.loads(SEED.read_text(encoding="utf-8"))
    feats = data["features"]
    ports = []
    for f in feats:
        p = f.get("properties") or {}
        coords = (f.get("geometry") or {}).get("coordinates") or []
        if len(coords) != 2:
            continue
        lon, lat = float(coords[0]), float(coords[1])
        pid = str(p.get("id") or "").strip()
        name = str(p.get("name") or "").strip()
        if not pid or not name:
            continue
        ports.append(
            {
                "_id": pid,
                "name": name,
                "lat": lat,
                "lon": lon,
            }
        )
    return ports


def _load_cache(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    ports = data.get("ports") if isinstance(data, dict) else None
    return ports if isinstance(ports, dict) else {}


def _save_cache(path: Path, ports: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"version": 1, "ports": ports}, ensure_ascii=False),
        encoding="utf-8",
    )


def _cached_entry(ports: dict, port: dict) -> dict | None:
    hit = ports.get(str(port["_id"]))
    if not isinstance(hit, dict):
        return None
    if hit.get("lat") != port.get("lat") or hit.get("lon") != port.get("lon"):
        return None
    return hit


async def _validate_port(
    port: dict,
    sem: asyncio.Semaphore,
    ports: dict,
    stats: dict,
    budget_s: int,
    t0: float,
    budget_state: dict,
) -> None:
    pid = str(port["_id"])
    cached = _cached_entry(ports, port)
    try:
        if cached is None:
            async with sem:
                # Verification du budget APRES avoir acquis le semaphore,
                # sinon toutes les coroutines passent le check a t=0.
                if budget_state["stopped"] or time.time() - t0 >= budget_s:
                    budget_state["stopped"] = True
                    stats["budget_stopped"] += 1
                    return
                elements = await overpass_around(port["lat"], port["lon"])
            # Reponse reussie (meme elements == []) : on stocke.
            ports[pid] = {
                "lat": port.get("lat"),
                "lon": port.get("lon"),
                "elements": elements,
            }
            stats["checked"] += 1
            status = f"OK ({len(elements)} elements)"
        else:
            elements = cached.get("elements")
            if not isinstance(elements, list):
                elements = []
            stats["cache"] += 1
            status = f"cache ({len(elements)} elements)"
        print(
            f"[{stats['checked'] + stats['cache'] + stats['budget_stopped']}] "
            f"{port['name']}: {status}",
            flush=True,
        )
    except Exception as exc:
        stats["failed"] += 1
        print(
            f"[{stats['checked'] + stats['cache'] + stats['budget_stopped']}] "
            f"{port['name']}: FAIL {type(exc).__name__}: {exc}",
            flush=True,
        )


async def main(cache_path: Path, budget_s: int) -> int:
    ports = load_ports()
    cache = _load_cache(cache_path)
    todo = [p for p in ports if str(p["_id"]) not in cache]
    print(
        f"{len(ports)} ports au total, {len(todo)} restants a interroger",
        flush=True,
    )
    if not todo:
        # Verifier la completude du cache existant
        complete = sum(
            1 for v in cache.values()
            if isinstance(v, dict) and v.get("lat") and v.get("lon")
            and isinstance(v.get("elements"), list)
        )
        if complete >= len(ports):
            print(f"cache Overpass complet {complete}/{len(ports)}", flush=True)
            return 0
        print(
            f"cache Overpass incomplet {complete}/{len(ports)}",
            flush=True,
        )
        return 2

    sem = asyncio.Semaphore(CONCURRENCY)
    stats = {"checked": 0, "failed": 0, "cache": 0, "budget_stopped": 0}
    budget_state = {"stopped": False}
    t0 = time.time()

    for port in todo:
        if budget_state["stopped"]:
            break
        await _validate_port(port, sem, cache, stats, budget_s, t0, budget_state)
        if stats["checked"] > 0 and stats["checked"] % SAVE_EVERY == 0:
            _save_cache(cache_path, cache)
        await asyncio.sleep(POLITE_DELAY_S)

    _save_cache(cache_path, cache)

    complete = sum(
        1 for v in cache.values()
        if isinstance(v, dict) and v.get("lat") and v.get("lon")
        and isinstance(v.get("elements"), list)
    )
    print(
        f"Termine: {complete}/{len(ports)} ports dans {cache_path}",
        flush=True,
    )
    if budget_state["stopped"]:
        print(
            f"budget de {budget_s}s atteint: arret propre (code 2)",
            flush=True,
        )
        return 2
    if complete < len(ports):
        print(
            f"cache Overpass incomplet {complete}/{len(ports)}",
            flush=True,
        )
        return 2
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Construire le cache Overpass OSM")
    parser.add_argument(
        "--cache",
        required=True,
        help="Chemin du fichier cache JSON (format version 1)",
    )
    parser.add_argument(
        "--budget-s",
        type=int,
        default=1500,
        help="Budget temps en secondes pour les requetes Overpass",
    )
    args = parser.parse_args()
    try:
        rc = asyncio.run(main(Path(args.cache), args.budget_s))
    except Exception as exc:
        print(f"build_osm_snapshot: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
    raise SystemExit(rc)
