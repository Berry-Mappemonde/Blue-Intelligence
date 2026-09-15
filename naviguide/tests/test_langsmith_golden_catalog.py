"""Le catalogue des trajets or reste cohérent."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "langsmith_golden_legs.json"

_REQUIRED_LEG = ("id", "project", "agent", "title", "look_for", "inputs")
_AGENTS = frozenset({"meteo", "guard", "custom", "pirate", "orchestrator"})


def test_catalog_shape():
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    assert data["version"] == 1
    ids = [leg["id"] for leg in data["legs"]]
    assert len(ids) == len(set(ids))
    for leg in data["legs"]:
        for key in _REQUIRED_LEG:
            assert key in leg, f"{leg.get('id')} manque {key}"
        assert leg["agent"] in _AGENTS
        assert leg["project"].startswith("naviguide-")
        assert leg["look_for"]
        if leg["agent"] == "orchestrator":
            assert len(leg["inputs"]["waypoints"]) >= 2
        else:
            assert "from_stop" in leg["inputs"]
            assert "to_stop" in leg["inputs"]
    based = {case["based_on"] for case in data["eval_cases"]}
    assert based <= set(ids)


def test_cli_list_and_check(capsys):
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    sys.path.insert(0, str(ROOT))
    from langsmith_golden_legs import main

    assert main(["--list"]) == 0
    listed = capsys.readouterr().out
    assert "meteo-mayotte-reunion-janvier" in listed

    assert main(["--check"]) == 0
    checked = capsys.readouterr().out
    assert "Contrôle LangSmith" in checked
    assert "activé" in checked
