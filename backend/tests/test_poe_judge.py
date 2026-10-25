"""NemotronJudge (app/agents/poe_judge.py): an advisory critic that never writes evidence.

Runs use the real pipeline on the sample fixture. Where the judge must answer, the
generator is replaced by a stub that answers role="judge" calls as Nightshift would;
the brief keeps its deterministic sample path.
"""
import asyncio
import json
import os
from pathlib import Path

import pytest

from app.adapters import evidence_store
from app.agents import poe_judge
from app.agents.evaluator import evaluate
from app.core import generator
from app.pipeline import run_pipeline as pipeline

CREDENTIAL_ENV = ('ZETARIS_API_KEY', 'ZETARIS_ORG_ID', 'ZETARIS_REST_URL', 'METERLESS_BASE_URL',
                  'METERLESS_RUNTIME_TOKEN', 'METERLESS_MODEL', 'MODEL_BASE_URL', 'MODEL_API_KEY',
                  'MODEL_NAME', 'NVIDIA_API_KEY')
ANTIGUA = 'Antigua and Barbuda'
DEEP_WATER = 'Deep water Harbor'
ST_GEORGES = 'Port of St. George’s'


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv('HMEM_DIR', str(tmp_path / 'hmem'))
    monkeypatch.setenv('TRACE_LOG_PATH', str(tmp_path / 'trace.jsonl'))
    monkeypatch.setenv('TRACE_STDOUT', '0')
    monkeypatch.setenv('SAMPLE_MODE', 'true')
    for name in CREDENTIAL_ENV:
        monkeypatch.delenv(name, raising=False)
    return tmp_path


@pytest.fixture
def live_judge(monkeypatch):
    """Returns (set_answer, calls). set_answer(fn) turns SAMPLE_MODE off, takes Mongo down
    (stored evidence then comes from the snapshots) and installs a stub generator whose
    judge answer is fn(prompt). Runs before set_answer are plain sample-mode baselines."""
    calls, answer = [], {}

    def set_answer(fn):
        answer['fn'] = fn
        monkeypatch.delenv('SAMPLE_MODE', raising=False)
        monkeypatch.setattr(evidence_store, '_mongo_records', mongo_down)
        monkeypatch.setattr(generator, 'generate', generate)

    def mongo_down(mrgid):
        raise ConnectionError('mongo down')

    async def generate(prompt, system=None, *, json_mode=False, role='json', run_id=None,
                       sample_fn=None, model=None):
        calls.append(dict(role=role, run_id=run_id, prompt=prompt))
        if role == 'judge':
            return dict(text='{}', parsed=answer['fn'](prompt), model='nvidia/nemotron-test',
                        provider='nightshift', run_id=run_id, sample=False, status='success', duration_ms=1.0)
        return dict(text=sample_fn(prompt, system), model='caller-sample-fn', provider='sample',
                    run_id=run_id, sample=True, status='sample', duration_ms=1.0, fallback_reason='stub')

    return set_answer, calls


def run(zone, run_id=None):
    return asyncio.run(pipeline.run_pipeline(zone, run_id))


def rows(isolated):
    return [json.loads(line) for line in Path(isolated / 'trace.jsonl').read_text(encoding='utf-8').splitlines()]


def critique(isolated):
    events = [r for r in rows(isolated) if r['agent_name'] == poe_judge.AGENT_NAME]
    assert len(events) == 1
    return events[0]


def deterministic(result):
    """What only the deterministic pipeline may decide, per port."""
    return {p['name']: (p['registry'], p['confidence'], p['verdict']) for p in result['ports']}


def snippet_quote(result, port_name, length=60):
    """A verbatim slice of a port's stored official evidence snippet."""
    port = next(p for p in result['ports'] if p['name'] == port_name)
    snippet = ' '.join(port['registry']['official_evidence'][0]['snippet'].split())
    return snippet[10:10 + length]


# ---------------------------------------------------------------------------
# Skipped: no provider call, no change
# ---------------------------------------------------------------------------
def test_skipped_in_sample_mode_without_a_provider_call(isolated, monkeypatch):
    roles = []
    real = generator.generate

    async def spy(*args, **kwargs):
        roles.append(kwargs.get('role'))
        return await real(*args, **kwargs)

    monkeypatch.setattr(generator, 'generate', spy)
    result = run('Bermuda', 'judge-sample')
    event = critique(isolated)
    assert event['status'] == 'skipped' and event['reason'] == 'SAMPLE_MODE=true'
    assert event['run_id'] == 'judge-sample' and event['handoff'] == {'from': 'NemotronJudge', 'to': 'EvaluatorAgent'}
    assert roles == ['brief']  # the judge never called the generator
    assert result['judge']['status'] == 'skipped' and result['components']['judge'] == 'skipped'
    port = result['ports'][0]
    assert port['name'] == ST_GEORGES and port['judge'] is None
    assert (port['registry']['tier'], port['confidence'], port['verdict']) == ('tier1', 67, 'pass')
    assert os.environ['SAMPLE_MODE'] == 'true'


def test_skipped_when_no_provider_answers_and_sample_mode_never_set(isolated, monkeypatch):
    monkeypatch.delenv('SAMPLE_MODE')
    monkeypatch.setenv('METERLESS_BASE_URL', 'http://127.0.0.1:9/v1')  # nothing listens: offline
    monkeypatch.setattr(evidence_store, '_mongo_records',
                        lambda mrgid: (_ for _ in ()).throw(ConnectionError('mongo down')))
    result = run('Bermuda', 'judge-offline')
    event = critique(isolated)
    assert event['status'] == 'skipped'
    assert 'nightshift: offline' in event['reason'] and 'nvidia: not_configured' in event['reason']
    assert event['provider'] == 'sample' and event['judgments'] == []
    assert all(p['judge'] is None for p in result['ports'])
    assert {r['run_id'] for r in rows(isolated)} == {'judge-offline'}
    judge_calls = [r for r in rows(isolated) if r['agent_name'] == 'MeterlessGenerator'
                   and r['input_summary']['role'] == 'judge']
    assert len(judge_calls) == 1 and judge_calls[0]['status'] == 'sample'
    assert 'SAMPLE_MODE' not in os.environ


def test_skipped_without_official_evidence_text(isolated, live_judge):
    set_answer, calls = live_judge
    set_answer(lambda prompt: {'ports': []})
    result = run('Angola')  # registry match only: no official snippet to judge from
    assert critique(isolated)['reason'] == 'no official evidence text for this zone'
    assert [c['role'] for c in calls] == ['brief']
    assert all(p['judge'] is None for p in result['ports'])


def test_unusable_answer_is_skipped(isolated, live_judge):
    set_answer, _ = live_judge
    set_answer(lambda prompt: {'ports': [{'name': 'Nowhere Harbour', 'verdict': 'poe'},
                                         {'name': ST_GEORGES, 'verdict': 'definitely'}]})
    result = run('Bermuda')
    event = critique(isolated)
    assert event['status'] == 'skipped' and event['reason'] == 'no usable answer'
    assert result['ports'][0]['judge'] is None


def test_timeout_is_skipped_and_leaves_ports_unchanged(isolated, monkeypatch):
    monkeypatch.delenv('SAMPLE_MODE')

    async def slow(*args, **kwargs):
        await asyncio.sleep(5)

    monkeypatch.setattr(generator, 'generate', slow)
    ports = [dict(name=ST_GEORGES, verdict='flag', confidence=60,
                  registry=dict(tier='tier1', official_evidence=[dict(url='https://www.gov.bm/x',
                                                                      snippet='St. George’s is a port of entry.')]))]
    out = asyncio.run(poe_judge.judge_zone(dict(run_id='judge-timeout', ports=ports), 'Bermuda', timeout_s=0.05))
    assert out['judge']['status'] == 'skipped' and out['judge']['reason'] == 'no answer within 0.05s'
    assert out['ports'] == ports and out['needs_retry'] == []


# ---------------------------------------------------------------------------
# Answered: recorded, never evidence
# ---------------------------------------------------------------------------
def test_judge_never_changes_tier_validation_evidence_or_confidence(isolated, live_judge):
    baseline = {zone: deterministic(run(zone)) for zone in ('Bermuda', ANTIGUA)}
    set_answer, calls = live_judge
    # The opposite of the pipeline everywhere, with quotes that are in no evidence text.
    set_answer(lambda prompt: {'ports': [
        {'name': ST_GEORGES, 'verdict': 'not_poe', 'reason': 'only an address',
         'quoted_excerpt': 'St. George’s is closed to all foreign vessels by order.'},
        {'name': DEEP_WATER, 'verdict': 'not_poe', 'reason': 'no designation', 'quoted_excerpt': ''}]})
    for zone in ('Bermuda', ANTIGUA):
        result = run(zone)
        assert deterministic(result) == baseline[zone]
        assert all(p['judge']['verdict'] == 'not_poe' for p in result['ports'])
    assert [c['role'] for c in calls].count('judge') == 2  # one call per zone
    st_georges = deterministic(run('Bermuda'))[ST_GEORGES]
    assert (st_georges[0]['tier'], st_georges[1], st_georges[2]) == ('tier1', 67, 'pass')


def test_disagreement_is_recorded_on_the_port(isolated, live_judge):
    set_answer, _ = live_judge
    set_answer(lambda prompt: {'ports': [{'name': 'St. George’s', 'verdict': 'not_poe', 'reason': 'x',
                                          'quoted_excerpt': ''}]})
    port = run('Bermuda')['ports'][0]
    assert port['verdict'] == 'pass'
    assert port['judge'] == dict(verdict='not_poe', reason='x', quoted_excerpt='', excerpt_verified=False,
                                 disagrees=True)
    row = critique(isolated)['judgments'][0]
    assert row['port_verdict'] == 'pass' and row['disagrees'] is True
    assert (row['reason'], row['quoted_excerpt']) == ('x', '')


def test_trace_event_carries_reason_and_excerpt_cut_to_200_chars(isolated, live_judge):
    set_answer, _ = live_judge
    reason, excerpt = 'r' * 300, 'St. George’s ' * 30
    set_answer(lambda prompt: {'ports': [{'name': ST_GEORGES, 'verdict': 'poe', 'reason': reason,
                                          'quoted_excerpt': excerpt}]})
    port = run('Bermuda')['ports'][0]
    row = critique(isolated)['judgments'][0]
    assert len(row['reason']) == len(row['quoted_excerpt']) == poe_judge.TRACE_TEXT_CHARS
    assert row['reason'].endswith('…') and row['quoted_excerpt'] == excerpt.strip()[:199] + '…'
    assert port['judge']['reason'] == reason[:300]  # the port keeps the full (300-char capped) text


def test_unverified_or_verified_excerpt_never_counts_as_evidence(isolated, live_judge):
    """A tier3 port the judge calls a port of entry, quoting real official text, stays tier3."""
    set_answer, _ = live_judge
    sample = run('Bermuda')
    quote = snippet_quote(sample, ST_GEORGES)
    st_georges = next(p for p in sample['ports'] if p['name'] == ST_GEORGES)
    ely = dict(name="Ely's Harbour", lat=32.26, lon=-64.87, source_urls=[], verdict=None,
               registry=dict(tier='tier3', validation='unconfirmed - review needed', official_evidence=[],
                             matches=[], reasons=['tier3: no official evidence, no registry match']))
    state = evaluate(dict(run_id='judge-unit', ports=[dict(st_georges, source_urls=[]), ely]))
    before = {p['name']: (p['registry'], p['confidence'], p['verdict']) for p in state['ports']}
    set_answer(lambda prompt: {'ports': [
        {'name': "Ely's Harbour", 'verdict': 'poe', 'reason': 'quoted', 'quoted_excerpt': quote},
        {'name': ST_GEORGES, 'verdict': 'poe', 'reason': 'invented',
         'quoted_excerpt': 'All yachts must clear at St. George’s within one hour.'}]})
    judged = asyncio.run(poe_judge.judge_zone(state, 'Bermuda'))
    by_name = {p['name']: p for p in judged['ports']}
    assert by_name["Ely's Harbour"]['judge']['excerpt_verified'] is True
    assert by_name[ST_GEORGES]['judge']['excerpt_verified'] is False
    after = evaluate(judged)
    assert {p['name']: (p['registry'], p['confidence']) for p in after['ports']} == \
        {name: (registry, confidence) for name, (registry, confidence, _) in before.items()}
    assert by_name["Ely's Harbour"]['registry']['official_evidence'] == []
    assert next(p for p in after['ports'] if p['name'] == "Ely's Harbour")['verdict'] != 'pass'


def test_disagreement_on_a_flagged_port_triggers_one_evaluator_retry(isolated, live_judge):
    baseline = run(ANTIGUA)
    assert baseline['retries'] == 0
    set_answer, calls = live_judge
    quote = snippet_quote(baseline, DEEP_WATER)
    set_answer(lambda prompt: {'ports': [{'name': DEEP_WATER, 'verdict': 'poe', 'reason': 'designated',
                                          'quoted_excerpt': quote}]})
    (isolated / 'trace.jsonl').unlink()  # keep only the judged run's trace
    result = run(ANTIGUA, 'judge-retry')
    trace = rows(isolated)
    event = critique(isolated)
    assert event['status'] == 'ok' and event['retry_requested'] == [DEEP_WATER]
    assert event['provider'] == 'nightshift' and event['served_model'] == 'nvidia/nemotron-test'
    assert event['judgments'] == [dict(port_name=DEEP_WATER, verdict='poe', port_verdict='flag',
                                       excerpt_verified=True, disagrees=True, reason='designated',
                                       quoted_excerpt=quote)]
    retries = [r for r in trace if r['action'] == 'prepare_retry']
    assert len(retries) == 1 and retries[0]['retry_hint'] == poe_judge.RETRY_HINT
    assert any(r['action'] == 'research_port' for r in trace)
    assert result['retries'] == 1 and [c['role'] for c in calls].count('judge') == 1
    assert {r['run_id'] for r in trace} == {'judge-retry'}
    # The retry re-ran the same scoring: the verdict and score are the pipeline's.
    assert deterministic(result) == deterministic(baseline)
    assert result['ports'][0]['judge']['disagrees'] is True


# ---------------------------------------------------------------------------
# Excerpt check
# ---------------------------------------------------------------------------
TEXTS = [dict(url='https://www.gov.bm/customs', text='Vessels must report to   Customs at\nSt. George’s on arrival.')]


@pytest.mark.parametrize('excerpt, expected', [
    ("vessels must report to customs at st. george's", True),  # case, spacing and apostrophe aside
    ('"Vessels must report to Customs at St. George’s on arrival."', True),
    ('Customs at', False),  # too short to verify anything
    ('Vessels must report to Customs at Hamilton', False),
    ('', False),
    (None, False),
])
def test_excerpt_verified_only_when_inside_the_evidence_text(excerpt, expected):
    assert poe_judge.excerpt_verified(excerpt, TEXTS) is expected
