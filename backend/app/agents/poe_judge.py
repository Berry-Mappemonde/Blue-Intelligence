"""Jugement sémantique groupé (Batch) des ports de référence V1 par Nemotron Ultra.

Remplace l'évaluation séquentielle port par port par un SEUL appel Nemotron
qui évalue tous les ports d'une zone en une fois, éliminant les timeouts
HTTP 499 (client) et 502 (saturation serveur Nightshift).

Format de sortie attendu de Nemotron :
{
    "evaluations": [
        {
            "name": "Nom du port",
            "is_poe": true/false,
            "tier": "tier1" | "tier2" | "tier_registered" | "tier3",
            "confidence": 85,
            "official_excerpt": "citation textuelle de preuve",
            "reasoning": "explication"
        }
    ]
}

La fonction publique retourne un mapping {port_name: evaluation}.
"""
from __future__ import annotations

import logging
from typing import Optional

from app.core.llm import ask_json

logger = logging.getLogger(__name__)

TIER1 = "tier1"          # Commercial Port of Entry (official source + designation)
TIER2 = "tier2"          # Yachting / leisure Port of Entry (official source)
TIER_REGISTERED = "tier_registered"  # Mentioned without clear status
TIER3 = "tier3"          # Not confirmed

_VALID_TIERS = {TIER1, TIER2, TIER_REGISTERED, TIER3}

# Prompt Nemotron : officier maritime et juridique (évaluation groupée d'une zone).
JUDGE_SYSTEM = """Tu es un officier maritime et juridique. Tu juges si plusieurs ports
candidats sont des Ports of Entry (points d'entrée pour les navires étrangers :
bureau de douane, immigration, contrôle maritime, clearance) d'après les
documents officiels d'une zone maritime.

Règles :
- Accepte les synonymes : 'port of entry', 'ports of entry', 'port d'entrée',
  'ports d'entrée', 'puerto de entrada', 'puertos de entrada', 'porto de
  entrada', 'portos de entrada', 'alfândega', 'alfândegas', 'dédouanement',
  'despacho aduaneiro', 'porto designado', 'port designated', 'porto di entrata',
  'porte d'entrée maritime', 'lieu de première arrivée', 'place of first
  arrival', 'designated port', 'capitania de puerto', 'capitanería de puerto'.
- Accepte les variations orthographiques : 'Harbour'/'Harbor', 'St.'/'Saint',
  'Ste.'/'Sainte', 'Mt.'/'Mount', accents et diacritiques ignorés.
- Un nom de port seul dans une adresse ou un bloc de contact NE suffit pas.
- Il faut une désignation officielle explicite (décret, gazette, liste officielle,
  arrêté ministériel, site gouvernemental .gov/.gouv/.gob).
- Évalue CHAQUE port de la liste indépendamment.
- Réponds UNIQUEMENT avec un JSON strict, sans prose, sans markdown.

Schema de sortie :
{
  "evaluations": [
    {
      "name": "<nom exact du port>",
      "is_poe": <true/false>,
      "tier": "<tier1|tier2|tier_registered|tier3>",
      "confidence": <int 0-100>,
      "official_excerpt": "<citation textuelle EXACTE de la source justifiant la décision, ou ''>",
      "reasoning": "<brève explication sémantique en français>"
    }
  ]
}

Tiers :
- tier1 : Port of Entry commercial confirmé par une source officielle qui le nomme
          près d'un terme d'entrée fort (port of entry, designated port, ...).
- tier2 : Port de plaisance/yachting confirmé par une source officielle (marina,
          clearance yacht, ...).
- tier_registered : le port est mentionné dans une source officielle mais sans
          statut d'entrée clair.
- tier3 : non confirmé, aucune source officielle ne le désigne comme PoE.
"""


def _coerce_judgment(raw: dict) -> dict:
    """Nettoie et valide un jugement individuel retourné par Nemotron."""
    is_poe = bool(raw.get("is_poe"))
    tier = str(raw.get("tier") or TIER3).strip().lower()
    if tier not in _VALID_TIERS:
        tier = TIER3
    try:
        confidence = int(raw.get("confidence") or 0)
    except (TypeError, ValueError):
        confidence = 0
    confidence = max(0, min(100, confidence))
    official_excerpt = str(raw.get("official_excerpt") or "").strip()
    reasoning = str(raw.get("reasoning") or "").strip()

    # Cohérence : si is_poe est False, tier ne devrait pas être tier1/tier2
    if not is_poe and tier in (TIER1, TIER2):
        tier = TIER_REGISTERED if confidence >= 40 else TIER3

    return {
        "is_poe": is_poe,
        "tier": tier,
        "confidence": confidence,
        "official_excerpt": official_excerpt,
        "reasoning": reasoning,
    }


def _default_judgment(reason: str = "fallback déterministe") -> dict:
    """Jugement par défaut quand Nemotron est indisponible (tier3, confidence faible)."""
    return {
        "is_poe": False,
        "tier": TIER3,
        "confidence": 20,
        "official_excerpt": "",
        "reasoning": reason,
        "_engine": "deterministic",
    }


def _build_user_prompt(ports: list[dict], official_texts: list[str], zone_name: str) -> str:
    """Construit le prompt utilisateur unique pour l'évaluation groupée de tous les ports d'une zone."""
    # Liste des ports candidats
    port_lines = []
    for port in ports:
        name = port.get("name") or "inconnu"
        city = port.get("city") or ""
        mrgid = port.get("mrgid")
        lat = port.get("lat")
        lon = port.get("lon")
        port_lines.append(
            f"- {name} (ville={city}, zone={zone_name}, mrgid={mrgid}, lat={lat}, lon={lon})"
        )
    ports_section = "\n".join(port_lines) if port_lines else "(aucun port candidat)"

    # Texte officiel consolidé de la zone
    official_section = "\n\n".join(official_texts) if official_texts else "(aucun document officiel disponible)"

    prompt = f"""ZONE : {zone_name}

PORTS CANDIDATS (Zetaris V1, blue_intel.poe_ports) à évaluer :
{ports_section}

TEXTES DES SOURCES OFFICIELLES DE LA ZONE :
{official_section}

TÂCHE : En tant qu'officier maritime et juridique, analyse pour CHAQUE port de la liste ci-dessus
si les documents officiels le désignent comme un Port of Entry (bureau de douane,
immigration, contrôle maritime). Comprends les synonymes et les variations orthographiques.

Pour chaque port, indique :
- son nom exact,
- s'il est un Port of Entry (is_poe: true/false),
- son tier (tier1, tier2, tier_registered, tier3),
- son score de confiance (0-100),
- l'extrait textuel de preuve (official_excerpt, citation exacte ou ''),
- une brève explication (reasoning).

Réponds en JSON strict avec la clé "evaluations" contenant un objet par port, sans prose, sans markdown."""
    return prompt


async def judge_zone_ports_with_nemotron(
    ports: list[dict],
    official_texts: list[str],
    zone_name: str,
    settings: Optional[dict] = None,
    log=None,
) -> dict[str, dict]:
    """Juge tous les ports d'une zone en un SEUL appel Nemotron Ultra (rôle 'judge').

    Args:
        ports: liste des dictionnaires de ports issus de Zetaris.
        official_texts: liste des textes officiels de la zone (snippets evidence_store).
        zone_name: nom de la zone (contexte pour le prompt).
        settings: paramètres de l'application (clés API, etc.).
        log: fonction de log optionnelle.

    Returns:
        Mapping {port_name: evaluation} où chaque évaluation contient
        {is_poe, tier, confidence, official_excerpt, reasoning, _engine}.
    """
    log = log or (lambda m: None)
    if not ports:
        return {}

    if not official_texts:
        log(f"Nemotron judge batch: aucun texte officiel pour {zone_name}, tier3 par défaut pour {len(ports)} port(s)")
        return {
            (p.get("name") or "inconnu"): _default_judgment(reason="aucun document officiel")
            for p in ports
        }

    prompt = _build_user_prompt(ports, official_texts, zone_name)

    try:
        raw = await ask_json(
            prompt,
            system=JUDGE_SYSTEM,
            settings=settings,
            max_tokens=2000,
            log=log,
            role="judge",
        )
        evaluations = raw.get("evaluations") or []
        results: dict[str, dict] = {}
        for entry in evaluations:
            name = entry.get("name") or "inconnu"
            judgment = _coerce_judgment(entry)
            judgment["_engine"] = "nemotron"
            results[name] = judgment
            log(f"Nemotron judge batch: {name} → is_poe={judgment['is_poe']}, "
                f"tier={judgment['tier']}, confidence={judgment['confidence']}")

        # S'assurer que chaque port a une évaluation (fallback tier3 pour ceux manquants)
        for port in ports:
            name = port.get("name") or "inconnu"
            if name not in results:
                results[name] = _default_judgment(reason="non évalué par Nemotron")

        log(f"Nemotron judge batch: {len(results)}/{len(ports)} port(s) évalués pour {zone_name}")
        return results
    except Exception as exc:
        log(f"Nemotron judge batch: échec pour {zone_name} ({type(exc).__name__}: {str(exc)[:120]}), fallback déterministe")
        return {
            (p.get("name") or "inconnu"): _default_judgment(reason=f"nemotron indisponible: {type(exc).__name__}")
            for p in ports
        }
