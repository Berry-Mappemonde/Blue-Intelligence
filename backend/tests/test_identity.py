"""Identity guardrail: same_site is not find_building — no network."""
from __future__ import annotations

import asyncio
import inspect
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core import dedup, identity  # noqa: E402
from app.core.geo import destination_point, haversine_km  # noqa: E402
from app.core.run_rules import bind_rules, reset_rules, snapshot_for_run  # noqa: E402
from app.services import capitainerie_world as cw  # noqa: E402


class _FakeColl:
    def __init__(self, docs=None):
        self.docs = list(docs or [])

    def _match_one(self, doc, q):
        return all(doc.get(k) == v for k, v in (q or {}).items())

    async def find_one(self, q=None, proj=None):
        for d in self.docs:
            if self._match_one(d, q or {}):
                return d
        return None

    async def insert_one(self, doc):
        self.docs.append(doc)

    async def update_one(self, q, upd, upsert=False):
        doc = await self.find_one(q)
        if not doc:
            return None
        if "$set" in upd:
            doc.update(upd["$set"])
        if "$unset" in upd:
            for k in upd["$unset"]:
                doc.pop(k, None)
        return None


ORIGIN = {"lat": 46.15, "lon": -1.16}


def _at(km: float, bearing: float = 90.0) -> tuple[float, float]:
    return destination_point(ORIGIN["lat"], ORIGIN["lon"], bearing, km)


def _office(name: str, km: float, bearing: float = 90.0, **extra) -> dict:
    lat, lon = _at(km, bearing)
    return {"name": name, "title": name, "lat": lat, "lon": lon, **extra}


class TestGuardrailDisagreement:
    def test_similar_names_at_400m_are_same_site_not_same_building(self):
        a = {"title": "Port de Papeete", "name": "Port de Papeete", **ORIGIN}
        b = _office("Papeete Port", 0.40)
        dist = haversine_km(a["lat"], a["lon"], b["lat"], b["lon"])
        assert dist == pytest.approx(0.40, abs=0.01)
        assert 0.25 < dist < 0.5
        assert identity.same_site(a, b) is True
        assert identity.find_building(b["lat"], b["lon"], [a]) is None

    def test_unnamed_at_200m_is_building_not_site(self):
        osm = {
            **ORIGIN,
            "title": "Capitainerie des Minimes",
            "name": "Capitainerie des Minimes",
        }
        shom = _office("", 0.20)
        assert identity.find_building(shom["lat"], shom["lon"], [osm]) is not None
        assert identity.same_site(osm, shom) is False

    def test_different_names_at_200m_overlay_without_name(self):
        osm = {
            **ORIGIN,
            "title": "Capitainerie des Minimes",
            "name": "Capitainerie des Minimes",
        }
        shom = _office("SMCFAC 6", 0.20)
        hit = identity.find_building(shom["lat"], shom["lon"], [osm])
        assert hit is not None
        assert hit.doc is osm
        assert identity.same_site(osm, shom) is False


class TestFindBuilding:
    def test_inclusive_250m_exclusive_beyond(self):
        osm = {**ORIGIN, "osm_id": "node/1"}
        on = _office("SHOM", 0.25)
        under = _office("SHOM", 0.249)
        over = _office("SHOM", 0.251)
        hit = identity.find_building(on["lat"], on["lon"], [osm])
        assert hit is not None
        assert hit.distance_km == pytest.approx(0.25, abs=0.001)
        assert identity.find_building(under["lat"], under["lon"], [osm]) is not None
        assert identity.find_building(over["lat"], over["lon"], [osm]) is None

    def test_closest_wins_not_last(self):
        near = {**ORIGIN, "_id": "near"}
        far = _office("far", 0.20)
        far["_id"] = "far"
        probe = _office("probe", 0.05)
        hit = identity.find_building(probe["lat"], probe["lon"], [far, near])
        assert hit is not None
        assert hit.doc["_id"] == "near"

    def test_tie_keeps_first(self):
        first = {**ORIGIN, "_id": "first"}
        second = {**ORIGIN, "_id": "second"}
        hit = identity.find_building(ORIGIN["lat"], ORIGIN["lon"], [first, second])
        assert hit is not None
        assert hit.doc["_id"] == "first"

    def test_skips_broken_coords(self):
        bad = [
            {"lat": None, "lon": -1.16},
            {"lat": 46.15, "lon": "x"},
            {"lat": float("nan"), "lon": -1.16},
            {"name": "no-xy"},
        ]
        good = {**ORIGIN, "_id": "ok"}
        probe = _office("p", 0.05)
        hit = identity.find_building(probe["lat"], probe["lon"], [*bad, good])
        assert hit is not None
        assert hit.doc["_id"] == "ok"

    def test_antimeridian_still_matches(self):
        west = {"lat": 0.0, "lon": 179.9992, "_id": "w"}
        elat, elon = destination_point(0.0, 179.9992, 90.0, 0.18)
        assert elon < 0  # crossed 180°
        hit = identity.find_building(elat, elon, [west])
        assert hit is not None
        assert hit.doc["_id"] == "w"

    def test_never_reads_names(self):
        src = inspect.getsource(identity.find_building)
        assert "text_similarity" not in src
        assert "normalize_name" not in src
        assert "same_site" not in src
        assert "is_duplicate" not in src

    def test_run_rule_widens_radius(self):
        osm = {**ORIGIN, "_id": "osm"}
        far = _office("NOAA", 0.35)
        assert identity.find_building(far["lat"], far["lon"], [osm]) is None
        snap = snapshot_for_run(
            mode="capitaineries",
            overrides={"capitaineries.merge_km": 0.40},
        )
        token = bind_rules(snap)
        try:
            hit = identity.find_building(far["lat"], far["lon"], [osm])
            assert hit is not None
            assert hit.doc["_id"] == "osm"
        finally:
            reset_rules(token)
        assert identity.find_building(far["lat"], far["lon"], [osm]) is None


class TestSameSiteUnchanged:
    def test_alias_is_duplicate(self):
        a = {"title": "Port de Papeete", "lat": -17.535, "lon": -149.57}
        b = {"title": "Papeete Port", "lat": -17.536, "lon": -149.571}
        assert identity.same_site(a, b) is True
        assert dedup.is_duplicate(a, b) is True

    def test_nan_coords_are_not_a_site(self):
        a = {"title": "Port A", "lat": float("nan"), "lon": 0.0}
        b = {"title": "Port B", "lat": float("nan"), "lon": 0.0}
        assert dedup.is_duplicate(a, b) is False


class TestCapitaineriesDoNotUseSiteMerge:
    def test_module_does_not_import_dedup(self):
        src = Path(cw.__file__).read_text()
        assert "from app.core.dedup" not in src
        assert "import app.core.dedup" not in src
        assert "same_site" not in src

    def test_upsert_shom_400m_is_orphan_even_with_close_names(self):
        osm = {
            "_id": "node/1", "osm_id": "node/1",
            "name": "Port de Papeete", "title": "Port de Papeete",
            **ORIGIN, "source": "openstreetmap",
            "sources": ["openstreetmap"], "tags": {},
        }
        coll = _FakeColl([osm])
        lat, lon = _at(0.40)
        cand = {
            "shom_id": "shom:far", "name": "Papeete Port",
            "lat": lat, "lon": lon, "tags": {},
            "telephone": None, "canal_vhf": None, "sources": ["shom"],
        }
        assert identity.same_site(
            {"title": osm["name"], "lat": osm["lat"], "lon": osm["lon"]},
            {"title": cand["name"], "lat": cand["lat"], "lon": cand["lon"]},
        ) is True
        result = asyncio.run(
            cw.upsert_shom(coll, cand, "2026-09-09T00:00:00Z", list(coll.docs)),
        )
        assert result == "inserted"
        assert len(coll.docs) == 2
        orphan = next(d for d in coll.docs if d.get("shom_id") == "shom:far")
        assert "osm_id" not in orphan


class TestHaversineDomainClamp:
    """`asin(sqrt(a))` reçoit parfois une valeur > 1.0 : deux points quasi
    antipodaux font dépasser 1.0 à l'arrondi flottant près.

    Sans `min(1.0, ...)` — la protection qu'a déjà
    `climatology_common.haversine_nm` — `haversine_km` lève alors
    `ValueError: math domain error`.
    """

    # Couple qui fait sortir `sqrt(a)` du domaine de asin (`a` vaut
    # 1.0000000000000004). Reproduit sur CPython x86-64 ; ailleurs le test reste
    # vert : il ne peut que se faire moins incisif, jamais faux.
    ANTIPODAL_TRIGGER = (
        58.1602059533397, 164.643942223191,
        -58.1602059498364, 344.64394216128903,
    )

    def test_known_antipodal_trigger_does_not_raise(self):
        dist = haversine_km(*self.ANTIPODAL_TRIGGER)
        assert dist == pytest.approx(20015.086, abs=1.0)

    def test_antipodal_domain_never_raises(self):
        # propriété : aucune paire de coordonnées ne doit faire sortir asin de son
        # domaine. Balayage déterministe sur tout le domaine géographique.
        for i in range(2000):
            t = i / 2000.0
            lat = -89.0 + 178.0 * t
            lon = -180.0 + 360.0 * ((i * 7919) % 2000) / 2000.0
            dist = haversine_km(lat, lon, -lat, lon + 180.0)
            assert 15000.0 < dist <= 20020.0

    def test_ordinary_distance_is_unchanged(self):
        # les règles 500 m / 250 m reposent sur cette distance : elle doit rester juste
        assert haversine_km(48.0, -4.0, 48.0045, -4.0) == pytest.approx(0.5, abs=0.01)
        assert haversine_km(48.0, -4.0, 48.0, -4.0) == pytest.approx(0.0, abs=1e-9)

    def test_sibling_haversine_nm_implementations_are_clamped_too(self):
        """Les trois haversines du dépôt doivent partager la protection.

        `marina_build.haversine_nm` ne l'avait pas : sur le même couple
        antipodal, elle levait ValueError (math domain error).
        """
        from app.services.climatology_common import haversine_nm as cc_nm
        from app.services.marina_build import haversine_nm as mb_nm
        for fn in (cc_nm, mb_nm):
            dist = fn(*self.ANTIPODAL_TRIGGER)
            assert 10800.0 < dist <= 10810.0
        assert mb_nm(48.0, -4.0, 48.0045, -4.0) == pytest.approx(0.27, abs=0.01)
