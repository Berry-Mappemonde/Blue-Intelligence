"""Garde-fou LangSmith — aucun réseau, aucune clé."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langsmith_local import apply_langsmith_guard, inspect_langsmith


def test_off_when_tracing_unset():
    decision = inspect_langsmith(environ={}, hostname="macbook-de-jean.local")
    assert decision.enabled is False
    assert decision.reason == "tracing_not_requested"


def test_off_when_tracing_without_local_flag():
    decision = inspect_langsmith(
        environ={"LANGSMITH_TRACING": "true", "LANGSMITH_API_KEY": "lsv2_xxx"},
        hostname="macbook-de-jean.local",
    )
    assert decision.enabled is False
    assert decision.reason == "missing_local_flag"


def test_on_when_local_and_tracing():
    decision = inspect_langsmith(
        environ={
            "LANGSMITH_LOCAL": "1",
            "LANGSMITH_TRACING": "true",
            "LANGSMITH_PROJECT": "naviguide-meteo-dev",
            "LANGSMITH_TRACING_SAMPLING_RATE": "1",
        },
        hostname="macbook-de-jean.local",
    )
    assert decision.enabled is True
    assert decision.reason == "enabled"
    assert decision.project == "naviguide-meteo-dev"


def test_legacy_langchain_flag_counts_as_requested():
    decision = inspect_langsmith(
        environ={"LANGCHAIN_TRACING_V2": "true", "LANGSMITH_LOCAL": "1"},
        hostname="macbook-de-jean.local",
    )
    assert decision.tracing_requested is True
    assert decision.enabled is True


def test_prod_host_wins_even_with_local():
    decision = inspect_langsmith(
        environ={"LANGSMITH_LOCAL": "1", "LANGSMITH_TRACING": "true"},
        hostname="vps-52ba6d62.vps.ovh.net",
    )
    assert decision.enabled is False
    assert decision.reason == "production_host"


def test_staging_env_is_blocked():
    decision = inspect_langsmith(
        environ={
            "LANGSMITH_LOCAL": "1",
            "LANGSMITH_TRACING": "true",
            "NAVIGUIDE_ENV": "staging",
        },
        hostname="macbook-de-jean.local",
    )
    assert decision.enabled is False
    assert decision.reason == "production_env"


def test_production_url_is_blocked():
    decision = inspect_langsmith(
        environ={
            "LANGSMITH_LOCAL": "1",
            "LANGSMITH_TRACING": "true",
            "VITE_API_URL": "https://www.naviguide.fr",
        },
        hostname="macbook-de-jean.local",
    )
    assert decision.enabled is False
    assert decision.reason == "production_url"


def test_apply_clears_all_trace_flags_when_blocked():
    env = {
        "LANGSMITH_TRACING": "true",
        "LANGCHAIN_TRACING_V2": "true",
        "LANGCHAIN_TRACING": "true",
    }
    decision = apply_langsmith_guard(environ=env, hostname="macbook-de-jean.local")
    assert decision.enabled is False
    assert env["LANGSMITH_TRACING"] == "false"
    assert env["LANGCHAIN_TRACING_V2"] == "false"
    assert env["LANGCHAIN_TRACING"] == "false"


def test_apply_keeps_tracing_when_allowed():
    env = {
        "LANGSMITH_LOCAL": "yes",
        "LANGSMITH_TRACING": "true",
        "LANGSMITH_PROJECT": "naviguide-orchestrator-dev",
    }
    decision = apply_langsmith_guard(environ=env, hostname="MacBook-Pro.local")
    assert decision.enabled is True
    assert env["LANGSMITH_TRACING"] == "true"


def test_localhost_api_url_is_not_production():
    decision = inspect_langsmith(
        environ={
            "LANGSMITH_LOCAL": "1",
            "LANGSMITH_TRACING": "true",
            "VITE_API_URL": "http://localhost:8000",
        },
        hostname="macbook-de-jean.local",
    )
    assert decision.enabled is True
