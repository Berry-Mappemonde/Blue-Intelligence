#!/usr/bin/env python3
"""Charge le Mongo de CI depuis les fichiers du dépôt.

Lit ``seed/projects.geojson``, ``seed/ports_of_entry.geojson`` et
``backend/data/eez_world_map.geojson``. N'accepte que
``mongodb://127.0.0.1`` ou ``mongodb://localhost``, base ``bi_ci``.
Refuse Atlas, le VPS OVH et toute URL avec identifiant.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

from pymongo import MongoClient
from shapely.geometry import shape

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
CI_DB_NAME = "bi_ci"
_LOCAL_HOSTS = {"127.0.0.1", "localhost"}
_BLOCKED = (
    "mongodb+srv",
    "mongodb.net",
    "135.125.",
    "ovh.net",
    "ovh.ca",
    "nebius",
)


def assert_ci_target(mongo_url: str, db_name: str) -> None:
    """Lève SystemExit si la cible n'est pas le Mongo jetable de CI."""
    raw = (mongo_url or "").strip()
    low = raw.lower()
    if not raw or any(token in low for token in _BLOCKED):
        raise SystemExit("refus: MONGO_URL n'est pas un Mongo de CI")
    if not low.startswith("mongodb://"):
        raise SystemExit("refus: seul mongodb:// vers la boucle locale est accepté")
    parsed = urlparse(raw)
    if parsed.username or parsed.password or "@" in (parsed.netloc or ""):
        raise SystemExit("refus: pas d'identifiants dans l'URL de CI")
    host = (parsed.hostname or "").lower()
    if host not in _LOCAL_HOSTS:
        raise SystemExit(f"refus: hôte {host or 'vide'}")
    if db_name != CI_DB_NAME:
        raise SystemExit(f"refus: seule la base {CI_DB_NAME} peut être réinitialisée")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _anchor(geom) -> list[float]:
    geoms = list(geom.geoms) if hasattr(geom, "geoms") else [geom]
    big = max(geoms, key=lambda g: g.area)
    pt = big.representative_point()
    return [round(pt.x, 4), round(pt.y, 4)]


def _projects(fc: dict) -> list[dict]:
    docs = []
    for feat in fc.get("features") or []:
        props = feat.get("properties") or {}
        coords = (feat.get("geometry") or {}).get("coordinates") or []
        if len(coords) != 2:
            continue
        lon, lat = float(coords[0]), float(coords[1])
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            continue
        title = str(props.get("title") or "").strip()
        url = str(props.get("url") or "").strip()
        pid = str(props.get("id") or "").strip()
        if not title or not url or not pid:
            continue
        funder = str(props.get("funder") or "").strip()
        docs.append({
            "_id": pid,
            "title": title,
            "url": url,
            "description": props.get("description") or "",
            "funder": funder,
            "funders": [funder] if funder else [],
            "location": props.get("location"),
            "s_ocean": props.get("s_ocean"),
            "snapped": bool(props.get("snapped")),
            "image": props.get("image"),
            "category": props.get("category"),
            "category_group": props.get("category_group"),
            "lon": lon,
            "lat": lat,
        })
    return docs


def _ports(fc: dict) -> list[dict]:
    docs = []
    for feat in fc.get("features") or []:
        props = feat.get("properties") or {}
        coords = (feat.get("geometry") or {}).get("coordinates") or []
        if len(coords) != 2:
            continue
        lon, lat = float(coords[0]), float(coords[1])
        pid = str(props.get("id") or "").strip()
        name = str(props.get("name") or "").strip()
        if not pid or not name:
            continue
        mrgid = int(props["mrgid"])
        docs.append({
            "_id": pid,
            "dedup_key": pid,
            "name": name,
            "city": props.get("city"),
            "note": props.get("note"),
            "mrgid": mrgid,
            "zone_name": props.get("zone_name"),
            "country_iso2": props.get("country_iso2"),
            "validated": bool(props.get("validated")),
            "distance_km": props.get("distance_km"),
            "geocode_source": props.get("geocode_source"),
            "source_urls": props.get("source_urls") or [],
            "extracted_at": props.get("extracted_at"),
            "lon": lon,
            "lat": lat,
        })
    return docs


def _zones(fc: dict, port_counts: Counter) -> list[dict]:
    docs = []
    for feat in fc.get("features") or []:
        props = feat.get("properties") or {}
        mrgid = props.get("mrgid")
        geom_raw = feat.get("geometry")
        if mrgid is None or not geom_raw:
            continue
        geom = shape(geom_raw)
        mrgid = int(mrgid)
        n = int(port_counts.get(mrgid) or 0)
        docs.append({
            "_id": str(mrgid),
            "mrgid": mrgid,
            "geoname": props.get("geoname"),
            "name": props.get("name") or props.get("geoname"),
            "pol_type": props.get("pol_type"),
            "iso2": props.get("iso2"),
            "sovereign": props.get("sovereign"),
            "geometry": geom_raw,
            "bbox": [round(v, 4) for v in geom.bounds],
            "anchor": _anchor(geom),
            "status": "ia" if n else "non_generee",
            "poe_count": n,
            "generated_at": None,
            "sources": [],
            "whitelist": [],
        })
    return docs


def seed(mongo_url: str, db_name: str) -> dict:
    assert_ci_target(mongo_url, db_name)
    client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    client.drop_database(db_name)
    db = client[db_name]
    projects = _projects(_load(REPO / "seed" / "projects.geojson"))
    ports = _ports(_load(REPO / "seed" / "ports_of_entry.geojson"))
    zones = _zones(
        _load(BACKEND / "data" / "eez_world_map.geojson"),
        Counter(p["mrgid"] for p in ports),
    )
    if len(projects) < 4463 or len(ports) < 1169 or len(zones) != 285:
        raise SystemExit(
            f"refus: seed incomplet projects={len(projects)} "
            f"ports={len(ports)} zones={len(zones)}"
        )
    db.projects.insert_many(projects, ordered=False)
    db.poe_ports.insert_many(ports, ordered=False)
    db.eez_zones.insert_many(zones, ordered=False)
    summary = {
        "db": db_name,
        "projects": db.projects.count_documents({}),
        "poe_ports": db.poe_ports.count_documents({}),
        "eez_zones": db.eez_zones.count_documents({}),
        "zones_ia": db.eez_zones.count_documents({"status": "ia"}),
    }
    client.close()
    return summary


def main() -> None:
    mongo_url = os.environ.get("MONGO_URL") or ""
    db_name = os.environ.get("DB_NAME") or ""
    summary = seed(mongo_url, db_name)
    print(
        f"bi_ci: {summary['projects']} projets, {summary['poe_ports']} ports, "
        f"{summary['eez_zones']} ZEE dont {summary['zones_ia']} au statut ia"
    )


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        print(f"seed_ci_mongo: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
