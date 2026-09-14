#!/usr/bin/env python3
"""Build backend/data/master_seeds.json (Projects CDC C5).

Prefer `enrich_master_seeds.py`: it classifies homes / lists / Complet queue.
This export calls the same enrichment (plus the “most frequent
domain” vote that glued organizations onto Decade / Surfrider).

Usage:
    python3 scripts/enrich_master_seeds.py --from-geojson ../seed/projects.geojson
    python3 scripts/export_master_seeds.py --from-geojson ../seed/projects.geojson
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.services.master_seeds import (  # noqa: E402
    MASTER_SEEDS_PATH,
    build_master_seeds,
    dump_master_seeds,
    fetch_production_projects,
    projects_from_geojson,
    seeds_for_run,
)


def projects_from_mongo() -> list[dict]:
    from app.config import DB_NAME, MONGO_URL
    from pymongo import MongoClient

    db = MongoClient(MONGO_URL)[DB_NAME]
    return list(db.projects.find({}, {"url": 1, "funders": 1, "funder": 1, "title": 1}))


def main() -> int:
    p = argparse.ArgumentParser(description="Export MasterSeeds (~861 v1 funders + 21 curated)")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--from-geojson", type=Path, help="GeoJSON v1 (seed/projects.geojson)")
    src.add_argument("--from-api", action="store_true", help="GET https://blueintelligence.online/api/projects")
    src.add_argument("--from-mongo", action="store_true", help="Collection live projects (MONGO_URL)")
    p.add_argument("--out", type=Path, default=MASTER_SEEDS_PATH)
    args = p.parse_args()

    if args.from_geojson:
        fc = json.loads(args.from_geojson.read_text(encoding="utf-8"))
        projects = projects_from_geojson(fc)
        source = str(args.from_geojson)
    elif args.from_api:
        projects = fetch_production_projects()
        source = "https://blueintelligence.online/api/projects"
    else:
        projects = projects_from_mongo()
        source = "mongo:projects"

    seeds = build_master_seeds(projects)
    path = dump_master_seeds(seeds, args.out, source=source)
    queued = seeds_for_run(seeds)
    print(
        f"Wrote {path} — {len(seeds)} financeurs "
        f"({len(queued)} file Complet / queue=crawl)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
