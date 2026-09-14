#!/usr/bin/env bash
# Generate the 12 CMEMS wind roses on the Mac.
# Do not run on the VPS (8 GB).
#
# Usage, from anywhere:
#   bash scripts/climatology/gen_wind_atlas_mac.sh
#
# Resume after an interruption (same command):
#   bash scripts/climatology/gen_wind_atlas_mac.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [ -x "$ROOT/backend/.venv/bin/python" ]; then
  PY="$ROOT/backend/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
else
  echo "Python 3 introuvable. Installe-le (python.org) puis réessaie." >&2
  exit 1
fi

ENV_FILE="$ROOT/backend/.env"
if [ ! -f "$ENV_FILE" ]; then
  echo "Fichier manquant : backend/.env" >&2
  echo "Ajoute ces deux lignes (sans les commiter) :" >&2
  echo "  COPERNICUS_USERNAME=ton-email" >&2
  echo "  COPERNICUS_PASSWORD=ton-mot-de-passe" >&2
  exit 1
fi

echo "Projet : $ROOT"
echo "Python : $PY"
echo "Les 12 mois vont défiler (souvent plusieurs heures)."
echo "Tu peux fermer d'autres apps. Ne mets pas le Mac en veille :"
echo "ce script utilise caffeinate. Relance la même commande s'il s'arrête."
echo

if command -v caffeinate >/dev/null 2>&1; then
  exec caffeinate -i "$PY" scripts/climatology/gen_wind_atlas.py --all --skip-existing "$@"
else
  exec "$PY" scripts/climatology/gen_wind_atlas.py --all --skip-existing "$@"
fi
