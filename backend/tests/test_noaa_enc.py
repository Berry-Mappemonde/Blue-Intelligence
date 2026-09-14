"""H2–H4 : NOAA ENC Direct feux/bouées — API mockée, pas de S-57."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import noaa_enc


CHESAPEAKE = (-76.6, 36.9, -75.9, 37.4)
MED = (3.0, 41.0, 9.0, 44.0)


class _Resp:
    def __init__(self, payload):
        self.status_code = 200
        self.headers = {"content-type": "application/geo+json"}
        self.content = b"{}"
        self._payload = payload

    def json(self):
        return self._payload


class _Client:
    def __init__(self):
        self.urls = []

    async def get(self, url, params=None, headers=None, timeout=None):
        self.urls.append(url)
        return _Resp({
            "type": "FeatureCollection",
            "features": [{
                "id": 42,
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-76.3, 37.1]},
                "properties": {"OBJNAM": "Cape Henry Light", "OBJECTID": 42},
            }],
        })


def test_med_bbox_is_not_us():
    assert noaa_enc.bbox_intersects_us(MED) is False
    assert noaa_enc.bbox_intersects_us(CHESAPEAKE) is True


def test_fetch_aids_skips_mediterranean():
    import asyncio
    client = _Client()
    docs = asyncio.run(noaa_enc.fetch_aids(client, MED))
    assert docs == []
    assert client.urls == []


def test_fetch_aids_chesapeake_mocked():
    import asyncio
    client = _Client()
    docs = asyncio.run(noaa_enc.fetch_aids(client, CHESAPEAKE, layers=(
        ("enc_harbour", 11, "light"),
    )))
    assert len(docs) == 1
    assert docs[0]["kind"] == "light"
    assert docs[0]["noaa_id"].startswith("noaa:enc_harbour:11:")
    assert client.urls


def test_aids_geojson_is_versioned():
    fc = noaa_enc.aids_geojson([{
        "_id": "noaa:enc_harbour:11:1",
        "name": "Light",
        "kind": "light",
        "service": "enc_harbour",
        "lat": 37.1,
        "lon": -76.3,
    }])
    assert fc["metadata"]["dataset"] == "noaa-aids"
    assert fc["metadata"]["disclaimer"]
    assert fc["metadata"]["content_sha256"]
    assert fc["features"][0]["properties"]["source"] == "noaa"


def test_overlay_osm_light_is_250m_not_500m():
    noaa = {"lat": 37.1, "lon": -76.3}
    near = {"lat": 37.101, "lon": -76.3, "name": "OSM light"}
    far = {"lat": 37.106, "lon": -76.3, "name": "too far"}
    assert noaa_enc.overlay_osm_light(noaa, [near]) is not None
    assert noaa_enc.overlay_osm_light(noaa, [far]) is None
