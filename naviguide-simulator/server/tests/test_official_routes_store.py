"""Lot RF2 — routes officielles : stock, en préparation, aucun fournisseur sur la requête."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import official_store
import voyage_store


def _boom(*_a, **_k):
    raise AssertionError("fournisseur externe appelé sur le chemin HTTP")


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("NAVIGUIDE_OFFICIAL_STORE_DIR", str(tmp_path / "store"))
    monkeypatch.setenv("NAVIGUIDE_VOYAGE_DIR", str(tmp_path / "voyages"))
    monkeypatch.setenv("NAVIGUIDE_OFFICIAL_WORKER", "0")
    monkeypatch.setenv("NAVIGUIDE_SEED_OFFICIAL", "0")
    monkeypatch.delenv("SIMULATOR_MONGO_URL", raising=False)
    voyage_store._DIR = tmp_path / "voyages"
    official_store.reset()
    official_store.configure(disk_dir=tmp_path / "store", mongo_url="")
    from main import app
    return TestClient(app)


def _block_externals(monkeypatch):
    import climatology_atlas
    import voyage_api
    import ensemble_eta
    import plan_review
    import film_script
    import ici_engine
    import story_cascade

    monkeypatch.setattr(climatology_atlas, "atlas_wind_at_dt", _boom)
    monkeypatch.setattr(climatology_atlas, "prefetch_points", _boom)
    monkeypatch.setattr(voyage_api, "_climo_clock", _boom)
    monkeypatch.setattr(ensemble_eta, "preheat_official_eta", _boom)
    monkeypatch.setattr(ensemble_eta, "peek_official_eta", _boom)
    monkeypatch.setattr(plan_review, "review_official", _boom)
    monkeypatch.setattr(plan_review, "comment_plan", _boom)
    monkeypatch.setattr(film_script, "official_film", _boom)
    monkeypatch.setattr(ici_engine, "fill_dossier", _boom)
    monkeypatch.setattr(story_cascade, "cascade_text", _boom)


def test_missing_entry_is_preparing_not_500(client, monkeypatch):
    _block_externals(monkeypatch)
    r = client.get("/voyage/official/moments")
    assert r.status_code == 200
    assert r.json()["status"] == "preparing"
    assert r.json()["moments"] == []

    r = client.get("/voyage/official/eta", params={"stop": "Nouméa"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "preparing"
    assert body["members"] == 0

    r = client.get("/voyage/official/plan-review")
    assert r.status_code == 200
    assert r.json()["status"] == "preparing"
    assert r.json()["legs"] == []

    r = client.get("/voyage/official/film?lang=fr&seconds=150")
    assert r.status_code == 200
    assert r.json()["status"] == "preparing"
    assert r.json()["chapters"] == []

    r = client.get("/voyage/official/clock")
    assert r.status_code == 200
    assert r.json()["status"] == "preparing"


def test_seeded_store_served_while_externals_explode(client, tmp_path, monkeypatch):
    official_store.seed_disk(tmp_path / "store")
    _block_externals(monkeypatch)

    moments = client.get("/voyage/official/moments")
    assert moments.status_code == 200
    assert moments.json()["count"] >= 1
    assert moments.json()["status"] == "ready"

    eta = client.get("/voyage/official/eta", params={"stop": "Nouméa"})
    assert eta.status_code == 200
    assert eta.json()["members"] > 0

    review = client.get("/voyage/official/plan-review")
    assert review.status_code == 200
    assert review.json()["legs"][0]["to"]

    film = client.get("/voyage/official/film?lang=fr&seconds=150")
    assert film.status_code == 200
    assert "Saint-Maur" in film.json()["chapters"][0]["text"]

    clock = client.get("/voyage/official/clock")
    assert clock.status_code == 200
    assert clock.json()["t0"].startswith("2026-05-15")


def test_put_official_does_not_compute_clock(client, monkeypatch):
    import voyage_api

    monkeypatch.setattr(voyage_api, "_climo_clock", _boom)
    r = client.put("/voyage/official", json={
        "t0": "2026-05-15T08:00:00Z",
        "points": [
            {"lat": 46.15, "lon": -1.16, "cumNm": 0, "filmCum": 0, "jump": False, "nonMaritime": False},
            {"lat": 40.0, "lon": -15.0, "cumNm": 650, "filmCum": 650, "jump": False, "nonMaritime": False},
        ],
        "marks": [],
    })
    assert r.status_code == 200
    voy = voyage_store.load_voyage("berry-mappemonde-2026-officiel")
    assert voy is not None
    assert not (voy.get("clock") or {}).get("vertices")
