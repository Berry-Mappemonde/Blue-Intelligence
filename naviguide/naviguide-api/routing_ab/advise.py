"""Automatic advice: gates already present, KEEP/DROP, next gate, 20 nm.

Usage (from naviguide-api/):
    python -m routing_ab.advise --out routing_ab/out
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .cargo import anti_shipping_score
from .decide import decide_gate
from .engines import run_engine
from .enriched import GATES, stitch_via_route, vias_for_leg
from .filament import mean_dist_to_filament_nm, offset_from_filament
from .itinerary_gates import (
    ITINERARY_GATES,
    missing_canals_on_path,
)
from .legs import (
    CAP_VERDE,
    CAYENNE,
    HAUT_AUS_2,
    HAUT_AUS_3,
    NOUMEA,
    PAPEETE,
    SAINTE_LUCIE,
    TORRES_ITIN,
    WALLIS,
)
from .metrics import coral_sea_points, land_hits, path_length_nm


def _land_fn():
    try:
        from global_land_mask import globe

        return lambda lat, lon: bool(globe.is_land(lat, lon))
    except Exception:
        return None


def _cargo_route(start, end) -> tuple[list[list[float]], Optional[str]]:
    result = run_engine("searoute_14", start, end)
    return result.coords, result.error


def _measure_pair(start, end, vias: list, is_land):
    cargo, err = _cargo_route(start, end)
    if err or not cargo:
        return None, None, err

    def route_fn(a, b):
        coords, e = _cargo_route(a, b)
        if e or not coords:
            raise RuntimeError(e or "empty sub-route")
        return coords

    if vias:
        try:
            gated = stitch_via_route(route_fn, start, end)
        except Exception as exc:
            return cargo, None, str(exc)
    else:
        gated = cargo
    return cargo, gated, None


def _stats(coords, is_land) -> dict:
    return {
        "nm": path_length_nm(coords),
        "coral": coral_sea_points(coords),
        "land": land_hits(coords, is_land),
        "anti": anti_shipping_score(coords),
        "n": len(coords),
    }


# Sheets to judge automatically (one leg + the gate vias).
GATE_CASES = (
    {
        "id": "torres_gne_pow",
        "title": "Torres (already on the itinerary)",
        "start": NOUMEA,
        "end": TORRES_ITIN,
        "in_itinerary": True,
        "leg": "Nouméa → Torres",
    },
    {
        "id": "mentawai_west",
        "title": "West Mentawai (prototype, not in the app)",
        "start": HAUT_AUS_2,
        "end": HAUT_AUS_3,
        "in_itinerary": False,
        "leg": "haut Australie 2 → 3",
    },
    {
        "id": "antimeridian_pacific",
        "title": "Via 180° Wallis–Nouméa (prototype)",
        "start": WALLIS,
        "end": NOUMEA,
        "in_itinerary": False,
        "leg": "Wallis → Nouméa",
    },
)


def advise_gates(is_land) -> list[dict]:
    rows = []
    for case in GATE_CASES:
        start, end = case["start"], case["end"]
        vias = vias_for_leg(start, end)
        cargo, gated, err = _measure_pair(start, end, vias, is_land)
        if err or cargo is None:
            rows.append({
                **case,
                "vias": vias,
                "decision": {"verdict": "À MESURER", "why": err or "empty route"},
            })
            continue
        cs, gs = _stats(cargo, is_land), _stats(gated or cargo, is_land)
        decision = decide_gate(
            cs["nm"], gs["nm"],
            cs["coral"], gs["coral"],
            cs["land"], gs["land"],
            cs["anti"],
            case["in_itinerary"],
        )
        rows.append({
            **{k: case[k] for k in ("id", "title", "in_itinerary", "leg")},
            "vias": [[v[0], v[1]] for v in vias],
            "cargo": cs,
            "gated": gs,
            "decision": decision,
        })
    return rows


def advise_next_gate(is_land) -> dict:
    """Cayenne → Papeete: 6000 nm with no Panama plot on the itinerary."""
    cargo, err = _cargo_route(CAYENNE, PAPEETE)
    missing = missing_canals_on_path(cargo) if cargo else []
    return {
        "leg": "Cayenne → Papeete",
        "cargo_nm": path_length_nm(cargo) if cargo else None,
        "cargo_land": land_hits(cargo, is_land) if cargo else None,
        "missing_canals": missing,
        "error": err,
        "recommendation": (
            f"Next gate to place: {missing[0]} "
            "(the cargo line crosses the canal; the itinerary has no plot inside)."
            if missing else
            "No obvious missing canal on Cayenne → Papeete."
        ),
    }


def advise_ocean_offset(is_land) -> dict:
    """One ocean leg: 20 nm beside the filament, mid-run only."""
    cargo, err = _cargo_route(CAP_VERDE, SAINTE_LUCIE)
    if err or not cargo:
        return {"leg": "Cap-Vert → Sainte-Lucie", "error": err or "empty route"}
    shifted = offset_from_filament(cargo, offset_nm=20.0, is_land=is_land)
    return {
        "leg": "Cap-Vert → Sainte-Lucie",
        "offset_nm": 20,
        "cargo_nm": path_length_nm(cargo),
        "shifted_nm": path_length_nm(shifted),
        "mean_dist_to_fil_before_nm": mean_dist_to_filament_nm(cargo, cargo),
        "mean_dist_to_fil_after_nm": mean_dist_to_filament_nm(shifted, cargo),
        "cargo_coords": cargo,
        "shifted_coords": shifted,
        "error": err,
        "plain": (
            "On this leg, the line was pushed about 20 nm in mid-ocean "
            "without moving the approaches. "
            f"Mean gap to the cargo filament: "
            f"{mean_dist_to_filament_nm(shifted, cargo):.1f} nm "
            f"(before: {mean_dist_to_filament_nm(cargo, cargo):.1f})."
        ),
    }


def build_advice() -> dict:
    is_land = _land_fn()
    gates = advise_gates(is_land)
    nxt = advise_next_gate(is_land)
    ocean = advise_ocean_offset(is_land)
    # Do not serialize huge polylines twice in the text JSON:
    ocean_slim = {k: v for k, v in ocean.items() if k not in {"cargo_coords", "shifted_coords"}}
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "plain": {
            "deja_la": (
                "Yes: the circumnavigation gates are already in itineraryPoints.ts "
                "(Torres, Australia highs, Cape of Good Hope, Corsica / Atlantic plots). "
                "The app already sends them to GET /route, one leg after another."
            ),
            "prototype": (
                "Beside that, routing_ab/enriched.py has 3 trial gates (Torres, Mentawai, "
                "via 180°) that are NOT wired into the app."
            ),
            "automatise": (
                "The program measures and proposes GARDER / JETER / INUTILE. "
                "You only say whether you override a line — you do not place "
                "the points by hand."
            ),
            "main": (
                "You do not have to print the chart to decide Mentawai or Panama: "
                "the numbers do it. The chart is only for when you disagree."
            ),
        },
        "itinerary_gates": [
            {"name": g.name, "lon": g.lon, "lat": g.lat, "kind": g.kind, "note": g.note}
            for g in ITINERARY_GATES
        ],
        "prototype_gates": [
            {"id": g.id, "vias": [[v[0], v[1]] for v in g.vias]}
            for g in GATES
        ],
        "decisions": gates,
        "next_gate": nxt,
        "ocean_offset": ocean_slim,
        "geojson": {
            "type": "FeatureCollection",
            "features": _offset_features(ocean),
        },
    }


def _offset_features(ocean: dict) -> list[dict]:
    feats = []
    if ocean.get("cargo_coords"):
        feats.append({
            "type": "Feature",
            "properties": {"engine": "cargo filament", "color": "#2563eb"},
            "geometry": {"type": "LineString", "coordinates": ocean["cargo_coords"]},
        })
    if ocean.get("shifted_coords"):
        feats.append({
            "type": "Feature",
            "properties": {"engine": "20 nm beside", "color": "#16a34a"},
            "geometry": {"type": "LineString", "coordinates": ocean["shifted_coords"]},
        })
    return feats


def _html(advice: dict) -> str:
    dec_rows = ""
    for d in advice["decisions"]:
        dec = d.get("decision", {})
        dec_rows += (
            f"<tr><td>{d['title']}</td><td>{d['leg']}</td>"
            f"<td><strong>{dec.get('verdict','')}</strong></td>"
            f"<td>{dec.get('why','')}</td></tr>"
        )
    itin = "".join(
        f"<li><strong>{g['name']}</strong> — {g['note']} "
        f"({g['lat']:.3f}, {g['lon']:.3f})</li>"
        for g in advice["itinerary_gates"] if g["kind"] == "porte"
    )
    geo = json.dumps(advice["geojson"])
    nxt = advice["next_gate"].get("recommendation", "")
    ocean = advice["ocean_offset"].get("plain", "")
    p = advice["plain"]
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<title>NAVIGUIDE — gate advice</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<style>
 body {{ font-family: Georgia, serif; margin: 0; background: #f6f3ee; color: #1c1917; }}
 header {{ padding: 1rem 1.5rem; background: #1e3a5f; color: #fff; }}
 .wrap {{ padding: 1rem 1.5rem 2rem; }}
 table {{ border-collapse: collapse; width: 100%; background: #fff; }}
 th, td {{ border: 1px solid #d6d3d1; padding: 0.4rem 0.55rem; text-align: left; }}
 th {{ background: #e7e5e4; }}
 #map {{ height: 380px; margin-top: 1rem; }}
</style></head>
<body>
<header><h1>Automatic advice — gates and traffic</h1>
<p>You do not have to do everything by hand. Berry gates are already on the itinerary.</p></header>
<div class="wrap">
<p>{p['deja_la']}</p>
<p>{p['prototype']}</p>
<p>{p['automatise']}</p>
<h2>Gates already in the app</h2>
<ul>{itin}</ul>
<h2>Automatic verdicts</h2>
<table><tr><th>Gate</th><th>Leg</th><th>Verdict</th><th>Why</th></tr>
{dec_rows}</table>
<h2>Next gate</h2>
<p>{nxt}</p>
<h2>Traffic: 20 nm beside the filament (Cap-Vert → Sainte-Lucie)</h2>
<p>{ocean}</p>
<div id="map"></div>
</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const fc = {geo};
const map = L.map('map').setView([10, -40], 4);
L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{attribution: '&copy; OSM'}}).addTo(map);
const layer = L.geoJSON(fc, {{
  style: f => ({{ color: f.properties.color, weight: 3 }})
}}).addTo(map);
if (fc.features.length) map.fitBounds(layer.getBounds().pad(0.2));
</script>
</body></html>
"""


def write_advice(advice: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    slim = {k: v for k, v in advice.items() if k != "geojson"}
    (out_dir / "advise.json").write_text(json.dumps(slim, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "advise.html").write_text(_html(advice), encoding="utf-8")
    (out_dir / "advise.geojson").write_text(json.dumps(advice["geojson"]), encoding="utf-8")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Automatic gate / traffic advice")
    parser.add_argument("--out", default="routing_ab/out")
    args = parser.parse_args(argv)
    advice = build_advice()
    write_advice(advice, Path(args.out))
    print(f"wrote {args.out}/advise.html")
    for d in advice["decisions"]:
        dec = d["decision"]
        print(f"  {dec.get('verdict','?'):<10} {d['title']} — {dec.get('why','')}")
    print(" ", advice["next_gate"].get("recommendation"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
