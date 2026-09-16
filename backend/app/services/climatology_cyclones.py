"""IBTrACS v04r01 tracks (since 1980) — numeric counter, not an LLM "season"."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path

from app.services.climatology_common import (
    CYCLONE_PERIOD,
    IBTRACS_CREDIT,
    KIND,
    LICENSE_IBTRACS,
    SOURCE_IDS,
    climatology_dir,
    haversine_nm,
    parse_month,
    point_to_segment_nm,
    rule,
    wrap_lon,
)

NCEI_STORM_URL = "https://www.ncei.noaa.gov/products/international-best-track-archive"


def cyclones_path() -> Path:
    return climatology_dir() / "cyclones" / "ibtracs_since1980.json"


def has_snapshot() -> bool:
    return cyclones_path().is_file()


@lru_cache(maxsize=1)
def _load_index() -> dict:
    path = cyclones_path()
    if not path.is_file():
        return {"kind": KIND, "storms": [], "period": CYCLONE_PERIOD, "count": 0}
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw.setdefault("storms", [])
    return raw


def reload_index() -> dict:
    _load_index.cache_clear()
    return _load_index()


def _min_kn() -> float:
    return float(rule("climatology.cyclone_min_kn", 34))


def storms_for_month(month: int, *, min_kn: float | None = None) -> list[dict]:
    month = parse_month(month)
    floor = _min_kn() if min_kn is None else float(min_kn)
    out = []
    for s in _load_index().get("storms") or []:
        months = s.get("months") or []
        if month not in months:
            continue
        if float(s.get("max_wind_kn") or 0) < floor:
            continue
        out.append(s)
    return out


def _unwrap_lon(prev: float, lon: float) -> float:
    x = float(lon)
    while x - prev > 180.0:
        x -= 360.0
    while x - prev < -180.0:
        x += 360.0
    return x


def _meridians_between(x0: float, x1: float) -> list[float]:
    if x0 == x1:
        return []
    lo, hi = (x0, x1) if x0 < x1 else (x1, x0)
    found: list[float] = []
    k = int((lo - 180.0) // 360.0) + 1
    while True:
        m = 180.0 + 360.0 * k
        if m >= hi:
            break
        if m > lo:
            found.append(m)
        k += 1
        if len(found) > 8:
            break
    return found if x0 < x1 else list(reversed(found))


def _split_antimeridian(coords: list[list[float]]) -> list[list[list[float]]]:
    """Cut at 180°. Both sides get the interpolated meridian (no 358° hop)."""
    clean = [c for c in coords if len(c) >= 2]
    if len(clean) < 2:
        return [clean] if clean else []
    uw = [[float(clean[0][0]), float(clean[0][1])]]
    for pt in clean[1:]:
        uw.append([_unwrap_lon(uw[-1][0], float(pt[0])), float(pt[1])])
    parts: list[list[list[float]]] = []
    cur: list[list[float]] = [[wrap_lon(uw[0][0]), uw[0][1]]]
    for prev, pt in zip(uw, uw[1:]):
        cuts = _meridians_between(prev[0], pt[0])
        if not cuts:
            cur.append([wrap_lon(pt[0]), pt[1]])
            continue
        px, py = prev[0], prev[1]
        x1, y1 = pt[0], pt[1]
        for m in cuts:
            t = 1.0 if x1 == px else (m - px) / (x1 - px)
            y = py + (y1 - py) * t
            cur.append([180.0, y])
            if len(cur) >= 2:
                parts.append(cur)
            cur = [[-180.0, y]]
            px, py = m, y
        cur.append([wrap_lon(x1), y1])
    if len(cur) >= 2:
        parts.append(cur)
    return parts


def _color(max_wind: float) -> str:
    if max_wind >= 96:
        return "#ef4444"
    if max_wind >= 64:
        return "#f97316"
    return "#eab308"


def tracks_geojson(month: int) -> dict:
    month = parse_month(month)
    features = []
    for s in storms_for_month(month):
        coords = [[wrap_lon(p[0]), p[1]] for p in (s.get("coords") or []) if len(p) >= 2]
        for part in _split_antimeridian(coords):
            if len(part) < 2:
                continue
            features.append({
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": part},
                "properties": {
                    "kind": KIND,
                    "sid": s.get("sid"),
                    "name": s.get("name"),
                    "season": s.get("season"),
                    "basin": s.get("basin"),
                    "month": month,
                    "max_wind_kn": s.get("max_wind_kn"),
                    "wind_source": s.get("wind_source"),
                    "color": _color(float(s.get("max_wind_kn") or 0)),
                    "url": f"{NCEI_STORM_URL}",
                },
            })
    return {
        "type": "FeatureCollection",
        "features": features,
        "attribution": LICENSE_IBTRACS,
        "_climatology": {
            "kind": KIND,
            "month": month,
            "period": CYCLONE_PERIOD,
            "source_ids": [SOURCE_IDS["cyclone"]],
            "snapshot_present": has_snapshot(),
            "wind_note": (
                "USA_WIND (1 min) when present, else WMO_WIND "
                "(10 min, basin-dependent). Field wind_source names the mix."
            ),
        },
    }


def _in_dayrange(storm: dict, month: int, day: int | None, dayrange: int) -> bool:
    if day is None:
        return month in (storm.get("months") or [])
    start = storm.get("start")
    end = storm.get("end")
    if not start or not end:
        return month in (storm.get("months") or [])
    try:
        s = datetime.fromisoformat(str(start)[:10]).date()
        e = datetime.fromisoformat(str(end)[:10]).date()
    except ValueError:
        return month in (storm.get("months") or [])
    # Window around the calendar day, storm year.
    year = s.year
    try:
        center = date(year, month, min(day, 28 if month == 2 else 30 if month in (4, 6, 9, 11) else 31))
    except ValueError:
        center = date(year, month, 15)
    lo, hi = center - timedelta(days=dayrange), center + timedelta(days=dayrange)
    return s <= hi and e >= lo


def crossings(
    lat1: float, lon1: float, lat2: float, lon2: float,
    month: int, *, day: int | None = None, dayrange: int | None = None,
    radius_nm: float | None = None,
) -> dict:
    """OpenCPN ``CycloneTrackCrossings`` spirit: integer + list, never prose."""
    month = parse_month(month)
    window = int(dayrange if dayrange is not None else rule("climatology.cyclone_dayrange", 21))
    radius = float(radius_nm if radius_nm is not None else rule("climatology.cyclone_radius_nm", 120))
    hits = []
    for s in _load_index().get("storms") or []:
        if float(s.get("max_wind_kn") or 0) < _min_kn():
            continue
        if not _in_dayrange(s, month, day, window):
            continue
        coords = s.get("coords") or []
        near = False
        for pt in coords:
            if len(pt) < 2:
                continue
            if point_to_segment_nm(pt[1], pt[0], lat1, lon1, lat2, lon2) <= radius:
                near = True
                break
        if not near and len(coords) >= 2:
            # Track segment vs leg (samples)
            for a, b in zip(coords, coords[1:]):
                if abs(a[0] - b[0]) > 180:
                    continue
                if (
                    point_to_segment_nm(lat1, lon1, a[1], a[0], b[1], b[0]) <= radius
                    or point_to_segment_nm(lat2, lon2, a[1], a[0], b[1], b[0]) <= radius
                ):
                    near = True
                    break
        if near:
            hits.append({
                "sid": s.get("sid"),
                "name": s.get("name"),
                "season": s.get("season"),
                "basin": s.get("basin"),
                "max_wind_kn": s.get("max_wind_kn"),
                "wind_source": s.get("wind_source"),
                "start": s.get("start"),
                "end": s.get("end"),
            })
    return {
        "kind": KIND,
        "count": len(hits),
        "storms": hits,
        "month": month,
        "dayrange": window,
        "radius_nm": radius,
        "period": CYCLONE_PERIOD,
        "source": SOURCE_IDS["cyclone"],
        "snapshot_present": has_snapshot(),
    }


def tracks_in_month(month: int) -> int:
    return len(storms_for_month(month))


def nearby_count(lat: float, lon: float, month: int, radius_nm: float | None = None) -> int:
    radius = float(radius_nm if radius_nm is not None else rule("climatology.cyclone_radius_nm", 120))
    n = 0
    for s in storms_for_month(month):
        for pt in s.get("coords") or []:
            if len(pt) >= 2 and haversine_nm(lat, lon, pt[1], pt[0]) <= radius:
                n += 1
                break
    return n
