"""Public report URLs, report listing auth, and settings bounds."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "bi_test_report_settings")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

from app.core import public_url, report_rate
from app.main import app
from app.routers.projects import report_email_html

client = TestClient(app)

_PUBLIC = "https://1.1.1.1/reef"


@pytest.fixture(autouse=True)
def _reset_report_rate():
    report_rate.reset()
    yield
    report_rate.reset()


class _Coll:
    def __init__(self, docs=None):
        self.docs = [dict(d) for d in (docs or [])]
        self.writes = []

    async def insert_one(self, doc):
        self.docs.append(dict(doc))

    async def update_one(self, q, upd, upsert=False):
        self.writes.append((q, upd))

    def find(self, q=None):
        return self

    def sort(self, *a, **k):
        return self

    async def to_list(self, n=None):
        rows = [dict(d) for d in self.docs]
        return rows if n is None else rows[:n]


class _ReportDB:
    def __init__(self):
        self.reported_projects = _Coll()
        self.deeplink_pages = _Coll()


class _Settings:
    def __init__(self):
        self.doc = {"_id": "global", "extract_concurrency": 2, "min_zoom": 2}
        self.updates = []

    async def find_one(self, q):
        return dict(self.doc)

    async def update_one(self, q, upd, upsert=False):
        written = dict(upd["$set"])
        self.updates.append(written)
        self.doc.update(written)


class _SettingsDB:
    def __init__(self):
        self.settings = _Settings()


def _patch_reports(monkeypatch) -> _ReportDB:
    import app.routers.projects as projects
    fake = _ReportDB()
    monkeypatch.setattr(projects, "db", fake)
    monkeypatch.setattr(projects.swarm, "running", False)
    return fake


def _patch_settings(monkeypatch) -> _Settings:
    import app.routers.misc as misc
    from app.config import DEFAULT_SETTINGS
    fake = _SettingsDB()

    async def get_settings():
        return {**DEFAULT_SETTINGS, **fake.settings.doc}

    monkeypatch.setattr(misc, "db", fake)
    monkeypatch.setattr(misc, "get_settings", get_settings)
    return fake.settings


def test_public_url_rejects_non_public_targets():
    blocked = [
        "http://169.254.169.254/latest/meta-data/",
        "http://127.0.0.1:27017/",
        "http://10.1.2.3/",
        "http://192.168.0.5/admin",
        "http://172.16.0.1/",
        "http://0.0.0.0/",
        "http://224.0.0.1/",
        "http://240.0.0.1/",
        "http://100.64.0.1/",
        "http://[::1]/",
        "http://[fe80::1]/",
        "http://[fc00::1]/",
        "http://[fd12:3456::1]/",
        "http://[ff02::1]/",
        "http://[::]/",
        "http://localhost/latest",
        "http://foo.localhost/a",
        "http://printer.local/a",
        "http://metadata.google.internal/",
        "http://user:pass@1.1.1.1/",
        "http://1.1.1.1:27017/",
        "http://2130706433/",
        "http://127.1/",
        "ftp://1.1.1.1/a",
        "httpx://1.1.1.1/",
        "file:///etc/passwd",
        "http://1.1.1.1/a b",
        "http://1.1.1.1/a\nb",
    ]
    for url in blocked:
        assert public_url.public_url_error(url), url
    assert public_url.public_url_error("https://1.1.1.1/reef") is None
    assert public_url.public_url_error("https://8.8.8.8/") is None
    assert public_url.public_url_error("http://[2001:4860:4860::8888]/") is None
    assert public_url.public_url_error("https://1.1.1.1:443/a") is None
    assert public_url.public_url_error("http://1.1.1.1:80/a") is None


def test_dns_answer_with_a_private_address_is_rejected(monkeypatch):
    def fake_getaddrinfo(host, port, *a, **k):
        return [(None, None, None, None, ("10.1.2.3", 0))]

    monkeypatch.setattr(public_url.socket, "getaddrinfo", fake_getaddrinfo)
    assert public_url.public_url_error("https://evil.example/secret")


def test_dns_answer_with_only_public_addresses_is_allowed(monkeypatch):
    def fake_getaddrinfo(host, port, *a, **k):
        return [
            (None, None, None, None, ("8.8.8.8", 0)),
            (None, None, None, None, ("2001:4860:4860::8888", 0)),
        ]

    monkeypatch.setattr(public_url.socket, "getaddrinfo", fake_getaddrinfo)
    assert public_url.public_url_error("https://ocean.example/projects/1") is None


def test_report_rejects_internal_urls_and_does_not_store(monkeypatch):
    monkeypatch.setenv("ADMIN_KEY", "sesame")
    fake = _patch_reports(monkeypatch)
    samples = [
        "http://169.254.169.254/latest/meta-data/",
        "http://127.0.0.1:27017/",
        "http://[::1]/",
        "http://[fe80::1]/",
        "http://localhost/admin",
        "http://db.internal/mongo",
        "ftp://1.1.1.1/file",
        "http://user@1.1.1.1/",
        "http://1.1.1.1:8080/",
    ]
    for url in samples:
        r = client.post("/api/report-project", json={"name": "Probe", "url": url, "description": "x"})
        assert r.status_code == 422, (url, r.status_code, r.text)
    assert fake.reported_projects.docs == []
    assert fake.deeplink_pages.writes == []


def test_report_legacy_400_and_length_limits(monkeypatch):
    fake = _patch_reports(monkeypatch)
    bad_url = client.post("/api/report-project", json={"name": "TEST_x", "url": "not-a-url", "description": "d"})
    assert bad_url.status_code == 400
    empty = client.post("/api/report-project", json={"name": "  ", "url": _PUBLIC, "description": ""})
    assert empty.status_code == 400
    long_name = client.post("/api/report-project", json={"name": "n" * 201, "url": _PUBLIC})
    assert long_name.status_code == 422
    long_url = client.post("/api/report-project", json={"name": "n", "url": "https://1.1.1.1/" + ("a" * 2048)})
    assert long_url.status_code == 422
    long_desc = client.post(
        "/api/report-project",
        json={"name": "n", "url": _PUBLIC, "description": "d" * 5001},
    )
    assert long_desc.status_code == 422
    assert fake.reported_projects.docs == []
    assert fake.deeplink_pages.writes == []


def test_report_rate_limit(monkeypatch):
    fake = _patch_reports(monkeypatch)
    statuses = []
    for i in range(report_rate.LIMIT + 2):
        r = client.post("/api/report-project", json={"name": f"Reef {i}", "url": f"{_PUBLIC}?n={i}"})
        statuses.append(r.status_code)
    assert statuses[:report_rate.LIMIT] == [200] * report_rate.LIMIT
    assert statuses[report_rate.LIMIT:] == [429, 429]
    assert len(fake.reported_projects.docs) == report_rate.LIMIT
    assert len(fake.deeplink_pages.writes) == report_rate.LIMIT


def test_report_email_escapes_user_fields(monkeypatch):
    html = report_email_html(
        'Reef <img src=x onerror=alert(1)>',
        "https://1.1.1.1/a?q=1&b=2",
        "<script>alert(1)</script>",
    )
    assert "<script>" not in html
    assert "<img" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "q=1&amp;b=2" in html
    assert 'href="https://1.1.1.1/a?q=1&amp;b=2"' in html

    import types
    sent = {}

    class _Emails:
        @staticmethod
        def send(params):
            sent.update(params)
            return {"id": "email_1"}

    fake_mod = types.ModuleType("resend")
    fake_mod.Emails = _Emails
    fake_mod.api_key = ""
    monkeypatch.setitem(sys.modules, "resend", fake_mod)
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    _patch_reports(monkeypatch)
    name = "Line\n<script>"
    r = client.post("/api/report-project", json={
        "name": name,
        "url": _PUBLIC,
        "description": "<b>bold</b>",
    })
    assert r.status_code == 200, r.text
    assert r.json()["email_status"] == "sent"
    assert "\n" not in sent["subject"]
    assert "<script>" not in sent["html"]
    assert "&lt;script&gt;" in sent["html"]
    assert "&lt;b&gt;bold&lt;/b&gt;" in sent["html"]


def test_reports_require_admin_key(monkeypatch):
    import app.routers.projects as projects
    fake = _ReportDB()
    fake.reported_projects.docs = [{
        "_id": "rep-1",
        "name": "Kept",
        "url": "https://1.1.1.1/kept",
        "description": "hidden",
        "email_status": "skipped",
    }]
    monkeypatch.setattr(projects, "db", fake)

    monkeypatch.delenv("ADMIN_KEY", raising=False)
    open_dev = client.get("/api/reports")
    assert open_dev.status_code == 200

    monkeypatch.setenv("ADMIN_KEY", "sesame")
    missing = client.get("/api/reports")
    assert missing.status_code == 401
    wrong = client.get("/api/reports", headers={"X-Admin-Key": "nope"})
    assert wrong.status_code == 401
    ok = client.get("/api/reports", headers={"X-Admin-Key": "sesame"})
    assert ok.status_code == 200
    body = ok.json()
    assert body[0]["id"] == "rep-1"
    assert body[0]["name"] == "Kept"
    assert body[0]["url"] == "https://1.1.1.1/kept"
    assert "_id" not in body[0]


@pytest.mark.parametrize("payload", [
    {"claude_budget_usd": 1000000},
    {"min_zoom": 0},
    {"min_zoom": 9},
    {"max_markers": 6000},
    {"max_markers": 49},
    {"extract_concurrency": -5},
    {"extract_concurrency": 17},
    {"tinyfish_agents": 999},
    {"tinyfish_agents": 0},
    {"extract_concurrency": 2, "tinyfish_agents": 999},
])
def test_settings_out_of_range_rejected_and_not_written(monkeypatch, payload):
    monkeypatch.delenv("ADMIN_KEY", raising=False)
    store = _patch_settings(monkeypatch)
    before = dict(store.doc)
    r = client.put("/api/settings", json=payload)
    assert r.status_code == 422, r.text
    assert store.updates == []
    assert store.doc == before


def test_settings_in_range_is_stored(monkeypatch):
    monkeypatch.delenv("ADMIN_KEY", raising=False)
    store = _patch_settings(monkeypatch)
    payload = {
        "claude_budget_usd": 12.5,
        "min_zoom": 1,
        "max_markers": 5000,
        "extract_concurrency": 4,
        "tinyfish_agents": 2,
        "follow_the_money": False,
        "llm_provider": "auto",
    }
    r = client.put("/api/settings", json=payload)
    assert r.status_code == 200, r.text
    assert store.updates == [payload]
    body = r.json()
    assert body["claude_budget_usd"] == 12.5
    assert body["min_zoom"] == 1
    assert body["max_markers"] == 5000
    assert body["extract_concurrency"] == 4
    assert body["tinyfish_agents"] == 2
    assert body["follow_the_money"] is False


def test_deeplink_cache_skips_non_public_urls_and_keeps_them(monkeypatch):
    import app.services.swarm_pipeline as sp
    from app.services.swarm_pipeline import Swarm
    from tests.test_project_runs import _FakeDB

    monkeypatch.setattr(sp, "MASTER_SEEDS", [])
    monkeypatch.setattr(sp, "seeds_for_run", lambda seeds: [])
    processed = []

    async def worker(idx):
        while True:
            try:
                item = await asyncio.wait_for(sw.queue.get(), timeout=0.2)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                return
            try:
                processed.append(item.get("url"))
            finally:
                try:
                    sw.queue.task_done()
                except ValueError:
                    pass

    sw = Swarm(_FakeDB())
    sw.running = True
    sw.mode = "full"
    sw.force_rescan = False
    sw.run_id = "20261018-report-guard"
    sw.settings = {
        "discover_concurrency": 1,
        "extract_concurrency": 1,
        "full_max_urls_per_seed": 10,
        "tinyfish_agents": 1,
        "allow_tinyfish_agent": False,
    }
    private = "http://169.254.169.254/latest/meta-data/"
    loopback = "http://127.0.0.1:27017/"
    public = "https://cached.org/projects/old"
    sw.db.deeplink_pages.docs = [
        {"url": private, "funder": "X", "source": "user-report"},
        {"url": loopback, "funder": "X", "source": "user-report"},
        {"url": public, "funder": "X", "source": "cache"},
    ]
    monkeypatch.setattr(sw, "_extract_worker", worker)

    asyncio.run(sw._run())

    assert processed == [public]
    kept = [d["url"] for d in sw.db.deeplink_pages.docs]
    assert private in kept
    assert loopback in kept
    assert public in kept
    msgs = " ".join(e["msg"] for e in sw.logs)
    assert "skip non-public URL" in msgs
    assert "not fetched, kept" in msgs
    assert "169.254.169.254" in msgs
    assert "127.0.0.1" in msgs
    assert "not yet extracted → queued" in msgs
