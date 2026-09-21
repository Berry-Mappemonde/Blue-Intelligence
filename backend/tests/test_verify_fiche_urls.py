"""Unit tests for fiche URL extraction and HTTP checker (mocked)."""
from __future__ import annotations

import sys
import unittest
from io import BytesIO
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from fiche_url_extract import (  # noqa: E402
    extract_from_geojson,
    extract_from_poe_zone_fiche,
    normalize_http_url,
)
from verify_fiche_urls import (  # noqa: E402
    UrlCheckResult,
    check_one_url,
    render_markdown,
)


class TestFicheUrlExtract(unittest.TestCase):
    def test_normalize_http_url(self):
        self.assertEqual(normalize_http_url("https://example.org/x"), "https://example.org/x")
        self.assertTrue(normalize_http_url("example.org/x",).startswith("https://"))
        self.assertIsNone(normalize_http_url("mailto:a@b.c"))
        self.assertIsNone(normalize_http_url(""))

    def test_extract_projects_and_poe_ports(self):
        fc = {
            "type": "FeatureCollection",
            "metadata": {"dataset": "projects"},
            "features": [{
                "properties": {"id": "p1", "title": "T", "url": "https://oceanfdn.org/x"},
            }],
        }
        refs = extract_from_geojson(Path("projects.geojson"), fc)
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].field, "url")

        poe = {
            "type": "FeatureCollection",
            "features": [{
                "properties": {
                    "id": "port1",
                    "name": "Marseille",
                    "source_urls": ["https://douane.gouv.fr/a", "https://douane.gouv.fr/b"],
                },
            }],
        }
        refs2 = extract_from_geojson(Path("ports_of_entry.geojson"), poe)
        self.assertEqual(len(refs2), 2)

    def test_extract_poe_zone_fiche_td_bu(self):
        fiche = {
            "mrgid": 17,
            "zone_name": "France hexagone",
            "url_td": {"url": "https://gov.example/list.pdf"},
            "sources_td": [{"url": "https://gov.example/list.pdf"}],
            "ports": [{
                "name": "Marseille",
                "url_bu": {"url": "https://gov.example/marseille"},
                "source_urls": ["https://gov.example/marseille"],
            }],
        }
        refs = extract_from_poe_zone_fiche(fiche)
        fields = {r.field for r in refs}
        self.assertIn("url_td", fields)
        self.assertIn("url_bu", fields)


class TestUrlChecker(unittest.TestCase):
    def test_check_one_url_ok(self):
        class FakeResp:
            def getcode(self):
                return 200

            def geturl(self):
                return "https://example.org/"

            def read(self, n=-1):
                return b"<html>ok</html>"

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

        with mock.patch("verify_fiche_urls.urlopen", lambda *a, **k: FakeResp()):
            res = check_one_url("https://example.org/", timeout=5, retries=0, user_agent="test")
        self.assertEqual(res.status, "ok")
        self.assertEqual(res.http_status, 200)

    def test_check_one_url_soft_fail_403(self):
        from urllib.error import HTTPError

        def boom(*a, **k):
            raise HTTPError("https://x/", 403, "Forbidden", hdrs=None, fp=BytesIO(b""))

        with mock.patch("verify_fiche_urls.urlopen", boom):
            res = check_one_url("https://x/", timeout=5, retries=0, user_agent="test")
        self.assertEqual(res.status, "soft_fail")

    def test_render_markdown_counts(self):
        refs = [
            type("R", (), {
                "dataset": "projects", "entity_id": "1", "entity_label": "A",
                "field": "url", "url": "https://bad.example/",
            })(),
        ]
        by_url = {
            "https://bad.example/": UrlCheckResult(
                "https://bad.example/", "broken", 404, None, "not found", 10),
        }
        md = render_markdown(refs, by_url, generated_at="2026-01-01", source_note="test")
        self.assertIn("broken", md)
        self.assertIn("bad.example", md)


if __name__ == "__main__":
    unittest.main()
