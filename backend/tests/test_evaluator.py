"""EvaluatorAgent checking node — no network, three hand-made ports."""
from __future__ import annotations

import json
from copy import deepcopy
from inspect import getsourcefile
from pathlib import Path
from uuid import UUID

import pytest

from app.agents import evaluator
from app.agents.evaluator import (
    RETRY_LIMIT,
    evaluate,
    finalise,
    prepare_retry,
    route_after_evaluation,
)
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


@pytest.fixture(autouse=True)
def trace_log_path(tmp_path, monkeypatch):
    path = tmp_path / "logs" / "trace.jsonl"
    monkeypatch.setenv("TRACE_LOG_PATH", str(path))
    return path


def _by_name(ports):
    return {p["name"]: p for p in ports}


def test_sample_ports_land_in_expected_score_bands():
    assert score_port(PASS_PORT)["confidence"] > 60
    assert score_port(FLAG_PORT)["confidence"] > 60
    assert score_port(RETRY_PORT)["confidence"] < 40


def test_evaluator_reuses_the_original_backend_scorer():
    repo_root = Path(__file__).resolve().parents[2]
    assert evaluator.score_port is score_port
    assert Path(getsourcefile(score_port)).resolve() == (
        repo_root / "backend" / "app" / "services" / "poe_confidence.py"
    )


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
    parsed = state["trace"]
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


@pytest.mark.parametrize("retry_count", [RETRY_LIMIT, RETRY_LIMIT + 1])
def test_finalise_flags_unconfirmed_ports_without_dropping_any(retry_count):
    state = evaluate({
        "ports": [PASS_PORT, FLAG_PORT, RETRY_PORT],
        "retry_count": retry_count,
        "request_id": "test-request",
    })
    before = deepcopy(state)
    assert route_after_evaluation(state) == "done"

    done = finalise(state)

    assert state == before
    assert done["request_id"] == "test-request"
    assert done["retry_count"] == retry_count
    assert [p["name"] for p in done["ports"]] == ["Papeete", "Hamburg", "Somewhere"]
    assert done["ports"][:2] == state["ports"][:2]
    flagged = done["ports"][2]
    assert flagged["verdict"] == "flag"
    assert flagged["reasons"][:-1] == state["ports"][2]["reasons"]
    assert flagged["reasons_en"][:-1] == state["ports"][2]["reasons_en"]
    assert flagged["reasons_en"][-1] == "unconfirmed after max retries"
    assert done["needs_retry"] == []
    assert route_after_evaluation(done) == "done"
    assert done["trace"][:-1] == state["trace"]
    assert done["trace"][-1]["action"] == "finalise_port"
    assert done["trace"][-1]["verdict"] == "flag"
    assert done["trace"][-1]["reasons"] == flagged["reasons_en"]
    assert finalise(done) == done


@pytest.mark.parametrize("ports", [[], [PASS_PORT, FLAG_PORT]])
def test_finalise_without_retries_keeps_evaluated_state(ports):
    state = evaluate({"ports": ports})
    assert route_after_evaluation(state) == "done"
    assert finalise(state) == state


@pytest.mark.parametrize("initial", [None, 0, 1, "1"])
def test_prepare_retry_increments_without_mutating_input(initial):
    state = evaluate({"ports": [PASS_PORT, RETRY_PORT], "retry_count": initial})
    before = deepcopy(state)

    prepared = prepare_retry(state)

    assert state == before
    assert prepared["retry_count"] == int(initial or 0) + 1
    assert prepared["ports"] == state["ports"]
    assert prepared["needs_retry"] == state["needs_retry"]
    assert prepared["trace"][:-1] == state["trace"]
    handoff = prepared["trace"][-1]
    assert handoff["action"] == "prepare_retry"
    assert handoff["handoff"] == {"from": "EvaluatorAgent", "to": "retry"}
    assert handoff["input_summary"] == {
        "port_name": "Somewhere", "retry_count": prepared["retry_count"],
    }
    assert handoff["reasons"] == state["needs_retry"][0]["reasons_en"]


def test_prepare_retry_defaults_missing_count_to_zero():
    state = prepare_retry({})
    assert state == {"retry_count": 1, "trace": [], "run_id": state["run_id"]}
    assert UUID(state["run_id"]).version == 4


def test_retry_loop_stops_at_limit_and_preserves_ports():
    state = evaluate({"ports": [PASS_PORT, FLAG_PORT, RETRY_PORT]})
    for expected_count in range(1, RETRY_LIMIT + 1):
        assert route_after_evaluation(state) == "retry"
        state = evaluate(prepare_retry(state))
        assert state["retry_count"] == expected_count

    assert route_after_evaluation(state) == "done"
    done = finalise(state)
    assert [p["verdict"] for p in done["ports"]] == ["pass", "flag", "flag"]
    assert done["needs_retry"] == []
    assert sum(e["action"] == "prepare_retry" for e in done["trace"]) == RETRY_LIMIT


def test_evaluate_adds_english_reasons_and_preserves_french():
    state = evaluate({"ports": [PASS_PORT, FLAG_PORT, RETRY_PORT]})
    by_name = _by_name(state["ports"])
    assert by_name["Papeete"]["reasons"] == score_port(PASS_PORT)["reasons"]
    assert by_name["Papeete"]["reasons_en"] == [
        "national source not on the allowlist",
        "Claude and OpenRouter agree",
        "catalogue + LLM + NER",
        "inside the EEZ, geocoders agree",
        "OSM: port infrastructure / customs",
    ]
    assert by_name["Hamburg"]["reasons_en"] == [
        "national source not on the allowlist",
        "catalogue + LLM + NER",
        "inside the EEZ",
        "OSM: port infrastructure / customs",
        "incomplete map (missing lat/lon or geocoders disagree)",
    ]
    assert by_name["Somewhere"]["reasons_en"] == [
        "web synthesis without a source page",
        "single extractor",
        "not geocoded",
        "no direct source (empty URLs or synthesis only)",
        "incomplete map (missing lat/lon or geocoders disagree)",
    ]
    for port, entry in zip(state["ports"], state["trace"]):
        assert entry["reasons"] == port["reasons_en"]


def test_unknown_french_reason_passes_through(monkeypatch):
    unknown = "nouvelle raison non traduite"

    def score_with_unknown_reason(port):
        scored = score_port(port)
        scored["reasons"].append(unknown)
        return scored

    monkeypatch.setattr(evaluator, "score_port", score_with_unknown_reason)
    state = evaluate({"ports": [PASS_PORT]})
    assert state["ports"][0]["reasons"][-1] == unknown
    assert state["ports"][0]["reasons_en"][-1] == unknown
    assert state["trace"][0]["reasons"][-1] == unknown


def test_trace_file_and_stdout_match_state_and_append(trace_log_path, capsys):
    assert not trace_log_path.parent.exists()
    port = {**RETRY_PORT, "name": 'Port d\'Été\n"East"'}
    state = evaluate({"ports": [port], "retry_count": RETRY_LIMIT - 1})
    first_line = trace_log_path.read_text(encoding="utf-8")
    state = finalise(evaluate(prepare_retry(state)))

    saved = trace_log_path.read_text(encoding="utf-8")
    printed = capsys.readouterr().out
    assert saved.startswith(first_line)
    assert saved.endswith("\n")
    assert printed == saved
    assert len(saved.splitlines()) == 4
    assert [json.loads(line) for line in saved.splitlines()] == state["trace"]
    assert [entry["action"] for entry in state["trace"]] == [
        "evaluate_port", "prepare_retry", "evaluate_port", "finalise_port",
    ]
    assert [entry["input_summary"]["retry_count"] for entry in state["trace"]] == [
        RETRY_LIMIT - 1, RETRY_LIMIT, RETRY_LIMIT, RETRY_LIMIT,
    ]
    for entry in state["trace"]:
        assert entry["agent_name"] == "EvaluatorAgent"
        assert entry["run_id"] == state["run_id"]
        assert entry["input_summary"]["port_name"] == port["name"]
    assert state["trace"][-1]["reasons"][-1] == "unconfirmed after max retries"


def test_default_trace_path_is_root_relative(tmp_path, monkeypatch):
    repo_root = Path(__file__).resolve().parents[2]
    assert evaluator.DEFAULT_TRACE_LOG_DIR == repo_root / "logs"
    # Exercise the default without writing outside the temporary test directory.
    default_dir = tmp_path / "repo" / "logs"
    monkeypatch.setattr(evaluator, "DEFAULT_TRACE_LOG_DIR", default_dir)
    monkeypatch.delenv("TRACE_LOG_PATH")
    monkeypatch.chdir(tmp_path)
    state = evaluate({"ports": [PASS_PORT], "run_id": "demo-run_1"})
    assert state["run_id"] == "demo-run_1"
    default_path = default_dir / "trace-demo-run_1.jsonl"
    assert json.loads(default_path.read_text(encoding="utf-8")) == state["trace"][0]


def test_runs_use_separate_files_and_keep_ids_across_retries(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    monkeypatch.setattr(evaluator, "DEFAULT_TRACE_LOG_DIR", log_dir)
    monkeypatch.delenv("TRACE_LOG_PATH")
    original = {"ports": [RETRY_PORT], "retry_count": RETRY_LIMIT - 1}
    before = deepcopy(original)
    first = evaluate(original)
    second = evaluate(original)
    assert original == before
    assert UUID(first["run_id"]).version == 4
    assert UUID(second["run_id"]).version == 4
    assert first["run_id"] != second["run_id"]

    run_id = first["run_id"]
    prepared = prepare_retry(first)
    assert prepared["run_id"] == run_id
    reevaluated = evaluate(prepared)
    assert reevaluated["run_id"] == run_id
    done = finalise(reevaluated)
    assert done["run_id"] == run_id

    assert {path.name for path in log_dir.iterdir()} == {
        f"trace-{run_id}.jsonl", f'trace-{second["run_id"]}.jsonl',
    }
    for state in (done, second):
        path = log_dir / f'trace-{state["run_id"]}.jsonl'
        entries = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        assert entries == state["trace"]
        assert all(entry["run_id"] == state["run_id"] for entry in entries)


@pytest.mark.parametrize("node", [evaluate, prepare_retry, finalise])
def test_nodes_generate_run_id_even_for_empty_state(node):
    original = {}
    state = node(original)
    assert UUID(state["run_id"]).version == 4
    assert original == {}


@pytest.mark.parametrize("run_id", ["", "../outside", "a/../../outside", "a\\outside", 42])
def test_invalid_run_ids_are_rejected_before_logging(run_id, trace_log_path):
    with pytest.raises(ValueError, match="run_id"):
        evaluate({"ports": [PASS_PORT], "run_id": run_id})
    assert not trace_log_path.exists()
