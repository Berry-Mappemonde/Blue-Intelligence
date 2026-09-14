#!/usr/bin/env bash
# Génère les 12 mois Hs P50 / P90 WAVERYS PT3H sur le Mac.
# Ne pas lancer sur le VPS (8 Go) : un mois à la fois, mais 27 ans de 3 h.
#
# Usage, depuis n'importe où :
#   bash scripts/climatology/gen_wave_pct_mac.sh
#
# Un seul mois (ex. juillet, recette 40°S) :
#   bash scripts/climatology/gen_wave_pct_mac.sh --month 7
#
# Reprendre après une coupure (même commande) :
#   bash scripts/climatology/gen_wave_pct_mac.sh
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
if [ ! -f "$ENV_FILE" ] && [ -z "${COPERNICUS_USERNAME:-}" ] && [ -z "${COPERNICUS_ID:-}" ]; then
  echo "Fichier manquant : backend/.env" >&2
  echo "Ajoute ces deux lignes (sans les commiter) :" >&2
  echo "  COPERNICUS_USERNAME=ton-email" >&2
  echo "  COPERNICUS_PASSWORD=ton-mot-de-passe" >&2
  exit 1
fi

echo "Projet : $ROOT"
echo "Python : $PY"
echo "Les 12 mois de houle P50/P90 (PT3H 1993–2019) vont défiler."
echo "C'est plus long que les roses de vent. Relance la même commande s'il s'arrête :"
echo "le mois en cours reprend à l'année suivante. Un mois déjà en p50_p90 est sauté."
echo

if [ "$#" -eq 0 ]; then
  SET=(--all --skip-existing)
else
  SET=("$@")
  skip=0
  for a in "${SET[@]}"; do
    if [ "$a" = "--skip-existing" ]; then
      skip=1
    fi
  done
  if [ "$skip" -eq 0 ]; then
    SET+=(--skip-existing)
  fi
fi

if command -v caffeinate >/dev/null 2>&1; then
  exec caffeinate -i "$PY" scripts/climatology/gen_wave_pct.py "${SET[@]}"
else
  exec "$PY" scripts/climatology/gen_wave_pct.py "${SET[@]}"
fi
