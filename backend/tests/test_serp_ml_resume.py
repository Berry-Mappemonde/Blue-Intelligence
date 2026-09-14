"""Iteration 14 tests — SERP classifier (ml_core/ml_routes), rank_candidates_ml (poe.py)
and PoE regressions (zones/ports). Auto-resume (poe_routes.schedule_job_resume)
is tested separately in E2E (backend restart required) — see /app/tests/ script.
"""
from pathlib import Path
import os
import sys
import time

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values(Path(__file__).resolve().parent.parent.parent / "frontend" / ".env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(scope="session")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# --- ml_routes module: model status ----------------------------------------
class TestMlStatus:
    def test_serp_classifier_present(self, api):
        r = api.get(f"{BASE_URL}/api/ml/status", timeout=60)
        assert r.status_code == 200
        models = r.json()["models"]
        assert "serp_classifier" in models
        m = models["serp_classifier"]
        assert m["n_pos"] >= 150, m  # depends on the number of sourced zones in the database
        assert m["accuracy"] >= 0.9, m
        assert m["f1"] >= 0.9, m
        assert m["n_neg"] >= 195


# --- Module ml_routes : POST /serp/predict ---------------------------------
class TestSerpPredict:
    def test_official_url_positive(self, api):
        r = api.post(f"{BASE_URL}/api/ml/serp/predict",
                     json={"url": "https://www.douane.gouv.fr/demarche/ports-entree"}, timeout=60)
        assert r.status_code == 200
        d = r.json()
        assert d["official_list"] is True
        assert d["score"] > 0.5
        assert d["url"].endswith("ports-entree")

    def test_touristic_url_negative(self, api):
        r = api.post(f"{BASE_URL}/api/ml/serp/predict",
                     json={"url": "https://www.tripadvisor.com/Attractions-g147-Activities-Fiji.html"},
                     timeout=60)
        assert r.status_code == 200
        d = r.json()
        assert d["official_list"] is False
        assert d["score"] < 0.5

    @pytest.mark.parametrize("url,expected", [
        ("https://www.dps.alaska.gov/ports-of-entry", True),
        ("https://myblog.wordpress.com/2019/07/sailing-holiday-in-greece", False),
    ])
    def test_discriminative(self, api, url, expected):
        r = api.post(f"{BASE_URL}/api/ml/serp/predict", json={"url": url}, timeout=60)
        assert r.status_code == 200
        assert r.json()["official_list"] is expected, r.text

    def test_missing_url_returns_400(self, api):
        r = api.post(f"{BASE_URL}/api/ml/serp/predict", json={}, timeout=30)
        assert r.status_code == 400
        assert "url" in r.json()["detail"]

    def test_blank_url_returns_400(self, api):
        r = api.post(f"{BASE_URL}/api/ml/serp/predict", json={"url": "   "}, timeout=30)
        assert r.status_code == 400

    def test_train_status_exposes_metrics(self, api):
        r = api.get(f"{BASE_URL}/api/ml/train/serp/status", timeout=30)
        assert r.status_code == 200
        st = r.json()
        metrics = st.get("summary") or st.get("model_on_disk")
        assert metrics, st
        assert metrics["n_pos"] >= 150
        assert metrics["accuracy"] >= 0.9


# --- ml_routes module: POST /train/serp (retrain) ---------------------------
class TestSerpTraining:
    def test_retrain_completes(self, api):
        r = api.post(f"{BASE_URL}/api/ml/train/serp", timeout=60)
        assert r.status_code == 202, r.text
        assert r.json()["status"] == "started"

        deadline = time.time() + 180
        st = {}
        while time.time() < deadline:
            st = api.get(f"{BASE_URL}/api/ml/train/serp/status", timeout=30).json()
            if not st.get("running") and st.get("summary"):
                break
            time.sleep(4)
        assert st.get("error") is None, st
        summary = st.get("summary")
        assert summary, st
        assert summary["n_pos"] >= 150, summary
        assert summary["accuracy"] >= 0.9, summary
        assert any("weak supervision" in line for line in st.get("logs_tail", [])), st.get("logs_tail")

    def test_conflict_when_already_running(self, api):
        # immediate rerun: either 202 (previous finished) or 409
        r = api.post(f"{BASE_URL}/api/ml/train/serp", timeout=60)
        assert r.status_code in (202, 409)
        if r.status_code == 202:
            r2 = api.post(f"{BASE_URL}/api/ml/train/serp", timeout=10)
            assert r2.status_code in (202, 409)
        # wait for the end so later tests are not polluted
        deadline = time.time() + 180
        while time.time() < deadline:
            if not api.get(f"{BASE_URL}/api/ml/train/serp/status", timeout=30).json().get("running"):
                break
            time.sleep(4)

    def test_predict_still_works_after_retrain(self, api):
        r = api.post(f"{BASE_URL}/api/ml/serp/predict",
                     json={"url": "https://www.douane.gouv.fr/demarche/ports-entree"}, timeout=60)
        assert r.status_code == 200
        assert r.json()["official_list"] is True


# --- UNIT poe.rank_candidates_ml -------------------------------------------
class TestRankCandidatesMl:
    @staticmethod
    def _cands():
        return [
            {"url": "https://www.tripadvisor.com/Attractions-g147-Activities-Fiji.html",
             "domain": "tripadvisor.com"},
            {"url": "https://www.douane.gouv.fr/demarche/ports-entree", "domain": "douane.gouv.fr"},
            {"url": "https://www.dps.alaska.gov/ports-of-entry", "domain": "alaska.gov"},
        ]

    def test_gov_ranked_before_tripadvisor(self):
        from app.services import poe_pipeline as poe
        logs = []
        ranked = poe.rank_candidates_ml(self._cands(), logs.append)
        domains = [c["domain"] for c in ranked]
        assert domains.index("douane.gouv.fr") < domains.index("tripadvisor.com"), domains
        assert domains.index("alaska.gov") < domains.index("tripadvisor.com"), domains
        assert logs and "classifieur SERP" in logs[0]

    def test_single_candidate_returned_as_is(self):
        from app.services import poe_pipeline as poe
        one = self._cands()[:1]
        assert poe.rank_candidates_ml(one, lambda m: None) == one
        assert poe.rank_candidates_ml([], lambda m: None) == []

    def test_low_score_dropped_only_with_alternatives(self):
        from app.services import poe_pipeline as poe
        cands = self._cands() + [
            {"url": "https://booking.example.org/hotel/deals/9999", "domain": "booking.example.org"},
            {"url": "https://www.cbp.gov/travel/pleasure-boats/ports-of-entry", "domain": "cbp.gov"},
        ]
        ranked = poe.rank_candidates_ml(cands, lambda m: None)
        assert len(ranked) >= 3
        assert ranked[0]["domain"].endswith(".gov") or ".gouv" in ranked[0]["domain"]


# --- PoE REGRESSION --------------------------------------------------------
class TestPoeRegression:
    def test_zones_count(self, api):
        r = api.get(f"{BASE_URL}/api/poe/zones", timeout=120)
        assert r.status_code == 200
        data = r.json()
        assert data["count"] == 285, data["count"]
        assert len(data["items"]) == 285, len(data["items"])
        assert data["summary"]["total_ports"] >= 1169  # baseline = seed/

    def test_ports_all_osm_validated(self, api):
        r = api.get(f"{BASE_URL}/api/poe/ports", timeout=180)
        assert r.status_code == 200
        feats = r.json()["features"]
        assert len(feats) >= 1169  # baseline = seed/, len(feats)
        missing = [f["properties"].get("name") for f in feats
                   if f["properties"].get("osm_confidence") is None]
        assert not missing, f"{len(missing)} PoE sans osm_confidence: {missing[:5]}"

    def test_no_mongo_object_id_leak(self, api):
        r = api.get(f"{BASE_URL}/api/poe/ports", timeout=180)
        assert "_id" not in r.text[:5000] or '"_id":{"$oid"' not in r.text
