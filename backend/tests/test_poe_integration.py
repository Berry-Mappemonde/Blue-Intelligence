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
    context = ('[SOURCE: https://www.customs.gov.bm/yachts]\nPorts of entry: St. George\'s Harbour.\n\n'
               '[SYNTHÈSE DE RECHERCHE (à recouper)]\nInvented Harbour is a port of entry.')
    ports = asyncio.run(poe_pipeline.extract_ports_llm(context, BERMUDA, lambda m: None))
    assert extractor.await_count == 1  # previously: UnboundLocalError before any extraction
    by_name = {p['name']: p for p in ports}
    # Named in the fetched official document AND listed in both registries: tier 1.
    assert by_name['Port of St. George’s']['registry']['tier'] == 'tier1'
    assert by_name['Port of St. George’s']['registry']['official_evidence'] == [
        {'url': 'https://www.customs.gov.bm/yachts', 'name_found': 'saint george'}]
    assert by_name['Port of St. George’s']['zetaris_validation'] == 'official'
    # Independent registries, not BI's seed: no coordinates on the candidate, so no distance.
    assert by_name['Port of St. George’s']['registry_matches'] == [
        {'source': 'unlocode', 'code': 'BMSGE', 'name': 'Saint George', 'distance_km': None},
        {'source': 'wpi', 'code': 'BMSGE', 'name': 'St George', 'distance_km': None, 'first_port_of_entry': 'Yes'}]
    # Only the research synthesis mentions it: not a fetched document, so tier 3.
    assert by_name['Invented Harbour']['registry']['tier'] == 'tier3'
    assert by_name['Invented Harbour']['zetaris_validation'] == 'unconfirmed - review needed'
    assert by_name['Invented Harbour']['registry_matches'] == []


def test_extract_ports_llm_with_a_run_recorder_uses_its_run_id(monkeypatch):
    extract_with(monkeypatch, [{'name': 'Port of St. George’s', 'city': None}])
    events = []

    class Recorder:  # same shape as app.core.events.ZoneRecorder (no .get)
        _rec = type('RunRecorder', (), {'run_id': 'run-20261023'})()

        async def event(self, step, **payload):
            events.append((step, payload))

    seen = {}
    real = poe_pipeline.validate_ports_zetaris

    async def spy(zone, run_id, settings=None, candidates=None):
        seen['run_id'] = run_id
        return await real(zone, run_id, settings, candidates)

    monkeypatch.setattr(poe_pipeline, 'validate_ports_zetaris', spy)
    asyncio.run(poe_pipeline.extract_ports_llm('text', BERMUDA, lambda m: None, rec=Recorder()))
    assert seen['run_id'] == 'run-20261023'
    assert ('zetaris_crossref', {
        'mode': 'sample', 'country_iso2': 'BM', 'registry_entries': 12, 'official_count': 0, 'matched': [],
        'tiers': {'tier1': [], 'tier2': [], 'tier_registered': ['Port of St. George’s'], 'tier3': []},
        'documents_with_text': 0}) in events


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
    # Seed ports carry no fetched document text: a registry match alone is never "validated".
    assert body['validated_ports'] == [] and body['zetaris_mode'] == 'sample'
    assert [p['name'] for p in body['non_validated_ports']] == ['Port of St. George’s']
    assert body['ports_by_tier'] == {'tier_registered': ['Port of St. George’s']}
    evidence = body['non_validated_ports'][0]['registry']
    assert evidence['tier'] == 'tier_registered' and evidence['validation'] == 'registered - entry status unverified'
    assert [(m['source'], m['code']) for m in evidence['matches']] == [('unlocode', 'BMSGE'), ('wpi', 'BMSGE')]
    assert all(m['distance_km'] < 1 for m in evidence['matches'])
    assert body['registry'] == {'mode': 'sample', 'country_iso2': 'BM', 'registry_entries': 12, 'official_count': 0,
                                'tiers': {'tier1': 0, 'tier2': 0, 'tier_registered': 1, 'tier3': 0},
                                'coord_mismatch_count': 0}
    assert body['nemotron_status'] == {'provider': 'sample', 'model': 'caller-sample-fn',
                                       'nemotron': False, 'fallback_reason': 'SAMPLE_MODE=true'}
    assert body['brief'].startswith('Clearance brief: Bermuda')
    assert 'Registered port, entry status unverified: listed in UN/LOCODE BMSGE' in body['brief']
    assert 'does not establish port-of-entry status' in body['brief']
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
    assert [m['code'] for m in out[0]['registry_matches']] == ['BMSGE', 'BMSGE']
    assert out[0]['registry']['tier'] == 'tier_registered'


def test_name_key_strips_accents():
    assert poe_pipeline.zetaris_name_key('Luka Brčko') == poe_pipeline.zetaris_name_key('LUKA BRCKO') == 'luka brcko'
    zetaris = asyncio.run(poe_pipeline.validate_ports_zetaris('Albania', 'accent-test'))
    out = asyncio.run(poe_pipeline.cross_reference_zetaris(
        [{'name': 'PORT OF DURRES'}, {'name': 'Luka Brčko'}], {'name': 'albania'}, zetaris))
    assert out[0]['registry']['tier'] == 'tier_registered'  # UN/LOCODE "Durrës", WPI "Durres"
    assert out[1]['registry']['tier'] == 'tier3'


def test_validate_ports_zetaris_live_failure_falls_back_to_sample(monkeypatch, isolated):
    import json
    from app.adapters import zetaris
    monkeypatch.setenv('SAMPLE_MODE', 'false')
    monkeypatch.setenv('ZETARIS_API_KEY', 'test-key')
    monkeypatch.setenv('ZETARIS_ORG_ID', '1')
    monkeypatch.setenv('ZETARIS_REST_URL', 'http://127.0.0.1:9/api/v1.0')  # nothing listens
    monkeypatch.setattr(zetaris.time, 'sleep', lambda seconds: None)
    result = asyncio.run(poe_pipeline.validate_ports_zetaris('Bermuda', 'zetaris-down'))
    assert result['mode'] == 'fallback' and result['registry_entries'] == 12
    rows = [json.loads(line) for line in (isolated / 'trace.jsonl').read_text().splitlines()]
    assert [(r['action'], r.get('status')) for r in rows if r['agent_name'] == 'ZetarisAdapter'] == [
        ('zetaris_query', 'error'), ('zetaris_fallback', 'fallback'),
        ('zetaris_query', 'ok'), ('zetaris_query', 'ok')]
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
