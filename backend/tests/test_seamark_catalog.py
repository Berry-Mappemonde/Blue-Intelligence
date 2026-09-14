"""C1–C3 : catalogue OSM — statuts et mapping inverse d'export."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.seamark_catalog import exact_key, osm_tags_for_field, seamark_type


def test_mouillages_exploite():
    for typ in ("anchorage", "mooring", "anchor_berth"):
        row = seamark_type(typ)
        assert row, typ
        assert row["status"] == "exploite"


def test_export_mapping_fuel_badge():
    tags = osm_tags_for_field("fuel")
    assert tags.get("fuel") == "yes"
    assert tags.get("seamark:small_craft_facility:category") == "fuel"


def test_satellite_keys_are_candidat_before_dump():
    assert exact_key("natural=coastline")["status"] == "candidat"
    assert seamark_type("depth_area")["status"] == "candidat"
