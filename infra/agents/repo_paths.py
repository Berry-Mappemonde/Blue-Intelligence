"""Réglages de la boucle de nuit pour Blue Intelligence.

Les scripts de ce dossier importent ces noms. On ne recopie pas la
même chaîne dans le texte d'un prompt.
"""
from __future__ import annotations

import os
from pathlib import Path


# Racine du checkout Blue Intelligence à piloter (obligatoire).
def bi_root() -> Path:
    v = os.environ.get("BLUE_INTELLIGENCE_ROOT")
    if not v:
        raise SystemExit(
            "BLUE_INTELLIGENCE_ROOT manquant : "
            "chemin du checkout Blue Intelligence "
            "(ex. export BLUE_INTELLIGENCE_ROOT=~/blue-intelligence)"
        )
    return Path(v).expanduser().resolve()


# Racine de ce dépôt d'outillage (ops-toolkit côté BI).
OPS_ROOT = Path(__file__).resolve().parents[3]

REPO_SLUG = "Berry-Mappemonde/Blue-Intelligence"
DEFAULT_REPO = "https://github.com/" + REPO_SLUG
PROD_URL = "https://blueintelligence.online"

# Plan des lots et docs de méthode : dans CE dépôt privé (ops-toolkit), jamais dans les dépôts publics.
# BIM_PROMPTS_MD : lire un autre plan (chemin absolu, ou relatif à ce dépôt).
def _ops_path(v: str) -> str:
    q = Path(v).expanduser()
    return str((q if q.is_absolute() else OPS_ROOT / v).resolve())


PROMPTS_MD = _ops_path(os.environ.get("BIM_PROMPTS_MD") or "docs/BATCHS_POST_SPLIT.md")
REGLES_MD = _ops_path("REGLES_WORKFLOW_AGENT.md")
WORKFLOW_INDUSTRIEL = _ops_path("docs/WORKFLOW_INDUSTRIEL.md")

# Chemins clés du repo BI
BACKEND_DIR = "backend"
FRONTEND_DIR = "frontend"
TESTS_DIR = "backend/tests"
DOCS_DIR = "docs"

# Environnement
SERVER_ENV = "backend/.env"
DOCKER_COMPOSE = "infra/docker-compose.yml"