"""Runnable product: fresh-clone CLI, POST /run, H-MEM research, fallbacks, bounds."""
import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.adapters import zetaris
from app.agents.evaluator import RETRY_LIMIT
from app.pipeline import run_pipeline as pipeline
from app.pipeline.api import app

REPO_ROOT = Path(__file__).resolve().parents[2]
FIRST_INPUT = sorted((REPO_ROOT / 'input_examples').glob('*.json'))[0]
AGENTS = {'ZetarisAdapter', 'HMemAgent', 'EvaluatorAgent', 'ResearchAgent', 'BriefingAgent', 'MeterlessGenerator'}
OUTPUT_KEYS = {'run_id', 'zone', 'mode', 'ports', 'summary', 'brief', 'llm', 'components', 'retries',
               'memory', 'trace_file', 'timings_ms', 'error'}
PORT_KEYS = {'name', 'verdict', 'confidence', 'reasons_en', 'sources', 'memories_recalled', 'research'}
_CREDENTIAL_ENV = ('ZETARIS_API_KEY', 'ZETARIS_ORG_ID', 'ZETARIS_REST_URL', 'METERLESS_BASE_URL',
                   'METERLESS_RUNTIME_TOKEN', 'METERLESS_MODEL', 'MODEL_BASE_URL', 'MODEL_API_KEY',
                   'MODEL_NAME', 'NVIDIA_API_KEY')


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path, request):
    monkeypatch.setenv('HMEM_DIR', str(tmp_path / 'hmem'))
    monkeypatch.setenv('TRACE_LOG_PATH', str(tmp_path / 'trace.jsonl'))
    monkeypatch.setenv('TRACE_STDOUT', '0')
    if not request.node.name.startswith('test_live_'):
        monkeypatch.setenv('SAMPLE_MODE', 'true')
        for name in _CREDENTIAL_ENV:
            monkeypatch.delenv(name, raising=False)
    return tmp_path


def trace_rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines()]


def run(zone, run_id=None, **kwargs):
    return asyncio.run(pipeline.run_pipeline(zone, run_id, **kwargs))


def assert_schema(result):
    assert set(result) == OUTPUT_KEYS
    assert result['ports'] and all(set(p) == PORT_KEYS for p in result['ports'])
    assert isinstance(result['brief'], str) and result['brief']
    assert result['llm']['provider'] and result['llm']['model']
    assert result['timings_ms']['total'] >= 0


def run_cli(tmp_path, name, hmem_dir):
    """`python backend/run.py` from the repo root with no MONGO_URL, keys or .env."""
    out, trace = tmp_path / f'{name}.json', tmp_path / f'{name}.trace.jsonl'
    env = {'PATH': os.environ.get('PATH', ''), 'HOME': str(tmp_path), 'HMEM_DIR': str(hmem_dir),
           'TRACE_LOG_PATH': str(trace)}
    proc = subprocess.run(
        [sys.executable, 'backend/run.py', '--no-dotenv', '--input', str(FIRST_INPUT.relative_to(REPO_ROOT)),
         '--output', str(out)],
        cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr
    return proc, json.loads(out.read_text(encoding='utf-8')), trace_rows(trace)


@pytest.fixture(scope='module')
def cli_runs(tmp_path_factory):
    tmp = tmp_path_factory.mktemp('cli')
    first = run_cli(tmp, 'first', tmp / 'hmem')
    second = run_cli(tmp, 'second', tmp / 'hmem')
    return first, second


def test_fresh_clone_cli_succeeds_in_sample_mode(cli_runs):
    (proc, result, _), _ = cli_runs
    assert 'SAMPLE_MODE enabled automatically' in proc.stderr
    assert_schema(result)
    assert result['error'] is None and result['mode'] == 'sample'
    assert result['components'] == {'zetaris': 'sample', 'llm': 'sample'}
    assert result['llm']['model'] == 'caller-sample-fn'
    # stdout: JSONL trace events, then the same result as pretty JSON.
    lines = proc.stdout.splitlines()
    start = lines.index('{')
    assert all(json.loads(line)['run_id'] == result['run_id'] for line in lines[:start])
    assert json.loads('\n'.join(lines[start:])) == result


def test_trace_has_every_agent_one_run_id_and_retry(cli_runs):
    (_, result, rows), _ = cli_runs
    assert AGENTS <= {r['agent_name'] for r in rows}
    assert {r['run_id'] for r in rows} == {result['run_id']}
    assert any(r['action'] == 'prepare_retry' for r in rows)
    handoffs = {(r['handoff']['from'], r['handoff']['to']) for r in rows if r.get('handoff')}
    assert {('HMemAgent', 'EvaluatorAgent'), ('ResearchAgent', 'EvaluatorAgent'),
            ('BriefingAgent', 'HMemAgent')} <= handoffs
    assert [r['agent_name'] for r in rows][0] == 'RunPipeline' and rows[-1]['action'] == 'run_end'


def test_second_run_recalls_first_run_memories(cli_runs):
    (_, first, _), (_, second, rows) = cli_runs
    assert first['memory']['recalled'] == 0
    assert second['memory']['recalled'] >= 1
    recall = [r for r in rows if r['agent_name'] == 'HMemAgent' and r['action'] == 'recall']
    assert recall and all(r['memories'] for r in recall)
    assert recall[0]['memories'][0]['provenance']['refs'] == [first['run_id']]


def test_research_uses_remembered_official_source(monkeypatch, isolated):
    official = 'https://www.customs.gov.bm/yachts'
    port = {'name': 'Port of St. George’s', 'lat': 32.38, 'lon': -64.67, 'source_urls': [official],
            'validated': True, 'geocode_source': 'nominatim', 'zone_name': 'Bermuda', 'mrgid': 8493, 'id': 'p1'}
    current = [port]
    monkeypatch.setattr(zetaris.ZetarisClient, 'get_ports', lambda self, **kw: [dict(p) for p in current])
    first = run('Bermuda', 'research-first')
    assert first['ports'][0]['research'] is None  # official source present: no retry
    current = [dict(port, source_urls=[])]  # this run's data lost the source
    second = run('Bermuda', 'research-second')
    out = second['ports'][0]
    assert out['research'] == {'outcome': 'hmem_official_source', 'url': official,
                               'memory_id': out['research']['memory_id']}
    assert out['sources'] == [{'url': official, 'provenance': 'hmem'}]
    assert out['verdict'] == 'flag' and out['confidence'] > 40 and second['retries'] == 1
    rows = [r for r in trace_rows(isolated / 'trace.jsonl') if r['run_id'] == 'research-second']
    research = [r for r in rows if r['agent_name'] == 'ResearchAgent']
    assert research[0]['outcome'] == 'hmem_official_source' and research[0]['url'] == official
    assert '(from verification memory)' in second['brief']


def test_post_run_returns_same_schema():
    client = TestClient(app)
    assert client.get('/healthz').json() == {'status': 'ok', 'sample_mode': True}
    response = client.post('/run', json={'zone_name': 'Angola', 'run_id': 'api-angola'})
    assert response.status_code == 200
    result = response.json()
    assert_schema(result)
    assert result['run_id'] == 'api-angola' and result['zone'] == 'Angola'
    assert client.post('/run', json={'zone_name': 'Angola', 'run_id': '../escape'}).status_code == 422
    assert client.post('/run', json={}).status_code == 422


def test_zetaris_live_failure_falls_back_to_sample(monkeypatch, isolated):
    monkeypatch.delenv('SAMPLE_MODE')
    monkeypatch.setenv('ZETARIS_API_KEY', 'test-key')
    monkeypatch.setenv('ZETARIS_ORG_ID', '1')
    monkeypatch.setenv('ZETARIS_REST_URL', 'http://127.0.0.1:9/api/v1.0')  # nothing listens
    monkeypatch.setenv('METERLESS_BASE_URL', 'http://127.0.0.1:9/v1')
    monkeypatch.setattr(zetaris.time, 'sleep', lambda seconds: None)
    result = run('Angola', 'zetaris-down')
    assert result['error'] is None and result['ports']
    assert result['components']['zetaris'] == 'fallback' and result['mode'] == 'sample'
    assert result['llm']['provider'] == 'sample'
    rows = trace_rows(isolated / 'trace.jsonl')
    statuses = [r.get('status') for r in rows if r['agent_name'] == 'ZetarisAdapter']
    assert statuses == ['error', 'fallback', 'ok']
    assert 'test-key' not in (isolated / 'trace.jsonl').read_text()


def test_timeout_returns_partial_result(monkeypatch):
    monkeypatch.setattr(pipeline, 'recall_node', lambda state: time.sleep(30))
    started = time.monotonic()
    result = run('Angola', 'slow-run', timeout_s=0.5)
    assert time.monotonic() - started < 5
    assert 'timed out after 0.5s during HMemAgent.recall' in result['error']
    assert result['ports'][0]['verdict'] is None and result['summary'] == {'unevaluated': 1}
    assert result['memory']['remembered'] is False


def test_retries_are_capped_and_every_port_is_finalised():
    result = run('Bermuda')
    assert result['retries'] == RETRY_LIMIT
    assert {p['verdict'] for p in result['ports']} <= {'pass', 'flag'}


def test_unknown_zone_and_invalid_input():
    result = run('Atlantis', 'no-zone')
    assert result['ports'] == [] and "no ports of entry found for zone 'Atlantis'" in result['error']
    for zone, run_id in (('', None), ('Bermuda', '../x'), (None, None)):
        with pytest.raises(ValueError):
            run(zone, run_id)


def test_sample_brief_is_built_from_port_data():
    brief = pipeline.sample_brief('Angola', [{'name': 'Porto de Luanda', 'verdict': 'flag', 'confidence': 60,
                                             'check_reasons': ['single geocoder, not cross-checked'],
                                             'source_urls': ['https://amn.gov.ao/x']}])
    assert brief.splitlines() == [
        'Clearance brief: Angola',
        'Confirmed ports of entry: none confirmed in this run.',
        'Flagged, verify before relying on them:',
        '- Porto de Luanda (confidence 60/100): single geocoder, not cross-checked. Sources: https://amn.gov.ao/x',
        pipeline.DISCLAIMER,
    ]


@pytest.mark.skipif(os.environ.get('ZETARIS_LIVE') != '1', reason='Set ZETARIS_LIVE=1 for local Zetaris')
def test_live_zone_through_real_zetaris(monkeypatch):
    monkeypatch.setenv('SAMPLE_MODE', 'false')
    result = run('Bermuda', 'live-zetaris')
    assert result['components']['zetaris'] == 'live', result['error']
    assert result['mode'] == 'live' and result['ports']


@pytest.mark.skipif(os.environ.get('NIGHTSHIFT_LIVE') != '1', reason='Set NIGHTSHIFT_LIVE=1 for local Nightshift')
def test_live_brief_served_by_nemotron(monkeypatch):
    monkeypatch.setenv('SAMPLE_MODE', 'false')
    result = run('Angola', 'live-nightshift')
    assert result['llm']['provider'] == 'nightshift', result['llm']['fallback_reason']
    assert 'nemotron' in result['llm']['model'].lower(), result['llm']['model']
    assert 'Luanda' in result['brief']
