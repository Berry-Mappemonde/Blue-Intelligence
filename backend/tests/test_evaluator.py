"""EvaluatorAgent checking node — no network, three hand-made ports."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent.evaluator import evaluate, route_after_evaluation
from app.services.poe_confidence import score_port

# High score, real source, map agreed → pass.
PASS_PORT = {
    "name": "Papeete",
    "extraction_engine": "catalog",
    "extraction_agreement": True,
    "claude_agreement": True,
    "validated": True,
    "spatial_kind": "in_eez",
    "geocode_agree": True,
    "lat": -17.5,
    "lon": -149.5,
    "note": "catalogue officiel (nom + coordonnées dans la source)",
    "source_urls": ["https://douane.gouv.fr/x"],
    "osm_confidence": 0.9,
}

# Score can exceed 60, but geocodeurs disagree → flag.
FLAG_PORT = {
    "name": "Hamburg",
    "extraction_engine": "catalog",
    "extraction_agreement": True,
    "validated": True,
    "spatial_kind": "in_eez",
    "geocode_agree": False,
    "lat": 53.54,
    "lon": 9.99,
    "source_urls": ["https://zoll.de/x"],
    "osm_confidence": 0.9,
}

# Synthesis only, no coords → retry (confidence < 40).
RETRY_PORT = {
    "name": "Somewhere",
    "from_synthesis": True,
    "extraction_engine": "llm",
    "validated": False,
    "spatial_kind": "rejected",
    "source_urls": [],
}


def _by_name(ports):
    return {p["name"]: p for p in ports}


def test_sample_ports_land_in_expected_score_bands():
    assert score_port(PASS_PORT)["confidence"] > 60
    assert score_port(FLAG_PORT)["confidence"] > 60
    assert score_port(RETRY_PORT)["confidence"] < 40


def test_evaluate_assigns_pass_flag_retry():
    state = evaluate({
        "ports": [PASS_PORT, FLAG_PORT, RETRY_PORT],
        "retry_count": 0,
        "trace": [],
    })
    by_name = _by_name(state["ports"])
    assert by_name["Papeete"]["verdict"] == "pass"
    assert by_name["Hamburg"]["verdict"] == "flag"
    assert by_name["Somewhere"]["verdict"] == "retry"
    assert [p["name"] for p in state["needs_retry"]] == ["Somewhere"]
    assert by_name["Papeete"]["confidence"] > 60
    assert any("géocodeurs" in r or "carte" in r for r in by_name["Hamburg"]["reasons"])
    assert any("synthèse" in r.lower() or "source non réelle" in r
               for r in by_name["Somewhere"]["reasons"])


def test_trace_is_one_json_entry_per_port():
    state = evaluate({
        "ports": [PASS_PORT, FLAG_PORT, RETRY_PORT],
        "retry_count": 0,
        "trace": [],
    })
    assert len(state["trace"]) == 3
    parsed = [json.loads(entry) for entry in state["trace"]]
    assert [e["port_name"] for e in parsed] == ["Papeete", "Hamburg", "Somewhere"]
    assert [e["verdict"] for e in parsed] == ["pass", "flag", "retry"]
    for entry in parsed:
        assert entry["agent_name"] == "EvaluatorAgent"
        assert entry["action"] == "evaluate_port"
        assert "timestamp" in entry
        assert isinstance(entry["reasons"], list)


def test_route_after_evaluation():
    retrying = evaluate({
        "ports": [RETRY_PORT],
        "retry_count": 0,
        "trace": [],
    })
    assert route_after_evaluation(retrying) == "retry"
    retrying["retry_count"] = 1
    assert route_after_evaluation(retrying) == "retry"
    retrying["retry_count"] = 2
    assert route_after_evaluation(retrying) == "done"

    done = evaluate({
        "ports": [PASS_PORT, FLAG_PORT],
        "retry_count": 0,
        "trace": [],
    })
    assert route_after_evaluation(done) == "done"
