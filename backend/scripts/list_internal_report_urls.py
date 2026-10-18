#!/usr/bin/env python3
"""Print report and deeplink rows whose URL fails the public-host check.

Read-only. This script only calls find(). It does not update, delete,
or insert anything. A purge, if one is needed, is a separate decision.

Usage (from backend/):
    python3 scripts/list_internal_report_urls.py

Each matching row is one line: collection, _id, url, separated by tabs.
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.core.public_url import public_url_error  # noqa: E402

COLLECTIONS = ("deeplink_pages", "reported_projects")


def list_internal(db):
    """Return (collection, _id, url) for stored URLs that must not be fetched."""
    cache: dict = {}
    rows = []
    for name in COLLECTIONS:
        for doc in db[name].find({}, {"_id": 1, "url": 1}):
            url = "" if doc.get("url") is None else str(doc.get("url"))
            if public_url_error(url, resolve_cache=cache):
                rows.append((name, doc.get("_id"), url))
    return rows


def main() -> int:
    from app.config import DB_NAME, MONGO_URL
    from pymongo import MongoClient

    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=8_000)
    try:
        for name, doc_id, url in list_internal(client[DB_NAME]):
            print(f"{name}\t{doc_id}\t{url}", flush=True)
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
