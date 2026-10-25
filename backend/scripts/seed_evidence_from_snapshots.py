"""Fill the Mongo collection poe_evidence from the committed official-page snapshots.

For a deployment that has Zetaris and Mongo but has not run generation on these zones:
it gives run.py, POST /run and /api/poe/verify the same stored evidence without
regenerating. Administrator command, never an agent action.

Each snapshot in backend/data/sample/official_pages/ goes through the generation path
unchanged: its sections become "[SOURCE: url]" blocks with the page's fetch metadata
(sha256, fetched_at, extract_level), then evidence_store.documents_from_context ->
evidence_store.build_records (the registry_check grounding) -> evidence_store.store
(upsert on mrgid + port_key + url, newest three per port). No record is written by
hand, and re-running writes the same records again.

Port names are the zone's ports in Zetaris (ZetarisClient.get_ports(mrgid=...)): the
live view when ZETARIS_* are set, otherwise the bundled sample fixture. Only ports that
an official snapshot designates get a record.

Dry run is the default: it prints each record it would write and whether it is new,
an update or unchanged (a read-only lookup, when Mongo is reachable). Only --apply
writes. The database is MONGO_URL / DB_NAME (or --mongo-url / --db); .env files are
loaded as in run.py, never overriding the environment.

    cd backend
    .venv/bin/python scripts/seed_evidence_from_snapshots.py                  # dry run, every zone
    .venv/bin/python scripts/seed_evidence_from_snapshots.py --zone Bermuda --apply
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

MONGO_TIMEOUT_MS = 3000
RUN_ID = 'seed-evidence'


def load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for path in (REPO_ROOT / '.env', BACKEND_DIR / '.env'):
        if path.is_file():
            load_dotenv(path)  # never overrides variables already set


def snapshot_pages(zone: str | None = None) -> list[dict]:
    """The committed snapshots, optionally only those of one zone (name or mrgid)."""
    from app.adapters import evidence_store
    pages = [json.loads(p.read_text(encoding='utf-8'))
             for p in sorted(evidence_store.SAMPLE_PAGES_DIR.glob('*.json'))]
    if zone is None:
        return pages
    wanted = zone.strip().casefold()
    return [page for page in pages
            if any(wanted in (str(z.get('mrgid')), str(z.get('zone_name') or '').casefold())
                   for z in page.get('zones') or [])]


def generation_inputs(pages: list[dict]) -> tuple[str, list[dict]]:
    """The collected text and used_sources generation would hold after fetching these pages."""
    blocks = [f"[SOURCE: {page['url']}]\n{section['text']}"
              for page in pages for section in page.get('sections') or []]
    used = [dict(url=page['url'], sha256=page['sha256'], collected_at=page['fetched_at'],
                 level=page.get('extract_level')) for page in pages]
    return '\n\n'.join(blocks), used


def zetaris_ports(mrgid: int) -> tuple[list[str], str]:
    """The zone's port names in Zetaris, and the adapter mode (live or sample)."""
    from app.adapters.zetaris import ZetarisClient
    client = ZetarisClient(run_id=RUN_ID)
    return [p['name'] for p in client.get_ports(mrgid=mrgid) if p.get('name')], client.mode


def plan(zone: str | None = None, ports_for=zetaris_ports) -> list[dict]:
    """Per snapshot zone: {mrgid, zone_name, ports, zetaris_mode, records}."""
    from app.adapters import evidence_store
    by_zone: dict[int, dict] = {}
    for page in snapshot_pages(zone):
        for z in page.get('zones') or []:
            entry = by_zone.setdefault(int(z['mrgid']), dict(zone_name=z.get('zone_name'), pages=[]))
            entry['pages'].append(page)
    out = []
    for mrgid, entry in sorted(by_zone.items()):
        names, mode = ports_for(mrgid)
        raw, used = generation_inputs(entry['pages'])
        records = evidence_store.build_records(
            mrgid, names, evidence_store.documents_from_context(raw, used))
        out.append(dict(mrgid=mrgid, zone_name=entry['zone_name'], ports=names, zetaris_mode=mode,
                        records=records))
    return out


async def _status(coll, record: dict) -> str:
    from app.adapters import evidence_store
    key = {k: record[k] for k in ('mrgid', 'port_key', 'url')}
    current = await coll.find_one(key, {'_id': 0})
    if current is None:
        return 'new'
    same = all(current.get(k) == record.get(k) for k in evidence_store.RECORD_FIELDS)
    return 'unchanged' if same else 'update'


async def seed(db, *, zone: str | None = None, apply: bool = False, ports_for=zetaris_ports) -> list[dict]:
    """Plan the records, mark each new / update / unchanged (db None: unknown), store on apply."""
    from app.adapters import evidence_store
    zones = plan(zone, ports_for)
    for z in zones:
        z['status'] = [await _status(db[evidence_store.COLLECTION], r) if db is not None else 'unknown'
                       for r in z['records']]
        z['stored'] = await evidence_store.store(db, z['records']) if apply and z['records'] else 0
    return zones


def report(zones: list[dict], apply: bool, db_label: str) -> None:
    print(f"{'APPLY' if apply else 'DRY RUN (nothing written; add --apply)'}: poe_evidence in {db_label}")
    for z in zones:
        print(f"\n{z['zone_name']} (mrgid {z['mrgid']}), ports from Zetaris ({z['zetaris_mode']}): "
              f"{', '.join(z['ports']) or 'none'}")
        if not z['records']:
            print('  no record: no port of this zone is designated in its snapshots')
        for record, status in zip(z['records'], z['status']):
            snippet = ' '.join(record['snippet'].split())
            print(f"  [{status}] {record['port_key']!r} <- {record['url']}\n"
                  f"      matched {record['matched_name']!r}: {snippet[:110]}...")
    total = sum(len(z['records']) for z in zones)
    counts = {s: sum(z['status'].count(s) for z in zones) for s in ('new', 'update', 'unchanged', 'unknown')}
    summary = ', '.join(f'{n} {s}' for s, n in counts.items() if n)
    done = f"; stored {sum(z['stored'] for z in zones)}" if apply else ''
    print(f"\n{total} record(s) for {len(zones)} zone(s): {summary or 'none'}{done}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--zone', help='only this zone (name or mrgid)')
    parser.add_argument('--apply', action='store_true', help='write to Mongo (default: dry run)')
    parser.add_argument('--mongo-url', help='default: MONGO_URL')
    parser.add_argument('--db', help='default: DB_NAME')
    args = parser.parse_args(argv)
    load_env()
    os.environ.setdefault('TRACE_STDOUT', '0')  # Zetaris trace events go to logs/ only
    mongo_url = args.mongo_url or os.environ.get('MONGO_URL') or 'mongodb://127.0.0.1:27017'
    db_name = args.db or os.environ.get('DB_NAME')
    if not db_name:
        parser.error('no database: set DB_NAME or pass --db')
    os.environ.setdefault('MONGO_URL', mongo_url)
    os.environ.setdefault('DB_NAME', db_name)

    from motor.motor_asyncio import AsyncIOMotorClient
    from pymongo.errors import PyMongoError

    async def run() -> int:
        client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=MONGO_TIMEOUT_MS)
        db = client[db_name]
        try:
            await client.admin.command('ping')
        except PyMongoError as exc:
            if args.apply:
                print(f'Mongo unreachable ({type(exc).__name__}); nothing written.', file=sys.stderr)
                return 1
            print(f'Mongo unreachable ({type(exc).__name__}): statuses unknown.', file=sys.stderr)
            db = None
        try:
            zones = await seed(db, zone=args.zone, apply=args.apply)
        finally:
            client.close()
        if not zones:
            print(f'No official-page snapshot for zone {args.zone!r}.', file=sys.stderr)
            return 2
        report(zones, args.apply, f'{db_name} (Mongo reachable: {db is not None})')
        return 0

    return asyncio.run(run())


if __name__ == '__main__':
    raise SystemExit(main())
