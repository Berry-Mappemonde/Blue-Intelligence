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
from app.agents.registry_check import (
    OFFICIAL, REGISTERED, TIER1, TIER2, TIER3, TIER_REGISTERED, UNCONFIRMED, check_ports, match_port,
    name_variants,
)
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
                unlocode="BEANR", wpi_number="31250", country_iso2="BE")
    matches, _ = match_port({"name": "Port of Anvers", "lat": 51.23, "lon": 4.41}, [wpi], "BE")
    assert matches == [{"source": "wpi", "code": "BEANR", "name": "Antwerpen", "distance_km": 1.64}]


def test_unlocode_name_without_diacritics_is_matched():
    unlocode = entry("unlocode", "Durrës", code="ALDRZ", name_ascii="Durres", country_iso2="AL")
    assert match_port({"name": "PORT OF DURRES"}, [unlocode], "AL")[0][0]["code"] == "ALDRZ"


def test_country_code_must_match():
    elsewhere = entry("unlocode", "Freeport", 26.5, -78.7, code="BSFPO", country_iso2="BS")
    assert match_port({"name": "Freeport", "lat": 26.5, "lon": -78.7}, [elsewhere], "BM") == ([], [])
    # The port's own country_iso2 wins over the zone's; no country at all: no match.
    assert match_port({"name": "Freeport", "country_iso2": "BS"}, [elsewhere], "BM")[0]
    assert match_port({"name": "Freeport"}, [elsewhere], None) == ([], [])


# --- 25 km gate and coord_mismatch ---------------------------------------------------------
def test_25_km_gate_accepts_22_km_and_flags_beyond_as_coord_mismatch():
    near = entry("unlocode", "Saint George", 32.383333, -64.683333, code="BMSGE", country_iso2="BM")
    at_22 = entry("wpi", "St George", 32.5, -64.5, unlocode="BMSGE", country_iso2="BM")
    at_37 = entry("wpi", "St George", 32.6, -64.4, unlocode="BMXXX", country_iso2="BM")
    matches, mismatched = match_port(ST_GEORGE, [near, at_22], "BM")
    assert [(m["source"], m["distance_km"]) for m in matches] == [("unlocode", 0.67), ("wpi", 21.21)]
    assert mismatched == []
    matches, mismatched = match_port(ST_GEORGE, [at_37], "BM")
    assert matches == [] and mismatched == [
        {"source": "wpi", "code": "BMXXX", "name": "St George", "distance_km": 35.59}]


def test_coord_mismatch_is_recorded_not_dropped():
    far = entry("unlocode", "Saint George", 32.7, -64.3, code="BMSGE", country_iso2="BM")
    ports, summary = registry_check.annotate([dict(ST_GEORGE, extra="kept")],
                                             {"mode": "sample", "country_iso2": "BM", "entries": [far]}, "mm")
    reg = ports[0]["registry"]
    assert ports[0]["extra"] == "kept" and reg["tier"] == TIER3
    assert reg["coord_mismatch"] == [{"source": "unlocode", "code": "BMSGE", "name": "Saint George",
                                      "distance_km": 50.05}]
    assert any(r.startswith("coord_mismatch: UN/LOCODE BMSGE (50.05 km)") for r in reg["reasons"])
    assert summary["coord_mismatch_count"] == 1


def test_distance_gate_skipped_when_either_side_lacks_coordinates():
    registry = [entry("unlocode", "Hamilton", code="BMBDA", country_iso2="BM")]
    matches, mismatched = match_port({"name": "Hamilton", "lat": 32.29, "lon": -64.78}, registry, "BM")
    assert matches == [{"source": "unlocode", "code": "BMBDA", "name": "Hamilton", "distance_km": None}]
    wpi = [entry("wpi", "Hamilton", 32.3, -64.78, country_iso2="BM")]
    assert match_port({"name": "Hamilton"}, wpi, "BM")[0][0]["distance_km"] is None
    assert mismatched == []


def test_closest_entry_wins_per_source():
    a = entry("unlocode", "Freeport", 32.32, -64.83, code="BMFPT", country_iso2="BM")
    b = entry("unlocode", "Freeport", 32.5, -64.5, code="BMFP2", country_iso2="BM")
    c = entry("unlocode", "Freeport", None, None, code="BMFP3", country_iso2="BM")
    matches, _ = match_port({"name": "Freeport", "lat": 32.316, "lon": -64.833}, [c, b, a], "BM")
    assert matches[0]["code"] == "BMFPT"


def test_haversine_known_distance():
    assert registry_check.haversine_km(51.5074, -0.1278, 48.8566, 2.3522) == pytest.approx(343.5, abs=1)


# --- official source grounding ------------------------------------------------------------
GOV_BM = "https://www.customs.gov.bm/yachts"


def test_source_texts_from_context_keeps_documents_not_synthesis():
    context = (f"[SOURCE: {GOV_BM}]\nClear at St. George's.\n\n"
               "[SOURCE: https://example.com/blog]\nA blog.\n\n"
               "[SYNTHÈSE DE RECHERCHE (à recouper)]\nHamilton is a port of entry.")
    texts = registry_check.source_texts_from_context(context)
    assert texts == {GOV_BM: "Clear at St. George's.", "https://example.com/blog": "A blog."}
    assert registry_check.source_texts_from_context("no source blocks") == {}


@pytest.mark.parametrize("url, text, found", [
    (GOV_BM, "Yachts must clear customs at St. George's Harbour on arrival.", "saint george"),
    (GOV_BM, "Yachts must clear customs at ST GEORGES.", "saint george"),
    (GOV_BM, "Yachts must clear customs at Hamilton.", None),            # name absent
    ("https://www.noonsite.com/bermuda", "Clear at St. George's.", None),  # not an official URL
    (GOV_BM, "", None),                                                 # no text kept
    (GOV_BM, "Georgetown is not St Georgeville.", None),                # whole words only
])
def test_official_source_grounding(url, text, found):
    evidence = registry_check.official_source_evidence({"name": "Port of St. George’s"}, {url: text})
    assert evidence == ([{"url": url, "name_found": found}] if found else [])


def test_grounding_needs_fetched_text_for_the_port_s_own_urls():
    port = {"name": "Port of St. George’s", "source_urls": [GOV_BM]}
    assert registry_check.official_source_evidence(port, None) == []
    assert registry_check.official_source_evidence(port, {"https://www.gov.bm/other": "St. George's"}) == []


def test_grounding_accepts_registry_alternate_names():
    port = {"name": "Antwerp"}
    texts = {"https://www.ports.gov.be/fr": "Les ports d'Anvers et de Zeebrugge."}
    assert registry_check.official_source_evidence(port, texts) == []
    assert registry_check.official_source_evidence(port, texts, ("Antwerpen", "Antwerp; Anvers")) == [
        {"url": "https://www.ports.gov.be/fr", "name_found": "anvers"}]


# --- tiers through Zetaris (sample fixtures) ----------------------------------------------
def test_tier1_official_source_and_registry(isolated):
    texts = {GOV_BM: "Yachts must clear customs at St. George's Harbour on arrival."}
    ports, summary = check_ports([ST_GEORGE], BERMUDA, "reg-t1", source_texts=texts)
    reg = ports[0]["registry"]
    assert reg["tier"] == TIER1 and reg["label"] == "Official Commercial Port of Entry"
    assert reg["validation"] == ports[0]["zetaris_validation"] == OFFICIAL
    assert reg["official_evidence"] == [{"url": GOV_BM, "name_found": "saint george"}]
    assert reg["matches"] == ports[0]["registry_matches"] == [
        {"source": "unlocode", "code": "BMSGE", "name": "Saint George", "distance_km": 0.67},
        {"source": "wpi", "code": "BMSGE", "name": "St George", "distance_km": 0.67, "first_port_of_entry": "Yes"}]
    assert reg["first_port_of_entry"] == "Yes"
    assert reg["reasons"][0] == (f"Official Commercial Port of Entry: named in official source {GOV_BM}, "
                                 "and listed in UN/LOCODE BMSGE (0.67 km), WPI BMSGE (0.67 km)")
    assert "First Port of Entry (supporting evidence only)" in reg["reasons"][1]
    assert summary["tiers"] == {TIER1: 1, TIER2: 0, TIER_REGISTERED: 0, TIER3: 0}
    assert summary["official_count"] == 1
    event = [r for r in trace_rows(isolated / "trace.jsonl") if r["action"] == "registry_check"][0]
    assert event["agent_name"] == "ZetarisAdapter" and event["run_id"] == "reg-t1"
    assert event["tier"] == event["status"] == TIER1 and event["reasons"] == reg["reasons"]


def test_tier2_official_source_without_registry_match():
    port = {"name": "Conch Inn Marina", "lat": 26.5465414, "lon": -77.0515419}
    texts = {"https://www.bahamas.gov.bs/customs": "Ports of entry for pleasure craft include Conch Inn Marina."}
    ports, _ = check_ports([port], {"name": "Bahamas", "mrgid": 8404}, "reg-t2", source_texts=texts)
    reg = ports[0]["registry"]
    assert reg["tier"] == TIER2 and reg["label"] == "Official Yachting Port of Entry"
    assert reg["matches"] == [] and ports[0]["zetaris_validation"] == OFFICIAL
    assert reg["reasons"][0].startswith("Official Yachting Port of Entry: named in official source "
                                        "https://www.bahamas.gov.bs/customs; not listed")


def test_tier_registered_never_claims_port_of_entry():
    ports, summary = check_ports([dict(ST_GEORGE, source_urls=[GOV_BM])], BERMUDA, "reg-reg")
    reg = ports[0]["registry"]
    assert reg["tier"] == TIER_REGISTERED and reg["label"] == "Registered port, entry status unverified"
    assert reg["validation"] == ports[0]["zetaris_validation"] == REGISTERED != OFFICIAL
    assert reg["official_evidence"] == []  # official URL, but no fetched text: does not count
    assert "a registry listing does not establish port-of-entry status" in reg["reasons"][0]
    assert not any("Official" in r for r in reg["reasons"])
    assert summary["official_count"] == 0 and summary["tiers"][TIER_REGISTERED] == 1


def test_tier3_neither_and_traced(isolated):
    ports, summary = check_ports([{"name": "Invented Harbour", "lat": 32.3, "lon": -64.7}], BERMUDA, "reg-none",
                                 source_texts={GOV_BM: "Clear at St. George's."})
    reg = ports[0]["registry"]
    assert reg["tier"] == TIER3 and ports[0]["zetaris_validation"] == UNCONFIRMED == "unconfirmed - review needed"
    assert reg["matches"] == [] and reg["official_evidence"] == [] and summary["official_count"] == 0
    assert reg["reasons"][0].startswith("Unconfirmed - review needed: no fetched official document names it")
    event = [r for r in trace_rows(isolated / "trace.jsonl") if r["action"] == "registry_check"][0]
    assert event["status"] == TIER3 and event["registry_entries"] == 12


def test_wpi_match_with_coordinates_for_hamilton():
    ports, _ = check_ports([{"name": "Hamilton Harbour", "lat": 32.2935, "lon": -64.7823}], BERMUDA, "reg-ham")
    by_source = {m["source"]: m for m in ports[0]["registry_matches"]}
    assert by_source["wpi"] == {"source": "wpi", "code": "BMBDA", "name": "Hamilton", "distance_km": 0.73,
                                "first_port_of_entry": "Yes"}
    assert by_source["unlocode"]["distance_km"] is None  # UN/LOCODE BMBDA has no coordinates
    assert ports[0]["registry"]["tier"] == TIER_REGISTERED


def test_seed_coordinates_18_km_off_are_within_tolerance():
    # BI's seed geocode for Antwerp is ~18 km from both registry entries: inside 25 km.
    ports, _ = check_ports([{"name": "Antwerp (Antwerpen)", "lat": 51.0669817, "lon": 4.3097669}],
                           {"name": "Belgium", "mrgid": 3293}, "reg-far")
    assert [m["distance_km"] for m in ports[0]["registry_matches"]] == [18.24, 17.79]
    assert ports[0]["registry"]["coord_mismatch"] == []


def test_zone_without_country_queries_a_box_around_candidates():
    port = dict(ST_GEORGE, country_iso2="BM")  # the port's own country still gates the match
    ports, summary = check_ports([port], {"name": "Nowhere Sea"}, "reg-bbox")
    assert summary["country_iso2"] is None and summary["registry_entries"] > 0
    assert ports[0]["registry"]["tier"] == TIER_REGISTERED
    ports, _ = check_ports([ST_GEORGE], {"name": "Nowhere Sea"}, "reg-bbox-2")
    assert ports[0]["registry"]["tier"] == TIER3  # no country known: no registry match


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
    assert summary["mode"] == "fallback" and ports[0]["registry"]["tier"] == TIER_REGISTERED
    rows = trace_rows(isolated / "trace.jsonl")
    assert [(r["action"], r["status"]) for r in rows] == [
        ("zetaris_query", "error"), ("zetaris_fallback", "fallback"), ("zetaris_query", "ok"),
        ("zetaris_query", "ok"), ("registry_check", TIER_REGISTERED)]
    assert all(r["agent_name"] == "ZetarisAdapter" for r in rows)
    assert "registry-test-key" not in (isolated / "trace.jsonl").read_text()


def test_outage_without_fallback_never_marks_official(monkeypatch):
    def down(self, *args, **kwargs):
        raise ZetarisUnavailable("fixture unreadable")
    monkeypatch.setattr(ZetarisClient, "get_registry_ports", down)
    ports, summary = check_ports([ST_GEORGE], BERMUDA, "reg-unavailable")
    assert summary["mode"] == "unavailable" and ports[0]["registry"]["tier"] == TIER3


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
    assert summary["mode"] == "live" and ports[0]["registry"]["tier"] == TIER_REGISTERED
