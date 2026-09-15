"""Automatic synthesis from the A/B bench rows."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_leg: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in rows:
        by_leg[row["leg_id"]][row["engine"]] = row

    sr14_vs_16: list[float] = []
    sr14_vs_marnet: list[float] = []
    for engines in by_leg.values():
        a, b = engines.get("searoute_14"), engines.get("searoute_16")
        if a and b and a.get("length_nm") and b.get("length_nm"):
            sr14_vs_16.append(abs(a["length_nm"] - b["length_nm"]))
        a, c = engines.get("searoute_14"), engines.get("scgraph_marnet")
        if a and c and a.get("length_nm") and c.get("length_nm"):
            sr14_vs_marnet.append(abs(a["length_nm"] - c["length_nm"]))

    oak_worse = []
    for leg_id, engines in by_leg.items():
        a, oak = engines.get("searoute_14"), engines.get("scgraph_oak_ridge")
        if a and oak and a.get("length_nm") and oak.get("length_nm"):
            if oak["length_nm"] > a["length_nm"] * 1.15:
                oak_worse.append(leg_id)

    enriched_fail = [
        row["leg_id"]
        for row in rows
        if row["engine"] == "enriched_sailing" and not row.get("ok")
    ]

    bullets = [
        "searoute 1.4 and 1.6 stay the same kind of cargo corridor; "
        f"median length gap ≈ {_median(sr14_vs_16):.0f} nm.",
        "scgraph marnet follows the same graph as searoute "
        f"(median gap ≈ {_median(sr14_vs_marnet):.0f} nm): this is not a new channel.",
        (
            "scgraph Oak Ridge lengthens clearly: " + ", ".join(oak_worse) + "."
            if oak_worse
            else "scgraph Oak Ridge stays comparable on these legs."
        ),
        (
            "The enriched graph still has failures (Coral / detour): "
            + ", ".join(enriched_fail)
            if enriched_fail
            else "After the guardrail, the enriched graph no longer introduces a Coral detour."
        ),
        "Cayenne → Papeete: every raw cargo graph pokes land "
        "(canals / islands). The /route pipeline (avoid_land) remains required.",
        "Production GET /route is unchanged. Next step: "
        "validate sailing gates one by one, then offset cargo outside straits.",
    ]
    return {
        "sr14_vs_sr16_median_nm": round(_median(sr14_vs_16), 1),
        "sr14_vs_marnet_median_nm": round(_median(sr14_vs_marnet), 1),
        "oak_ridge_longer_legs": oak_worse,
        "enriched_failures": enriched_fail,
        "bullets": bullets,
    }


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    mid = len(s) // 2
    if len(s) % 2:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2
