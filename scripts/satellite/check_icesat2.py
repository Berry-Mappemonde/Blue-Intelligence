#!/usr/bin/env python3
"""Dit si une trace ICESat-2 croise la bbox (CMR NASA).

Pas de téléchargement de granules. Si zéro granule : on n'invente pas
de profondeur (on saute S4).
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from corridor import default_bbox

HERE = Path(__file__).resolve().parent
CMR = "https://cmr.earthdata.nasa.gov/search/granules.json"


def count_granules(short_name: str, bbox: list[float]) -> int:
    west, south, east, north = bbox
    q = urllib.parse.urlencode({
        "short_name": short_name,
        "bounding_box": f"{west},{south},{east},{north}",
        "page_size": 5,
    })
    req = urllib.request.Request(
        f"{CMR}?{q}",
        headers={"Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    entries = (payload.get("feed") or {}).get("entry") or []
    return len(entries)


def main() -> int:
    p = argparse.ArgumentParser(description="Présence ICESat-2 sur le corridor")
    p.add_argument("--manifest", type=Path, default=HERE / "scenes_la_rochelle.json")
    args = p.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    bbox = manifest.get("bbox") or default_bbox()
    atl24 = count_granules("ATL24", bbox)
    atl03 = count_granules("ATL03", bbox)
    report = {
        "bbox": bbox,
        "atl24": atl24,
        "atl03": atl03,
        "sdb_allowed": atl24 > 0 or atl03 > 0,
    }
    print(json.dumps(report, indent=2))
    if report["sdb_allowed"]:
        print(
            "Une trace ICESat-2 croise la zone : S4 (Stumpf) est possible.",
            file=sys.stderr,
        )
        return 0
    print(
        "Aucune trace ICESat-2 sur cette emprise : on n'invente pas de profondeur.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
