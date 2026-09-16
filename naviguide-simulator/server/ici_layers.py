"""Familles hors dump carte pour le sac `ici()`.

Satellites (CDSE STAC), Open-Meteo / GRIB2, EMODnet au point,
AtoN (NOAA ENC + Overpass), mouillages OSM, Review/Gold.
Jamais d’invention : null + source/reason si le produit manque.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

import httpx

USER_AGENT = "NAVIGUIDE-simulator/0.2 (Berry-Mappemonde expedition)"

STAC_SEARCH = "https://stac.dataspace.copernicus.eu/v1/search"
STAC_COLLECTION = "sentinel-2-l2a"
CDSE_TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu/auth/realms/CDSE"
    "/protocol/openid-connect/token"
)
COPERNICUS_BROWSER = "https://browser.dataspace.copernicus.eu/"
OPEN_METEO_FORECAST = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_MARINE = "https://marine-api.open-meteo.com/v1/marine"
EMODNET_DEPTH = "https://rest.emodnet-bathymetry.eu/depth_sample"
EMODNET_BATHY_WMS = "https://ows.emodnet-bathymetry.eu/wms"
EMODNET_SEABED_WMS = "https://drive.emodnet-geology.eu/geoserver/gtk/wms"
EMODNET_CABLES_WMS = "https://ows.emodnet-humanactivities.eu/wms"
OVERPASS_ENDPOINTS = (
    "https://overpass.openstreetmap.fr/api/interpreter",
    "https://overpass-api.de/api/interpreter",
)

US_BBOXES: tuple[tuple[float, float, float, float], ...] = (
    (-125.0, 24.0, -66.0, 49.5),
    (-179.5, 51.0, -129.0, 72.0),
    (-160.5, 18.8, -154.5, 22.4),
    (-68.0, 17.8, -65.2, 18.6),
)

MAX_ATON = 8
MAX_SCENES = 1
_stac_token: dict[str, Any] = {"value": None, "ts": 0.0}
_TOKEN_TTL = 500.0

DERIVED_NULL = {
    "coastline": {
        "value": None,
        "source": "sentinel-pilot",
        "reason": "not_generated",
    },
    "sdb": {
        "value": None,
        "source": "sentinel-pilot",
        "reason": "not_generated",
    },
    "intertidal": {
        "value": None,
        "source": "sentinel-pilot",
        "reason": "not_generated",
    },
}


def absent(kind: str, source: str | None, reason: str) -> dict:
    return {
        "kind": kind,
        "source": source,
        "reason": reason,
        "value": None,
    }


def empty_satellites() -> dict:
    return {
        "kind": "observation",
        "source": None,
        "reason": None,
        "scene": None,
        "scenes": [],
        "bbox": None,
        "link": None,
        "derived": {k: dict(v) for k, v in DERIVED_NULL.items()},
    }


def empty_weather() -> dict:
    return {
        "kind": "forecast",
        "source": None,
        "reason": None,
        "issued": None,
        "model": None,
        "wind": None,
        "wave": None,
        "current": None,
        "current_reason": "rtofs_not_ingested",
    }


def empty_emodnet() -> dict:
    return {
        "kind": "observation",
        "source": "emodnet",
        "reason": None,
        "bathy": None,
        "seabed": None,
        "cables": None,
    }


def empty_aton() -> dict:
    return {
        "nearby": [],
        "source": None,
        "reason": None,
    }


def empty_review() -> dict:
    return {
        "zee": None,
        "amp": None,
        "source": None,
        "reason": None,
    }


def bbox_intersects_us(bbox: tuple[float, float, float, float]) -> bool:
    west, south, east, north = bbox
    for uw, us, ue, un in US_BBOXES:
        if west < ue and east > uw and south < un and north > us:
            return True
    return False


def scene_bbox(lat: float, lon: float, nm: float = 8.0) -> list[float]:
    dlat = nm / 60.0
    import math
    clat = max(0.2, abs(math.cos(math.radians(lat))))
    dlon = nm / (60.0 * clat)
    return [lon - dlon, lat - dlat, lon + dlon, lat + dlat]


def _browser_link(lat: float, lon: float, when: str | None = None) -> str:
    q = {
        "zoom": "11",
        "lat": f"{lat:.5f}",
        "lng": f"{lon:.5f}",
        "datasetId": "S2_L2A_CDAS",
    }
    if when:
        q["fromTime"] = when
        q["toTime"] = when
    return f"{COPERNICUS_BROWSER}?{urlencode(q)}"


def _stac_item_link(scene_id: str | None) -> str | None:
    if not scene_id:
        return None
    return f"https://stac.dataspace.copernicus.eu/v1/collections/{STAC_COLLECTION}/items/{scene_id}"


async def _cdse_token(client: httpx.AsyncClient) -> str | None:
    now = time.time()
    if _stac_token["value"] and now - _stac_token["ts"] < _TOKEN_TTL:
        return _stac_token["value"]
    user = (os.getenv("CDSE_USERNAME") or "").strip()
    password = os.getenv("CDSE_PASSWORD") or ""
    if not user or not password:
        return None
    try:
        r = await client.post(
            CDSE_TOKEN_URL,
            data={
                "client_id": "cdse-public",
                "grant_type": "password",
                "username": user,
                "password": password,
            },
            headers={"User-Agent": USER_AGENT},
            timeout=8.0,
        )
        r.raise_for_status()
        token = (r.json() or {}).get("access_token")
    except Exception:
        return None
    if not token:
        return None
    _stac_token["value"] = token
    _stac_token["ts"] = now
    return token


def slim_stac_scene(feat: dict, lat: float, lon: float) -> dict | None:
    if not isinstance(feat, dict):
        return None
    props = feat.get("properties") or {}
    scene_id = feat.get("id")
    when = props.get("datetime") or props.get("start_datetime")
    bbox = feat.get("bbox")
    links = feat.get("links") or []
    href = None
    for link in links:
        if isinstance(link, dict) and link.get("rel") in ("self", "canonical"):
            href = link.get("href")
            break
    href = href or _stac_item_link(scene_id)
    return {
        "kind": "observation",
        "product": (feat.get("collection") or STAC_COLLECTION),
        "id": scene_id,
        "datetime": when,
        "platform": props.get("platform") or props.get("constellation"),
        "cloud_cover": props.get("eo:cloud_cover"),
        "bbox": bbox,
        "link": href,
        "browser": _browser_link(lat, lon, when),
    }


async def fetch_satellite_scene(
    client: httpx.AsyncClient,
    lat: float,
    lon: float,
) -> dict:
    bag = empty_satellites()
    bbox = scene_bbox(lat, lon)
    bag["bbox"] = bbox
    bag["link"] = _browser_link(lat, lon)
    body = {
        "collections": [STAC_COLLECTION],
        "bbox": bbox,
        "datetime": f"2025-01-01T00:00:00Z/{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "limit": MAX_SCENES,
        "sortby": [{"field": "properties.datetime", "direction": "desc"}],
        "query": {"eo:cloud_cover": {"lt": 40}},
    }
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json, application/json",
        "Content-Type": "application/json",
    }
    token = await _cdse_token(client)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        r = await client.post(STAC_SEARCH, json=body, headers=headers, timeout=10.0)
        r.raise_for_status()
        payload = r.json() if r.content else {}
    except Exception as exc:
        bag["reason"] = f"cdse_stac_unavailable:{type(exc).__name__}"
        bag["source"] = "cdse-stac"
        return bag
    features = payload.get("features") if isinstance(payload, dict) else []
    scenes = []
    for feat in features or []:
        item = slim_stac_scene(feat, lat, lon)
        if item:
            scenes.append(item)
    if scenes:
        bag["scene"] = scenes[0]
        bag["scenes"] = scenes
        bag["source"] = "cdse-stac"
        bag["reason"] = None
        bag["link"] = scenes[0].get("link") or bag["link"]
        bag["bbox"] = scenes[0].get("bbox") or bbox
    else:
        bag["source"] = "cdse-stac"
        bag["reason"] = "no_scene_in_bbox"
    return bag


def attach_derived_from_science(satellites: dict, science_items: list | None) -> dict:
    out = dict(satellites or empty_satellites())
    derived = {k: dict(v) for k, v in (out.get("derived") or DERIVED_NULL).items()}
    for item in science_items or []:
        if (item.get("source") or "") != "sentinel-pilot":
            continue
        kind = str(item.get("kind") or "")
        payload = {
            "value": {
                "name": item.get("name"),
                "kind": kind or "dataset",
                "url": item.get("url"),
                "doi": item.get("doi"),
                "nm": item.get("nm"),
                "method": item.get("method"),
                "error_m": item.get("error_m"),
            },
            "source": "sentinel-pilot",
            "reason": None,
        }
        if kind == "coastline" or "coast" in str(item.get("name") or "").lower():
            derived["coastline"] = payload
        elif kind in ("depth_area", "sdb", "depth") or item.get("error_m") is not None:
            derived["sdb"] = payload
        elif kind == "intertidal":
            derived["intertidal"] = payload
    out["derived"] = derived
    return out


async def fetch_weather_forecast(
    client: httpx.AsyncClient,
    lat: float,
    lon: float,
) -> dict:
    bag = empty_weather()
    issued = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    wind = None
    wave = None
    try:
        r = await client.get(
            OPEN_METEO_FORECAST,
            params={
                "latitude": f"{lat:.4f}",
                "longitude": f"{lon:.4f}",
                "current": "wind_speed_10m,wind_direction_10m",
                "wind_speed_unit": "kn",
                "models": "gfs_global",
                "timezone": "UTC",
            },
            headers=headers,
            timeout=8.0,
        )
        r.raise_for_status()
        cur = (r.json() or {}).get("current") or {}
        if cur.get("wind_speed_10m") is not None:
            wind = {
                "kind": "forecast",
                "source": "openmeteo-gfs",
                "speedKnots": float(cur["wind_speed_10m"]),
                "dirFromDeg": float(cur.get("wind_direction_10m") or 0),
                "time": cur.get("time"),
            }
    except Exception as exc:
        bag["reason"] = f"openmeteo_unavailable:{type(exc).__name__}"
        return bag
    try:
        r = await client.get(
            OPEN_METEO_MARINE,
            params={
                "latitude": f"{lat:.4f}",
                "longitude": f"{lon:.4f}",
                "current": "wave_height,wave_direction,wave_period",
                "models": "ncep_gfswave025",
                "timezone": "UTC",
            },
            headers=headers,
            timeout=8.0,
        )
        r.raise_for_status()
        cur = (r.json() or {}).get("current") or {}
        if cur.get("wave_height") is not None:
            wave = {
                "kind": "forecast",
                "source": "openmeteo-gfs-wave",
                "hs": float(cur["wave_height"]),
                "dirDeg": cur.get("wave_direction"),
                "periodS": cur.get("wave_period"),
                "time": cur.get("time"),
            }
    except Exception:
        wave = None
    if not wind and not wave:
        bag["reason"] = "openmeteo_empty"
        bag["source"] = "openmeteo"
        return bag
    bag.update({
        "kind": "forecast",
        "source": "openmeteo-gfs",
        "reason": None,
        "issued": issued,
        "model": "GFS 0.25° / GFS-Wave 0.25° (Open-Meteo)",
        "wind": wind,
        "wave": wave,
        "current": None,
        "current_reason": "rtofs_not_ingested",
    })
    return bag


def _depth_from_emodnet_payload(payload: dict | None) -> dict | None:
    if not isinstance(payload, dict) or payload.get("avg") is None:
        if isinstance(payload, dict) and payload.get("depth_m") is not None:
            return {
                "kind": "observation",
                "source": payload.get("source") or "emodnet-bathymetry",
                "depth_m": payload.get("depth_m"),
                "on_land": payload.get("on_land"),
            }
        return None
    try:
        raw = float(payload["avg"])
    except (TypeError, ValueError):
        return None
    depth_m = raw if raw >= 0 else -raw
    on_land = raw >= 0 and raw < 0.3
    return {
        "kind": "observation",
        "source": "emodnet-bathymetry",
        "depth_m": round(depth_m, 1),
        "on_land": on_land,
        "raw": raw,
    }


def _gfi_properties(payload: Any) -> dict | None:
    if not isinstance(payload, dict):
        return None
    feats = payload.get("features")
    if isinstance(feats, list) and feats:
        props = feats[0].get("properties") or {}
        return props if isinstance(props, dict) else None
    if payload.get("type") == "Feature":
        props = payload.get("properties") or {}
        return props if isinstance(props, dict) else None
    return None


async def _wms_feature_info(
    client: httpx.AsyncClient,
    url: str,
    layers: str,
    lat: float,
    lon: float,
) -> dict | None:
    delta = 0.02
    # WMS 1.3.0 + EPSG:4326 = lat,lon order.
    bbox = f"{lat - delta},{lon - delta},{lat + delta},{lon + delta}"
    params = {
        "SERVICE": "WMS",
        "VERSION": "1.3.0",
        "REQUEST": "GetFeatureInfo",
        "LAYERS": layers,
        "QUERY_LAYERS": layers,
        "INFO_FORMAT": "application/json",
        "CRS": "EPSG:4326",
        "BBOX": bbox,
        "WIDTH": "101",
        "HEIGHT": "101",
        "I": "50",
        "J": "50",
        "FEATURE_COUNT": "3",
    }
    r = await client.get(
        url,
        params=params,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=8.0,
    )
    r.raise_for_status()
    ctype = (r.headers.get("content-type") or "").lower()
    if "json" not in ctype:
        return None
    return r.json() if r.content else None


async def fetch_emodnet_point(
    client: httpx.AsyncClient,
    bi: str,
    lat: float,
    lon: float,
) -> dict:
    bag = empty_emodnet()
    bathy = None
    try:
        r = await client.get(
            f"{bi}/depth",
            params={"lat": lat, "lon": lon},
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=8.0,
        )
        r.raise_for_status()
        bathy = _depth_from_emodnet_payload(r.json() if r.content else None)
    except Exception:
        bathy = None
    if bathy is None:
        try:
            r = await client.get(
                EMODNET_DEPTH,
                params={"geom": f"POINT({lon} {lat})"},
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                timeout=10.0,
            )
            r.raise_for_status()
            bathy = _depth_from_emodnet_payload(r.json() if r.content else None)
        except Exception as exc:
            bathy = {
                "value": None,
                "source": "emodnet-bathymetry",
                "reason": f"depth_sample_unavailable:{type(exc).__name__}",
            }
    if bathy is None:
        bathy = {
            "value": None,
            "source": "emodnet-bathymetry",
            "reason": "no_sample_at_point",
        }
    seabed = None
    try:
        raw = await _wms_feature_info(
            client, EMODNET_SEABED_WMS, "seabed_substrate_1m", lat, lon,
        )
        props = _gfi_properties(raw)
        if props:
            label = (
                props.get("substrate")
                or props.get("SUBSTRATE")
                or props.get("folk_5")
                or props.get("FOLK_5")
                or props.get("gray_cin")
                or props.get("GRAY_CIN")
            )
            seabed = {
                "kind": "observation",
                "source": "emodnet-geology",
                "label": label,
                "properties": {k: props[k] for k in list(props)[:8]},
            }
        else:
            seabed = {
                "value": None,
                "source": "emodnet-geology",
                "reason": "no_feature_at_point",
            }
    except Exception as exc:
        seabed = {
            "value": None,
            "source": "emodnet-geology",
            "reason": f"wms_unavailable:{type(exc).__name__}",
        }
    cables = None
    try:
        raw = await _wms_feature_info(
            client, EMODNET_CABLES_WMS, "telecablesactual,powercables", lat, lon,
        )
        props = _gfi_properties(raw)
        if props:
            cables = {
                "kind": "observation",
                "source": "emodnet-human-activities",
                "nearby": True,
                "name": props.get("name") or props.get("NAME") or props.get("status"),
                "properties": {k: props[k] for k in list(props)[:8]},
            }
        else:
            cables = {
                "kind": "observation",
                "source": "emodnet-human-activities",
                "nearby": False,
                "reason": "no_feature_at_point",
            }
    except Exception as exc:
        cables = {
            "value": None,
            "source": "emodnet-human-activities",
            "reason": f"wms_unavailable:{type(exc).__name__}",
        }
    bag.update({
        "bathy": bathy,
        "seabed": seabed,
        "cables": cables,
        "reason": None,
    })
    return bag


def slim_aton_feature(feat: dict, lat0: float, lon0: float, haversine_nm) -> dict | None:
    props = feat.get("properties") or {}
    geom = feat.get("geometry") or {}
    coords = geom.get("coordinates")
    lat = props.get("lat")
    lon = props.get("lon")
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        if geom.get("type") == "Point" and isinstance(coords, (list, tuple)) and len(coords) >= 2:
            lon, lat = float(coords[0]), float(coords[1])
        else:
            return None
    name = (
        props.get("name")
        or props.get("OBJNAM")
        or props.get("seamark:name")
        or props.get("kind")
        or ""
    )
    if not str(name).strip():
        return None
    return {
        "name": str(name).strip()[:120],
        "lat": round(float(lat), 5),
        "lon": round(float(lon), 5),
        "nm": round(haversine_nm(lat0, lon0, float(lat), float(lon)), 1),
        "kind": props.get("kind") or props.get("seamark:type"),
        "source": props.get("source") or "noaa",
    }


def aton_from_overpass(elements: list, lat0: float, lon0: float, haversine_nm) -> list[dict]:
    found = []
    for el in elements or []:
        tags = el.get("tags") or {}
        lat = el.get("lat")
        lon = el.get("lon")
        if lat is None or lon is None:
            center = el.get("center") or {}
            lat, lon = center.get("lat"), center.get("lon")
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            continue
        name = tags.get("seamark:name") or tags.get("name") or tags.get("seamark:type")
        if not name:
            continue
        found.append({
            "name": str(name)[:120],
            "lat": round(float(lat), 5),
            "lon": round(float(lon), 5),
            "nm": round(haversine_nm(lat0, lon0, float(lat), float(lon)), 1),
            "kind": tags.get("seamark:type"),
            "source": "osm-overpass",
        })
    found.sort(key=lambda x: x["nm"])
    return found[:MAX_ATON]


async def fetch_noaa_aids(
    client: httpx.AsyncClient,
    bi: str,
    bbox: tuple[float, float, float, float],
    lat: float,
    lon: float,
    haversine_nm,
    radius_nm: float,
) -> list[dict]:
    if not bbox_intersects_us(bbox):
        return []
    west, south, east, north = bbox
    try:
        r = await client.get(
            f"{bi}/noaa/aids",
            params={"bbox": f"{west:.5f},{south:.5f},{east:.5f},{north:.5f}"},
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=12.0,
        )
        r.raise_for_status()
        data = r.json() if r.content else {}
    except Exception:
        return []
    found = []
    for feat in (data.get("features") if isinstance(data, dict) else []) or []:
        item = slim_aton_feature(feat, lat, lon, haversine_nm)
        if item and item["nm"] <= radius_nm + 0.05:
            found.append(item)
    found.sort(key=lambda x: x["nm"])
    return found[:MAX_ATON]


async def fetch_overpass_aton(
    client: httpx.AsyncClient,
    bbox: tuple[float, float, float, float],
    lat: float,
    lon: float,
    haversine_nm,
) -> tuple[list[dict], str | None]:
    west, south, east, north = bbox
    query = (
        f"[out:json][timeout:12];"
        f'(node["seamark:type"~"^(light|light_major|light_minor|buoy|buoy_lateral|'
        f'buoy_cardinal|buoy_special_purpose|beacon|beacon_lateral|beacon_cardinal)$"]'
        f"({south:.5f},{west:.5f},{north:.5f},{east:.5f}););"
        f"out body 20;"
    )
    last_err = None
    for url in OVERPASS_ENDPOINTS:
        try:
            r = await client.post(
                url,
                content=query.encode("utf-8"),
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json",
                    "Content-Type": "text/plain",
                },
                timeout=14.0,
            )
            r.raise_for_status()
            data = r.json() if r.content else {}
            elements = data.get("elements") if isinstance(data, dict) else []
            return aton_from_overpass(elements or [], lat, lon, haversine_nm), None
        except Exception as exc:
            last_err = type(exc).__name__
            continue
    return [], f"overpass_unavailable:{last_err or 'error'}"


async def fetch_aton(
    client: httpx.AsyncClient,
    bi: str,
    lat: float,
    lon: float,
    radius_nm: float,
    haversine_nm,
    radius_bbox,
) -> dict:
    bag = empty_aton()
    bbox = radius_bbox(lat, lon, radius_nm)
    noaa = await fetch_noaa_aids(client, bi, bbox, lat, lon, haversine_nm, radius_nm)
    osm, osm_err = await fetch_overpass_aton(client, bbox, lat, lon, haversine_nm)
    merged: dict[tuple, dict] = {}
    for item in noaa + osm:
        key = (round(item["lat"], 4), round(item["lon"], 4), item["name"])
        if key not in merged or item["nm"] < merged[key]["nm"]:
            merged[key] = item
    nearby = sorted(merged.values(), key=lambda x: x["nm"])[:MAX_ATON]
    sources = []
    if noaa:
        sources.append("noaa-enc")
    if osm:
        sources.append("osm-overpass")
    bag["nearby"] = nearby
    if sources:
        bag["source"] = "+".join(sources)
        bag["reason"] = None
    elif osm_err and not bbox_intersects_us(bbox):
        bag["source"] = None
        bag["reason"] = f"outside_us_enc;{osm_err}"
    elif osm_err:
        bag["source"] = "noaa-enc"
        bag["reason"] = osm_err
    elif not bbox_intersects_us(bbox):
        bag["source"] = None
        bag["reason"] = "outside_us_enc;no_osm_seamark"
    else:
        bag["source"] = "noaa-enc"
        bag["reason"] = "no_aid_in_bbox"
    return bag


async def fetch_review(
    client: httpx.AsyncClient,
    bi: str,
    zee: dict | None,
    nearest_amp: dict | None,
) -> dict:
    bag = empty_review()
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    mrgid = zee.get("mrgid") if zee else None
    got = False
    if mrgid:
        try:
            r = await client.get(
                f"{bi}/review/fiche",
                params={"kind": "eez", "id": str(mrgid)},
                headers=headers,
                timeout=5.0,
            )
            if r.status_code == 401:
                bag["reason"] = "review_requires_admin"
                return bag
            if r.status_code == 404:
                bag["zee"] = {
                    "gold_on": None,
                    "source": "review_fiche",
                    "reason": "fiche_not_found",
                    "id": mrgid,
                }
            else:
                r.raise_for_status()
                data = r.json() if r.content else {}
                bag["zee"] = {
                    "gold_on": data.get("gold_on"),
                    "gold_ready": data.get("gold_ready"),
                    "pre_gold": data.get("pre_gold"),
                    "source": "review_fiche",
                    "id": mrgid,
                }
                got = True
        except Exception as exc:
            bag["reason"] = f"review_unavailable:{type(exc).__name__}"
            return bag
    site_id = (nearest_amp or {}).get("site_id") or (nearest_amp or {}).get("id")
    if site_id:
        try:
            r = await client.get(
                f"{bi}/review/fiche",
                params={"kind": "amp", "id": str(site_id)},
                headers=headers,
                timeout=5.0,
            )
            if r.status_code == 200:
                data = r.json() if r.content else {}
                bag["amp"] = {
                    "gold_on": data.get("gold_on"),
                    "gold_ready": data.get("gold_ready"),
                    "pre_gold": data.get("pre_gold"),
                    "source": "review_fiche",
                    "id": site_id,
                    "name": nearest_amp.get("name") if nearest_amp else None,
                }
                got = True
            elif r.status_code == 401 and not bag.get("reason"):
                bag["reason"] = "review_requires_admin"
            elif r.status_code == 404:
                bag["amp"] = {
                    "gold_on": None,
                    "source": "review_fiche",
                    "reason": "fiche_not_found",
                    "id": site_id,
                }
        except Exception:
            if not bag.get("amp"):
                bag["amp"] = {
                    "gold_on": None,
                    "source": "review_fiche",
                    "reason": "review_unavailable",
                    "id": site_id,
                }
    if got:
        bag["source"] = "review_fiche"
        if bag.get("reason") == "review_requires_admin":
            bag["reason"] = None
    elif not bag.get("reason") and not mrgid and not site_id:
        bag["reason"] = "no_entity"
    return bag


def climatology_rose(point: dict | None) -> dict | None:
    if not isinstance(point, dict):
        return None
    atlas = point.get("wind_atlas") or {}
    if not isinstance(atlas, dict):
        return None
    dirs = atlas.get("directions_from")
    if atlas.get("stat") not in ("rose", "average") and not dirs and atlas.get("calm_pct") is None:
        return None
    return {
        "stat": atlas.get("stat"),
        "sectors_deg": atlas.get("sectors_deg") or 45,
        "directions_from": dirs or [],
        "calm_pct": atlas.get("calm_pct"),
        "gale_pct": atlas.get("gale_pct"),
        "most_likely": atlas.get("most_likely"),
        "vector_mean": atlas.get("vector_mean"),
    }
