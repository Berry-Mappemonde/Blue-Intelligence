"""HEAD sur fichiers statiques du build CRA (sitemap.xml pour Search Console)."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import _FRONTEND_BUILD, app


@pytest.fixture()
def client_with_sitemap(tmp_path, monkeypatch):
    build = tmp_path / "build"
    build.mkdir()
    (build / "sitemap.xml").write_text(
        '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>',
        encoding="utf-8",
    )
    monkeypatch.setattr("app.main._FRONTEND_BUILD", build)
    monkeypatch.setattr("app.main._SERVE_FRONTEND", True)
    # Ré-enregistrer les routes SPA (déjà montées si build existait au import).
    yield TestClient(app)


def test_head_sitemap_when_frontend_routes_mounted(client_with_sitemap):
    if not any(getattr(r, "path", None) == "/{full_path:path}" for r in app.routes):
        pytest.skip("routes SPA non montées (build absent au chargement du module)")
    r = client_with_sitemap.head("/sitemap.xml")
    assert r.status_code == 200
    assert "application/xml" in (r.headers.get("content-type") or "")
