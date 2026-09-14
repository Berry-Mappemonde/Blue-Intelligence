"""C15–C16: judge “is this a navigation rule?” — no network."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.nav_rule import (
    apply_nav_rule_gate,
    heuristic_navigation_rule,
    judge_navigation_rule,
    should_write_vhf,
)
from app.services.marina_enrich import marina_from_pages


def test_fixture_vhf_is_a_rule():
    assert heuristic_navigation_rule("VHF 09 à l'entrée") is True


def test_fixture_restaurant_is_not_a_rule():
    assert heuristic_navigation_rule("restaurant avec vue mer") is False


def test_should_not_write_invented_vhf():
    assert should_write_vhf("restaurant avec vue mer", "09") is False
    assert should_write_vhf("VHF 09 à l'entrée", "09") is True
    gated = apply_nav_rule_gate({"canal_vhf": "09"}, "restaurant avec vue mer")
    assert gated["canal_vhf"] is None


def test_marina_from_pages_drops_tourist_vhf():
    tourist = marina_from_pages([{"text": "Restaurant avec vue mer. Tél 05 46 00 00 00"}])
    assert tourist.get("canal_vhf") in (None, "")


def test_judge_heuristic_without_llm():
    import asyncio
    vhf = asyncio.run(judge_navigation_rule("VHF 09 à l'entrée", use_llm=False))
    resto = asyncio.run(judge_navigation_rule("restaurant avec vue mer", use_llm=False))
    assert vhf["navigation_rule"] is True
    assert vhf["engine"] == "heuristic"
    assert resto["navigation_rule"] is False
