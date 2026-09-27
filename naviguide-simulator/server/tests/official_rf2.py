"""Helpers RF2 — hors chemin HTTP : poser le stock pour les tests existants."""
from __future__ import annotations

from typing import Any, Optional

import official_store


def put_family(family: str, payload: Any, key: Optional[str] = None) -> dict:
    return official_store.get_store().put(family, payload, key=key)


def put_moments(rows: list, voyage_id: str = official_store.DEFAULT_ROUTE) -> dict:
    return put_family("moments", {
        "status": official_store.STATUS_READY,
        "voyageId": voyage_id,
        "moments": rows,
        "count": len(rows),
    })


def put_eta_stop(stop: str, payload: dict) -> dict:
    cur = official_store.get_store().payload("eta") or {"status": "ready", "stops": {}}
    stops = dict(cur.get("stops") or {})
    stops[stop] = payload
    return put_family("eta", {"status": "ready", "stops": stops})


def put_review(payload: dict) -> dict:
    body = dict(payload)
    body.setdefault("status", "ready")
    return put_family("plan_review", body)
