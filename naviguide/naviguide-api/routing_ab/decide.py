"""Automatic KEEP / DROP / USELESS rules — the skipper may override.

Verdict tokens stay French (GARDER / JETER / INUTILE / À MESURER) so
existing bench reports and tests stay stable.
"""

from __future__ import annotations

from typing import Any, Optional


def decide_gate(
    cargo_nm: Optional[float],
    gated_nm: Optional[float],
    cargo_coral: int,
    gated_coral: int,
    cargo_land: int,
    gated_land: int,
    cargo_anti: Optional[float],
    in_itinerary: bool,
    extra_ratio_useless: float = 1.10,
    extra_ratio_reject: float = 1.35,
) -> dict[str, Any]:
    """Decide from the numbers, not from a map looked at by hand."""
    if cargo_nm is None or gated_nm is None or cargo_nm <= 0:
        return {"verdict": "À MESURER", "why": "not enough numbers (engine missing)."}

    ratio = gated_nm / cargo_nm
    if gated_coral > cargo_coral:
        return {
            "verdict": "JETER",
            "why": "the gate recreates a Coral Sea detour (or makes it worse).",
            "ratio": round(ratio, 3),
        }
    if gated_land > cargo_land + 1:
        return {
            "verdict": "JETER",
            "why": "the gate adds points on land.",
            "ratio": round(ratio, 3),
        }
    if ratio > extra_ratio_reject:
        return {
            "verdict": "JETER",
            "why": f"detour too long ({ratio:.2f}× the cargo route).",
            "ratio": round(ratio, 3),
        }
    if in_itinerary and gated_coral == 0:
        return {
            "verdict": "GARDER",
            "why": "already on the Berry itinerary, and the line stays clean.",
            "ratio": round(ratio, 3),
        }
    if (
        cargo_coral == 0
        and cargo_land == 0
        and (cargo_anti or 0) >= 0.99
        and ratio > extra_ratio_useless
    ):
        return {
            "verdict": "INUTILE",
            "why": (
                "cargo is already off-lane and off-land; "
                f"the gate lengthens by {(ratio - 1) * 100:.0f} % with no traffic gain."
            ),
            "ratio": round(ratio, 3),
        }
    if cargo_coral > 0 and gated_coral == 0:
        return {
            "verdict": "GARDER",
            "why": "the gate avoids a Coral Sea detour.",
            "ratio": round(ratio, 3),
        }
    return {
        "verdict": "GARDER",
        "why": "the gate worsens neither land nor Coral Sea; lengthening is acceptable.",
        "ratio": round(ratio, 3),
    }
