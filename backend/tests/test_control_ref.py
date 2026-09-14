"""C4 : SMCFAC voisin ≤ 250 m = contrôle, pas identité."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.identity import OVERLAY_RADIUS_KM
from app.services.control_ref import control_ref_from_candidates


def test_smcfac_within_250m_is_published_ref():
    marina = {"lat": 46.15, "lon": -1.15}
    smcfac = {
        "shom_id": "shom:smcfac:1",
        "name": "Ponton SHOM",
        "source": "shom",
        "lat": 46.1508,
        "lon": -1.15,
        "tags": {"shom:layer": "smcfac"},
    }
    out = control_ref_from_candidates(marina["lat"], marina["lon"], [smcfac])
    assert out["status"] == "published_ref"
    assert out["ref"]["id"] == "shom:smcfac:1"
    assert out["ref"]["layer"] == "smcfac"
    assert out["ref"]["distance_m"] <= int(OVERLAY_RADIUS_KM * 1000) + 1


def test_far_smcfac_is_osm_only():
    marina = {"lat": 46.15, "lon": -1.15}
    far = {
        "shom_id": "shom:smcfac:2",
        "lat": 46.16,
        "lon": -1.15,
        "tags": {"shom:layer": "smcfac"},
    }
    out = control_ref_from_candidates(marina["lat"], marina["lon"], [far])
    assert out["status"] == "osm_only"
    assert out["ref"] is None


def test_no_candidates_osm_only():
    assert control_ref_from_candidates(46.15, -1.15, [])["status"] == "osm_only"
