#!/usr/bin/env python3
"""Complète le Mongo de CI avec la validation OSM réelle et le scan d'anomalies.

Réutilise ``overpass_around``, ``score_confidence`` et ``scan_poe_anomalies``.
N'écrit que dans ``bi_ci`` sur 127.0.0.1 ou localhost. Une requête Overpass
qui échoue ne reçoit aucun ``osm_confidence`` : aucun score n'est inventé.

Mode offline (``CI_OSM_OFFLINE=1``) : aucun appel réseau n'est effectué. Un
port absent du cache compte comme un échec. Seuls les refus finals sont
appliqués (ports manquants / absence d'anomalie -> exit 1).
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))

from seed_ci_mongo import assert_ci_target  # noqa: E402

from app.services.osm_validate import overpass_around, score_confidence  # noqa: E402

_CONCURRENCY = 3
_ROUNDS = 4
_CACHE_ENV = "CI_OSM_CACHE"
_OFFLINE_ENV = "CI_OSM_OFFLINE"


def osm_updates(port: dict, elements: list[dict]) -> dict:
    """Mêmes champs que ``validate_ports``. Ni le nom ni les coordonnées."""
    conf, tags, n = score_confidence(elements)
    fresh = {**port, "osm_confidence": conf, "osm_tags": tags}
    updates = {
        "osm_confidence": conf,
        "osm_tags": tags,
        "osm_matches": n,
        "osm_checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    try:
        from app.services.poe_confidence import apply_score, score_port

        official = any(
            "gouv" in (u or "") or "gov" in (u or "") or "gob" in (u or "")
            for u in (port.get("source_urls") or [])
        )
        apply_score(fresh, score_port(fresh, official_source=official))
    except Exception:
        pass
    updates["confidence"] = fresh.get("confidence")
    updates["confidence_parts"] = fresh.get("confidence_parts")
    updates["confidence_reasons"] = fresh.get("confidence_reasons")
    return updates


def _cache_path() -> Path | None:
    raw = (os.environ.get(_CACHE_ENV) or "").strip()
    return Path(raw) if raw else None


def _load_cache(path: Path | None) -> dict:
    if path is None or not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    ports = data.get("ports") if isinstance(data, dict) else None
    return ports if isinstance(ports, dict) else {}


def _cached_elements(port: dict, cache: dict) -> list[dict] | None:
    hit = cache.get(str(port["_id"]))
    if not isinstance(hit, dict):
        return None
    if hit.get("lat") != port.get("lat") or hit.get("lon") != port.get("lon"):
        return None
    elements = hit.get("elements")
    if not isinstance(elements, list):
        return None
    return elements


def _is_offline() -> bool:
    return os.environ.get(_OFFLINE_ENV, "").strip() in {"1", "true", "True"}


async def _validate_port(db, port: dict, sem: asyncio.Semaphore, cache: dict,
                         stats: dict, offline: bool) -> None:
    cached = _cached_elements(port, cache)
    try:
        if cached is None:
            if offline:
                stats["missing"] += 1
                stats["errors"].append(
                    f"{port.get('name')}: port absent du cache Overpass (offline)"
                )
                return
            async with sem:
                elements = await overpass_around(port["lat"], port["lon"])
            cache[str(port["_id"])] = {
                "lat": port.get("lat"),
                "lon": port.get("lon"),
                "elements": elements,
            }
        else:
            elements = cached
            stats["cache"] += 1
        updates = osm_updates(port, elements)
        await db.poe_ports.update_one({"_id": port["_id"]}, {"$set": updates})
        stats["checked"] += 1
    except Exception as exc:
        stats["failed"] += 1
        stats["errors"].append(
            f"{port.get('name')}: {type(exc).__name__}: {str(exc)[:80]}"
        )


async def _enrich(mongo_url: str, db_name: str) -> dict:
    from motor.motor_asyncio import AsyncIOMotorClient

    from app.core.ml import scan_poe_anomalies

    offline = _is_offline()
    cache_file = _cache_path() if offline else None
    cache = _load_cache(cache_file) if cache_file else {}
    client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=10_000)
    db = client[db_name]
    await client.admin.command("ping")
    sem = asyncio.Semaphore(_CONCURRENCY)
    pending_filter = {
        "lat": {"$ne": None},
        "lon": {"$ne": None},
        "osm_checked_at": {"$exists": False},
    }
    try:
        for round_n in range(1, _ROUNDS + 1):
            ports = await db.poe_ports.find(pending_filter).to_list(20_000)
            if not ports:
                break
            stats = {
                "checked": 0, "failed": 0, "cache": 0,
                "missing": 0, "errors": [],
            }
            started = time.time()
            await asyncio.gather(*[
                _validate_port(db, port, sem, cache, stats, offline)
                for port in ports
            ])
            if cache_file and not offline:
                # Seul le job osm-cache ecrit le cache ; les shards offline
                # ne le font pas.
                pass
            print(
                f"round {round_n}: {stats['checked']} validés, "
                f"{stats['failed']} échecs, {stats['cache']} depuis le cache, "
                f"{stats.get('missing', 0)} absents du cache (offline), "
                f"{time.time() - started:.0f}s",
                flush=True,
            )
            for line in stats["errors"][:8]:
                print(f"  {line}", flush=True)
            if stats["failed"] and round_n < _ROUNDS:
                await asyncio.sleep(8)
    finally:
        client.close()

    missing = await db.poe_ports.count_documents(pending_filter)
    total = await db.poe_ports.count_documents({})
    with_conf = await db.poe_ports.count_documents({"osm_confidence": {"$ne": None}})
    if missing or with_conf < total:
        raise SystemExit(
            f"refus: {missing} ports sans validation OSM "
            f"({with_conf}/{total} avec osm_confidence)"
        )
    summary = await scan_poe_anomalies(db)
    flagged = int(summary.get("anomalies_flagged") or 0)
    if flagged < 1:
        raise SystemExit(f"refus: scan d'anomalies sans drapeau ({summary})")
    return {
        "poe_ports": total,
        "osm_confidence": with_conf,
        "anomalies_flagged": flagged,
    }


def main() -> None:
    mongo_url = os.environ.get("MONGO_URL") or ""
    db_name = os.environ.get("DB_NAME") or ""
    assert_ci_target(mongo_url, db_name)
    summary = asyncio.run(_enrich(mongo_url, db_name))
    print(
        f"bi_ci: {summary['osm_confidence']}/{summary['poe_ports']} ports "
        f"avec osm_confidence, {summary['anomalies_flagged']} anomalies"
    )


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        print(f"enrich_ci_osm: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
