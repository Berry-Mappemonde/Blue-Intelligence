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
