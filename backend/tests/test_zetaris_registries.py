"""Independent registry validation: UN/LOCODE + World Port Index held in Zetaris."""
from __future__ import annotations

import json
import math
import os

import httpx
import pytest

from app.adapters import registry_sources, zetaris
from app.adapters.zetaris import ZetarisClient, ZetarisUnavailable
from app.agents import registry_check
from app.agents.registry_check import OFFICIAL, UNCONFIRMED, check_ports, match_port, name_variants
from scripts import zetaris_setup

BERMUDA = {"name": "Bermuda", "mrgid": 8402}
ST_GEORGE = {"name": "Port of St. George’s", "lat": 32.3810447, "lon": -64.676717}
LIVE = pytest.mark.skipif(os.environ.get("ZETARIS_LIVE") != "1", reason="Set ZETARIS_LIVE=1 for local Zetaris")


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path, request):
    monkeypatch.setenv("TRACE_LOG_PATH", str(tmp_path / "trace.jsonl"))
    monkeypatch.setenv("TRACE_STDOUT", "0")
    if not request.node.name.startswith("test_live_"):
        monkeypatch.setenv("SAMPLE_MODE", "true")
        for name in ("ZETARIS_API_KEY", "ZETARIS_ORG_ID", "ZETARIS_REST_URL"):
            monkeypatch.delenv(name, raising=False)
    return tmp_path


def trace_rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def entry(source, name, lat=None, lon=None, **fields):
    return dict(source=source, name=name, lat=lat, lon=lon, **fields)


# --- source parsing -----------------------------------------------------------------------
@pytest.mark.parametrize("raw, expected", [
    ("3223N 06441W", (32.383333, -64.683333)),   # St George's, Bermuda
    ("3744N 02540W", (37.733333, -25.666667)),   # Ponta Delgada, Azores
    ("0848S 01314E", (-8.8, 13.233333)),         # southern and eastern hemispheres
    (" 0000N 00000E ", (0.0, 0.0)),
])
def test_unlocode_coordinates_ddmm_to_decimal(raw, expected):
    assert registry_sources.parse_unlocode_coordinates(raw) == pytest.approx(expected)


@pytest.mark.parametrize("raw", ["", None, "3260N 06441W", "3223N 06460W", "9100N 00000E",
                                 "0000N 18100E", "3223 06441", "3223N06441W", "32.38 -64.68"])
def test_unlocode_coordinates_reject_malformed(raw):
    assert registry_sources.parse_unlocode_coordinates(raw) is None


def test_unlocode_keeps_only_function_position_1_ports():
    # UNECE CSV order: Change, Country, Location, Name, NameWoDiacritics, Subdivision, Function,
    # Status, Date, IATA, Coordinates, Remarks.
    lines = [
        ',"BM","","BERMUDA","BERMUDA","","","","","","",""',             # country header row
        ',"BM","SGE","Saint George","Saint George","","1-------","AI","0207","","3223N 06441W",""',
        ',"BM","BDA","Hamilton","Hamilton","","1-3-----","AI","0207","","",""',
        ',"BM","XAP","Airport only","Airport only","","----4---","AI","0207","","3220N 06442W",""',
        ',"AL","DRZ","Durrës","Durres","","1-------","RL","0207","","",""',
    ]
    rows = registry_sources.unlocode_ports(lines)
    assert [r["code"] for r in rows] == ["BMSGE", "BMBDA", "ALDRZ"]
    assert rows[0]["lat"] == pytest.approx(32.383333) and rows[1]["lat"] is None
    assert rows[2]["name"] == "Durrës" and rows[2]["name_ascii"] == "Durres"
    assert set(rows[0]) == set(registry_sources.UNLOCODE_COLUMNS)


def test_wpi_rows_get_iso2_from_unlocode_or_country_name():
    text = ("World Port Index Number,Main Port Name,Alternate Port Name,UN/LOCODE,Country Code,"
            "Latitude,Longitude,First Port of Entry,Quarantine - Pratique,Harbor Use\n"
            "10140,St George,Saint George's Harbor,BM SGE,Bermuda,32.383333,-64.683333,Yes,Yes,Unknown\n"
            "10145,Ireland Island,,,Bermuda,32.316667,-64.833333,No,nan,\n")
    rows = registry_sources.wpi_ports(text)
    assert rows[0]["unlocode"] == "BMSGE" and rows[0]["country_iso2"] == "BM"
    assert rows[1]["country_iso2"] == "BM"  # majority UN/LOCODE prefix of the country name
    assert rows[0]["harbor_use"] is None and rows[1]["quarantine_pratique"] is None
    assert rows[0]["first_port_of_entry"] == "Yes" and rows[0]["wpi_number"] == "10140"


def test_fixtures_are_real_subsets_in_rest_shape():
    for source, columns in (("unlocode", registry_sources.UNLOCODE_COLUMNS), ("wpi", registry_sources.WPI_COLUMNS)):
        body = json.loads((zetaris.SAMPLE_DIR / f"{source}_ports.json").read_text(encoding="utf-8"))
        assert body["columns"] == list(columns) and body["data"]
        country = columns.index("country_iso2")
        assert {row[country] for row in body["data"]} <= set(registry_sources.FIXTURE_COUNTRIES)
        assert all(len(row) == len(columns) and all(isinstance(c, str) for c in row) for row in body["data"])


# --- name normalisation -------------------------------------------------------------------
@pytest.mark.parametrize("candidate, registry", [
    ("Port of St. George’s", "Saint George"),
    ("PORT OF ST GEORGES", "St George"),
    ("Porto / Marina de Ponta Delgada", "Ponta Delgada"),
    ("Antwerp (Antwerpen)", "Antwerpen"),
    ("Port Autonome de Cotonou", "Cotonou"),
    ("BRIDGETOWN PORT", "Bridgetown"),
    ("Anchorage Small Boat Harbor", "Anchorage"),
    ("Road Town Jetty / Port of Road Town", "Road Town"),
    ("Durrës", "Durres"),
])
def test_name_variants_match(candidate, registry):
    assert name_variants(candidate) & name_variants(registry)


@pytest.mark.parametrize("candidate, registry", [
    ("Invented Harbour", "Saint George"), ("Hamilton", "Saint George"), ("Port Louis", "Port Mathurin"),
])
def test_name_variants_do_not_overmatch(candidate, registry):
    assert not name_variants(candidate) & name_variants(registry)


def test_wpi_alternate_names_are_matched():
    wpi = entry("wpi", "Antwerpen", 51.216667, 4.4, alternate_name="Antwerp; Anvers",
                unlocode="BEANR", wpi_number="31250")
    matches, _ = match_port({"name": "Port of Anvers", "lat": 51.23, "lon": 4.41}, [wpi])
    assert matches == [{"source": "wpi", "code": "BEANR", "name": "Antwerpen", "distance_km": 1.64}]


# --- distance gate ------------------------------------------------------------------------
def test_distance_gate_rejects_a_same_name_entry_beyond_10_km():
    near = entry("unlocode", "Saint George", 32.383333, -64.683333, code="BMSGE")
    far = entry("wpi", "St George", 32.5, -64.5, unlocode="BMSGE")  # ~22 km away
    matches, rejected = match_port(ST_GEORGE, [near, far])
    assert [m["source"] for m in matches] == ["unlocode"] and matches[0]["distance_km"] < 1
    assert rejected == [{"source": "wpi", "code": "BMSGE", "name": "St George", "distance_km": 21.21}]


def test_distance_gate_skipped_when_either_side_lacks_coordinates():
    registry = [entry("unlocode", "Hamilton", code="BMBDA")]
    matches, rejected = match_port({"name": "Hamilton", "lat": 32.29, "lon": -64.78}, registry)
    assert matches == [{"source": "unlocode", "code": "BMBDA", "name": "Hamilton", "distance_km": None}]
    assert match_port({"name": "Hamilton"}, [entry("wpi", "Hamilton", 32.3, -64.78)])[0][0]["distance_km"] is None
    assert rejected == []


def test_closest_entry_wins_per_source():
    a = entry("unlocode", "Freeport", 32.32, -64.83, code="BMFPT")
    b = entry("unlocode", "Freeport", 26.5, -78.7, code="BSFPO")
    c = entry("unlocode", "Freeport", None, None, code="XXFPT")
    matches, rejected = match_port({"name": "Freeport", "lat": 32.316, "lon": -64.833}, [c, b, a])
    assert matches[0]["code"] == "BMFPT" and [r["code"] for r in rejected] == ["BSFPO"]


def test_haversine_known_distance():
    assert registry_check.haversine_km(51.5074, -0.1278, 48.8566, 2.3522) == pytest.approx(343.5, abs=1)


# --- registry check through Zetaris (sample fixtures) -------------------------------------
def test_unlocode_and_wpi_match_st_georges(isolated):
    ports, summary = check_ports([ST_GEORGE], BERMUDA, "reg-bm")
    assert summary == {"mode": "sample", "country_iso2": "BM", "registry_entries": 12, "official_count": 1}
    port = ports[0]
    assert port["zetaris_validation"] == OFFICIAL
    assert port["registry_matches"] == [
        {"source": "unlocode", "code": "BMSGE", "name": "Saint George", "distance_km": 0.67},
        {"source": "wpi", "code": "BMSGE", "name": "St George", "distance_km": 0.67, "first_port_of_entry": "Yes"}]
    event = [r for r in trace_rows(isolated / "trace.jsonl") if r["action"] == "registry_check"][0]
    assert event["agent_name"] == "ZetarisAdapter" and event["run_id"] == "reg-bm"
    assert event["validation"] == OFFICIAL and event["matches"] == port["registry_matches"]


def test_wpi_match_with_coordinates_for_hamilton():
    ports, _ = check_ports([{"name": "Hamilton Harbour", "lat": 32.2935, "lon": -64.7823}], BERMUDA, "reg-ham")
    by_source = {m["source"]: m for m in ports[0]["registry_matches"]}
    assert by_source["wpi"] == {"source": "wpi", "code": "BMBDA", "name": "Hamilton", "distance_km": 0.73,
                                "first_port_of_entry": "Yes"}
    assert by_source["unlocode"]["distance_km"] is None  # UN/LOCODE BMBDA has no coordinates


def test_no_match_is_unconfirmed_and_traced(isolated):
    ports, summary = check_ports([{"name": "Invented Harbour", "lat": 32.3, "lon": -64.7}], BERMUDA, "reg-none")
    assert ports[0]["zetaris_validation"] == UNCONFIRMED == "unconfirmed - review needed"
    assert ports[0]["registry_matches"] == [] and summary["official_count"] == 0
    event = [r for r in trace_rows(isolated / "trace.jsonl") if r["action"] == "registry_check"][0]
    assert event["status"] == "unconfirmed" and event["registry_entries"] == 12


def test_seed_coordinates_far_from_the_registry_stay_unconfirmed():
    # BI's seed geocode for Antwerp is ~18 km from both registry entries: the name alone is not enough.
    ports, _ = check_ports([{"name": "Antwerp (Antwerpen)", "lat": 51.0669817, "lon": 4.3097669}],
                           {"name": "Belgium", "mrgid": 3293}, "reg-far")
    assert ports[0]["zetaris_validation"] == UNCONFIRMED


def test_zone_without_country_queries_a_box_around_candidates():
    ports, summary = check_ports([ST_GEORGE], {"name": "Nowhere Sea"}, "reg-bbox")
    assert summary["country_iso2"] is None and summary["registry_entries"] > 0
    assert ports[0]["zetaris_validation"] == OFFICIAL


@pytest.mark.parametrize("zone, iso2", [
    ({"name": "Alaska", "mrgid": 8463}, "US"),  # no iso2 of its own: sovereign
    ({"name": "Azores"}, "PT"),
    ({"name": "anything", "iso2": "bm"}, "BM"),
    ("Bermuda", "BM"),
    ({"name": "Nowhere Sea"}, None),
])
def test_zone_iso2(zone, iso2):
    assert registry_check.zone_iso2(zone) == iso2


def test_live_failure_falls_back_to_fixtures(monkeypatch, isolated):
    monkeypatch.setenv("SAMPLE_MODE", "false")
    monkeypatch.setenv("ZETARIS_API_KEY", "registry-test-key")
    monkeypatch.setenv("ZETARIS_ORG_ID", "1")
    monkeypatch.setenv("ZETARIS_REST_URL", "http://127.0.0.1:9/api/v1.0")  # nothing listens
    monkeypatch.setattr(zetaris.time, "sleep", lambda seconds: None)
    ports, summary = check_ports([ST_GEORGE], BERMUDA, "reg-down")
    assert summary["mode"] == "fallback" and ports[0]["zetaris_validation"] == OFFICIAL
    rows = trace_rows(isolated / "trace.jsonl")
    assert [(r["action"], r["status"]) for r in rows] == [
        ("zetaris_query", "error"), ("zetaris_fallback", "fallback"), ("zetaris_query", "ok"),
        ("zetaris_query", "ok"), ("registry_check", "ok")]
    assert all(r["agent_name"] == "ZetarisAdapter" for r in rows)
    assert "registry-test-key" not in (isolated / "trace.jsonl").read_text()


def test_outage_without_fallback_never_marks_official(monkeypatch):
    def down(self, *args, **kwargs):
        raise ZetarisUnavailable("fixture unreadable")
    monkeypatch.setattr(ZetarisClient, "get_registry_ports", down)
    ports, summary = check_ports([ST_GEORGE], BERMUDA, "reg-unavailable")
    assert summary["mode"] == "unavailable" and ports[0]["zetaris_validation"] == UNCONFIRMED


# --- adapter ------------------------------------------------------------------------------
def test_get_registry_ports_filters_sample_by_country_and_bbox():
    client = ZetarisClient(run_id="adapter")
    unlocode = client.get_registry_ports("bm", source="unlocode")
    assert unlocode and {p["country_iso2"] for p in unlocode} == {"BM"}
    assert {p["source"] for p in unlocode} == {"unlocode"}
    st_george = next(p for p in unlocode if p["code"] == "BMSGE")
    assert st_george["lat"] == pytest.approx(32.383333) and st_george["subdivision"] is None
    boxed = client.get_registry_ports(bbox=(32.0, -65.0, 33.0, -64.0), source="wpi")
    assert boxed and all(32 <= p["lat"] <= 33 and -65 <= p["lon"] <= -64 for p in boxed)


def test_get_registry_ports_builds_guarded_sql(monkeypatch, isolated):
    monkeypatch.setenv("SAMPLE_MODE", "false")
    monkeypatch.setenv("ZETARIS_API_KEY", "registry-test-key")
    monkeypatch.setenv("ZETARIS_ORG_ID", "1")
    sent = {}

    def post(url, **kwargs):
        sent.update(kwargs["json"])
        return httpx.Response(200, json={"data": [["BM", "SGE", "BMSGE", "Saint George", "Saint George",
                                                    "null", "1-------", "AI", "32.383333", "-64.683333"]]})

    monkeypatch.setattr(httpx, "post", post)
    rows = ZetarisClient(run_id="sql").get_registry_ports("BM", bbox=(32, -65, 33, -64), source="unlocode")
    assert sent["sql"] == (
        "SELECT country_iso2, location, code, name, name_ascii, subdivision, function_code, status, lat, lon "
        "FROM blue_intel.unlocode_ports WHERE country_iso2 = 'BM' AND lat BETWEEN 32.000000 AND 33.000000 "
        "AND lon BETWEEN -65.000000 AND -64.000000")
    assert rows == [dict(country_iso2="BM", location="SGE", code="BMSGE", name="Saint George",
                         name_ascii="Saint George", subdivision=None, function_code="1-------", status="AI",
                         lat=32.383333, lon=-64.683333, source="unlocode")]
    query = trace_rows(isolated / "trace.jsonl")[0]
    assert query["action"] == "zetaris_query" and "blue_intel.unlocode_ports" in query["input_summary"]["sql"]


@pytest.mark.parametrize("kwargs", [
    {"source": "seed"}, {"country_iso2": "BMU"}, {"country_iso2": "B'"}, {"country_iso2": "1A"},
    {"country_iso2": 12}, {"bbox": (1, 2, 3)}, {"bbox": (33, -65, 32, -64)}, {"bbox": (32, -64, 33, -65)},
    {"bbox": (math.nan, 0, 1, 1)}, {"bbox": (0, 0, 91, 1)}, {"bbox": (True, 0, 1, 1)},
    {"bbox": ("0; DROP TABLE x", 0, 1, 1)}, {"bbox": "0,0,1,1"},
])
def test_get_registry_ports_rejects_unsafe_filters(kwargs):
    with pytest.raises(ValueError):
        ZetarisClient(run_id="bad").get_registry_ports(**kwargs)


def test_registry_rows_with_invalid_coordinates_are_rejected(monkeypatch):
    monkeypatch.setenv("SAMPLE_MODE", "false")
    monkeypatch.setenv("ZETARIS_API_KEY", "k")
    monkeypatch.setenv("ZETARIS_ORG_ID", "1")
    row = ["BM", "SGE", "BMSGE", "Saint George", "Saint George", "null", "1-------", "AI", "95", "-64.6"]
    monkeypatch.setattr(httpx, "post", lambda *a, **k: httpx.Response(200, json={"data": [row]}))
    with pytest.raises(ZetarisUnavailable, match="invalid coordinate"):
        ZetarisClient(run_id="coords").get_registry_ports("BM")


def test_trace_event_redacts_the_api_key(monkeypatch, isolated):
    monkeypatch.setenv("ZETARIS_API_KEY", "registry-secret-1234")
    monkeypatch.setenv("ZETARIS_ORG_ID", "1")
    ZetarisClient(run_id="ev").trace_event("registry_check", note="key registry-secret-1234")
    row = trace_rows(isolated / "trace.jsonl")[0]
    assert row["agent_name"] == "ZetarisAdapter" and row["action"] == "registry_check"
    assert "registry-secret-1234" not in json.dumps(row)


# --- setup script -------------------------------------------------------------------------
def test_setup_registry_statements_substitute_the_platform_path():
    sql = zetaris_setup.statements(zetaris_setup.REGISTRY_SQL_FILE,
                                   {"registry_dir": zetaris_setup.ZETARIS_REGISTRY_DIR})
    assert len(sql) == 5 and sql[0].startswith("CREATE LIGHTNING DATABASE BLUE_INTEL_REGISTRIES")
    assert f'PATH "{zetaris_setup.ZETARIS_REGISTRY_DIR}/unlocode_ports.csv"' in sql[1]
    assert "VIEW unlocode_ports WITH CONTAINER blue_intel" in sql[3]
    assert "VIEW wpi_ports WITH CONTAINER blue_intel" in sql[4]
    assert not any("{" in s for s in sql)


# --- live ---------------------------------------------------------------------------------
@LIVE
def test_live_registry_views_for_bermuda():
    client = ZetarisClient(run_id="live-registries")
    assert client.mode == "live", "Live test needs ZETARIS_API_KEY and SAMPLE_MODE=false"
    unlocode = client.get_registry_ports("BM", source="unlocode")
    wpi = client.get_registry_ports("BM", source="wpi")
    assert "BMSGE" in {p["code"] for p in unlocode} and {p["country_iso2"] for p in unlocode} == {"BM"}
    assert {"BMSGE", "BMBDA"} <= {p["unlocode"] for p in wpi}
    counts = {view: int(client.query(f"SELECT COUNT(*) FROM blue_intel.{view}", limit=1)[0][0])
              for view in ("unlocode_ports", "wpi_ports")}
    assert counts["unlocode_ports"] > 10000 and counts["wpi_ports"] > 3000
    ports, summary = check_ports([ST_GEORGE], BERMUDA, "live-registries")
    assert summary["mode"] == "live" and ports[0]["zetaris_validation"] == OFFICIAL
