"""GET /api/health — public JSON probe: status, memory, uptime."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

from app.main import app
from app.routers import health

# No context manager: startup (Mongo indexes, grids) stays off.
client = TestClient(app)

_KEYS = {"status", "memory_used_pct", "uptime_s"}


def _patch_probe(monkeypatch, memory: float | None, db_ok: bool) -> None:
    monkeypatch.setattr(health, "memory_used_pct", lambda: memory)

    async def _ping() -> bool:
        return db_ok

    monkeypatch.setattr(health, "db_ping_ok", _ping)


def test_health_returns_exactly_three_keys(monkeypatch):
    _patch_probe(monkeypatch, 12.5, True)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert set(body) == _KEYS
    assert body["status"] == "ok"
    assert body["memory_used_pct"] == 12.5
    assert isinstance(body["memory_used_pct"], float)
    assert isinstance(body["uptime_s"], int)
    assert body["uptime_s"] >= 0


def test_health_degraded_when_memory_high(monkeypatch):
    _patch_probe(monkeypatch, 85.0, True)
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == _KEYS
    assert body["status"] == "degraded"
    assert body["memory_used_pct"] == 85.0


def test_health_degraded_when_db_ping_fails(monkeypatch):
    _patch_probe(monkeypatch, 10.0, False)
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == _KEYS
    assert body["status"] == "degraded"
    assert body["memory_used_pct"] == 10.0
    assert "secret" not in response.text
    assert "Traceback" not in response.text


def test_health_unknown_memory_is_null_not_degraded(monkeypatch):
    _patch_probe(monkeypatch, None, True)
    body = client.get("/api/health").json()
    assert set(body) == _KEYS
    assert body["memory_used_pct"] is None
    assert body["status"] == "ok"
    _patch_probe(monkeypatch, None, False)
    assert client.get("/api/health").json()["status"] == "degraded"


def test_memory_probe_unreadable_returns_none(tmp_path, monkeypatch):
    missing = tmp_path / "missing"
    assert health.cgroup_memory_used_pct(missing, tmp_path) is None
    assert health.rss_memory_used_pct(missing, missing) is None
    monkeypatch.setattr(health, "cgroup_memory_used_pct", lambda *_a, **_k: None)
    monkeypatch.setattr(health, "rss_memory_used_pct", lambda *_a, **_k: None)
    assert health.memory_used_pct() is None


def test_health_stays_public_with_admin_key(monkeypatch):
    monkeypatch.setenv("ADMIN_KEY", "sesame")
    _patch_probe(monkeypatch, 10.0, True)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    locked = client.get("/api/admin/check")
    assert locked.status_code == 401


def test_cgroup_memory_preferred_when_readable(tmp_path):
    proc = tmp_path / "cgroup"
    proc.write_text("0::/system.slice/blue-intelligence.service\n", encoding="utf-8")
    root = tmp_path / "sys"
    service = root / "system.slice" / "blue-intelligence.service"
    service.mkdir(parents=True)
    (service / "memory.current").write_text("1610612736\n", encoding="utf-8")
    (service / "memory.max").write_text("3221225472\n", encoding="utf-8")
    assert health.cgroup_memory_used_pct(proc, root) == 50.0


def test_cgroup_unlimited_falls_back_to_rss(tmp_path, monkeypatch):
    proc = tmp_path / "cgroup"
    proc.write_text("0::/svc\n", encoding="utf-8")
    root = tmp_path / "sys"
    service = root / "svc"
    service.mkdir(parents=True)
    (service / "memory.current").write_text("100\n", encoding="utf-8")
    (service / "memory.max").write_text("max\n", encoding="utf-8")
    assert health.cgroup_memory_used_pct(proc, root) is None

    status = tmp_path / "status"
    meminfo = tmp_path / "meminfo"
    status.write_text("Name:\tpython\nVmRSS:\t  1024 kB\n", encoding="utf-8")
    meminfo.write_text("MemTotal:        8192 kB\n", encoding="utf-8")
    real_rss = health.rss_memory_used_pct
    monkeypatch.setattr(health, "cgroup_memory_used_pct", lambda *_a, **_k: None)
    monkeypatch.setattr(
        health, "rss_memory_used_pct", lambda *_a, **_k: real_rss(status, meminfo)
    )
    assert health.memory_used_pct() == 12.5


def test_db_ping_failure_stays_boolean(monkeypatch):
    class _Admin:
        async def command(self, *args, **kwargs):
            raise RuntimeError("mongodb://user:secret@db.internal:27017 down")

    class _Client:
        admin = _Admin()

    import app.db

    monkeypatch.setattr(app.db, "client", _Client())
    assert asyncio.run(health.db_ping_ok()) is False


def test_db_ping_timeout_is_one_second(monkeypatch):
    seen: dict[str, float | None] = {}

    class _Admin:
        async def command(self, *args, **kwargs):
            from pymongo._csot import get_timeout

            seen["csot"] = get_timeout()
            return {"ok": 1}

    class _Client:
        admin = _Admin()

    import app.db

    monkeypatch.setattr(app.db, "client", _Client())
    assert asyncio.run(health.db_ping_ok()) is True
    assert seen["csot"] == 1.0
