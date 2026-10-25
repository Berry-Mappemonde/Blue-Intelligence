"""Récupère les credentials Zetaris (orgId + token) via login admin,
écrit backend/.env en mode live, puis lance zetaris_setup.py --apply.
Le token n'est jamais affiché à l'écran."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import httpx

LOGIN_URL = "http://localhost:3000/api/auth/login"
BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND_DIR / ".env"

ADMIN_EMAIL = "admin@zetaris.com"
ADMIN_PW = "Zetaris1@"
ZETARIS_REST_URL = "http://localhost:8888/api/v1.0"


def get_credentials() -> tuple[int, str]:
    """Retourne (org_id, token) sans jamais imprimer le token."""
    payload = {"username": ADMIN_EMAIL, "password": ADMIN_PW}
    with httpx.Client(timeout=30.0) as client:
        response = client.post(LOGIN_URL, headers={"Content-Type": "application/json"}, json=payload)
    if response.status_code != 200:
        raise RuntimeError(f"Login échoué (HTTP {response.status_code})")
    data = response.json()
    org_id = data.get("orgId")
    token = data.get("idToken")
    if not org_id or not token:
        raise RuntimeError(f"Réponse login incomplète: {data!r}")
    return int(org_id), token


def write_env(org_id: int, token: str) -> None:
    """Écrit (ou met à jour) backend/.env avec les vraies variables Zetaris."""
    lines: list[str] = []
    keys_seen: set[str] = set()
    base_lines = [
        "PORT=8002",
        "DB_NAME=blueintel_db_v2",
        "MONGO_DB=blueintel_db_v2",
        "MONGO_URL=mongodb://127.0.0.1:27017",
        "SEARXNG_URL=http://127.0.0.1:8890",
        "NIGHTSHIFT_API_KEY=",
        "SAMPLE_MODE=false",
        f"ZETARIS_REST_URL={ZETARIS_REST_URL}",
        f"ZETARIS_ORG_ID={org_id}",
        f"ZETARIS_API_KEY={token}",
    ]
    for line in base_lines:
        key = line.split("=", 1)[0]
        keys_seen.add(key)
        lines.append(line)
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f".env écrit ({ENV_FILE}) — variables: {', '.join(sorted(keys_seen))}")


def run_zetaris_setup(org_id: int, token: str) -> int:
    """Lance zetaris_setup.py --apply avec le python miniconda.
    Injecte les credentials Zetaris dans l'environnement du processus enfant
    (c'est ce que zetaris_setup.py lit via os.environ.get)."""
    script = BACKEND_DIR / "scripts" / "zetaris_setup.py"
    python = "/opt/miniconda3/bin/python"
    env = os.environ.copy()
    env["ZETARIS_API_KEY"] = token
    env["ZETARIS_ORG_ID"] = str(org_id)
    env["ZETARIS_REST_URL"] = ZETARIS_REST_URL
    env["SAMPLE_MODE"] = "false"
    cmd = [python, str(script), "--apply"]
    print(f"Lancement: {' '.join(cmd)} (credentials injectés dans l'environnement enfant)")
    result = subprocess.run(cmd, env=env, cwd=str(BACKEND_DIR), text=True)
    return result.returncode


def main() -> int:
    print("=== Étape 2 : récupération credentials Zetaris ===")
    org_id, token = get_credentials()
    print(f"orgId récupéré : {org_id}")
    print("Token récupéré (masqué pour sécurité).")

    print("\n=== Étape 4 : mise à jour backend/.env ===")
    write_env(org_id, token)

    print("\n=== Étape 3 : injection des 1 169 ports dans Zetaris ===")
    rc = run_zetaris_setup(org_id, token)
    if rc != 0:
        print(f"zetaris_setup.py --apply a échoué (code {rc})", file=sys.stderr)
        return rc

    print("\n=== Injection terminée avec succès ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
