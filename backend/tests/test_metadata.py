"""metadata.json (repo root): every path it names exists, and its agents and models match
the code and the recorded live run."""
import json
import re

from app.core import paths

ROOT = paths.REPO_ROOT
META = json.loads((ROOT / 'metadata.json').read_text(encoding='utf-8'))
_PATH = re.compile(r'^(?:backend|frontend|docs|seed|input_examples|output_examples)/[^\s<>]*$|^[A-Za-z_.-]+\.md$')


def _paths(node):
    if isinstance(node, dict):
        for value in node.values():
            yield from _paths(value)
    elif isinstance(node, list):
        for value in node:
            yield from _paths(value)
    elif isinstance(node, str) and _PATH.match(node):
        yield node


def _trace(name):
    return [json.loads(line) for line in (ROOT / 'output_examples' / name).read_text(encoding='utf-8').splitlines()]


def test_every_path_exists():
    found = sorted(set(_paths(META)))
    assert len(found) >= 30
    assert [p for p in found if not (ROOT / p).exists()] == []


def test_commands_use_existing_files():
    """Repository files named in the commands exist (the venv is created by the reader)."""
    files = [t for key in ('install', 'cli', 'http') for t in META['run'][key].split()
             if '/' in t and not t.startswith('backend/.venv/')]
    assert 'backend/run.py' in files and 'input_examples/01_bermuda.json' in files
    assert [f for f in files if not (ROOT / f).exists()] == []


def test_agents_match_the_traces():
    names = {a['name'] for a in META['agents']}
    traced = {r['agent_name'] for r in _trace('01_bermuda.live_nemotron.trace.jsonl') + _trace('04_benin.trace.jsonl')}
    assert names == traced - {'MeterlessGenerator'}
    for agent in META['agents']:
        assert agent['name'] in (ROOT / agent['code']).read_text(encoding='utf-8'), agent


def test_models_match_the_recorded_live_run():
    served = {r['input_summary']['role']: (r['requested_model'], r['served_model'])
              for r in _trace('01_bermuda.live_nemotron.trace.jsonl') if r['agent_name'] == 'MeterlessGenerator'}
    nemotron = META['sponsor_technology']['nvidia_nemotron']
    assert {role: model for role, (_, model) in served.items()} == nemotron['served_in_recorded_run']
    assert all(requested in nemotron['use'] for requested, _ in served.values())
