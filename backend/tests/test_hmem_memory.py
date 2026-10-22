"""Offline memory-node integration and persistence/engine regression tests."""
import json
from copy import deepcopy
import pytest
from app.engines.hmem import HMEM
from app.engines.hmem.embeddings import embed, cosine
from app.engines.hmem.types import ACTIONS, DAY_MS
from app.agents.memory import recall_node, remember_node
from app.agents.evaluator import evaluate, finalise, prepare_retry, route_after_evaluation


@pytest.fixture(autouse=True)
def storage(tmp_path, monkeypatch):
    monkeypatch.setenv('HMEM_DIR', str(tmp_path / 'memory'))
    monkeypatch.setenv('TRACE_LOG_PATH', str(tmp_path / 'trace.jsonl'))
    monkeypatch.setenv('TRACE_STDOUT', '0')
    monkeypatch.setenv('SAMPLE_MODE', 'true')
    return tmp_path


def port(verdict='pass', **extra):
    return {**dict(name='Papeete', zone_name='French Polynesia', verdict=verdict,
                   source_urls=['https://example.gov/ports'], reasons_en=['government source']), **extra}


def test_empty_recall():
    state = recall_node(dict(ports=[port()], run_id='empty'))
    assert state['ports'][0]['memory'] == []
    assert state['trace'][0]['handoff'] == {'from': 'HMemAgent', 'to': 'EvaluatorAgent'}


def test_remember_then_recall_second_run():
    remember_node(dict(ports=[port()], run_id='first'))
    result = recall_node(dict(ports=[port()], run_id='second'))['ports'][0]['memory']
    assert len(result) == 1 and isinstance(result[0]['score'], float)
    assert 'verdict pass' in result[0]['content']
    assert result[0]['provenance']['refs'] == ['first']
    assert result[0]['source'] == 'https://example.gov/ports'
    other = port()
    other['zone_name'] = 'another zone'
    assert recall_node(dict(ports=[other]))['ports'][0]['memory'] == []


def test_verdict_flip_retains_old_and_audits():
    remember_node(dict(ports=[port()], run_id='first'))
    remember_node(dict(ports=[port('flag')], run_id='second'))
    h = HMEM()
    old, new = h.store.all()
    assert old['supersededBy'] == new['id']
    assert new['missionId'] == 'second'
    actions = [e['action'] for e in h.ledger.all()]
    assert 'conflict_detected' in actions and 'conflict_resolved' in actions
    assert 'delete' not in actions
    resolution = next(e for e in h.ledger.all() if e['action'] == 'conflict_resolved')
    assert 'supersededBy' not in resolution['previousState']
    assert resolution['newState']['supersededBy'] == new['id']


def test_same_verdict_and_source_reinforces_without_duplicate():
    remember_node(dict(ports=[port()], run_id='first'))
    state = remember_node(dict(ports=[port()], run_id='second'))
    h = HMEM()
    assert len(h.store.all()) == 1
    assert h.store.all()[0]['confidence'] == pytest.approx(.75)
    assert h.store.all()[0]['accessCount'] == 1
    assert h.ledger.history('mem-1')[-1]['details']['kind'] == 'helpful'
    assert state['trace'][-1]['outcome'] == 'reinforced' and state['trace'][-1]['memory_id'] == 'mem-1'
    remember_node(dict(ports=[port()], run_id='third'))
    assert HMEM().store.get('mem-1')['accessCount'] == 2
    assert len(recall_node(dict(ports=[port()], run_id='fourth'))['ports'][0]['memory']) == 1


def test_changed_official_source_adds_record_without_superseding():
    remember_node(dict(ports=[port()], run_id='first'))
    state = remember_node(dict(ports=[port(source_urls=['https://customs.gov.pf/yachts'])], run_id='second'))
    h = HMEM()
    first, second = h.store.all()
    assert state['trace'][-1]['outcome'] == 'created' and second['id'] == 'mem-2'
    assert 'official source https://customs.gov.pf/yachts' in second['content']
    assert not first.get('supersededBy') and first['accessCount'] == 0


def test_jsonl_persistence_and_ephemeral_tier(storage):
    h = HMEM(clock=lambda: 123)
    working = h.add(dict(content='working memory', source='test'))
    durable = h.add(dict(content='long memory', source='test', layer='long_term'))
    transient = h.add(dict(content='short memory', source='test', layer='short_term'))
    h.feedback(working['id'], 'helpful')
    restarted = HMEM()
    assert restarted.store.get(working['id'])['confidence'] == pytest.approx(.75)
    assert restarted.store.get(durable['id']) and restarted.store.get(transient['id']) is None
    assert restarted.add(dict(content='next memory', source='test'))['id'] == 'mem-4'
    for name in ('working', 'long_term', 'ledger'):
        lines = (storage / 'memory' / f'{name}.jsonl').read_text().splitlines()
        assert lines and all(isinstance(json.loads(line), dict) for line in lines)
    history = restarted.ledger.all()
    history[0]['action'] = 'tampered'
    assert restarted.ledger.all()[0]['action'] == 'create'


def test_nodes_and_evaluator_share_trace(storage, monkeypatch, capsys):
    monkeypatch.setenv('TRACE_STDOUT', '1')
    p = port()
    p['source_urls'] = []
    state = recall_node(dict(ports=[p], run_id='e2e-memory'))
    state = evaluate(state)
    while route_after_evaluation(state) == 'retry':
        state = evaluate(prepare_retry(state))
    state = remember_node(finalise(state))
    assert len(state['ports']) == 1 and state['ports'][0]['verdict'] == 'flag'
    entries = [json.loads(line) for line in (storage / 'trace.jsonl').read_text().splitlines()]
    assert entries == state['trace']
    assert entries == [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert {e['agent_name'] for e in entries} == {'HMemAgent', 'EvaluatorAgent'}
    assert {e['run_id'] for e in entries} == {'e2e-memory'}
    assert all({'timestamp', 'agent_name', 'run_id', 'action', 'input_summary'} <= e.keys() for e in entries)
    assert entries[-1]['handoff'] == {'from': 'EvaluatorAgent', 'to': 'HMemAgent'}
    assert any(e['action'] == 'prepare_retry' for e in entries)


def test_recall_top_five_and_no_input_mutation():
    original = dict(ports=[port()], run_id='first')
    before = deepcopy(original)
    for i in range(7):  # distinct official sources, so each run adds a record
        remember_node(dict(ports=[port(source_urls=[f'https://port{i}.gov/list'])], run_id=f'run-{i}'))
    recalled = recall_node(original)
    assert original == before
    assert len(recalled['ports'][0]['memory']) == 5


def test_reject_unfinalised_and_unsafe_run_id():
    with pytest.raises(ValueError, match='finalised'):
        remember_node(dict(ports=[port('retry')]))
    with pytest.raises(ValueError, match='run_id'):
        recall_node(dict(ports=[], run_id='../escape'))
    assert HMEM().store.all() == []


def test_engine_mining_and_embedding():
    h = HMEM(persist_dir=None)
    mined = h.mine('user_correction', 'I prefer python for all scripting tasks. Tiny.')
    assert len(mined) == 1 and mined[0]['layer'] == 'short_term'
    assert mined[0]['provenance']['origin'] == 'user_correction'
    assert embed('Python!') == embed('python')
    assert len(embed('python')) == 64
    assert cosine(embed('python'), embed('python')) == pytest.approx(1)
    model = HMEM(persist_dir=None, miner_fn=lambda prompt: '["Always use Python for scripts"]')
    assert model.mine('chat_message', 'text')[0]['layer'] == 'working'
    assert model.mining.mine_document('guide', 'text')[0]['source'] == 'document:guide'


def test_sleep_backup_and_dream_rejection():
    now = [0]
    h = HMEM(clock=lambda: now[0], persist_dir=None)
    h.add(dict(content='prefer short bullet answers', type='preference', source='test'))
    h.add(dict(content='prefer python for scripting', type='preference', source='test'))
    before = h.store.snapshot_all()
    proposals = h.dreaming.dream()
    h.dreaming.reject(proposals[0]['id'])
    assert h.store.snapshot_all() == before
    with pytest.raises(ValueError):
        h.dreaming.approve(proposals[0]['id'])
    now[0] += 40 * DAY_MS
    report = h.sleep.execute()
    h.sleep.restore(report['backupId'])
    assert h.store.all() == before['records']
    assert h.ledger.all()[-1]['action'] == 'restore'
    assert len(ACTIONS) == 17


def test_auto_resolution_gate_and_no_deletion():
    h = HMEM(clock=lambda: 1750000000000, persist_dir=None)
    a = h.add(dict(content='a', source='test', confidence=1))
    b = h.add(dict(content='b', source='test', confidence=0))
    conflict = h.conflicts.register(a, b, 'test', .1)
    assert h.conflicts.auto_resolve(conflict) == 'queued'
    conflict['confidence'] = 1
    a['accessCount'] = 10
    assert h.conflicts.auto_resolve(conflict) == 'resolved'
    assert b['supersededBy'] == a['id'] and len(h.store.all()) == 2


def test_reference_embedding_and_exact_hybrid_score():
    # Golden output executed against upstream index.ts at 1742dec56a66e58e.
    vector = embed('Python docker')
    assert {i: v for i, v in enumerate(vector) if v} == pytest.approx({
        13: -0.6178215519319035, 23: -0.7863183388224225})
    h = HMEM(clock=lambda: 1750000000000, persist_dir=None)
    assert h.query('nothing')['context'] == ''
    m = h.add(dict(content='Deploy Python API on Monday', source='test', type='factual',
                   layer='long_term', confidence=.8, tags=['python']))
    assert h.retrieval.score_one(m, 'Python API deployment') == pytest.approx(0.39333130165364194)
    result = h.query('Python API deployment')
    assert result['trace']['scores'] == {'mem-1': .3933}
    assert result['context'] == ('[MEMORY CONTEXT]\n## tech\n'
        '- [LT] Deploy Python API on Monday (entities: python, deploy, api, monday) <mem-1>\n'
        '[/MEMORY CONTEXT]')


def test_latest_feedback_after_double_digit_id_restart():
    def sourced(i, verdict='pass'):
        return port(verdict, source_urls=[f'https://port{i}.gov/list'])
    for i in range(12):  # distinct official sources: mem-1 .. mem-12, all active
        remember_node(dict(ports=[sourced(i)], run_id=f'run-{i}'))
    remember_node(dict(ports=[sourced(11)], run_id='repeat'))  # unchanged: reinforce the latest
    h = HMEM()
    assert len(h.store.all()) == 12
    assert h.store.get('mem-12')['confidence'] == pytest.approx(.75)
    assert h.store.get('mem-11')['confidence'] == pytest.approx(.7)
    assert h.store.get('mem-2')['confidence'] == pytest.approx(.7)
    remember_node(dict(ports=[sourced(11, 'flag')], run_id='flip'))
    h = HMEM()
    assert len(h.store.all()) == 13
    assert all(h.store.get(f'mem-{i}')['supersededBy'] == 'mem-13' for i in range(1, 13))


def _held_by_another_thread(try_acquire):
    """Run try_acquire() in a fresh thread; True if the lock was free there."""
    import threading
    result = []
    worker = threading.Thread(target=lambda: result.append(try_acquire()))
    worker.start()
    worker.join(5)
    return result[0]


def _rlock_free():
    from app.agents import memory
    if memory._LOCK.acquire(blocking=False):
        memory._LOCK.release()
        return True
    return False


def test_thread_only_lock_without_filelock_or_fcntl(monkeypatch):
    import sys
    from app.agents import memory
    monkeypatch.setattr(memory, 'HAS_FILELOCK', False)
    monkeypatch.setitem(sys.modules, 'fcntl', None)  # `import fcntl` now raises ImportError
    remember_node(dict(ports=[port()], run_id='thread-only'))
    assert len(recall_node(dict(ports=[port()], run_id='thread-only-2'))['ports'][0]['memory']) == 1
    with memory._engine():
        assert _held_by_another_thread(_rlock_free) is False  # held while the engine is open
    assert _held_by_another_thread(_rlock_free) is True  # released afterwards
    with pytest.raises(RuntimeError):
        with memory._engine():
            raise RuntimeError('node failure')
    assert _held_by_another_thread(_rlock_free) is True  # released after an exception too


def test_fcntl_lock_released_exactly_once(monkeypatch, storage):
    fcntl = pytest.importorskip('fcntl')
    from app.agents import memory
    monkeypatch.setattr(memory, 'HAS_FILELOCK', False)
    closes = []
    original = memory._acquire_lock

    class CountingLock:
        def __init__(self, handle):
            self.handle = handle

        def close(self):
            closes.append(1)
            self.handle.close()

    monkeypatch.setattr(memory, '_acquire_lock', lambda directory: CountingLock(original(directory)))
    remember_node(dict(ports=[port()], run_id='fcntl'))
    assert closes == [1]
    with (storage / 'memory' / '.lock').open('a') as other:  # free again for another descriptor
        fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(other, fcntl.LOCK_UN)


def test_filelock_path_holds_and_releases(monkeypatch, storage):
    filelock = pytest.importorskip('filelock')
    from app.agents import memory
    monkeypatch.setattr(memory, 'HAS_FILELOCK', True)
    lock_path = str(storage / 'memory' / '.lock')

    def free():
        try:
            filelock.FileLock(lock_path).acquire(timeout=0).lock.release()
            return True
        except filelock.Timeout:
            return False

    remember_node(dict(ports=[port()], run_id='filelock'))
    with memory._engine():
        assert _held_by_another_thread(free) is False
    assert _held_by_another_thread(free) is True
