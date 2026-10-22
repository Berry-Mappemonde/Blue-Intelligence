"""All 13 unmodified Meterless vectors; assertions follow conformance/runner.ts."""
import json
from pathlib import Path
import pytest
from app.engines.hmem import HMEM
from app.engines.hmem.types import DAY_MS

VECTORS = json.loads((Path(__file__).parent / 'fixtures/hmem_vectors.json').read_text())
CASES = [(section, case) for section, cases in VECTORS['sections'].items() for case in cases]


@pytest.mark.parametrize('section,case', CASES, ids=[f'{s}/{c["id"]}' for s, c in CASES])
def test_conformance(section, case):
    now = [VECTORS['clock']]
    h = HMEM(clock=lambda: now[0], persist_dir=None)
    if section == 'record-validation':
        if case['expect'] == 'reject':
            with pytest.raises(ValueError):
                h.add(case['input'])
        else:
            assert h.add(case['input'])['source'] == case['input']['source']
    elif section == 'feedback-deltas':
        m = h.add(dict(content='feedback test', source='conformance', confidence=case['start']))
        h.feedback(m['id'], case['kind'])
        assert m['confidence'] == pytest.approx(case['expectConfidence'])
        if 'expectAccessDelta' in case:
            assert m['accessCount'] == case['expectAccessDelta']
        if 'expectTag' in case:
            assert case['expectTag'] in m['tags']
    elif section == 'ranking-order':
        records = {r['key']: h.add(dict(content=r['content'], confidence=r['confidence'],
                                      layer=r['layer'], source='conformance')) for r in case['records']}
        for r in case['records']:
            if 'supersededByKey' in r:
                h.store.update(records[r['key']]['id'], {'supersededBy': records[r['supersededByKey']]['id']})
        result = h.query(case['query'], dict(threshold=0, topN=10))
        assert [m['memory']['id'] for m in result['memories']] == [records[k]['id'] for k in case['expectOrder']]
    elif section == 'sleep-guardrails':
        records = {r['key']: h.add({k: v for k, v in r.items() if k != 'key'}) for r in case['records']}
        now[0] += case['ageDays'] * DAY_MS
        before = h.store.snapshot_all()
        plan = h.sleep.preview()
        assert h.store.snapshot_all() == before
        assert set(plan['toArchive']) == {records[k]['id'] for k in case['expectArchived']}
        report = h.sleep.execute(plan)
        assert isinstance(report['backupId'], str)
        for key in case['expectProtected']:
            assert h.store.get(records[key]['id']) is not None
    elif section == 'conflict-gate':
        a, b = [h.add(dict(source='conformance', **case[k])) for k in ('a', 'b')]
        conflicts = h.conflicts.scan()
        assert conflicts
        outcome = h.conflicts.auto_resolve(conflicts[0])
        assert outcome in ('resolved', 'queued')  # The upstream runner permits either at this gate.
        assert h.store.get(a['id']) and h.store.get(b['id'])
        if outcome == 'resolved':
            assert a.get('supersededBy') == b['id'] or b.get('supersededBy') == a['id']
        else:
            assert conflicts[0] in h.conflicts.queue()
    elif section == 'ledger-audit':
        m = h.add(dict(content='audited', source='conformance', confidence=case['start']))
        h.feedback(m['id'], case['kind'])
        entries = h.ledger.history(m['id'])
        assert [e['action'] for e in entries] == case['expectActions']
        assert entries[-1]['previousState']['confidence'] == pytest.approx(case['expectPrev'])
        assert entries[-1]['newState']['confidence'] == pytest.approx(case['expectNew'])
    elif section == 'dream-boundary':
        for record in case['records']:
            h.add(dict(source='conformance', **record))
        before = h.store.snapshot_all()
        proposals = h.dreaming.dream()
        assert proposals and h.store.snapshot_all() == before
        created = h.dreaming.approve(proposals[0]['id'])
        if created:
            assert created['layer'] == 'long_term' and created['derivedFrom']
    else:
        pytest.fail(f'Unimplemented vector section: {section}')
