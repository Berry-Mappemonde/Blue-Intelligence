#!/usr/bin/env python3
"""Export des fixtures V2 pour évaluation hors-ligne du jury (mode sample).

Connecté à la base `blueintel_db_v2` sur 127.0.0.1:27017 et exporte proprement
(sérialisation JSON sans ObjectId BSON brut) :

  * poe_ports : les 1 169 ports d'entrée avec leurs champs d'arbitrage Zetaris
  * eez_zones : métadonnées des zones ZEE
  * projects  : projets maritimes de référence

La sortie est sauvegardée dans `fixtures/v2_zones.json` (à la racine du projet).

Usage:
    python backend/scripts/export_v2_fixtures.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from pymongo import MongoClient  # noqa: E402
from bson import ObjectId  # noqa: E402


class FixtureEncoder(json.JSONEncoder):
    """Encodeur JSON qui gère les types BSON non natifs (ObjectId, datetime…)."""

    def default(self, obj: Any) -> Any:  # noqa: ANN401
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, bytes):
            return obj.decode("utf-8", errors="replace")
        return super().default(obj)


def _clean_doc(doc: dict[str, Any]) -> dict[str, Any]:
    """Nettoie un document MongoDB pour export JSON (sérialisation récursive)."""
    cleaned: dict[str, Any] = {}
    for key, value in doc.items():
        cleaned[key] = _serialize_value(value)
    return cleaned


def _serialize_value(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize_value(v) for v in value]
    return value


def export_collection(db, name: str) -> list[dict[str, Any]]:
    """Exporte une collection entière vers une liste de documents nettoyés."""
    cursor = db[name].find({})
    docs = [_clean_doc(doc) for doc in cursor]
    return docs


def main() -> int:
    mongo_url = os.environ.get("MONGO_URL", "mongodb://127.0.0.1:27017")
    db_name = os.environ.get("DB_NAME", "blueintel_db_v2")

    print(f"Connexion à MongoDB : {mongo_url} / base : {db_name}")
    client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    db = client[db_name]

    collections = ["poe_ports", "eez_zones", "projects"]
    fixtures: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": f"mongo:{db_name}",
        "collections": {},
    }

    for coll_name in collections:
        docs = export_collection(db, coll_name)
        fixtures["collections"][coll_name] = docs
        print(f"  {coll_name}: {len(docs)} documents exportés")

    client.close()

    fixtures_dir = REPO_ROOT / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    out_path = fixtures_dir / "v2_zones.json"

    payload = json.dumps(fixtures, ensure_ascii=False, indent=2, cls=FixtureEncoder)
    out_path.write_text(payload + "\n", encoding="utf-8")

    total = sum(len(v) for v in fixtures["collections"].values())
    print(f"\nFichier écrit : {out_path}")
    print(f"Total documents : {total}")
    print("Export V2 terminé.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
