#!/usr/bin/env python3
"""Télécharge 1–2 scènes Sentinel-2 (SAFE zip) via CDSE OData.

À lancer sur le Mac. Par défaut : 1 scène, dossier ~/Desktop/sentinel-pilot.
N'imprime jamais le mot de passe.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from cdse_auth import credentials

CATALOGUE = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
DOWNLOAD = "https://download.dataspace.copernicus.eu/odata/v1/Products"
TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu/auth/realms/CDSE"
    "/protocol/openid-connect/token"
)
HERE = Path(__file__).resolve().parent
DEFAULT_MANIFEST = HERE / "scenes_la_rochelle.json"


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


def product_name(scene_id: str) -> str:
    name = (scene_id or "").strip()
    if not name.endswith(".SAFE"):
        name = f"{name}.SAFE"
    return name


def lookup_product(token: str, scene_id: str) -> dict:
    name = product_name(scene_id)
    filt = f"Name eq '{name}'"
    url = f"{CATALOGUE}?$filter={urllib.parse.quote(filt)}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    items = payload.get("value") or []
    if not items:
        raise SystemExit(f"produit introuvable dans le catalogue : {name}")
    item = items[0]
    pid = item.get("Id")
    if not pid:
        raise SystemExit(f"produit sans Id : {name}")
    return {
        "id": pid,
        "name": item.get("Name") or name,
        "size": item.get("ContentLength"),
    }


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download_product(token: str, product_id: str, dest: Path) -> None:
    url = f"{DOWNLOAD}({product_id})/$value"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with urllib.request.urlopen(req, timeout=600) as resp, tmp.open("wb") as out:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
        tmp.replace(dest)
    except urllib.error.HTTPError as exc:
        if tmp.exists():
            tmp.unlink()
        print(f"téléchargement refusé (HTTP {exc.code})", file=sys.stderr)
        raise SystemExit(2) from exc


def default_out_dir() -> Path:
    desktop = Path.home() / "Desktop" / "sentinel-pilot"
    return desktop


def main() -> int:
    p = argparse.ArgumentParser(description="Télécharge les scènes listées (Mac)")
    p.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    p.add_argument("--limit", type=int, default=1, help="1 par défaut (fichier lourd)")
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--dry-run", action="store_true", help="Résout l'Id, n'écrit pas le zip")
    args = p.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    scenes = (manifest.get("scenes") or [])[: max(1, args.limit)]
    if not scenes:
        print("aucune scène dans le manifeste", file=sys.stderr)
        return 1
    out_dir = args.out or default_out_dir()
    token = access_token()
    receipts = []
    for scene in scenes:
        sid = scene.get("id")
        meta = lookup_product(token, sid)
        zip_name = meta["name"].replace(".SAFE", ".zip")
        dest = Path(out_dir) / zip_name
        rec = {
            "scene_id": sid,
            "product_id": meta["id"],
            "name": meta["name"],
            "bytes": meta["size"],
            "path": str(dest),
        }
        print(f"{meta['name']} → {dest} ({meta['size']} octets)")
        if not args.dry_run:
            if dest.exists() and dest.stat().st_size > 0:
                print(f"déjà là : {dest}")
            else:
                download_product(token, meta["id"], dest)
            rec["sha256"] = sha256_file(dest)
            rec["bytes_on_disk"] = dest.stat().st_size
            print(f"sha256 {rec['sha256']}")
        receipts.append(rec)
    receipt_path = Path(out_dir) / "download_receipt.json"
    if not args.dry_run:
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(
            json.dumps({"scenes": receipts}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"reçu : {receipt_path}")
    else:
        print(json.dumps({"dry_run": True, "scenes": receipts}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
