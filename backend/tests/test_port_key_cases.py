"""port_key cases shared with the frontend (poeRegistry.js portKey), so both sides key a
port the same way when /poe/verify results are merged into the fiche."""
import json

from app.agents.registry_check import port_key
from app.core import paths

CASES = paths.REPO_ROOT / 'frontend' / 'src' / 'components' / '__tests__' / 'portKeyCases.json'


def test_backend_port_key_matches_the_shared_cases():
    cases = json.loads(CASES.read_text(encoding='utf-8'))
    assert len(cases) >= 39
    assert [(c['name'], port_key(c['name'])) for c in cases] == [(c['name'], c['key']) for c in cases]


def test_shared_cases_cover_one_affix_per_end_and_every_apostrophe():
    keys = {c['name']: c['key'] for c in json.loads(CASES.read_text(encoding='utf-8'))}
    assert keys['Marina de Port Vauban'] == 'port vauban'
    assert keys['Port of the Isles'] == 'the isles'
    assert keys['St George‘s'] == keys['St George´s'] == keys["ST. GEORGE'S"] == 'saint george'
