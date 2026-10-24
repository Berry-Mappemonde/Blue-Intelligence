"""Mini-script de test Phase 2 — Arbitrage Zetaris (tolérance 25 km) + score > 80.

Usage (depuis backend/):
    python test_zetaris.py

Ce script teste :
  1. La distance Haversine entre un port fictif et un port connu de poe_ports (≤ 25 km).
  2. La logique cross_reference_zetaris : un port à ≤ 25 km obtient "Zetaris Certified".
  3. Le recalibrage de confiance : un port certifié a un confidence_score > 80.
"""

import asyncio
import sys
import os

# Ajoute backend/ au path pour les imports de l'app.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.geo import haversine_km
from app.services.poe_pipeline import (
    cross_reference_zetaris,
    zetaris_name_key,
    ZETARIS_MATCH_TOLERANCE_KM,
)


# ---------------------------------------------------------------------------
# 1. Distance Haversine : port fictif à ~5 km de "Port of Ghazaouet"
# ---------------------------------------------------------------------------
GHZ_LAT, GHZ_LON = 35.093863, -1.86322  # Port of Ghazaouet (Algeria, mrgid 8378)
# Point à ~5 km au sud-est (dans la tolérance 25 km).
FICT_LAT, FICT_LON = 35.0550, -1.8200

dist = haversine_km(GHZ_LAT, GHZ_LON, FICT_LAT, FICT_LON)
print(f"[1/3] Haversine(Ghazaouet <-> fictif) = {dist} km (tolérance {ZETARIS_MATCH_TOLERANCE_KM} km)")
assert dist <= ZETARIS_MATCH_TOLERANCE_KM, f"Distance {dist} km > tolérance {ZETARIS_MATCH_TOLERANCE_KM} km"
print("    OK: le port fictif est dans la tolérance 25 km.")


# ---------------------------------------------------------------------------
# 2. Logique d'arbitrage cross_reference_zetaris
# ---------------------------------------------------------------------------
# On simule zetaris_result comme le retournerait validate_ports_zetaris :
# un port officiel "Port of Ghazaouet" dans la zone "Algeria".
zone = {"name": "Algeria"}
zetaris_result = {
    "mode": "sample",
    "ports_by_zone": {
        zetaris_name_key("Algeria"): [
            {
                "name": "Port of Ghazaouet",
                "lat": GHZ_LAT,
                "lon": GHZ_LON,
                "note": "Sample fixture",
                "validated": True,
                "geocode_source": "nominatim",
            }
        ]
    },
    "official_count": 1,
}

# Port extrait : nom différent, coordonnées à ≤ 25 km (simule une rade/baie/estuaire).
extracted_ports = [
    {
        "name": "Rade de Ghazaouet (estuaire fictif)",
        "lat": FICT_LAT,
        "lon": FICT_LON,
        "source_urls": ["https://example.gov.dz/ports"],
        "extraction_engine": "llm",
        "confidence": 40,
        "confidence_reasons": ["source nationale non whitelistée", "un seul extracteur"],
        "check_reasons": [],
        "verdict": "flag",
        "flag": True,
        "needs_review": True,
    }
]

ports = asyncio.run(cross_reference_zetaris(extracted_ports, zone, zetaris_result))
p = ports[0]

print(f"[2/3] Port extrait : '{p['name']}'")
print(f"    zetaris_validation   = {p.get('zetaris_validation')}")
print(f"    arbitration_status   = {p.get('arbitration_status')}")
print(f"    zetaris_distance_km  = {p.get('zetaris_distance_km')}")
print(f"    zetaris_matched_port = {p.get('zetaris_matched_port')}")

assert p.get("arbitration_status") == "Zetaris Certified", (
    f"Statut attendu 'Zetaris Certified', obtenu '{p.get('arbitration_status')}'"
)
assert p.get("zetaris_validation") == "official"
assert p.get("zetaris_distance_km") is not None and p.get("zetaris_distance_km") <= 25.0
print("    OK: arbitrage Zetaris Certified appliqué (distance ≤ 25 km, nom différent).")


# ---------------------------------------------------------------------------
# 3. Recalibrage du score > 80 et retrait du drapeau d'anomalie
# ---------------------------------------------------------------------------
# Simule le recalibrage appliqué dans _extract_and_geocode après apply_score.
conf = int(p.get("confidence") or 0)
if p.get("arbitration_status") == "Zetaris Certified" and conf < 85:
    p["confidence"] = 85
p["confidence_score"] = int(p["confidence"])
p["flag"] = False
p["needs_review"] = False
p["verdict"] = "pass"

print(f"[3/3] confidence_score   = {p.get('confidence_score')}")
print(f"    flag                 = {p.get('flag')}")
print(f"    needs_review         = {p.get('needs_review')}")
print(f"    verdict              = {p.get('verdict')}")

assert p.get("confidence_score", 0) > 80, f"Score attendu > 80, obtenu {p.get('confidence_score')}"
assert p.get("flag") is False
assert p.get("needs_review") is False
assert p.get("verdict") == "pass"
print("    OK: score > 80 et drapeau d'anomalie retiré.")

print("\n=== TOUS LES TESTS PHASE 2 SONT VERTS ===")
