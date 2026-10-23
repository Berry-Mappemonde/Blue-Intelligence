"""Registry check: confirm candidate ports against independent registries held in Zetaris.

A candidate is "official" only if it matches a UN/LOCODE port (UNECE) or a World Port
Index entry (NGA Pub 150) by normalised name, and lies within MAX_DISTANCE_KM of the
registry coordinates when both sides have coordinates. Everything else is
"unconfirmed - review needed". Blue Intelligence's own seed GeoJSON is never the
reference, so the check is not circular. See app/adapters/registry_sources.py for the
sources and licences.

Each port gets ``registry_matches`` ([{source, code, name, distance_km}]) and
``zetaris_validation``; each check is traced as a ZetarisAdapter ``registry_check`` event.
"""
from __future__ import annotations

import math
import re
import unicodedata

from app.adapters.zetaris import ZetarisClient, ZetarisUnavailable

MAX_DISTANCE_KM = 10.0
OFFICIAL = "official"
UNCONFIRMED = "unconfirmed - review needed"
SOURCES = ("unlocode", "wpi")
REGISTRY_LIMIT = 10000

_APOSTROPHES = re.compile(r"[\'’‘`´]")
_POSSESSIVE = re.compile(r"[\'’‘`´]s\b", re.IGNORECASE)
# Leading words that name the facility, not the place ("Port of X", "Porto de X", "Luka X").
_PREFIXES = (
    "port autonome de", "port autonome d", "pkk porti i", "porti i", "port of", "port de", "port d",
    "porto de", "porto do", "porto da", "puerto de", "puerto del", "harbour of", "harbor of",
    "marina de", "marina di", "marina", "luka", "porto", "puerto", "port", "the",
)
# Trailing facility words ("Bridgetown Port", "Anchorage Small Boat Harbor").
_SUFFIXES = (
    "small boat harbour", "small boat harbor", "deep water harbour", "deep water harbor",
    "harbour", "harbor", "port", "marina", "jetty", "terminal",
)
_TOKENS = {"st": "saint", "ste": "sainte", "mt": "mount", "ft": "fort", "pt": "point"}


def name_key(name: str | None) -> str:
    """Casefold, strip accents and punctuation: "Luka Brčko" -> "luka brcko"."""
    text = unicodedata.normalize("NFKD", name or "")
    text = "".join(c for c in text if not unicodedata.combining(c)).casefold()
    text = _APOSTROPHES.sub("", text)
    return " ".join(re.sub(r"[\W_]+", " ", text).split())


def _strip(key: str, words: tuple[str, ...], leading: bool) -> str:
    for word in words:
        if leading and key.startswith(word + " "):
            return key[len(word) + 1:]
        if not leading and key.endswith(" " + word):
            return key[:-len(word) - 1]
    return key


def name_variants(*names: str | None) -> set[str]:
    """Matching keys for one or more names (a registry name and its alternates).

    Splits "A / B" and "A (B)", drops the possessive "'s" (with or without the apostrophe),
    strips facility words ("Port of", "Harbour", ...) and spells out St/Ste/Mt/Ft/Pt. The full
    key is always kept.
    """
    out: set[str] = set()
    for name in names:
        if not name:
            continue
        name = _POSSESSIVE.sub("", name)
        for part in re.split(r"[/;()]|,\s", name):
            key = name_key(part)
            if not key:
                continue
            stripped = _strip(_strip(key, _PREFIXES, leading=True), _SUFFIXES, leading=False)
            forms = {key, stripped}
            # A possessive written without its apostrophe: "St Georges" ~ "St George".
            forms |= {f[:-1] for f in forms if re.search(r"[a-z]{3}[^s]s$", f)}
            for candidate in forms:
                if candidate:
                    out.add(candidate)
                    out.add(" ".join(_TOKENS.get(t, t) for t in candidate.split()))
    return out


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi, dlmb = phi2 - phi1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * 6371.0088 * math.asin(min(1.0, math.sqrt(a)))


def _coords(item: dict) -> tuple[float, float] | None:
    lat, lon = item.get("lat"), item.get("lon")
    if isinstance(lat, bool) or isinstance(lon, bool):
        return None
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return None
    return (lat, lon) if math.isfinite(lat) and math.isfinite(lon) else None


def _entry_names(entry: dict) -> tuple:
    if entry.get("source") == "wpi":
        return entry.get("name"), entry.get("alternate_name")
    return entry.get("name"), entry.get("name_ascii")


def _entry_code(entry: dict) -> str | None:
    if entry.get("source") == "wpi":
        return entry.get("unlocode") or (f"WPI {entry['wpi_number']}" if entry.get("wpi_number") else None)
    return entry.get("code")


def match_port(port: dict, entries: list[dict], max_km: float = MAX_DISTANCE_KM) -> tuple[list[dict], list[dict]]:
    """(matches, rejected): name matches within max_km, and name matches the distance gate refused.

    Keeps the closest entry per source. distance_km is None when either side lacks coordinates.
    """
    variants = name_variants(port.get("name"))
    here = _coords(port)
    best: dict[str, dict] = {}
    rejected: list[dict] = []
    for entry in entries:
        if not variants & name_variants(*_entry_names(entry)):
            continue
        there = _coords(entry)
        distance = round(haversine_km(*here, *there), 2) if here and there else None
        evidence = dict(source=entry.get("source"), code=_entry_code(entry), name=entry.get("name"),
                        distance_km=distance)
        if entry.get("source") == "wpi" and entry.get("first_port_of_entry"):
            evidence["first_port_of_entry"] = entry["first_port_of_entry"]
        if distance is not None and distance > max_km:
            rejected.append(evidence)
            continue
        current = best.get(evidence["source"])
        rank = math.inf if distance is None else distance
        if current is None or rank < (math.inf if current["distance_km"] is None else current["distance_km"]):
            best[evidence["source"]] = evidence
    return [best[s] for s in SOURCES if s in best], rejected


def fetch_registry(country_iso2: str | None, run_id: str, bbox: tuple | None = None,
                   live_failed: bool = False) -> tuple[list[dict], str]:
    """Both registries for a country (or bbox); a live failure falls back to the sample fixtures.

    live_failed: Zetaris already failed earlier in this run, so go straight to the fixtures
    instead of waiting on the same outage again.
    """
    client = ZetarisClient(run_id=run_id)
    try:
        if live_failed and client.mode == "live":
            raise ZetarisUnavailable("Zetaris unavailable earlier in this run")
        entries = [e for source in SOURCES for e in client.get_registry_ports(
            country_iso2=country_iso2, bbox=bbox, source=source, limit=REGISTRY_LIMIT)]
        return entries, client.mode
    except ZetarisUnavailable as exc:
        if client.mode != "live":
            raise
        # Adapter messages are sanitized (no response bodies or credentials).
        client.trace_event("zetaris_fallback", status="fallback", reason=str(exc)[:200],
                           input_summary={"country_iso2": country_iso2, "bbox": bbox, "step": "registry"})
        client.mode = "sample"
        entries = [e for source in SOURCES for e in client.get_registry_ports(
            country_iso2=country_iso2, bbox=bbox, source=source, limit=REGISTRY_LIMIT)]
        return entries, "fallback"


def candidate_bbox(ports: list[dict], pad_deg: float = 0.5) -> tuple | None:
    """Padded box around the candidates' coordinates, used when the country is unknown."""
    points = [c for c in (_coords(p) for p in ports) if c]
    if not points or len(points) < len(ports):
        return None
    lats, lons = [p[0] for p in points], [p[1] for p in points]
    return (max(-90.0, min(lats) - pad_deg), max(-180.0, min(lons) - pad_deg),
            min(90.0, max(lats) + pad_deg), min(180.0, max(lons) + pad_deg))


def zone_iso2(zone: dict | str | None) -> str | None:
    """ISO2 of a zone: its own iso2, else the EEZ index (by mrgid, then name), else its sovereign's."""
    zone = {"name": zone} if isinstance(zone, str) else dict(zone or {})
    for key in ("iso2", "country_iso2", "sov_iso2"):
        value = zone.get(key)
        if isinstance(value, str) and re.fullmatch(r"[A-Za-z]{2}", value):
            return value.upper()
    try:
        from app.services.listing_ref import load_eez_index
        index = load_eez_index()
    except Exception:  # noqa: BLE001 — missing catalogue: fall back to a bbox query
        return None
    mrgid, name = zone.get("mrgid"), name_key(zone.get("name") or zone.get("zone_name"))
    found = next((z for z in index if mrgid is not None and str(z.get("mrgid")) == str(mrgid)), None)
    found = found or next((z for z in index if name and name in (name_key(z.get("name")),
                                                                 name_key(z.get("geoname")))), None)
    if not found:
        return None
    if found.get("iso2"):
        return str(found["iso2"]).upper()
    try:  # e.g. Alaska and the Azores have no iso2 of their own in the index
        import pycountry
        return pycountry.countries.lookup(found.get("sovereign") or "").alpha_2
    except (ImportError, LookupError):
        return None


def fetch_for_zone(zone: dict | str | None, ports: list[dict], run_id: str,
                   live_failed: bool = False) -> dict:
    """Registry entries for a zone: {mode, country_iso2, entries}.

    Queries by country ISO2 when the zone resolves to one, else by a box around the
    candidates. A Zetaris outage with no fallback gives mode "unavailable" and no entries,
    so every port stays unconfirmed, never official.
    """
    country = zone_iso2(zone)
    bbox = None if country else candidate_bbox(ports)
    if country is None and bbox is None:
        return dict(mode="no-country", country_iso2=None, entries=[])
    try:
        entries, mode = fetch_registry(country, run_id, bbox, live_failed)
    except (ZetarisUnavailable, ValueError) as exc:
        ZetarisClient(run_id=run_id).trace_event(
            "registry_unavailable", status="error", reason=str(exc)[:200],
            input_summary={"country_iso2": country})
        entries, mode = [], "unavailable"
    return dict(mode=mode, country_iso2=country, entries=entries)


def annotate(ports: list[dict], registry: dict, run_id: str) -> tuple[list[dict], dict]:
    """Add registry_matches / zetaris_validation to copies of ports; trace one event per port.

    Returns (ports, summary) with summary {mode, country_iso2, registry_entries, official_count}.
    """
    entries, country = registry.get("entries") or [], registry.get("country_iso2")
    client = ZetarisClient(run_id=run_id)
    client.mode = registry.get("mode") or client.mode
    out = []
    for raw in ports:
        port = dict(raw)
        matches, rejected = match_port(port, entries)
        port["registry_matches"] = matches
        port["zetaris_validation"] = OFFICIAL if matches else UNCONFIRMED
        client.trace_event(
            "registry_check", status="ok" if matches else "unconfirmed",
            input_summary={"port_name": port.get("name"), "country_iso2": country,
                           "has_coordinates": _coords(port) is not None},
            registry_entries=len(entries), matches=matches,
            rejected_by_distance=rejected[:3], max_distance_km=MAX_DISTANCE_KM,
            validation=port["zetaris_validation"])
        out.append(port)
    summary = dict(mode=client.mode, country_iso2=country, registry_entries=len(entries),
                   official_count=sum(1 for p in out if p["zetaris_validation"] == OFFICIAL))
    return out, summary


def check_ports(ports: list[dict], zone: dict | str | None, run_id: str,
                live_failed: bool = False) -> tuple[list[dict], dict]:
    """fetch_for_zone + annotate: the registry check step of the run pipeline."""
    return annotate(ports, fetch_for_zone(zone, ports, run_id, live_failed), run_id)
