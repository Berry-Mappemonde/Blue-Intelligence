#!/usr/bin/env python3
"""Compare a pilot GeoJSON to the EMODnet DTM (depth_sample).

For a coastline: note whether vertices are near 0 m.
For a depth_area with an estimated depth: compute error_m.
Without ICESat-2 / without an estimated depth: do not write a sounding.
"""
from __future__ import annotations

import argparse
import json
import statistics
import urllib.parse
import urllib.request
from pathlib import Path

DEPTH_URL = "https://rest.emodnet-bathymetry.eu/depth_sample"
USER_AGENT = "BlueIntelligence-satellite-pilot/1.0"


def emodnet_depth(lon: float, lat: float) -> float | None:
    geom = f"POINT({lon} {lat})"
    url = f"{DEPTH_URL}?{urllib.parse.urlencode({'geom': geom})}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None
    raw = payload.get("avg") if isinstance(payload, dict) else None
    if raw is None:
        return None
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return None
    return val if val >= 0 else -val


def iter_points(geom: dict):
    typ = geom.get("type")
    coords = geom.get("coordinates") or []
    if typ == "Point" and len(coords) >= 2:
        yield float(coords[0]), float(coords[1])
    elif typ == "LineString":
        for i, pt in enumerate(coords):
            if i % 3 != 0:
                continue
            if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                yield float(pt[0]), float(pt[1])
    elif typ == "Polygon" and coords:
        ring = coords[0]
        for i, pt in enumerate(ring):
            if i % 4 != 0:
                continue
            if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                yield float(pt[0]), float(pt[1])


def main() -> int:
    p = argparse.ArgumentParser(description="Compare un GeoJSON à EMODnet")
    p.add_argument("--in", dest="src", required=True, type=Path)
    p.add_argument("--out", dest="dst", required=True, type=Path)
    args = p.parse_args()
    fc = json.loads(args.src.read_text(encoding="utf-8"))
    errors = []
    for feat in fc.get("features") or []:
        geom = feat.get("geometry") or {}
        props = feat.setdefault("properties", {})
        samples = []
        for lon, lat in iter_points(geom):
            d = emodnet_depth(lon, lat)
            if d is not None:
                samples.append(d)
        if not samples:
            continue
        emod = round(statistics.median(samples), 1)
        props["emodnet_depth_m"] = emod
        props["emodnet_n"] = len(samples)
        est = props.get("depth_m") or props.get("est_depth_m")
        if est is not None:
            try:
                err = abs(float(est) - float(emod))
            except (TypeError, ValueError):
                err = None
            if err is not None:
                props["error_m"] = round(err, 1)
                errors.append(err)
        props["emodnet_doi"] = "EMODnet Bathymetry DTM (depth_sample)"
    args.dst.parent.mkdir(parents=True, exist_ok=True)
    args.dst.write_text(json.dumps(fc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if errors:
        print(f"error_m médian : {round(statistics.median(errors), 1)} m (n={len(errors)})")
    else:
        print("pas de profondeur estimée : EMODnet noté, aucun sondage inventé")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
