#!/usr/bin/env python3
"""
Envoie les trajets or Naviguide vers LangSmith — Mac local uniquement.

  python3 naviguide/scripts/langsmith_golden_legs.py --check
  python3 naviguide/scripts/langsmith_golden_legs.py --list
  python3 naviguide/scripts/langsmith_golden_legs.py
  python3 naviguide/scripts/langsmith_golden_legs.py --only meteo-mayotte-reunion-janvier
  python3 naviguide/scripts/langsmith_golden_legs.py --with-orchestrator

Les traces n'apparaissent que si LANGSMITH_LOCAL=1, LANGSMITH_TRACING=true
et LANGSMITH_API_KEY sont posés dans le .env du Mac.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List

_NAVIGUIDE_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _NAVIGUIDE_ROOT.parent
_CATALOG = _NAVIGUIDE_ROOT / "data" / "langsmith_golden_legs.json"

if str(_NAVIGUIDE_ROOT) not in sys.path:
    sys.path.insert(0, str(_NAVIGUIDE_ROOT))

from langsmith_local import boot_langsmith  # noqa: E402

_METEO_KEYS = (
    "from_stop", "to_stop", "lat", "lon", "nm_remaining",
    "language", "dest_lat", "dest_lon", "month",
)
_SIMPLE_KEYS = ("from_stop", "to_stop", "lat", "lon", "nm_remaining", "language")


def _load_catalog() -> dict:
    return json.loads(_CATALOG.read_text(encoding="utf-8"))


def _pick_legs(catalog: dict, only: str | None, with_orchestrator: bool) -> List[dict]:
    legs = list(catalog["legs"])
    if only:
        legs = [leg for leg in legs if leg["id"] == only]
        if not legs:
            known = ", ".join(item["id"] for item in catalog["legs"])
            raise SystemExit(f"Trajet inconnu {only!r}. Connus : {known}")
        return legs
    if with_orchestrator:
        return legs
    return [leg for leg in legs if not leg.get("optional")]


def _print_check(decision) -> None:
    print("")
    print("── Contrôle LangSmith ─────────────────────────────")
    print(f"  activé     : {'oui' if decision.enabled else 'non'}")
    print(f"  raison     : {decision.reason}")
    print(f"  projet     : {decision.project}")
    print(f"  échantillon: {decision.sampling_rate}")
    print(f"  message    : {decision.message}")
    if decision.enabled and not (os.environ.get("LANGSMITH_API_KEY") or "").strip():
        print("  clé        : MANQUANTE — colle LANGSMITH_API_KEY dans naviguide-api/.env")
    elif decision.enabled:
        print("  clé        : présente")
    print("──────────────────────────────────────────────────")
    print("")


def _print_list(legs: Iterable[dict]) -> None:
    print("Trajets or :")
    for leg in legs:
        flag = " (optionnel, --with-orchestrator)" if leg.get("optional") else ""
        print(f"  • {leg['id']:40}  {leg['title']}{flag}")
        print(f"      projet LangSmith : {leg['project']}")


def _trace_cm(project: str, enabled: bool):
    if not enabled:
        return contextlib.nullcontext()
    try:
        from langsmith import tracing_context
        return tracing_context(project_name=project)
    except ImportError:
        os.environ["LANGSMITH_PROJECT"] = project
        return contextlib.nullcontext()


def _run_meteo(inputs: dict) -> dict:
    api = str(_NAVIGUIDE_ROOT / "naviguide-api")
    if api not in sys.path:
        sys.path.insert(0, api)
    from agents.meteo_agent import run_meteo_agent
    kwargs = {k: inputs[k] for k in _METEO_KEYS if k in inputs}
    return run_meteo_agent(**kwargs)


def _run_guard(inputs: dict) -> dict:
    api = str(_NAVIGUIDE_ROOT / "naviguide-api")
    if api not in sys.path:
        sys.path.insert(0, api)
    from agents.guard_agent import run_guard_agent
    kwargs = {k: inputs[k] for k in _SIMPLE_KEYS if k in inputs}
    return run_guard_agent(**kwargs)


def _run_custom(inputs: dict) -> dict:
    api = str(_NAVIGUIDE_ROOT / "naviguide-api")
    if api not in sys.path:
        sys.path.insert(0, api)
    from agents.custom_agent import run_custom_agent
    kwargs = {k: inputs[k] for k in _SIMPLE_KEYS if k in inputs}
    return run_custom_agent(**kwargs)


def _run_pirate(inputs: dict) -> dict:
    api = str(_NAVIGUIDE_ROOT / "naviguide-api")
    if api not in sys.path:
        sys.path.insert(0, api)
    from agents.pirate_agent import run_pirate_agent
    kwargs = {k: inputs[k] for k in _SIMPLE_KEYS if k in inputs}
    return run_pirate_agent(**kwargs)


def _run_orchestrator(inputs: dict) -> dict:
    ws = str(_NAVIGUIDE_ROOT / "naviguide_workspace")
    if ws not in sys.path:
        sys.path.insert(0, ws)
    import naviguide_agent1.router as route_mod
    from naviguide_orchestrator.graph import build_orchestrator

    router_cls = next(
        getattr(route_mod, name)
        for name in dir(route_mod)
        if name.endswith("Router") and isinstance(getattr(route_mod, name), type)
    )
    state = {
        "waypoints": inputs["waypoints"],
        "vessel_specs": router_cls.VESSEL_PROFILE,
        "constraints": {},
        "expedition_id": None,
        "agent1_status": "pending",
        "agent1_errors": [],
        "route_plan": {},
        "anti_shipping_avg": 0.0,
        "polar_vmg": None,
        "polar_avg_speed": None,
        "total_eta_days": None,
        "agent3_status": "pending",
        "agent3_errors": [],
        "risk_report": {},
        "expedition_risk_level": "UNKNOWN",
        "expedition_plan": {},
        "executive_briefing": "",
        "messages": [],
        "errors": [],
        "status": "init",
        "language": inputs.get("language") or "fr",
        "chat_id": None,
        "access_token": None,
    }
    result = build_orchestrator().invoke(state)
    return {
        "status": result.get("status"),
        "agent1_status": result.get("agent1_status"),
        "agent3_status": result.get("agent3_status"),
        "expedition_risk_level": result.get("expedition_risk_level"),
        "errors": result.get("errors") or [],
    }


_RUNNERS = {
    "meteo": _run_meteo,
    "guard": _run_guard,
    "custom": _run_custom,
    "pirate": _run_pirate,
    "orchestrator": _run_orchestrator,
}


def _summarize(result: Any) -> str:
    if not isinstance(result, dict):
        return str(type(result))
    if "content" in result:
        text = (result.get("content") or "").replace("\n", " ")
        return text[:160] + ("…" if len(text) > 160 else "")
    parts = [
        f"status={result.get('status')}",
        f"agent1={result.get('agent1_status')}",
        f"agent3={result.get('agent3_status')}",
    ]
    return " ".join(parts)


def _run_leg(leg: dict, enabled: bool) -> None:
    runner = _RUNNERS[leg["agent"]]
    print(f"▶  {leg['id']}  →  projet {leg['project']}")
    print(f"    {leg['title']}")
    started = time.time()
    try:
        with _trace_cm(leg["project"], enabled):
            result = runner(leg["inputs"])
    except Exception as exc:
        print(f"    ✗  erreur : {exc}")
        return
    elapsed = time.time() - started
    print(f"    ✓  {elapsed:.1f}s  {_summarize(result)}")
    print("    À regarder dans LangSmith :")
    for hint in leg.get("look_for") or []:
        print(f"      – {hint}")
    print("")


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Trajets or Naviguide pour LangSmith (Mac local)."
    )
    parser.add_argument("--check", action="store_true", help="Contrôle le garde-fou, n'appelle aucun agent.")
    parser.add_argument("--list", action="store_true", help="Liste les trajets or.")
    parser.add_argument("--only", help="N'exécute que cet id de trajet.")
    parser.add_argument(
        "--with-orchestrator",
        action="store_true",
        help="Inclut les 2 trajets orchestrateur (plus lents, searoute).",
    )
    args = parser.parse_args(argv)

    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))

    catalog = _load_catalog()
    if args.list:
        _print_list(catalog["legs"])
        return 0

    decision = boot_langsmith()
    _print_check(decision)

    if args.check:
        return 0

    if not decision.enabled:
        print("Les agents vont tourner, mais aucune trace ne partira.")
        print("Pour allumer le microscope : docs/LANGSMITH_NAVIGUIDE.md")
        print("")

    legs = _pick_legs(catalog, args.only, args.with_orchestrator)
    print(f"{len(legs)} trajet(s) à enchaîner.\n")
    for leg in legs:
        _run_leg(leg, decision.enabled)
    print("Ensuite : https://smith.langchain.com  → projet du trajet → dernière trace.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
