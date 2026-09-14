"""Emprise du corridor Berry autour d'un point de la route (degrés)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROUTE = ROOT / "backend" / "data" / "route.geojson"

# 30 milles marins ≈ 0,5° de latitude.
NM30_DEG = 30 * 1852 / 111_320


def load_route(path: Path | None = None) -> dict:
    return json.loads((path or ROUTE).read_text(encoding="utf-8"))


def first_sea_lonlat(route: dict) -> tuple[float, float]:
    """Premier point maritime : La Rochelle sur la route officielle."""
    for feat in route.get("features") or []:
        props = feat.get("properties") or {}
        geom = feat.get("geometry") or {}
        if props.get("name") == "La Rochelle" and geom.get("type") == "Point":
            lon, lat = geom["coordinates"][:2]
            return float(lon), float(lat)
        if props.get("type") == "maritime" and geom.get("type") == "LineString":
            lon, lat = geom["coordinates"][0][:2]
            return float(lon), float(lat)
    raise SystemExit("aucun point maritime dans route.geojson")


def bbox_around(lon: float, lat: float, buffer_deg: float = NM30_DEG) -> list[float]:
    """Bbox [ouest, sud, est, nord] autour d'un point."""
    return [
        lon - buffer_deg,
        lat - buffer_deg,
        lon + buffer_deg,
        lat + buffer_deg,
    ]


def default_bbox(route: dict | None = None) -> list[float]:
    data = route if route is not None else load_route()
    lon, lat = first_sea_lonlat(data)
    return bbox_around(lon, lat)
