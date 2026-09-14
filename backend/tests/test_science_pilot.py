"""Pilote Sentinel : hors moisson SOURCES, GeoJSON versionné."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.science_build import PILOT_SOURCE, SOURCES, slim_feature
from app.services.science_pilot import docs_from_pilot_fc, wrap_pilot_export


def test_pilot_is_not_a_harvest_source():
    assert PILOT_SOURCE not in SOURCES


def test_docs_from_pilot_fc():
    fc = wrap_pilot_export({
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [[-1.2, 46.1], [-1.1, 46.15]]},
            "properties": {
                "id": "berry-1",
                "name": "Trait de côte pilote",
                "kind": "coastline",
                "error_m": 12.4,
                "method": "mndwi",
            },
        }],
    })
    assert fc["metadata"]["dataset"] == "sentinel-coastline"
    assert fc["metadata"]["source"] == PILOT_SOURCE
    docs = docs_from_pilot_fc(fc)
    assert len(docs) == 1
    assert docs[0]["source"] == PILOT_SOURCE
    assert docs[0]["error_m"] == 12.4
    slim = slim_feature(docs[0])
    assert slim["properties"]["error_m"] == 12.4
    assert slim["geometry"]["type"] == "LineString"
