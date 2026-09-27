"""Lot RF2 — stock officiel : une interface, deux dos (disque + mongomock)."""
from __future__ import annotations

import pytest

import official_store as store


def _backends(tmp_path):
    disk = store.OfficialStore(store.DiskBackend(tmp_path / "disk"))
    mongo = store.OfficialStore(store.MongoBackend(
        "mongodb://127.0.0.1:9/naviguide_simulator",
        client=store.mongo_test_client(),
    ))
    return [("disk", disk), ("mongo", mongo)]


@pytest.fixture(params=["disk", "mongo"])
def backend_store(request, tmp_path):
    if request.param == "disk":
        s = store.OfficialStore(store.DiskBackend(tmp_path / "disk"))
    else:
        s = store.OfficialStore(store.MongoBackend(
            "mongodb://127.0.0.1:9/naviguide_simulator",
            client=store.mongo_test_client(),
        ))
    store.configure(backend=s.backend)
    return s


def test_same_key_is_stable():
    a = store.make_key("berry-mappemonde-2026-officiel", "2026-05-15T08:00:00Z", "2026-09-26")
    b = store.make_key("berry-mappemonde-2026-officiel", "2026-05-15T08:00:00Z", "2026-09-26")
    assert a == b
    assert a != store.make_key("berry-mappemonde-2026-officiel", "2026-05-15T08:00:00Z", "2026-09-27")


def test_put_get_timestamp_and_atomic_replace(backend_store):
    key = store.make_key(date="2026-09-26")
    first = backend_store.put("moments", {"status": "ready", "moments": [1]}, key=key)
    assert first["storedAt"]
    assert first["dataDate"] == "2026-09-26"
    assert backend_store.payload("moments", key=key)["moments"] == [1]
    backend_store.put("moments", {"status": "ready", "moments": [2]}, key=key)
    assert backend_store.payload("moments", key=key)["moments"] == [2]


def test_restart_rereads_same_bytes(tmp_path):
    root = tmp_path / "persist"
    a = store.OfficialStore(store.DiskBackend(root))
    key = store.make_key(date="2026-09-26")
    a.put("film", {"status": "ready", "chapters": [{"text": "Saint-Maur"}]}, key=key)
    b = store.OfficialStore(store.DiskBackend(root))
    assert b.payload("film", key=key)["chapters"][0]["text"] == "Saint-Maur"


def test_mongo_restart_rereads_same_doc():
    client = store.mongo_test_client()
    key = store.make_key(date="2026-09-26")
    a = store.OfficialStore(store.MongoBackend("mongodb://127.0.0.1:9/x", client=client))
    a.put("eta", {"status": "ready", "stops": {"Nouméa": {"members": 8}}}, key=key)
    b = store.OfficialStore(store.MongoBackend("mongodb://127.0.0.1:9/x", client=client))
    assert b.payload("eta", key=key)["stops"]["Nouméa"]["members"] == 8


def test_same_key_fill_does_not_recompute(backend_store, monkeypatch):
    monkeypatch.setenv("NAVIGUIDE_OFFICIAL_DATA_DATE", "2026-09-26")
    store.configure(backend=backend_store.backend)
    backend_store.put("moments", {"status": "ready", "moments": ["kept"]})
    calls = []

    def boom():
        calls.append(1)
        return {"status": "ready", "moments": ["new"]}

    done = store.fill_missing(fillers={"moments": boom})
    assert done["moments"] == "kept"
    assert calls == []
    assert backend_store.payload("moments")["moments"] == ["kept"]


def test_force_fill_replaces(backend_store, monkeypatch):
    monkeypatch.setenv("NAVIGUIDE_OFFICIAL_DATA_DATE", "2026-09-26")
    store.configure(backend=backend_store.backend)
    backend_store.put("plan_review", {"status": "ready", "legs": []})
    done = store.fill_missing(
        force=True,
        fillers={"plan_review": lambda: {"status": "ready", "legs": [{"to": "Nouméa"}]}},
    )
    assert done["plan_review"] == "wrote"
    assert backend_store.payload("plan_review")["legs"][0]["to"] == "Nouméa"


def test_seed_disk_writes_six_families(tmp_path):
    wrote = store.seed_disk(tmp_path / "seed")
    assert set(wrote) == set(store.FAMILIES)
    s = store.get_store()
    assert s.payload("moments")["moments"]
    assert s.payload("film")["films"]["fr:150"]["chapters"]
    assert s.payload("eta")["stops"]["Nouméa"]["members"] > 0
    assert s.payload("climo")["clock"]["vertices"]
    assert s.payload("ici")["bags"]
    assert s.payload("plan_review")["legs"]


def test_lookup_helpers_after_seed(tmp_path):
    store.seed_disk(tmp_path / "seed")
    assert store.official_clock()["t0"].startswith("2026-05-15")
    body = store.official_moments()
    assert body["count"] >= 1
    assert store.official_eta("Nouméa")["members"] > 0
    assert store.official_plan_review()["legs"]
    film = store.official_film("fr", 150)
    assert film["chapters"]
    shifted = store.apply_film_t0(film, "2025-05-15T08:00:00Z")
    assert "2025" in shifted["chapters"][0]["text"]
    assert "2026" not in shifted["chapters"][0]["text"]
