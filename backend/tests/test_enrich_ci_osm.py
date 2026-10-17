"""L'enrichissement OSM de CI reste sur la base jetable et n'invente pas de score."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "enrich_ci_osm.py"
_spec = importlib.util.spec_from_file_location("enrich_ci_osm", _SCRIPT)
enrich = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
sys.modules["enrich_ci_osm"] = enrich
_spec.loader.exec_module(enrich)


def test_refuses_non_ci_targets():
    with pytest.raises(SystemExit):
        enrich.assert_ci_target("mongodb+srv://u:p@cluster.mongodb.net/app", "bi_ci")
    with pytest.raises(SystemExit):
        enrich.assert_ci_target("mongodb://135.125.226.16:27017", "bi_ci")
    with pytest.raises(SystemExit):
        enrich.assert_ci_target("mongodb://127.0.0.1:27017", "blue_intelligence")


def test_zero_match_stores_a_real_zero_without_touching_identity():
    port = {
        "_id": "p1",
        "name": "Nowhere Dock",
        "lat": 1.25,
        "lon": -2.5,
        "source_urls": [],
    }
    updates = enrich.osm_updates(port, [])
    assert updates["osm_confidence"] == 0.0
    assert updates["osm_tags"] == []
    assert updates["osm_matches"] == 0
    assert updates["osm_checked_at"]
    assert "name" not in updates
    assert "lat" not in updates
    assert "lon" not in updates
    assert port["name"] == "Nowhere Dock"


def test_harbour_tag_uses_the_product_score():
    updates = enrich.osm_updates(
        {"_id": "p2", "name": "Harbour", "lat": 10.0, "lon": 20.0, "source_urls": []},
        [{"tags": {"harbour": "yes"}}],
    )
    assert updates["osm_confidence"] == 0.5
    assert "harbour" in updates["osm_tags"]


def test_cache_rejects_a_moved_port():
    cache = {"p1": {"lat": 1.0, "lon": 2.0, "elements": [{"tags": {"harbour": "yes"}}]}}
    assert enrich._cached_elements({"_id": "p1", "lat": 1.0, "lon": 2.0}, cache) == [
        {"tags": {"harbour": "yes"}},
    ]
    assert enrich._cached_elements({"_id": "p1", "lat": 9.0, "lon": 2.0}, cache) is None
    assert enrich._cached_elements({"_id": "absent", "lat": 1.0, "lon": 2.0}, cache) is None
