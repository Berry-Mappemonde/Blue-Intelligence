"""Extract source URLs shown on map-point fiches (GeoJSON exports, API fiches, Mongo).

Each reference ties a URL back to dataset, entity id, human label, and field name.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse
from urllib.request import Request, urlopen

_HTTP_SCHEMES = frozenset({"http", "https"})
_OSM_WEB_TAG_KEYS = ("website", "contact:website", "url")


@dataclass(frozen=True, slots=True)
class FicheUrlRef:
    dataset: str
    entity_id: str
    entity_label: str
    field: str
    url: str


def normalize_http_url(raw: str | None) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or s.startswith("#"):
        return None
    low = s.lower()
    if low.startswith(("mailto:", "tel:", "javascript:", "data:")):
        return None
    if "://" not in s:
        if s.startswith("//"):
            s = "https:" + s
        elif re.match(r"^[a-z0-9][a-z0-9+.-]*:", s, re.I):
            return None
        else:
            s = "https://" + s
    try:
        p = urlparse(s)
    except ValueError:
        return None
    if p.scheme not in _HTTP_SCHEMES or not p.netloc:
        return None
    return s


def _add(refs: list[FicheUrlRef], dataset: str, entity_id: str, label: str,
         field: str, raw: str | None) -> None:
    url = normalize_http_url(raw)
    if not url:
        return
    refs.append(FicheUrlRef(dataset, str(entity_id or ""), (label or "")[:160], field, url))


def _entity_id(props: dict) -> str:
    for key in ("id", "site_id", "osm_id", "_id"):
        v = props.get(key)
        if v not in (None, ""):
            return str(v)
    return ""


def _entity_label(props: dict) -> str:
    for key in ("name", "title", "zone_name", "city"):
        v = props.get(key)
        if v:
            return str(v)
    return _entity_id(props)


def _dataset_from_path(path: Path, fc: dict) -> str:
    meta = fc.get("metadata") or {}
    ds = meta.get("dataset")
    if ds:
        return str(ds)
    stem = path.stem.lower()
    if stem in ("projects", "geojson"):
        return "projects"
    if stem in ("ports_of_entry", "poe"):
        return "formalities_ports"
    if stem == "marinas":
        return "marinas"
    if stem == "capitaineries":
        return "capitaineries"
    if stem == "amp":
        return "amp"
    if stem == "science":
        return "science"
    if stem == "anchorages":
        return "anchorages"
    return stem or "unknown"


def extract_from_geojson_file(path: Path) -> list[FicheUrlRef]:
    fc = json.loads(path.read_text(encoding="utf-8"))
    return extract_from_geojson(path, fc)


def extract_from_geojson(path: Path, fc: dict) -> list[FicheUrlRef]:
    dataset = _dataset_from_path(path, fc)
    refs: list[FicheUrlRef] = []
    for feat in fc.get("features") or []:
        props = feat.get("properties") or {}
        eid = _entity_id(props)
        label = _entity_label(props)
        if dataset == "projects":
            _add(refs, "projects", eid, label, "url", props.get("url"))
        elif dataset == "formalities_ports":
            for i, u in enumerate(props.get("source_urls") or []):
                _add(refs, "formalities_ports", eid, label, f"source_urls[{i}]", u)
        elif dataset == "marinas":
            _add(refs, "marinas", eid, label, "website", props.get("website"))
            _add(refs, "marinas", eid, label, "maps_place_url", props.get("maps_place_url"))
        elif dataset == "capitaineries":
            _add(refs, "capitaineries", eid, label, "website", props.get("website"))
        elif dataset == "amp":
            _add(refs, "amp", eid, label, "manager_url", props.get("manager_url"))
            _add(refs, "amp", eid, label, "visit_url", props.get("visit_url"))
        elif dataset == "science":
            _add(refs, "science", eid, label, "url", props.get("url"))
        elif dataset == "anchorages":
            tags = props.get("tags") or {}
            for key in _OSM_WEB_TAG_KEYS:
                _add(refs, "anchorages", eid, label, f"tags.{key}", tags.get(key))
        else:
            _add(refs, dataset, eid, label, "url", props.get("url"))
            for i, u in enumerate(props.get("source_urls") or []):
                _add(refs, dataset, eid, label, f"source_urls[{i}]", u)
    return refs


def extract_from_poe_zone_fiche(fiche: dict) -> list[FicheUrlRef]:
    """URLs on Formalities zone popups / Review EEZ cards (TD + BU)."""
    refs: list[FicheUrlRef] = []
    mrgid = fiche.get("mrgid") or fiche.get("zone_mrgid")
    zone_label = fiche.get("zone_name") or fiche.get("name") or f"ZEE {mrgid}"
    eid = str(mrgid or zone_label)
    td = fiche.get("url_td")
    if isinstance(td, dict):
        _add(refs, "formalities_zone", eid, zone_label, "url_td", td.get("url"))
    elif isinstance(td, str):
        _add(refs, "formalities_zone", eid, zone_label, "url_td", td)
    for i, rec in enumerate(fiche.get("sources_td") or []):
        if isinstance(rec, dict):
            _add(refs, "formalities_zone", eid, zone_label, f"sources_td[{i}]", rec.get("url"))
        else:
            _add(refs, "formalities_zone", eid, zone_label, f"sources_td[{i}]", rec)
    for port in fiche.get("ports") or []:
        pname = port.get("name") or ""
        plabel = f"{zone_label} — {pname}" if pname else zone_label
        pid = port.get("id") or port.get("name") or eid
        bu = port.get("url_bu")
        if isinstance(bu, dict):
            _add(refs, "formalities_zone", str(pid), plabel, "url_bu", bu.get("url"))
        for j, rec in enumerate(port.get("urls_bu") or []):
            if isinstance(rec, dict):
                _add(refs, "formalities_zone", str(pid), plabel, f"urls_bu[{j}]", rec.get("url"))
        for j, u in enumerate(port.get("source_urls") or []):
            _add(refs, "formalities_zone", str(pid), plabel, f"source_urls[{j}]", u)
    return refs


def dedupe_refs(refs: Iterable[FicheUrlRef]) -> list[FicheUrlRef]:
    seen: set[tuple[str, str, str, str, str]] = set()
    out: list[FicheUrlRef] = []
    for ref in refs:
        key = (ref.dataset, ref.entity_id, ref.entity_label, ref.field, ref.url)
        if key in seen:
            continue
        seen.add(key)
        out.append(ref)
    return out


_API_EXPORTS: tuple[tuple[str, str], ...] = (
    ("geojson", "projects.geojson"),
    ("marinas.geojson", "marinas.geojson"),
    ("anchorages.geojson", "anchorages.geojson"),
    ("capitaineries.geojson", "capitaineries.geojson"),
    ("amp.geojson", "amp.geojson"),
    ("poe.geojson", "ports_of_entry.geojson"),
    ("science.geojson", "science.geojson"),
)


def _fetch_json(url: str, user_agent: str, timeout: float) -> dict | list:
    req = Request(url, headers={"User-Agent": user_agent, "Accept": "application/json"})
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def extract_from_api(base_url: str, *, user_agent: str, timeout: float = 60.0,
                     include_zone_fiches: bool = True) -> list[FicheUrlRef]:
    """Download public /api/export/* GeoJSON and optional visible PoE zone fiches."""
    base = base_url.rstrip("/")
    refs: list[FicheUrlRef] = []
    for endpoint, filename in _API_EXPORTS:
        url = f"{base}/api/export/{endpoint}"
        fc = _fetch_json(url, user_agent, timeout)
        if not isinstance(fc, dict):
            continue
        refs.extend(extract_from_geojson(Path(filename), fc))
    if include_zone_fiches:
        zones_payload = _fetch_json(
            f"{base}/api/poe/zones?visible=true", user_agent, timeout)
        items = zones_payload.get("items") if isinstance(zones_payload, dict) else []
        for z in items or []:
            try:
                mid = int(z.get("mrgid") or 0)
            except (TypeError, ValueError):
                continue
            if not mid:
                continue
            fiche = _fetch_json(
                f"{base}/api/poe/zones/{mid}?visible=true", user_agent, timeout)
            if isinstance(fiche, dict):
                refs.extend(extract_from_poe_zone_fiche(fiche))
    return dedupe_refs(refs)
