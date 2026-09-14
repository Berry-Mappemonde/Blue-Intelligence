"""Charge CDSE_* depuis l'environnement et les .env gitignorés.

CMEMS (vent / houle / courant) n'est pas CDSE (images Sentinel).
Ne jamais imprimer le mot de passe. Ne jamais committer .env.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_ENV_FILES = (
    Path(__file__).resolve().parent / ".env",
    ROOT / "backend" / ".env",
)


def load_cdse_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        load_dotenv = None
    if load_dotenv is not None:
        for path in _ENV_FILES:
            if path.is_file():
                load_dotenv(path, override=False)
        return
    for path in _ENV_FILES:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            key, value = raw.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            os.environ.setdefault(key, value)


def credentials() -> tuple[str, str]:
    load_cdse_env()
    user = (
        os.environ.get("CDSE_USERNAME")
        or os.environ.get("CDSE_USER")
        or ""
    ).strip()
    password = (os.environ.get("CDSE_PASSWORD") or "").strip()
    if not user or not password:
        raise SystemExit(
            "CDSE_USERNAME et CDSE_PASSWORD manquent. "
            "À mettre dans scripts/satellite/.env (fichier non commité) "
            "ou dans l'environnement. Pas dans git."
        )
    return user, password
