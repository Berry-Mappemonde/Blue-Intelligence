#!/usr/bin/env python3
"""Stamp a pilot GeoJSON with metadata.version + sha256.

Usage (Mac, off the VPS):
  python3 scripts/satellite/export_pilot.py --in raw.geojson --out coastline.geojson
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.science_pilot import wrap_pilot_export  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Version a Sentinel pilot export")
    p.add_argument("--in", dest="src", required=True, help="raw GeoJSON")
    p.add_argument("--out", dest="dst", required=True, help="versioned GeoJSON")
    p.add_argument("--dataset", default="sentinel-coastline")
    args = p.parse_args()
    raw = json.loads(Path(args.src).read_text(encoding="utf-8"))
    if raw.get("type") != "FeatureCollection":
        print("attendu : FeatureCollection", file=sys.stderr)
        return 2
    out = wrap_pilot_export(raw, dataset=args.dataset)
    dst = Path(args.dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(out["metadata"]["version"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
