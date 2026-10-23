"""Integration of the agent modules into the production PoE pipeline (PR #33)."""
import asyncio
from unittest.mock import AsyncMock

import pytest

from app.services import poe_pipeline


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv('SAMPLE_MODE', 'true')
    monkeypatch.setenv('HMEM_DIR', str(tmp_path / 'hmem'))
    monkeypatch.setenv('TRACE_LOG_PATH', str(tmp_path / 'trace.jsonl'))
    monkeypatch.setenv('TRACE_STDOUT', '0')
    for name in ('NVIDIA_API_KEY', 'ZETARIS_API_KEY', 'ZETARIS_ORG_ID', 'METERLESS_RUNTIME_TOKEN', 'MODEL_API_KEY'):
        monkeypatch.delenv(name, raising=False)
    return tmp_path


BERMUDA = {'name': 'Bermuda', 'mrgid': 8493, 'iso2': 'BM'}


def extract_with(monkeypatch, ports):
    """Patch the LLM extractor and local NER; return the extractor mock."""
    extractor = AsyncMock(return_value=[dict(p) for p in ports])
    monkeypatch.setattr(poe_pipeline, 'extract_ports', extractor)
    import app.core.ml as ml
    monkeypatch.setattr(ml, 'extract_entities', lambda text: [])
    return extractor


def test_extract_ports_llm_runs_extraction_once_then_cross_references_zetaris(monkeypatch):
    extractor = extract_with(monkeypatch, [{'name': 'Port of St. George’s', 'city': None},
                                           {'name': 'Invented Harbour', 'city': None}])
    ports = asyncio.run(poe_pipeline.extract_ports_llm('Ports of entry: St. George.', BERMUDA, lambda m: None))
    assert extractor.await_count == 1  # previously: UnboundLocalError before any extraction
    by_name = {p['name']: p for p in ports}
    assert by_name['Port of St. George’s']['zetaris_validation'] == 'official'
    assert by_name['Port of St. George’s']['lat'] == pytest.approx(32.381, abs=1e-3)  # official coordinates
    assert by_name['Invented Harbour']['zetaris_validation'] == 'unofficial - review needed'


def test_extract_ports_llm_with_a_run_recorder_uses_its_run_id(monkeypatch):
    extract_with(monkeypatch, [{'name': 'Port of St. George’s', 'city': None}])
    events = []

    class Recorder:  # same shape as app.core.events.ZoneRecorder (no .get)
        _rec = type('RunRecorder', (), {'run_id': 'run-20261023'})()

        async def event(self, step, **payload):
            events.append((step, payload))

    seen = {}
    real = poe_pipeline.validate_ports_zetaris

    async def spy(zone_name, run_id, settings=None):
        seen['run_id'] = run_id
        return await real(zone_name, run_id, settings)

    monkeypatch.setattr(poe_pipeline, 'validate_ports_zetaris', spy)
    asyncio.run(poe_pipeline.extract_ports_llm('text', BERMUDA, lambda m: None, rec=Recorder()))
    assert seen['run_id'] == 'run-20261023'
    assert ('zetaris_crossref', {'mode': 'sample', 'official_count': 1, 'matched': ['Port of St. George’s']}) in events


def verify_client():
    """The formalities router alone (no Mongo startup hooks), as mounted by app.main."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routers import formalities
    app = FastAPI()
    app.include_router(formalities.router)
    return TestClient(app)


def test_poe_verify_runs_the_pipeline_in_sample_mode(isolated):
    from pathlib import Path
    response = verify_client().post('/api/poe/verify', json={'zone_name': 'Bermuda', 'mrgid': 8493})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['zone_name'] == 'Bermuda' and body['mrgid'] == 8493 and body['error'] is None
    assert [p['name'] for p in body['validated_ports']] == ['Port of St. George’s']
    assert body['non_validated_ports'] == [] and body['zetaris_mode'] == 'sample'
    assert body['nemotron_status'] == {'provider': 'sample', 'model': 'caller-sample-fn',
                                       'nemotron': False, 'fallback_reason': 'SAMPLE_MODE=true'}
    assert body['brief'].startswith('Clearance brief: Bermuda')
    trace = Path(body['trace_path'])
    assert trace == isolated / 'trace.jsonl' and trace.is_file()
    assert body['run_id'] in trace.read_text()


def test_poe_verify_rejects_a_missing_zone():
    assert verify_client().post('/api/poe/verify', json={}).status_code == 422
    assert verify_client().post('/api/poe/verify', json={'zone_name': '  '}).status_code == 422


@pytest.mark.parametrize('written', ["Port of St. George's", 'PORT OF ST GEORGES', 'port of st. george’s'])
def test_cross_reference_matches_names_without_case_accents_or_punctuation(written):
    zetaris = asyncio.run(poe_pipeline.validate_ports_zetaris('Bermuda', 'match-test'))
    out = asyncio.run(poe_pipeline.cross_reference_zetaris([{'name': written}], BERMUDA, zetaris))
    assert out[0]['zetaris_validation'] == 'official'


def test_name_key_strips_accents():
    assert poe_pipeline.zetaris_name_key('Luka Brčko') == poe_pipeline.zetaris_name_key('LUKA BRCKO') == 'luka brcko'
    zetaris = asyncio.run(poe_pipeline.validate_ports_zetaris('Bosnia and Herzegovina', 'accent-test'))
    out = asyncio.run(poe_pipeline.cross_reference_zetaris(
        [{'name': 'LUKA BRCKO'}], {'name': 'bosnia and herzegovina'}, zetaris))
    assert out[0]['zetaris_validation'] == 'official'


def test_validate_ports_zetaris_live_failure_falls_back_to_sample(monkeypatch, isolated):
    import json
    from app.adapters import zetaris
    monkeypatch.setenv('SAMPLE_MODE', 'false')
    monkeypatch.setenv('ZETARIS_API_KEY', 'test-key')
    monkeypatch.setenv('ZETARIS_ORG_ID', '1')
    monkeypatch.setenv('ZETARIS_REST_URL', 'http://127.0.0.1:9/api/v1.0')  # nothing listens
    monkeypatch.setattr(zetaris.time, 'sleep', lambda seconds: None)
    result = asyncio.run(poe_pipeline.validate_ports_zetaris('Bermuda', 'zetaris-down'))
    assert result['mode'] == 'fallback' and result['official_count'] == 1
    rows = [json.loads(line) for line in (isolated / 'trace.jsonl').read_text().splitlines()]
    assert [r.get('status') for r in rows if r['agent_name'] == 'ZetarisAdapter'] == ['error', 'fallback', 'ok']
    assert 'test-key' not in (isolated / 'trace.jsonl').read_text()


ZONE_GEOCODE = {'mrgid': 8493, 'name': 'Bermuda', 'iso2': 'BM', 'sovereign': 'United Kingdom', 'geometry': None}
OFFICIAL = 'https://www.customs.gov.bm/yachts'


def run_extract_and_geocode(monkeypatch, used_sources):
    async def fake_extract(context, zone, log, rec=None, catalog_text=None, settings=None):
        return [{'name': 'Port of St. George’s', 'geocodeable': False, 'extraction_engine': 'llm'}]
    monkeypatch.setattr(poe_pipeline, 'extract_ports_llm', fake_extract)
    from app.services import listing_ref  # community listing: slow fuzzy matching, irrelevant here
    monkeypatch.setattr(listing_ref, 'project_listing', lambda: {'ports': []})
    return asyncio.run(poe_pipeline._extract_and_geocode(ZONE_GEOCODE, 'ctx', used_sources, lambda m: None, settings={}))


def remember_official_verification():
    from app.agents.memory import remember_node
    remember_node({'run_id': 'earlier-run', 'ports': [{
        'name': 'Port of St. George’s', 'zone_name': 'Bermuda', 'verdict': 'flag',
        'source_urls': [OFFICIAL], 'reasons_en': ['government source']}]})


def hmem_rows(trace_file):
    import json
    return [json.loads(l) for l in trace_file.read_text().splitlines() if '"HMemAgent"' in l]


def test_weak_port_reuses_a_remembered_official_source(monkeypatch, isolated):
    forum = [{'url': 'https://sailing-forum.example/bermuda', 'official': False}]
    control = run_extract_and_geocode(monkeypatch, forum)[0]  # empty memory
    assert control['confidence_parts']['source'] < 30 and 'source_provenance' not in control
    remember_official_verification()
    doc = run_extract_and_geocode(monkeypatch, forum)[0]
    assert doc['source_urls'] == ['https://sailing-forum.example/bermuda', OFFICIAL]
    assert doc['source_provenance'] == {OFFICIAL: 'hmem'} and doc['hmem_memory_id']
    assert doc['confidence_parts']['source'] == 30 and doc['confidence'] > control['confidence']
    actions = [(r['action'], r.get('outcome')) for r in hmem_rows(isolated / 'trace.jsonl')]
    assert ('recall', None) in actions and actions[-1][0] == 'remember'


def test_port_with_a_state_source_does_not_borrow_from_memory(monkeypatch, isolated):
    remember_official_verification()
    doc = run_extract_and_geocode(monkeypatch, [{'url': 'https://www.gov.bm/ports', 'official': True}])[0]
    assert 'source_provenance' not in doc and doc['memories_recalled'] == 1
    assert doc['confidence_parts']['source'] == 30


def test_repeated_pipeline_runs_reinforce_instead_of_duplicating(monkeypatch, isolated):
    from app.engines.hmem import HMEM
    sources = [{'url': 'https://www.gov.bm/ports', 'official': True}]
    run_extract_and_geocode(monkeypatch, sources)
    run_extract_and_geocode(monkeypatch, sources)
    records = HMEM(persist_dir=isolated / 'hmem').store.all()
    assert len(records) == 1 and records[0]['confidence'] > 0.7  # one record, reinforced by helpful feedback
    outcomes = [r['outcome'] for r in hmem_rows(isolated / 'trace.jsonl') if r['action'] == 'remember']
    assert outcomes == ['created', 'reinforced']
