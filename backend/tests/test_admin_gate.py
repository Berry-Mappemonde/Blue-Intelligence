"""Admin gate — ADMIN_KEY required on /api/* writes and sensitive
reads (review, admin). Without ADMIN_KEY (dev), everything stays open.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

from app.main import app

# No context manager: startup events (Mongo indexes) are not
# triggered; the middleware is tested without a database.
client = TestClient(app)


def test_open_when_no_admin_key(monkeypatch):
    monkeypatch.delenv("ADMIN_KEY", raising=False)
    r = client.get("/api/admin/check")
    assert r.status_code == 200
    assert r.json()["admin_required"] is False


def test_writes_and_review_require_key(monkeypatch):
    monkeypatch.setenv("ADMIN_KEY", "sesame")
    assert client.get("/api/admin/check").status_code == 401
    assert client.put("/api/settings", json={"min_zoom": 3}).status_code == 401
    assert client.get("/api/review/queue").status_code == 401
    assert client.post("/api/swarm/deploy", json={}).status_code == 401


def test_correct_key_unlocks(monkeypatch):
    monkeypatch.setenv("ADMIN_KEY", "sesame")
    ok = client.get("/api/admin/check", headers={"X-Admin-Key": "sesame"})
    assert ok.status_code == 200
    assert ok.json()["admin_required"] is True
    bad = client.get("/api/admin/check", headers={"X-Admin-Key": "faux"})
    assert bad.status_code == 401


def test_public_report_stays_open(monkeypatch):
    monkeypatch.setenv("ADMIN_KEY", "sesame")
    # Public project reporting must never be blocked by the
    # admin gate (422 validation expected here, not 401).
    r = client.post("/api/report-project", json={})
    assert r.status_code != 401
