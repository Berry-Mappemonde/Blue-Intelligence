"""GET /api/amp — vue large hors de la boucle, vue étroite inchangée."""
from __future__ import annotations

import asyncio
import json

from fastapi.responses import Response

from app.routers import amp as amp_router
from app.services import amp as amp_svc

POLY = {
    "type": "Polygon",
    "coordinates": [[
        [3.0, 42.0], [3.4, 42.0], [3.4, 42.3], [3.0, 42.3], [3.0, 42.0],
    ]],
}

FRONTEND_KEYS = (
    "id", "site_id", "name", "country", "designation", "managing_authority",
    "lfp", "lat", "lon", "manager_url", "visit_url",
)


def _doc(site_id: str, geometry, **extra) -> dict:
    doc = {
        "_id": site_id,
        "site_id": site_id,
        "name": f"Parc {site_id}",
        "country": "France",
        "state": "",
        "designation": "Parc naturel marin",
        "category_name": "",
        "iucn_cat": "",
        "purpose": "Protéger le littoral",
        "lfp": 3,
        "entry": 1,
        "speed": 2,
        "managing_authority": "OFB",
        "gov_level": "",
        "wdpa_id": "",
        "year_est": 2012,
        "manager_url": "https://parc-marin.fr",
        "visit_url": "https://parc-marin.fr/visite",
        "visit_url_status": "found",
        "visit_url_source": "other_helpful_links",
        "lat": 42.15,
        "lon": 3.2,
        "fetched_at": "2026-01-01T00:00:00+00:00",
        "enriched_at": None,
        "geometry": geometry,
    }
    doc.update(extra)
    return doc


def _dense_polygon(n: int = 700, lon0: float = 3.0, lat0: float = 42.0) -> dict:
    top = [[lon0 + i * 0.4 / n, lat0] for i in range(n)]
    right = [[lon0 + 0.4, lat0 + i * 0.3 / n] for i in range(n)]
    bottom = [[lon0 + 0.4 - i * 0.4 / n, lat0 + 0.3] for i in range(n)]
    left = [[lon0, lat0 + 0.3 - i * 0.3 / n] for i in range(n)]
    ring = top + right + bottom + left
    ring.append(ring[0])
    return {"type": "Polygon", "coordinates": [ring]}


def _install_thread_spy(monkeypatch):
    seen: list[str] = []
    real = asyncio.to_thread

    async def spy(fn, *args, **kwargs):
        seen.append(getattr(fn, "__name__", type(fn).__name__))
        return await real(fn, *args, **kwargs)

    monkeypatch.setattr(amp_router.asyncio, "to_thread", spy)
    return seen


def _patch_reads(monkeypatch, docs):
    calls = {"query": 0, "sites": 0, "force": None}

    async def query(db, box, limit=8000):
        calls["query"] += 1
        assert limit == 8000
        # Copie : le rendu large détache la géométrie du document qu'on lui donne.
        return [dict(d) for d in docs]

    async def sites(db, box, force=False):
        calls["sites"] += 1
        calls["force"] = force
        return [dict(d) for d in docs], {
            "source": "cache",
            "truncated": False,
            "fetched": 0,
            "error": None,
        }

    monkeypatch.setattr(amp_router.amp_svc, "query_cache", query)
    monkeypatch.setattr(amp_router.amp_svc, "sites_in_bbox", sites)
    return calls


def test_lighten_keeps_points_and_small_polygons():
    point = {"type": "Point", "coordinates": [3.2, 42.1]}
    assert amp_svc.lighten_geometry_for_wide_view(point) == point
    assert amp_svc.lighten_geometry_for_wide_view(None) is None
    small = amp_svc.lighten_geometry_for_wide_view(POLY)
    assert small == amp_svc.sanitize_geometry(POLY)
    assert len(json.dumps(small)) <= amp_svc.WIDE_VIEW_GEOM_MAX_BYTES


def test_lighten_shrinks_a_dense_polygon_or_falls_back_to_an_outline(monkeypatch):
    dense = _dense_polygon()
    raw = len(json.dumps(dense))
    out = amp_svc.lighten_geometry_for_wide_view(dense)
    assert amp_svc.is_area_geom(out)
    assert len(json.dumps(out)) <= amp_svc.WIDE_VIEW_GEOM_MAX_BYTES
    assert len(json.dumps(out)) < raw

    def _no_repair(geom, max_bytes=800_000):
        return None

    monkeypatch.setattr(amp_svc, "repair_geometry_for_mongo", _no_repair)
    outline = amp_svc.lighten_geometry_for_wide_view(POLY)
    assert outline["type"] == "Polygon"
    ring = outline["coordinates"][0]
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    assert min(xs) == 3.0 and max(xs) == 3.4
    assert min(ys) == 42.0 and max(ys) == 42.3
    assert len(json.dumps(outline)) <= amp_svc.WIDE_VIEW_GEOM_MAX_BYTES


def test_narrow_bbox_keeps_full_geometry_and_skips_the_thread(monkeypatch):
    amp_router.clear_wide_amp_response_cache()
    dense = _dense_polygon(n=80)
    docs = [_doc("PS-NARROW", dense)]
    expected_props = amp_svc.public_properties(docs[0])
    calls = _patch_reads(monkeypatch, docs)
    seen = _install_thread_spy(monkeypatch)

    out = asyncio.run(amp_router.list_amp(bbox="3,42,4,43", force=True))

    assert calls["sites"] == 1
    assert calls["force"] is True
    assert calls["query"] == 0
    assert seen == []
    assert isinstance(out, dict)
    assert not isinstance(out, Response)
    assert out == amp_svc.to_feature_collection(docs, extra={
        "hint": None,
        "source": "cache",
        "truncated": False,
        "fetched": 0,
        "error": None,
    })
    feat = out["features"][0]
    assert feat["geometry"] == dense
    assert feat["properties"] == expected_props
    for key in FRONTEND_KEYS:
        assert key in feat["properties"]


def test_wide_bbox_renders_on_a_thread_and_bounds_the_payload(monkeypatch):
    amp_router.clear_wide_amp_response_cache()
    dense = _dense_polygon()
    point = {"type": "Point", "coordinates": [4.2, 43.1]}
    docs = [
        _doc("PS-AREA", dense, lat=42.15, lon=3.2),
        _doc("PS-POINT", point, lat=43.1, lon=4.2, lfp=5),
    ]
    expected = [amp_svc.public_properties(d) for d in docs]
    raw_fc = amp_svc.to_feature_collection(docs, extra={
        "hint": None,
        "source": "cache",
        "truncated": False,
        "fetched": 0,
    })
    raw_bytes = len(json.dumps(raw_fc, ensure_ascii=False).encode("utf-8"))
    calls = _patch_reads(monkeypatch, docs)
    seen = _install_thread_spy(monkeypatch)

    resp = asyncio.run(amp_router.list_amp(bbox="0,40,24,48", force=True))

    assert calls["query"] == 1
    assert calls["sites"] == 0
    assert seen == ["_render_wide_amp_json"]
    assert isinstance(resp, Response)
    assert resp.media_type == "application/json"
    body = resp.body
    assert isinstance(body, bytes)
    assert len(body) < raw_bytes // 4
    assert len(body) < 80_000
    data = json.loads(body)
    assert set(data) == {"type", "features", "hint", "source", "truncated", "fetched"}
    assert data["type"] == "FeatureCollection"
    assert data["hint"] is None
    assert data["source"] == "cache"
    assert data["truncated"] is False
    assert data["fetched"] == 0
    assert [f["id"] for f in data["features"]] == ["PS-AREA", "PS-POINT"]
    area, dot = data["features"]
    assert area["properties"] == expected[0]
    assert dot["properties"] == expected[1]
    for feat in data["features"]:
        for key in FRONTEND_KEYS:
            assert key in feat["properties"]
    assert amp_svc.is_area_geom(area["geometry"])
    assert len(json.dumps(area["geometry"])) <= amp_svc.WIDE_VIEW_GEOM_MAX_BYTES
    assert len(json.dumps(area["geometry"])) < len(json.dumps(dense))
    assert dot["geometry"] == point

    seen.clear()
    again = asyncio.run(amp_router.list_amp(bbox="0.04,40.04,24.04,48.04"))
    assert seen == []
    assert calls["query"] == 1
    assert again.body == body


def test_wide_empty_cache_hints_zoom(monkeypatch):
    amp_router.clear_wide_amp_response_cache()
    calls = _patch_reads(monkeypatch, [])
    seen = _install_thread_spy(monkeypatch)
    resp = asyncio.run(amp_router.list_amp(bbox="0,40,24,48"))
    assert calls["sites"] == 0
    assert seen == ["_render_wide_amp_json"]
    data = json.loads(resp.body)
    assert data["hint"] == "zoom"
    assert data["features"] == []
    assert data["source"] == "cache"


def test_wide_visible_filter_stays_in_the_response_and_the_cache_key(monkeypatch):
    amp_router.clear_wide_amp_response_cache()
    docs = [
        _doc("KEEP", POLY),
        _doc("DROP", POLY, name="Hors revue"),
    ]
    calls = _patch_reads(monkeypatch, docs)

    async def _filter(db, kind, rows, keyfn):
        assert kind == "amp"
        assert [keyfn(r) for r in rows] == ["KEEP", "DROP"]
        return [r for r in rows if r.get("site_id") == "KEEP"]

    monkeypatch.setattr("app.services.review_gold.filter_visible", _filter)
    seen = _install_thread_spy(monkeypatch)

    visible = asyncio.run(amp_router.list_amp(bbox="0,40,24,48", visible=True))
    hidden = asyncio.run(amp_router.list_amp(bbox="0,40,24,48", visible=False))

    assert calls["query"] == 2
    assert seen == ["_render_wide_amp_json", "_render_wide_amp_json"]
    vis = json.loads(visible.body)
    hid = json.loads(hidden.body)
    assert [f["id"] for f in vis["features"]] == ["KEEP"]
    assert [f["id"] for f in hid["features"]] == ["KEEP", "DROP"]
    assert vis["features"][0]["properties"]["name"] == "Parc KEEP"


def test_wide_cache_expires_and_stays_bounded(monkeypatch):
    amp_router.clear_wide_amp_response_cache()
    docs = [_doc("PS-1", POLY)]
    calls = _patch_reads(monkeypatch, docs)
    seen = _install_thread_spy(monkeypatch)
    clock = {"t": 1_000.0}
    monkeypatch.setattr(amp_router.time, "monotonic", lambda: clock["t"])

    bboxes = [
        "0,0,20,10",
        "20,0,40,10",
        "40,0,60,10",
        "0,10,20,20",
        "20,10,40,20",
    ]
    for bbox in bboxes:
        asyncio.run(amp_router.list_amp(bbox=bbox))
    assert calls["query"] == 5
    assert len(seen) == 5
    assert len(amp_router._wide_cache) == amp_router._WIDE_CACHE_MAX_ENTRIES

    asyncio.run(amp_router.list_amp(bbox=bboxes[-1]))
    assert calls["query"] == 5
    assert len(seen) == 5

    asyncio.run(amp_router.list_amp(bbox=bboxes[0]))
    assert calls["query"] == 6
    assert len(seen) == 6
    assert len(amp_router._wide_cache) == amp_router._WIDE_CACHE_MAX_ENTRIES

    clock["t"] += amp_router._WIDE_CACHE_TTL_S + 1
    asyncio.run(amp_router.list_amp(bbox=bboxes[-1]))
    assert calls["query"] == 7
    assert len(seen) == 7


def test_world_span_reads_the_cache_without_writing(monkeypatch):
    amp_router.clear_wide_amp_response_cache()
    docs = [_doc("PS-WORLD", POLY)]

    class _Sites:
        def __init__(self):
            self.queries = []

        def find(self, query, *args, **kwargs):
            self.queries.append(query)
            return self

        def limit(self, n):
            assert n == 8000
            return self

        async def to_list(self, n):
            assert n == 8000
            return docs

        def __getattr__(self, name):
            raise AssertionError(f"écriture ou lecture inattendue: {name}")

    class _DB:
        def __init__(self):
            self.amp_sites = _Sites()

    fake = _DB()
    monkeypatch.setattr(amp_router, "db", fake)

    async def query(*args, **kwargs):
        raise AssertionError("une emprise ≥ 60° liste le cache, sans $geoIntersects")

    async def sites(*args, **kwargs):
        raise AssertionError("pas d'appel ProtectedSeas")

    monkeypatch.setattr(amp_router.amp_svc, "query_cache", query)
    monkeypatch.setattr(amp_router.amp_svc, "sites_in_bbox", sites)
    seen = _install_thread_spy(monkeypatch)

    resp = asyncio.run(amp_router.list_amp(bbox="-180,-80,180,80"))

    assert fake.amp_sites.queries == [{}]
    assert seen == ["_render_wide_amp_json"]
    data = json.loads(resp.body)
    assert data["features"][0]["properties"]["site_id"] == "PS-WORLD"
    assert data["source"] == "cache"
    assert amp_svc.is_area_geom(data["features"][0]["geometry"])
