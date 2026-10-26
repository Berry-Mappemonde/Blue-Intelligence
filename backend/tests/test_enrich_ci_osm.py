"""L'enrichissement OSM de CI reste sur la base jetable et n'invente pas de score."""
from __future__ import annotations

import importlib.util
import json
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


# ---------------------------------------------------------------- mode offline (CI_OSM_OFFLINE=1)
class TestOfflineMode:
    def test_offline_missing_port_counts_as_failed_no_network(self, monkeypatch):
        """En mode offline, un port absent du cache est un échec et
        aucune fonction réseau n'est appelée."""
        called = []

        def fake_overpass(lat, lon):
            called.append((lat, lon))
            raise AssertionError("overpass_around ne doit pas être appelé en offline")

        monkeypatch.setattr(enrich, "overpass_around", fake_overpass)
        monkeypatch.setenv("CI_OSM_OFFLINE", "1")

        cache = {}  # cache vide : tous les ports sont absents
        stats = {"checked": 0, "failed": 0, "cache": 0, "missing": 0, "errors": []}

        import asyncio

        async def run():
            await enrich._validate_port(
                None, {"_id": "p1", "name": "X", "lat": 1.0, "lon": 2.0},
                None, cache, stats, offline=True,
            )

        asyncio.run(run())

        assert called == [], "aucune requête Overpass en mode offline"
        assert stats["missing"] == 1
        assert stats["checked"] == 0
        assert cache == {}, "rien n'est ajouté au cache en offline"

    def test_offline_cached_port_is_validated(self, monkeypatch):
        """En mode offline, un port présent dans le cache est validé."""
        called = []

        def fake_overpass(lat, lon):
            called.append((lat, lon))
            raise AssertionError("overpass_around ne doit pas être appelé en offline")

        monkeypatch.setattr(enrich, "overpass_around", fake_overpass)
        monkeypatch.setenv("CI_OSM_OFFLINE", "1")

        cache = {
            "p1": {
                "lat": 1.0,
                "lon": 2.0,
                "elements": [{"tags": {"harbour": "yes"}}],
            }
        }
        stats = {"checked": 0, "failed": 0, "cache": 0, "missing": 0, "errors": []}

        import asyncio

        class FakePorts:
            async def update_one(self, *a, **k):
                pass

        class FakeDb:
            poe_ports = FakePorts()

        async def run():
            await enrich._validate_port(
                FakeDb(), {"_id": "p1", "name": "X", "lat": 1.0, "lon": 2.0},
                None, cache, stats, offline=True,
            )

        asyncio.run(run())

        assert called == [], "aucune requête Overpass en mode offline"
        assert stats["cache"] == 1
        assert stats["checked"] == 1


# ---------------------------------------------------------------- build_osm_snapshot (pas de réseau)
def _load_build_script():
    script = Path(__file__).resolve().parents[1] / "scripts" / "build_osm_snapshot.py"
    spec = importlib.util.spec_from_file_location("build_osm_snapshot", script)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["build_osm_snapshot"] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


build = _load_build_script()


def test_build_snapshot_does_not_store_failures(tmp_path, monkeypatch):
    """build_osm_snapshot ne stocke rien pour un port en échec."""
    cache_file = tmp_path / "cache.json"

    calls = []

    async def fake_overpass(lat, lon):
        calls.append((lat, lon))
        raise RuntimeError("overpass down")

    monkeypatch.setattr(build, "overpass_around", fake_overpass)

    import asyncio

    async def run():
        return await asyncio.wait_for(
            build.main(cache_file, budget_s=1), timeout=5
        )

    rc = asyncio.run(run())

    assert rc == 2  # incomplet -> exit 2
    data = json.loads(cache_file.read_text(encoding="utf-8"))
    assert data["ports"] == {}, "aucun port stocké en cas d'échec"


def test_build_snapshot_resumes_skips_cached(tmp_path, monkeypatch):
    """Un port déjà présent dans le cache n'est pas re-interrogé."""
    cache_file = tmp_path / "cache.json"
    cache_file.write_text(
        json.dumps(
            {
                "version": 1,
                "ports": {
                    "p1": {"lat": 1.0, "lon": 2.0, "elements": [{"tags": {"harbour": "yes"}}]}
                },
            }
        ),
        encoding="utf-8",
    )

    # On ne teste que sur 3 ports (dont p1 deja en cache) pour rester rapide.
    monkeypatch.setattr(
        build,
        "load_ports",
        lambda: [
            {"_id": "p1", "name": "Port 1", "lat": 1.0, "lon": 2.0},
            {"_id": "p2", "name": "Port 2", "lat": 3.0, "lon": 4.0},
            {"_id": "p3", "name": "Port 3", "lat": 5.0, "lon": 6.0},
        ],
    )

    calls = []

    async def fake_overpass(lat, lon):
        calls.append((lat, lon))
        return [{"tags": {"leisure": "marina"}}]

    monkeypatch.setattr(build, "overpass_around", fake_overpass)
    monkeypatch.setattr(build, "POLITE_DELAY_S", 0)

    import asyncio

    async def run():
        return await asyncio.wait_for(
            build.main(cache_file, budget_s=60), timeout=10
        )

    rc = asyncio.run(run())

    assert rc == 0
    data = json.loads(cache_file.read_text(encoding="utf-8"))
    assert "p1" in data["ports"]
    assert data["ports"]["p1"]["elements"] == [{"tags": {"harbour": "yes"}}]
    # p2 et p3 ont ete interroges (mockes), p1 pas re-interroge
    assert calls == [(3.0, 4.0), (5.0, 6.0)], calls
