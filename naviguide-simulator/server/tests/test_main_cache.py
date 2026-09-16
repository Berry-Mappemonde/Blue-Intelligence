import asyncio
import json

import main


def test_weather_cache_reuses_one_grid_cell(monkeypatch):
    main._weather_cache.clear()
    calls = []

    def load(lat, lon):
        calls.append((lat, lon))
        return {"latitude": lat, "longitude": lon, "value": len(calls)}

    first = main._cached_weather("wind", main.PositionRequest(latitude=10.01, longitude=-20.01), load)
    second = main._cached_weather("wind", main.PositionRequest(latitude=10.11, longitude=-20.11), load)

    assert first["value"] == 1
    assert second["value"] == 1
    assert calls == [(10.01, -20.01)]


def test_satellite_endpoint_groups_all_three_products(monkeypatch):
    def cached(kind, _request, _loader):
        return {"kind": kind}

    monkeypatch.setattr(main, "_cached_weather", cached)
    data = main.get_satellite(main.PositionRequest(latitude=46.15, longitude=-1.16))

    assert data == {
        "wind": {"kind": "wind"},
        "wave": {"kind": "wave"},
        "current": {"kind": "current"},
    }


def test_ports_proxy_filters_the_requested_bbox(monkeypatch):
    async def fake_ports():
        return [
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-1.16, 46.15]}, "properties": {"name": "La Rochelle"}},
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [174.8, -18.1]}, "properties": {"name": "Suva"}},
        ]

    monkeypatch.setattr(main, "fetch_wpi_features", fake_ports)
    response = asyncio.run(main.proxy_ports(bbox="-2,45,0,47", maxFeatures=800))
    body = json.loads(response.body)

    assert [feature["properties"]["name"] for feature in body["features"]] == ["La Rochelle"]
    assert response.headers["cache-control"].startswith("public")
