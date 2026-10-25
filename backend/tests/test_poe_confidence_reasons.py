"""Raisons de confiance : traduction anglaise et exposition dans le GeoJSON.

`reasons_en` vit dans `poe_confidence` (table `REASONS_EN` partagée par
l'évaluateur et l'API). Le garde-fou qui vérifie que chaque raison produite par
`score_port` est traduite est dans `tests/test_evaluator.py`
(`test_every_scorer_reason_has_an_english_translation`) : on ne le duplique pas.

Aucun réseau.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.poe_confidence import reasons_en  # noqa: E402
from app.services.poe_pipeline import ports_to_geojson  # noqa: E402


def test_reasons_en_translates_known_reasons():
    assert reasons_en(["source d'État"]) == ["government source"]
    assert reasons_en(["non géocodé"]) == ["not geocoded"]


def test_reasons_en_never_rewrites_an_unknown_reason():
    # on n'invente pas de texte : une raison inconnue passe inchangée
    assert reasons_en(["raison inconnue"]) == ["raison inconnue"]


def test_reasons_en_passes_english_through():
    # les `check_reasons` de l'évaluateur sont déjà en anglais
    assert reasons_en(["single geocoder, not cross-checked"]) == [
        "single geocoder, not cross-checked",
    ]


def test_reasons_en_handles_empty_and_missing():
    assert reasons_en(None) == []
    assert reasons_en([]) == []


def test_geojson_exposes_the_breakdown():
    doc = {
        "_id": "p1", "name": "Papeete", "lat": -17.5, "lon": -149.5,
        "confidence": 88,
        "confidence_parts": {"source": 30, "reading": 25, "map": 25, "external": 8},
        "confidence_reasons": ["source d'État", "dans la ZEE"],
    }
    props = ports_to_geojson([doc])["features"][0]["properties"]
    assert props["confidence"] == 88
    assert props["confidence_parts"] == {
        "source": 30, "reading": 25, "map": 25, "external": 8,
    }
    assert props["confidence_reasons"] == ["source d'État", "dans la ZEE"]
    assert props["reasons_en"] == ["government source", "inside the EEZ"]


def test_geojson_has_no_english_when_no_reasons():
    """Pas de raison, pas de traduction : on n'écrit pas un champ vide."""
    props = ports_to_geojson([
        {"_id": "p2", "name": "X", "lat": 1.0, "lon": 2.0, "confidence": 10},
    ])["features"][0]["properties"]
    assert props["reasons_en"] is None
    assert props["confidence_parts"] is None


def test_geojson_translation_never_invents_text():
    doc = {
        "_id": "p3", "name": "Y", "lat": 1.0, "lon": 2.0,
        "confidence_reasons": ["raison inconnue"],
    }
    props = ports_to_geojson([doc])["features"][0]["properties"]
    assert props["reasons_en"] == ["raison inconnue"]
