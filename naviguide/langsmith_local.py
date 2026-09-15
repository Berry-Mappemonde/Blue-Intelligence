"""
LangSmith — microscope local uniquement.

Sans LANGSMITH_LOCAL=1, le tracing est coupé, même si LANGSMITH_TRACING=true.
Sur un hôte ou une URL de production (VPS OVH, naviguide.fr, …), le tracing
est coupé même avec LANGSMITH_LOCAL=1.

À appeler une fois au démarrage du process, après load_dotenv().
"""

from __future__ import annotations

import logging
import os
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, MutableMapping, Optional

log = logging.getLogger("naviguide.langsmith")

_TRACE_FLAGS = ("LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2", "LANGCHAIN_TRACING")

_PROD_HOST_MARKERS = (
    "vps.ovh",
    "vps-52ba6d62",
    "naviguide.fr",
)

_PROD_URL_MARKERS = (
    "naviguide.fr",
    "blueintelligence.online",
    "csw6hpki.run.complete.dev",
)

_PROD_URL_KEYS = (
    "VITE_API_URL",
    "VITE_ORCHESTRATOR_URL",
    "VITE_POLAR_API_URL",
    "VITE_WEATHER_ROUTING_URL",
    "BI_API_BASE",
    "PUBLIC_URL",
    "NAVIGUIDE_PUBLIC_URL",
)

_PROD_ENV_KEYS = ("NAVIGUIDE_ENV", "ENVIRONMENT", "APP_ENV")
_PROD_ENV_VALUES = frozenset({"production", "prod", "staging"})

_NAVIGUIDE_ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class LangSmithDecision:
    enabled: bool
    reason: str
    message: str
    project: str
    sampling_rate: str
    local: bool
    tracing_requested: bool


def _truthy(value: Optional[str]) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _env_get(env: Mapping[str, str], key: str) -> str:
    return (env.get(key) or "").strip()


def _tracing_requested(env: Mapping[str, str]) -> bool:
    return any(_truthy(_env_get(env, key)) for key in _TRACE_FLAGS)


def _is_local_flag(env: Mapping[str, str]) -> bool:
    return _truthy(_env_get(env, "LANGSMITH_LOCAL"))


def _production_host(hostname: str) -> Optional[str]:
    host = (hostname or "").strip().lower()
    for marker in _PROD_HOST_MARKERS:
        if marker in host:
            return marker
    return None


def _production_env(env: Mapping[str, str]) -> Optional[str]:
    for key in _PROD_ENV_KEYS:
        value = _env_get(env, key).lower()
        if value in _PROD_ENV_VALUES:
            return f"{key}={value}"
    return None


def _production_url(env: Mapping[str, str]) -> Optional[str]:
    for key in _PROD_URL_KEYS:
        value = _env_get(env, key).lower()
        if not value:
            continue
        for marker in _PROD_URL_MARKERS:
            if marker in value:
                return f"{key} contient {marker}"
    return None


def inspect_langsmith(
    *,
    environ: Optional[Mapping[str, str]] = None,
    hostname: Optional[str] = None,
) -> LangSmithDecision:
    """Décide si le tracing LangSmith a le droit de s'allumer. Ne mute rien."""
    env = os.environ if environ is None else environ
    host = socket.gethostname() if hostname is None else hostname
    project = _env_get(env, "LANGSMITH_PROJECT") or "naviguide-local"
    sampling = _env_get(env, "LANGSMITH_TRACING_SAMPLING_RATE") or "1"
    local = _is_local_flag(env)
    requested = _tracing_requested(env)

    prod_host = _production_host(host)
    if prod_host:
        return LangSmithDecision(
            enabled=False,
            reason="production_host",
            message=(
                f"LangSmith coupé : cet hôte ressemble à la production "
                f"({prod_host!r}). Le microscope reste sur le Mac."
            ),
            project=project,
            sampling_rate=sampling,
            local=local,
            tracing_requested=requested,
        )

    prod_env = _production_env(env)
    if prod_env:
        return LangSmithDecision(
            enabled=False,
            reason="production_env",
            message=(
                f"LangSmith coupé : {prod_env} n'est pas un environnement local."
            ),
            project=project,
            sampling_rate=sampling,
            local=local,
            tracing_requested=requested,
        )

    prod_url = _production_url(env)
    if prod_url:
        return LangSmithDecision(
            enabled=False,
            reason="production_url",
            message=f"LangSmith coupé : {prod_url}.",
            project=project,
            sampling_rate=sampling,
            local=local,
            tracing_requested=requested,
        )

    if not requested:
        return LangSmithDecision(
            enabled=False,
            reason="tracing_not_requested",
            message="LangSmith inactif (LANGSMITH_TRACING n'est pas true).",
            project=project,
            sampling_rate=sampling,
            local=local,
            tracing_requested=False,
        )

    if not local:
        return LangSmithDecision(
            enabled=False,
            reason="missing_local_flag",
            message=(
                "LangSmith ignoré : LANGSMITH_TRACING=true mais il manque "
                "LANGSMITH_LOCAL=1. Ajoute ce drapeau dans le .env de ton Mac, "
                "jamais sur le VPS."
            ),
            project=project,
            sampling_rate=sampling,
            local=False,
            tracing_requested=True,
        )

    return LangSmithDecision(
        enabled=True,
        reason="enabled",
        message=(
            f"LangSmith microscope local — projet {project!r} "
            f"(échantillon {sampling})."
        ),
        project=project,
        sampling_rate=sampling,
        local=True,
        tracing_requested=True,
    )


def apply_langsmith_guard(
    *,
    environ: Optional[MutableMapping[str, str]] = None,
    hostname: Optional[str] = None,
) -> LangSmithDecision:
    """Applique la décision : coupe les variables de tracing si besoin."""
    env: MutableMapping[str, str] = os.environ if environ is None else environ
    decision = inspect_langsmith(environ=env, hostname=hostname)

    if not decision.enabled:
        for key in _TRACE_FLAGS:
            env[key] = "false"
        if decision.tracing_requested:
            log.warning(decision.message)
            print(f"⚠️  {decision.message}")
        return decision

    env["LANGSMITH_TRACING"] = "true"
    log.info(decision.message)
    print(f"🔎 {decision.message}")
    if not _env_get(env, "LANGSMITH_API_KEY"):
        warn = (
            "LANGSMITH_TRACING est allumé mais LANGSMITH_API_KEY est vide — "
            "aucune trace ne partira. Colle ta clé dans le .env local."
        )
        log.warning(warn)
        print(f"⚠️  {warn}")
    return decision


def load_naviguide_dotenv() -> None:
    """Charge les .env Naviguide connus, sans écraser l'environnement déjà posé."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for path in (
        _NAVIGUIDE_ROOT / ".env",
        _NAVIGUIDE_ROOT / "naviguide_workspace" / ".env",
        _NAVIGUIDE_ROOT / "naviguide-api" / ".env",
    ):
        if path.is_file():
            load_dotenv(path, override=False)


def boot_langsmith() -> LangSmithDecision:
    """load_dotenv des .env Naviguide, puis garde-fou."""
    load_naviguide_dotenv()
    return apply_langsmith_guard()
