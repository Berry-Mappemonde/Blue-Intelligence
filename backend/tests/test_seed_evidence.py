"""backend/scripts/seed_evidence_from_snapshots.py: poe_evidence filled from the committed
official-page snapshots through the generation path, dry run by default, idempotent."""
import asyncio
import importlib.util
import json
import os
import subprocess
import sys

import pytest

from app.adapters import evidence_store
from app.core import paths
from test_evidence_store import FakeCollection, FakeDB

SCRIPT = paths.REPO_ROOT / 'backend' / 'scripts' / 'seed_evidence_from_snapshots.py'
spec = importlib.util.spec_from_file_location('seed_evidence_from_snapshots', SCRIPT)
seed_script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seed_script)

SNAPSHOT_ZONES = {8402: 'Bermuda', 8404: 'Bahamas', 8414: 'Antigua and Barbuda', 8463: 'Alaska'}


class SeedCollection(FakeCollection):
    async def find_one(self, flt, projection=None):
        found = [d for d in self.docs if all(d.get(k) == v for k, v in flt.items())]
        return {k: v for k, v in found[0].items() if k != '_id'} if found else None


class SeedDB(FakeDB):
    def __getitem__(self, name):
        return self.setdefault(name, SeedCollection())


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv('TRACE_LOG_PATH', str(tmp_path / 'trace.jsonl'))
    monkeypatch.setenv('TRACE_STDOUT', '0')
    monkeypatch.setenv('SAMPLE_MODE', 'true')  # ports come from the bundled Zetaris fixture
    for name in ('ZETARIS_API_KEY', 'ZETARIS_ORG_ID', 'ZETARIS_REST_URL'):
        monkeypatch.delenv(name, raising=False)


def stored(db):
    return sorted(({k: v for k, v in d.items() if k != '_id'} for d in db[evidence_store.COLLECTION].docs),
                  key=lambda r: (r['mrgid'], r['port_key'], r['url']))


def test_dry_run_writes_nothing_and_lists_every_record():
    db = SeedDB()
    zones = asyncio.run(seed_script.seed(db))
    assert {z['mrgid']: z['zone_name'] for z in zones} == SNAPSHOT_ZONES
    assert db[evidence_store.COLLECTION].docs == [] and db[evidence_store.COLLECTION].indexes == []
    records = [r for z in zones for r in z['records']]
    assert {(r['mrgid'], r['port_key']) for r in records} == {
        (8402, 'saint george'), (8404, 'conch inn'), (8414, 'deep water'), (8463, 'anchorage')}
    assert all(s == 'new' for z in zones for s in z['status'])


def test_apply_is_idempotent():
    db = SeedDB()
    first = asyncio.run(seed_script.seed(db, apply=True))
    after_first = stored(db)
    second = asyncio.run(seed_script.seed(db, apply=True))
    assert after_first and stored(db) == after_first
    assert all(s == 'new' for z in first for s in z['status'])
    assert all(s == 'unchanged' for z in second for s in z['status'])
    assert sum(z['stored'] for z in second) == len(after_first)  # rewritten with the same values


def test_records_are_identical_to_what_generation_builds_from_the_same_text():
    """poe_pipeline._store_evidence (generation) on the snapshot text, and the sample-mode
    lookup builder, give exactly the records the script stores."""
    from app.services import poe_pipeline
    seeded = SeedDB()
    zones = asyncio.run(seed_script.seed(seeded, apply=True))
    generated = SeedDB()
    for z in zones:
        pages = [json.loads(p.read_text(encoding='utf-8'))
                 for p in sorted(evidence_store.SAMPLE_PAGES_DIR.glob('*.json'))]
        pages = [p for p in pages if z['mrgid'] in {int(x['mrgid']) for x in p['zones']}]
        raw = '\n\n'.join(f"[SOURCE: {p['url']}]\n{s['text']}" for p in pages for s in p['sections'])
        used = [{'url': p['url'], 'sha256': p['sha256'], 'collected_at': p['fetched_at'],
                 'level': p['extract_level']} for p in pages]
        asyncio.run(poe_pipeline._store_evidence(generated, {'mrgid': z['mrgid']},
                                                 [{'name': n} for n in z['ports']], raw, used, lambda m: None))
        lookup_builder = evidence_store.build_records(z['mrgid'], z['ports'],
                                                      evidence_store.sample_documents(z['mrgid']))
        assert z['records'] == lookup_builder
    assert stored(seeded) == stored(generated) and len(stored(seeded)) == 5


def test_zone_filter_and_ports_from_zetaris():
    calls = []

    def ports_for(mrgid):
        calls.append(mrgid)
        return ['Port of St. George’s', 'Port of Hamilton'], 'live'

    zones = asyncio.run(seed_script.seed(SeedDB(), zone='bermuda', ports_for=ports_for))
    assert calls == [8402] and [z['zetaris_mode'] for z in zones] == ['live']
    # Hamilton is named near "ports of entry" on the gov.bm Customs page.
    assert {(r['port_key'], r['url']) for r in zones[0]['records']} == {
        ('saint george', 'https://www.gov.bm/department/customs'),
        ('saint george', 'https://planning.gov.bm/wp-content/uploads/2018/11/Scoping-Report.pdf'),
        ('hamilton', 'https://www.gov.bm/department/customs')}
    assert asyncio.run(seed_script.seed(SeedDB(), zone='8463', ports_for=ports_for))[0]['zone_name'] == 'Alaska'
    assert asyncio.run(seed_script.seed(SeedDB(), zone='Angola')) == []


def test_cli_dry_run_without_mongo_prints_and_exits_0(tmp_path):
    env = {'PATH': os.environ.get('PATH', ''), 'HOME': str(tmp_path), 'SAMPLE_MODE': 'true',
           'MONGO_URL': 'mongodb://127.0.0.1:1', 'DB_NAME': 'seed_test', 'TRACE_LOG_PATH': str(tmp_path / 't.jsonl')}
    proc = subprocess.run([sys.executable, str(SCRIPT), '--zone', 'Bermuda'], cwd=tmp_path, env=env,
                          capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    assert 'DRY RUN' in proc.stdout and "[unknown] 'saint george'" in proc.stdout
    assert 'Mongo unreachable' in proc.stderr
    apply = subprocess.run([sys.executable, str(SCRIPT), '--zone', 'Bermuda', '--apply'], cwd=tmp_path, env=env,
                           capture_output=True, text=True, timeout=60)
    assert apply.returncode == 1 and 'nothing written' in apply.stderr
