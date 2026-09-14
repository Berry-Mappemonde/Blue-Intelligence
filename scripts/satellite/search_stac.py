#!/usr/bin/env python3
"""Liste 1–2 scènes Sentinel-2 L1C sur le corridor (STAC CDSE).

ACOLITE refuse le L2A (correction ESA). Il faut le L1C (image brute).
N'écrit aucune image. À lancer sur le Mac de l'opérateur.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from cdse_auth import credentials
from corridor import default_bbox

TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu/auth/realms/CDSE"
    "/protocol/openid-connect/token"
)
STAC_SEARCH = "https://stac.dataspace.copernicus.eu/v1/search"
DEFAULT_COLLECTION = "sentinel-2-l1c"


def access_token() -> str:
    user, password = credentials()
    body = urllib.parse.urlencode({
        "client_id": "cdse-public",
        "grant_type": "password",
        "username": user,
        "password": password,
    }).encode("utf-8")
    req = urllib.request.Request(
        TOKEN_URL,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    token = payload.get("access_token")
    if not token:
        raise SystemExit("CDSE : réponse sans jeton")
    return token


def search_scenes(
    token: str,
    bbox: list[float],
    limit: int,
    max_cloud: float,
    collection: str = DEFAULT_COLLECTION,
) -> list[dict]:
    end = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = {
        "collections": [collection],
        "bbox": bbox,
        "datetime": f"2025-01-01T00:00:00Z/{end}",
        "limit": limit,
        "sortby": [{"field": "properties.eo:cloud_cover", "direction": "asc"}],
        "query": {"eo:cloud_cover": {"lt": max_cloud}},
    }
    raw = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        STAC_SEARCH,
        data=raw,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/geo+json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        print(f"STAC refusé (HTTP {exc.code}) : {detail}", file=sys.stderr)
        raise SystemExit(2) from exc
    items = []
    for feat in payload.get("features") or []:
        props = feat.get("properties") or {}
        items.append({
            "id": feat.get("id"),
            "datetime": props.get("datetime"),
            "cloud_cover": props.get("eo:cloud_cover"),
            "platform": props.get("platform"),
        })
    return items


def main() -> int:
    p = argparse.ArgumentParser(description="Recherche STAC Sentinel-2 (pas de téléchargement)")
    p.add_argument("--limit", type=int, default=2)
    p.add_argument("--max-cloud", type=float, default=20)
    p.add_argument(
        "--collection",
        default=DEFAULT_COLLECTION,
        help="Collection STAC (défaut : sentinel-2-l1c, requis par ACOLITE)",
    )
    p.add_argument("--out", type=Path, help="Écrire le manifeste JSON ici")
    args = p.parse_args()
    bbox = default_bbox()
    token = access_token()
    scenes = search_scenes(token, bbox, args.limit, args.max_cloud, args.collection)
    manifest = {
        "bbox": bbox,
        "collection": args.collection,
        "note": "L1C pour ACOLITE. Ne pas utiliser une scène MSIL2A.",
        "scenes": scenes,
    }
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not scenes:
        print("aucune scène sous le seuil de nuages", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
