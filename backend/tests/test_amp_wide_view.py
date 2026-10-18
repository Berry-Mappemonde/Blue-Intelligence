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

    async def load(db, box, span, limit=8000, batch_size=None):
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

    monkeypatch.setattr(amp_router.amp_svc, "collect_light_areas_for_wide_view", load)
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
            self.projections = []
            self.batches = []

        def find(self, query, projection=None, *args, **kwargs):
            self.queries.append(query)
            self.projections.append(projection)
            self._docs = [dict(d) for d in docs]
            self._i = 0
            return self

        def batch_size(self, n):
            self.batches.append(n)
            return self

        def limit(self, n):
            assert n == 8000
            self._limit = n
            return self

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self._i >= len(self._docs) or self._i >= getattr(self, "_limit", 8000):
                raise StopAsyncIteration
            doc = self._docs[self._i]
            self._i += 1
            return doc

        async def to_list(self, n=None):
            raise AssertionError("la vue large ne charge pas tous les documents d'un coup")

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
    assert fake.amp_sites.batches == [amp_svc.WIDE_VIEW_BATCH_SIZE]
    projection = fake.amp_sites.projections[0]
    assert projection["geometry"] == 1
    assert "ps_website_raw" not in projection
    assert seen == ["_lighten_wide_batch", "_render_wide_amp_json"]
    data = json.loads(resp.body)
    assert data["features"][0]["properties"]["site_id"] == "PS-WORLD"
    assert data["source"] == "cache"
    assert amp_svc.is_area_geom(data["features"][0]["geometry"])


def test_wide_cache_ttl_lasts_at_least_one_hour():
    assert amp_router._WIDE_CACHE_TTL_S >= 3600
    assert amp_router._WIDE_CACHE_TTL_S > 180


def test_wide_view_query_uses_the_sphere_index_below_sixty_degrees():
    query = amp_svc.wide_view_area_query((0.0, 40.0, 24.0, 48.0), 24.0)
    assert query["geometry"]["$geoIntersects"]["$geometry"]["type"] == "Polygon"
    assert amp_svc.wide_view_area_query((-180.0, -90.0, 180.0, 90.0), 360.0) == {}
    assert amp_svc.wide_view_area_query((-180.0, -90.0, 180.0, 90.0), 60.0) == {}


def _heavy_multipolygon(n_parts: int = 80, pts: int = 40, shift: float = 0.0) -> dict:
    """Plusieurs contours dentelés, plus autant d'îlots sous la tolérance d'affichage."""
    coords = []
    for i in range(n_parts):
        x = shift + (i % 20) * 0.2
        y = (i // 20) * 0.2
        ring = []
        for k in range(pts):
            radius = 0.04 + (0.008 if k % 2 == 0 else 0.0)
            ring.append([
                x + radius * (0.3 if k % 5 == 0 else 1.0) * (k / pts),
                y + ((k % 9) - 4) * 0.004,
            ])
        ring.append(ring[0])
        coords.append([ring])
        tx = x + 0.01
        ty = y + 0.01
        tiny = 1e-5
        coords.append([[
            [tx, ty], [tx + tiny, ty], [tx + tiny, ty + tiny],
            [tx, ty + tiny], [tx, ty],
        ]])
    return {"type": "MultiPolygon", "coordinates": coords}


def _legacy_wide_lighten(geom: dict):
    """Ancien chemin : décimation puis réparation Mongo (boucle de simplification)."""
    prepared = geom
    if geom.get("type") in ("Polygon", "MultiPolygon"):
        prepared = amp_svc._decimate_dense_geometry(geom)
    repaired = amp_svc.repair_geometry_for_mongo(
        prepared, max_bytes=amp_svc.WIDE_VIEW_GEOM_MAX_BYTES)
    if amp_svc.is_area_geom(repaired):
        return repaired
    return amp_svc._simplified_outline(geom)


def test_lighten_drops_tiny_parts_and_stays_valid():
    from shapely.geometry import shape
    from shapely.geometry.base import BaseGeometry

    geom = _heavy_multipolygon()
    calls = []
    original = BaseGeometry.buffer

    def _buffer(self, distance, *args, **kwargs):
        calls.append(distance)
        return original(self, distance, *args, **kwargs)

    BaseGeometry.buffer = _buffer
    try:
        out = amp_svc.lighten_geometry_for_wide_view(geom)
    finally:
        BaseGeometry.buffer = original
    assert calls == []
    assert amp_svc.is_area_geom(out)
    assert len(json.dumps(out)) <= amp_svc.WIDE_VIEW_GEOM_MAX_BYTES
    checked = shape(out)
    assert checked.is_valid
    out_parts = 1 if out["type"] == "Polygon" else len(out["coordinates"])
    assert out_parts < len(geom["coordinates"])
    assert out_parts <= max(1, (amp_svc.WIDE_VIEW_GEOM_MAX_BYTES - 32) // amp_svc._WIDE_VIEW_BYTES_PER_PART)


def test_lighten_falls_back_to_an_outline_when_the_single_pass_fails(monkeypatch):
    monkeypatch.setattr(amp_svc, "_simplify_wide_view_once", lambda *a, **k: None)
    dense = _dense_polygon()
    outline = amp_svc.lighten_geometry_for_wide_view(dense)
    assert outline["type"] == "Polygon"
    ring = outline["coordinates"][0]
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    assert min(xs) == 3.0 and max(xs) == 3.4
    assert min(ys) == 42.0 and max(ys) == 42.3
    assert len(json.dumps(outline)) <= amp_svc.WIDE_VIEW_GEOM_MAX_BYTES


def test_wide_view_streams_areas_in_bounded_batches(monkeypatch):
    amp_router.clear_wide_amp_response_cache()
    total = 100
    docs = [
        _doc(f"PS-{i}", POLY, lon=3.0 + (i % 10) * 0.01, lat=42.0 + (i // 10) * 0.01)
        for i in range(total)
    ]
    batch_sizes = []
    real_batch = amp_svc._lighten_wide_batch

    def _spy_batch(chunk):
        batch_sizes.append(len(chunk))
        return real_batch(chunk)

    monkeypatch.setattr(amp_svc, "_lighten_wide_batch", _spy_batch)
    threaded = []
    real_to_thread = asyncio.to_thread

    async def _spy_thread(fn, *args, **kwargs):
        threaded.append(getattr(fn, "__name__", ""))
        return await real_to_thread(fn, *args, **kwargs)

    monkeypatch.setattr(amp_svc.asyncio, "to_thread", _spy_thread)

    class _Sites:
        def __init__(self):
            self.query = None
            self.projection = None
            self.batch_size_n = None
            self.to_listed = False
            self._i = 0
            self._limit = 10 ** 9

        def find(self, query, projection=None, *args, **kwargs):
            self.query = query
            self.projection = projection
            self._i = 0
            return self

        def batch_size(self, n):
            self.batch_size_n = n
            return self

        def limit(self, n):
            self._limit = n
            return self

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self._i >= len(docs) or self._i >= self._limit:
                raise StopAsyncIteration
            doc = dict(docs[self._i])
            self._i += 1
            return doc

        async def to_list(self, n=None):
            self.to_listed = True
            raise AssertionError("to_list charge toute la collection")

    sites = _Sites()

    class _DB:
        amp_sites = sites

    monkeypatch.setattr(amp_router, "db", _DB())
    resp = asyncio.run(amp_router.list_amp(bbox="0,40,24,48"))

    assert sites.to_listed is False
    assert sites.batch_size_n == amp_svc.WIDE_VIEW_BATCH_SIZE
    assert sites.batch_size_n < total
    assert batch_sizes
    assert max(batch_sizes) <= amp_svc.WIDE_VIEW_BATCH_SIZE
    assert sum(batch_sizes) == total
    assert len(batch_sizes) > 1
    assert "$geoIntersects" in sites.query["geometry"]
    assert sites.projection["geometry"] == 1
    assert "ps_website_raw" not in sites.projection
    assert "_spy_batch" in threaded
    data = json.loads(resp.body)
    assert len(data["features"]) == total
    assert data["source"] == "cache"
    assert data["fetched"] == 0
    for feat in data["features"]:
        assert len(json.dumps(feat["geometry"])) <= amp_svc.WIDE_VIEW_GEOM_MAX_BYTES


def test_distinct_bboxes_build_at_the_same_time(monkeypatch):
    amp_router.clear_wide_amp_response_cache()
    state = {"n": 0}
    both = asyncio.Event()
    release = asyncio.Event()

    async def load(db, box, span, limit=8000, batch_size=None):
        state["n"] += 1
        if state["n"] >= 2:
            both.set()
        await release.wait()
        return [_doc("PS-1", POLY)]

    monkeypatch.setattr(amp_router.amp_svc, "collect_light_areas_for_wide_view", load)

    async def go():
        first = asyncio.create_task(amp_router.list_amp(bbox="0,0,20,10"))
        second = asyncio.create_task(amp_router.list_amp(bbox="40,0,60,10"))
        await asyncio.wait_for(both.wait(), timeout=1.0)
        release.set()
        await asyncio.gather(first, second)

    asyncio.run(go())
    assert state["n"] == 2


def test_same_quantised_bbox_is_built_once(monkeypatch):
    amp_router.clear_wide_amp_response_cache()
    state = {"n": 0}
    entered = asyncio.Event()
    release = asyncio.Event()

    async def load(db, box, span, limit=8000, batch_size=None):
        state["n"] += 1
        entered.set()
        await release.wait()
        return [_doc("PS-1", POLY)]

    monkeypatch.setattr(amp_router.amp_svc, "collect_light_areas_for_wide_view", load)

    async def go():
        first = asyncio.create_task(amp_router.list_amp(bbox="0,0,20,10"))
        await asyncio.wait_for(entered.wait(), timeout=1.0)
        second = asyncio.create_task(amp_router.list_amp(bbox="0.04,0.01,20.04,10.01"))
        await asyncio.sleep(0.05)
        assert state["n"] == 1
        release.set()
        left, right = await asyncio.gather(first, second)
        assert left.body == right.body

    asyncio.run(go())
    assert state["n"] == 1


def test_warmup_is_off_unless_the_env_flag_is_set(monkeypatch):
    monkeypatch.delenv(amp_router._WIDE_WARMUP_ENV, raising=False)
    assert amp_router.wide_view_warmup_enabled() is False
    assert amp_router.start_wide_amp_warmup() is None
    for raw in ("", "0", "false", "no", "off"):
        monkeypatch.setenv(amp_router._WIDE_WARMUP_ENV, raw)
        assert amp_router.wide_view_warmup_enabled() is False
        assert amp_router.start_wide_amp_warmup() is None


def test_warmup_only_reads_the_area_cache(monkeypatch):
    amp_router.clear_wide_amp_response_cache()
    amp_router._wide_warmup_task = None
    monkeypatch.setenv(amp_router._WIDE_WARMUP_ENV, "1")
    writes = []

    class _Sites:
        def find(self, query, projection=None, *args, **kwargs):
            assert query == {}
            self._i = 0
            self._docs = [_doc("PS-WARM", POLY)]
            return self

        def batch_size(self, n):
            return self

        def limit(self, n):
            return self

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self._i >= len(self._docs):
                raise StopAsyncIteration
            doc = dict(self._docs[self._i])
            self._i += 1
            return doc

        def __getattr__(self, name):
            writes.append(name)
            raise AssertionError(f"écriture inattendue: {name}")

    class _DB:
        amp_sites = _Sites()

    monkeypatch.setattr(amp_router, "db", _DB())

    async def go():
        task = amp_router.start_wide_amp_warmup()
        assert task is not None
        await task

    asyncio.run(go())
    assert writes == []
    assert amp_router._wide_cache
    cached = next(iter(amp_router._wide_cache.values()))[1]
    data = json.loads(cached)
    assert data["features"][0]["properties"]["site_id"] == "PS-WARM"
    assert data["source"] == "cache"
    assert data["fetched"] == 0


def test_wide_simplify_benchmark_is_faster_and_lighter():
    import time
    import tracemalloc

    from shapely.geometry import shape

    geoms = [_heavy_multipolygon(n_parts=60, pts=36, shift=float(i)) for i in range(3)]

    def _run(fn):
        started = time.perf_counter()
        outs = [fn(geom) for geom in geoms]
        return time.perf_counter() - started, outs

    def _peak(fn):
        tracemalloc.start()
        try:
            outs = [fn(geom) for geom in geoms]
            _current, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        return peak, outs

    before_s, before_outs = _run(_legacy_wide_lighten)
    after_s, after_outs = _run(amp_svc.lighten_geometry_for_wide_view)
    before_peak, _ = _peak(_legacy_wide_lighten)
    after_peak, _ = _peak(amp_svc.lighten_geometry_for_wide_view)
    print(
        "wide-view simplify benchmark: "
        f"areas={len(geoms)} "
        f"before={before_s:.4f}s peak={before_peak} "
        f"after={after_s:.4f}s peak={after_peak}"
    )
    assert before_s > 0
    assert after_s < before_s / 3
    assert after_peak < before_peak
    for out in before_outs + after_outs:
        assert amp_svc.is_area_geom(out)
        assert len(json.dumps(out)) <= amp_svc.WIDE_VIEW_GEOM_MAX_BYTES
        assert shape(out).is_valid
