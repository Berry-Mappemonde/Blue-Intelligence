"""Offline adapter tests plus an explicitly opted-in local Zetaris probe."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import UUID

import httpx
import pytest

from app.adapters import zetaris
from app.adapters.zetaris import ReadOnlyViolation, ZetarisClient, ZetarisUnavailable
from app.core import paths
from app.agents.evaluator import RETRY_LIMIT, evaluate, finalise, prepare_retry, route_after_evaluation
from scripts import zetaris_setup

TEST_KEY = "adapter-test-secret-8472"


@pytest.fixture(autouse=True)
def trace_path(tmp_path, monkeypatch):
    path = tmp_path / "logs" / "trace.jsonl"
    monkeypatch.setenv("TRACE_LOG_PATH", str(path))
    monkeypatch.delenv("TRACE_STDOUT", raising=False)
    return path


@pytest.fixture
def unit_env(monkeypatch):
    monkeypatch.setenv("ZETARIS_API_KEY", TEST_KEY)
    monkeypatch.setenv("ZETARIS_ORG_ID", "test-org")
    monkeypatch.delenv("ZETARIS_REST_URL", raising=False)
    monkeypatch.setenv("SAMPLE_MODE", "false")

    def no_network(*args, **kwargs):
        raise AssertionError("Unexpected network request in an offline test")

    monkeypatch.setattr(httpx, "post", no_network)
    sleeps = []
    monkeypatch.setattr(zetaris.time, "sleep", sleeps.append)
    return sleeps


@pytest.fixture
def client(unit_env):
    return ZetarisClient(run_id="unit-run")


def _entries(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


@pytest.mark.parametrize("sql", [
    "SELECT 1", " select name FROM ports; ", "SHOW LIGHTNING DATABASES",
    "DESCRIBE ports", "EXPLAIN SELECT * FROM ports",
    "WITH ports AS (SELECT 1) SELECT * FROM ports",
    "SELECT 'DROP TABLE x'", "SELECT 'it''s DROP; DELETE'",
    'SELECT "port name", updated_at FROM ports',
    "-- harmless comment\nSELECT 1; -- end",
    "/* harmless comment */ SELECT 1", "SELECT 6 / 2, 2 * 3",
    r"SELECT 'it\'s'", r'SELECT "say \"hi\""',
    r"SELECT 'a\'; DROP TABLE x'", r"SELECT 'back\slash'",
    r"SELECT 'a\\'", r'SELECT "a\"; DROP TABLE x"',
])
def test_read_only_allowed_without_io(client, sql, trace_path):
    assert client.dry_run(sql) is True
    assert not trace_path.exists()


@pytest.mark.parametrize("sql", [
    "CREATE TABLE x (id INT)", "DROP TABLE x", "INSERT INTO x VALUES (1)",
    "UPDATE x SET id=1", "DELETE FROM x", "ALTER TABLE x ADD y INT",
    "REGISTER DATABASE x", "UPSERT INTO x VALUES (1)", "TRUNCATE TABLE x",
    "GRANT SELECT ON x TO y", "REVOKE SELECT ON x FROM y",
    "SELECT 1; DROP TABLE x", "SELECT 1; SELECT 2", "SELECT 1;;",
    "WITH x AS (DELETE FROM ports RETURNING *) SELECT * FROM x",
    "EXPLAIN cReAtE TABLE x (id INT)", "SELECT * FROM x FOR UPDATE",
    "CALL dangerous_function()", "", "-- comment only", "SELECT 'unterminated",
    "SELECT 1 /* unterminated", "SELECT 1 /*! DROP TABLE x */",
    "SELECT 1 /* DROP TABLE x */",
    r"SELECT 'a\\'; DROP TABLE x", "SELECT 'a'; DROP",
    r'SELECT "a\\"; DROP TABLE x', r"SELECT 'a\'", r'SELECT "a\"',
    r"SELECT 'it\'s'; SELECT 2", r"SELECT 'it\'s'; DROP TABLE x",
])
def test_read_only_rejected_without_io(client, sql, trace_path):
    with pytest.raises(ReadOnlyViolation):
        client.dry_run(sql)
    assert not trace_path.exists()


def test_query_rejection_is_traced_before_network(client, trace_path):
    with pytest.raises(ReadOnlyViolation, match="Forbidden SQL keyword"):
        client.query("SELECT 1; DROP TABLE x")
    assert _entries(trace_path)[0]["status"] == "rejected"
    assert _entries(trace_path)[0]["row_count"] == 0


def test_query_success_headers_body_and_trace(client, monkeypatch, trace_path, capsys):
    calls = []

    def post(url, **kwargs):
        calls.append((url, kwargs))
        return httpx.Response(200, json={"data": [["Papeete", 88], ["Hamburg", 65]]})

    monkeypatch.setattr(httpx, "post", post)
    rows = client.query("SELECT name, confidence FROM ports", limit=20)
    assert rows == [["Papeete", 88], ["Hamburg", 65]]
    assert len(calls) == 1
    url, request = calls[0]
    assert url == "http://localhost:8888/api/v1.0/sql-editor/sqls/run"
    assert request["timeout"] == 15.0
    assert request["headers"] == {
        "Authorization": f"Bearer {TEST_KEY}", "X-Org-ID": "test-org",
        "X-Request-ID": request["headers"]["X-Request-ID"], "Content-Type": "application/json",
    }
    assert UUID(request["headers"]["X-Request-ID"]).version == 4
    assert UUID(request["json"]["queryId"]).version == 4
    assert request["json"] == {
        "queryId": request["json"]["queryId"], "sql": "SELECT name, confidence FROM ports",
        "source": "SqlEditor", "limit": 20,
    }
    entry = _entries(trace_path)[0]
    assert entry["agent_name"] == "ZetarisAdapter"
    assert entry["action"] == "zetaris_query"
    assert entry["run_id"] == "unit-run"
    assert entry["input_summary"] == {"sql": "SELECT name, confidence FROM ports"}
    assert entry["row_count"] == 2
    assert entry["duration_ms"] >= 0
    assert entry["timestamp"]
    assert entry["mode"] == "live"
    assert entry["status"] == "ok"
    assert json.loads(capsys.readouterr().out) == entry


@pytest.mark.parametrize("error", [httpx.ConnectError, httpx.ReadTimeout])
def test_connection_failures_retry_then_raise_safe_error(client, unit_env, monkeypatch, trace_path, error):
    requests = []

    def post(url, **kwargs):
        requests.append(kwargs)
        raise error(f"sensitive response {TEST_KEY}")

    monkeypatch.setattr(httpx, "post", post)
    with pytest.raises(ZetarisUnavailable, match="after 3 attempts") as caught:
        client.query("SELECT 1")
    assert len(requests) == 3
    assert unit_env == [0.5, 1.0]
    assert len({r["headers"]["X-Request-ID"] for r in requests}) == 3
    assert len({r["json"]["queryId"] for r in requests}) == 3
    assert TEST_KEY not in str(caught.value)
    assert caught.value.__suppress_context__
    assert len(_entries(trace_path)) == 1
    assert _entries(trace_path)[0]["status"] == "error"
    assert TEST_KEY not in trace_path.read_text()


@pytest.mark.parametrize("statuses", [[503, 502, 200], [500, 500, 500]])
def test_server_errors_retry(client, unit_env, monkeypatch, trace_path, statuses):
    calls = []

    def post(url, **kwargs):
        status = statuses[len(calls)]
        calls.append(kwargs)
        return httpx.Response(status, json={"data": [[1]]})

    monkeypatch.setattr(httpx, "post", post)
    if statuses[-1] == 200:
        assert client.query("SELECT 1") == [[1]]
        assert _entries(trace_path)[0]["status"] == "ok"
    else:
        with pytest.raises(ZetarisUnavailable, match="HTTP 500"):
            client.query("SELECT 1")
        assert _entries(trace_path)[0]["status"] == "error"
    assert len(calls) == 3
    assert unit_env == [0.5, 1.0]
    assert len(_entries(trace_path)) == 1


def test_client_error_does_not_retry_or_expose_response(client, unit_env, monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: httpx.Response(401, text=TEST_KEY))
    with pytest.raises(ZetarisUnavailable, match="HTTP 401") as caught:
        client.query("SELECT 1")
    assert TEST_KEY not in str(caught.value)
    assert unit_env == []


@pytest.mark.parametrize("response", [
    httpx.Response(200, text="not JSON"), httpx.Response(200, json={}),
    httpx.Response(200, json={"data": [{"id": 1}]}),
])
def test_malformed_response_is_unavailable(client, monkeypatch, response, trace_path):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: response)
    with pytest.raises(ZetarisUnavailable):
        client.query("SELECT 1")
    assert _entries(trace_path)[0]["status"] == "error"


@pytest.mark.parametrize("forced_sample", [True, False])
def test_sample_mode_and_missing_key_never_call_network(unit_env, monkeypatch, trace_path, forced_sample):
    if forced_sample:
        monkeypatch.setenv("SAMPLE_MODE", "TrUe")
    else:
        monkeypatch.delenv("ZETARIS_API_KEY")
    client = ZetarisClient()
    assert UUID(client.run_id).version == 4
    assert client.mode == "sample"
    assert client.query("SELECT * FROM ports", fixture="example", limit=1) == [
        ["Papeete", "French Polynesia", "sample"],
    ]
    assert _entries(trace_path)[0]["mode"] == "sample"
    with pytest.raises(ReadOnlyViolation):
        client.query("DELETE FROM ports", fixture="example")
    assert _entries(trace_path)[-1]["status"] == "rejected"


def test_sample_connection_probe(unit_env, monkeypatch, trace_path):
    monkeypatch.setenv("SAMPLE_MODE", "true")
    result = ZetarisClient().test_connection()
    assert result == {"status": "ok", "mode": "sample", "databases": ["sample_maritime"]}
    assert [e["input_summary"]["sql"] for e in _entries(trace_path)] == [
        "SELECT 1", "SHOW LIGHTNING DATABASES",
    ]


def test_missing_sample_and_path_traversal(unit_env, monkeypatch, trace_path):
    monkeypatch.setenv("SAMPLE_MODE", "true")
    client = ZetarisClient()
    with pytest.raises(ZetarisUnavailable, match="sample fixture"):
        client.query("SELECT 1", fixture="does_not_exist")
    with pytest.raises(ValueError, match="simple name"):
        client.query("SELECT 1", fixture="../../outside")
    assert [e["status"] for e in _entries(trace_path)] == ["error", "error"]


@pytest.mark.parametrize("probe", [[[1]], [["1"]], [[1.0]], [["1.0"]]])
def test_connection_contract_and_custom_url(unit_env, monkeypatch, probe):
    monkeypatch.setenv("ZETARIS_REST_URL", "http://zetaris.test/api/v1.0/")
    calls = []

    def post(url, **kwargs):
        assert url == "http://zetaris.test/api/v1.0/sql-editor/sqls/run"
        calls.append(kwargs["json"]["sql"])
        rows = probe if len(calls) == 1 else [["maritime"], ["customs"]]
        return httpx.Response(200, json={"data": rows})

    monkeypatch.setattr(httpx, "post", post)
    assert ZetarisClient().test_connection() == {
        "status": "ok", "mode": "live", "databases": ["maritime", "customs"],
    }
    assert calls == ["SELECT 1", "SHOW LIGHTNING DATABASES"]


def test_test_connection_reports_unavailable(client, monkeypatch):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: httpx.Response(503, text=TEST_KEY))
    result = client.test_connection()
    assert result["status"] == "unavailable"
    assert result["databases"] == []
    assert TEST_KEY not in json.dumps(result)


@pytest.mark.parametrize("probe", [[], [[]], [[1, 1]], [[True]], [[None]], [["oops"]], [["NaN"]], [["Infinity"]], [["1.0000000000000001"]]])
def test_connection_rejects_invalid_numeric_probe(client, monkeypatch, probe):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: httpx.Response(200, json={"data": probe}))
    assert client.test_connection()["status"] == "unavailable"


def test_central_paths_resolve_without_config_or_credentials():
    repo = Path(__file__).resolve().parents[2]
    assert paths.REPO_ROOT == repo
    assert paths.BACKEND_DIR == repo / "backend"
    assert paths.LOGS_DIR == repo / "logs"
    assert paths.SAMPLE_DATA_DIR == repo / "backend" / "data" / "sample"
    assert zetaris.DEFAULT_TRACE_LOG_DIR == paths.LOGS_DIR
    assert zetaris.SAMPLE_DIR == paths.SAMPLE_DATA_DIR / "zetaris"
    env = {key: value for key, value in os.environ.items() if key not in {"MONGO_URL", "DB_NAME"}}
    result = subprocess.run(
        [sys.executable, "-c", "from app.core import paths; import sys; assert 'app.config' not in sys.modules; print(paths.REPO_ROOT)"],
        cwd=paths.BACKEND_DIR, env=env, text=True, capture_output=True, check=True,
    )
    assert result.stdout.strip() == str(repo)


@pytest.mark.parametrize("sql, message", [
    ("BEGIN SELECT 1; SELECT 2; END;", "BEGIN"),
    ("begin SELECT 1; end;", "BEGIN"),
    ("SELECT $$a;b$$;", "dollar-quoting"),
])
def test_setup_splitter_rejects_unsupported_sql(tmp_path, monkeypatch, sql, message):
    sql_file = tmp_path / "setup.sql"
    sql_file.write_text(sql)
    monkeypatch.setattr(zetaris_setup, "SQL_FILE", sql_file)
    with pytest.raises(ValueError, match=message):
        zetaris_setup.statements()


def test_setup_splitter_preserves_quoted_semicolons(tmp_path, monkeypatch):
    sql_file = tmp_path / "setup.sql"
    sql_file.write_text("-- comment\nSELECT 'BEGIN;a'; SELECT \"b;c\";")
    monkeypatch.setattr(zetaris_setup, "SQL_FILE", sql_file)
    assert zetaris_setup.statements() == ["SELECT 'BEGIN;a'", 'SELECT "b;c"']


def test_missing_org_fails_before_network(unit_env, monkeypatch):
    monkeypatch.delenv("ZETARIS_ORG_ID")
    with pytest.raises(ZetarisUnavailable, match="ZETARIS_ORG_ID"):
        ZetarisClient().query("SELECT 1")


def test_trace_redacts_key_truncates_sql_and_appends(client, monkeypatch, trace_path, capsys):
    monkeypatch.setattr(httpx, "post", lambda *a, **k: httpx.Response(200, json={"data": [[1]]}))
    client.query(f"SELECT '{TEST_KEY}', '{'x' * 300}'")
    first = trace_path.read_text()
    client.query("SELECT 1")
    saved = trace_path.read_text()
    printed = capsys.readouterr().out
    assert saved.startswith(first)
    assert saved == printed
    assert TEST_KEY not in saved
    entries = _entries(trace_path)
    assert len(entries) == 2
    assert len(entries[0]["input_summary"]["sql"]) == 200
    assert "[REDACTED]" in entries[0]["input_summary"]["sql"]


def test_default_trace_location_and_stdout_override(client, monkeypatch, tmp_path, capsys):
    assert zetaris.DEFAULT_TRACE_LOG_DIR == Path(__file__).resolve().parents[2] / "logs"
    monkeypatch.setattr(zetaris, "DEFAULT_TRACE_LOG_DIR", tmp_path / "repo" / "logs")
    monkeypatch.delenv("TRACE_LOG_PATH")
    monkeypatch.setenv("TRACE_STDOUT", "0")
    monkeypatch.setattr(httpx, "post", lambda *a, **k: httpx.Response(200, json={"data": []}))
    monkeypatch.chdir(tmp_path)
    assert client.query("SELECT 1") == []
    assert capsys.readouterr().out == ""
    assert _entries(tmp_path / "repo" / "logs" / "trace-unit-run.jsonl")[0]["row_count"] == 0


@pytest.mark.parametrize("limit", [0, -1, True, "10"])
def test_invalid_limits_do_not_call_network(client, limit):
    with pytest.raises(ValueError, match="positive integer"):
        client.query("SELECT 1", limit=limit)


@pytest.mark.skipif(os.environ.get("ZETARIS_LIVE") != "1", reason="Set ZETARIS_LIVE=1 to probe local Zetaris")
def test_live_connection():
    client = ZetarisClient()
    assert client.mode == "live", "Live test needs ZETARIS_API_KEY and SAMPLE_MODE=false"
    result = client.test_connection()
    assert result["status"] == "ok", result.get("message", "Connection failed")
    assert isinstance(result["databases"], list)


def _assert_port_shape(port):
    assert set(port) == {"name", "lat", "lon", "source_urls", "validated", "geocode_source", "zone_name", "mrgid", "id"}
    assert isinstance(port["name"], str)
    assert isinstance(port["id"], str)
    for field in ("lat", "lon"):
        assert port[field] is None or isinstance(port[field], float)
    assert isinstance(port["source_urls"], list)
    assert all(isinstance(url, str) for url in port["source_urls"])
    assert port["validated"] is None or isinstance(port["validated"], bool)
    for field in ("geocode_source", "zone_name"):
        assert port[field] is None or isinstance(port[field], str)
    assert port["mrgid"] is None or type(port["mrgid"]) is int


def test_sample_ports_end_to_end_with_evaluator(unit_env, monkeypatch, trace_path):
    monkeypatch.setenv("SAMPLE_MODE", "true")
    run_id = "e2e-test"
    ports = ZetarisClient(run_id=run_id).get_ports()
    assert len(ports) == 20
    assert len({p["zone_name"] for p in ports}) > 1
    gov = [any(any(term in url for term in ("gov", "gouv", "gob")) for url in p["source_urls"]) for p in ports]
    assert any(gov) and not all(gov)
    seed = json.loads((Path(__file__).resolve().parents[2] / "seed" / "ports_of_entry.geojson").read_text())
    originals = {f["properties"]["id"]: f for f in seed["features"]}
    for port in ports:
        _assert_port_shape(port)
        original = originals[port["id"]]
        assert [port["lon"], port["lat"]] == original["geometry"]["coordinates"][:2]
        for field in set(port) - {"lat", "lon"}:
            assert port[field] == original["properties"].get(field)
    assert _entries(trace_path)[0]["row_count"] == 20
    assert _entries(trace_path)[0]["mode"] == "sample"
    _assert_evaluator_round_trip(ports, run_id, trace_path)


def _assert_evaluator_round_trip(ports, run_id, trace_path):
    original_ids = [port["id"] for port in ports]
    state = evaluate({"ports": ports, "run_id": run_id})
    had_retry = bool(state["needs_retry"])
    retries = 0
    while route_after_evaluation(state) == "retry":
        assert retries < RETRY_LIMIT, "Evaluator exceeded its retry limit"
        state = evaluate(prepare_retry(state))
        retries += 1
    state = finalise(state)
    assert [port["id"] for port in state["ports"]] == original_ids
    assert all(port["verdict"] in {"pass", "flag"} for port in state["ports"])
    assert state["needs_retry"] == []
    assert route_after_evaluation(state) == "done"
    entries = _entries(trace_path)
    assert {entry["agent_name"] for entry in entries} == {"ZetarisAdapter", "EvaluatorAgent"}
    assert all(entry["run_id"] == run_id for entry in entries)
    assert entries[0]["agent_name"] == "ZetarisAdapter"
    assert entries[1:] == state["trace"]
    if had_retry:
        assert retries > 0
        assert any(entry.get("handoff") == {"from": "EvaluatorAgent", "to": "retry"}
                   and entry["action"] == "prepare_retry" for entry in entries)
        assert any(entry.get("verdict") == "retry" for entry in entries)
    else:
        assert retries == 0


def test_get_ports_sample_filters_before_limit(unit_env, monkeypatch, trace_path):
    monkeypatch.delenv("ZETARIS_API_KEY")
    client = ZetarisClient()
    target = client.get_ports()[-1]
    assert client.get_ports(zone_name=target["zone_name"], mrgid=target["mrgid"], limit=1) == [target]
    assert _entries(trace_path)[-1]["row_count"] == 1
    assert len(client.get_ports(limit=3)) == 3
    assert client.get_ports(zone_name="No such zone") == []
    assert client.get_ports(mrgid=-1) == []
    assert _entries(trace_path)[-1]["row_count"] == 0


@pytest.mark.parametrize("zone", ["Alaska", "Côte d'Ivoire", "x'; DROP TABLE ports; --", "a\\b", ""])
def test_get_ports_encodes_filters_safely(client, monkeypatch, zone):
    calls = []

    def post(url, **kwargs):
        calls.append(kwargs)
        return httpx.Response(200, json={"data": []})

    monkeypatch.setattr(httpx, "post", post)
    assert client.get_ports(zone_name=zone, mrgid=8463, limit=7) == []
    sql = calls[0]["json"]["sql"]
    assert sql == zetaris._PORT_SELECT + (
        f" WHERE zone_name = decode(unhex('{zone.encode('utf-8').hex()}'), 'UTF-8') AND mrgid = 8463"
    )
    assert client.dry_run(sql)
    assert calls[0]["json"]["limit"] == 7


@pytest.mark.parametrize("filters", [{"mrgid": "1 OR 1=1"}, {"mrgid": True}, {"mrgid": 1.5}, {"zone_name": 123}])
def test_get_ports_rejects_invalid_filter_types(client, filters):
    with pytest.raises(ValueError):
        client.get_ports(**filters)


def test_get_ports_normalizes_rest_cells(client, monkeypatch):
    rows = [
        ["Port", "1.2", "-3.4", '["https://customs.gov"]', "false", "nominatim", "Zone", "8463", "id-1"],
        ["Unknown", "null", None, "null", "null", None, "Zone", "null", "id-2"],
    ]
    monkeypatch.setattr(httpx, "post", lambda *a, **k: httpx.Response(200, json={"data": rows}))
    ports = client.get_ports()
    for port in ports:
        _assert_port_shape(port)
    assert ports[0]["validated"] is False
    assert ports[0]["source_urls"] == ["https://customs.gov"]
    assert ports[0]["lat"] == 1.2 and ports[0]["mrgid"] == 8463
    assert ports[1]["lat"] is None and ports[1]["source_urls"] == []


@pytest.mark.parametrize("index,value", [(1, "NaN"), (2, "181"), (3, "not JSON"), (4, "unknown"), (7, "3.5")])
def test_get_ports_rejects_invalid_rest_fields(client, monkeypatch, index, value):
    row = ["Port", "1.2", "2.3", "[]", "true", "nominatim", "Zone", "1", "id"]
    row[index] = value
    monkeypatch.setattr(httpx, "post", lambda *a, **k: httpx.Response(200, json={"data": [row]}))
    with pytest.raises(ZetarisUnavailable, match="invalid field"):
        client.get_ports()


@pytest.mark.skipif(os.environ.get("ZETARIS_LIVE") != "1", reason="Set ZETARIS_LIVE=1 to query the real PoE view")
def test_live_get_ports_for_zone():
    client = ZetarisClient()
    assert client.mode == "live", "Live test needs ZETARIS_API_KEY and SAMPLE_MODE=false"
    ports = client.get_ports(zone_name="Alaska", mrgid=8463, limit=5)
    assert 0 < len(ports) <= 5
    for port in ports:
        _assert_port_shape(port)
        assert port["zone_name"] == "Alaska" and port["mrgid"] == 8463


@pytest.mark.skipif(os.environ.get("ZETARIS_LIVE") != "1", reason="Set ZETARIS_LIVE=1 for the Zetaris to evaluator integration")
def test_live_ports_end_to_end_with_evaluator(trace_path):
    run_id = "e2e-live-test"
    client = ZetarisClient(run_id=run_id)
    assert client.mode == "live", "Live test needs ZETARIS_API_KEY and SAMPLE_MODE=false"
    ports = client.get_ports(zone_name="Alaska", limit=20)
    assert ports and all(port["zone_name"] == "Alaska" for port in ports)
    _assert_evaluator_round_trip(ports, run_id, trace_path)
