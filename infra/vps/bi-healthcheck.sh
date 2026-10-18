#!/usr/bin/env bash
# Si Blue Intelligence n'est plus joignable en local, on la relance.
# Une API coincée (event loop morte, cgroup) ne sert plus un Complet :
# la sonde ne cherche pas à « respecter » un run qu'on ne peut plus interroger.
#
# 18 oct. 2026 : relance seulement après 3 échecs consécutifs sur le même
# processus. Une rafale d'appels (11:39 Toronto) faisait relancer BI dès le
# premier échec, cache froid à chaque fois : boucle de 9 relances en 9 min.
set -euo pipefail

UNIT=blue-intelligence
URL=http://127.0.0.1:8001/api/
MAX_FAILS=3
STATE_DIR="${HOME:-/home/ubuntu}/.local/state/bi-healthcheck"
STATE="$STATE_DIR/fails"

state="$(systemctl show -p SubState --value "$UNIT" 2>/dev/null || true)"
if [ "$state" != "running" ]; then
  rm -f "$STATE" 2>/dev/null || true
  exit 0
fi

if curl -fsS -m 8 -o /dev/null "$URL"; then
  rm -f "$STATE" 2>/dev/null || true
  exit 0
fi

pid="$(systemctl show -p MainPID --value "$UNIT" 2>/dev/null || echo 0)"
prev_pid=0
prev_fails=0
if [ -r "$STATE" ]; then
  read -r prev_pid prev_fails < "$STATE" || true
fi
case "$prev_fails" in ''|*[!0-9]*) prev_fails=0 ;; esac
if [ "$prev_pid" != "$pid" ]; then
  prev_fails=0
fi
fails=$((prev_fails + 1))

# Échec sûr : si l'état ne peut être ni lu ni écrit, la sonde ne doit pas
# se désactiver toute seule. On retombe sur l'ancien comportement (relance).
if [ -e "$STATE" ] && [ ! -r "$STATE" ]; then
  logger -t bi-healthcheck "état illisible ($STATE), relance par sécurité"
  fails=$MAX_FAILS
fi

if [ "$fails" -lt "$MAX_FAILS" ]; then
  if mkdir -p "$STATE_DIR" 2>/dev/null && { echo "$pid $fails" > "$STATE"; } 2>/dev/null; then
    logger -t bi-healthcheck "Blue Intelligence ne répond pas sur $URL (échec $fails/$MAX_FAILS, pid $pid) — pas de relance"
    exit 0
  fi
  logger -t bi-healthcheck "état non inscriptible ($STATE), relance par sécurité"
  fails=$MAX_FAILS
fi

rm -f "$STATE" 2>/dev/null || true
logger -t bi-healthcheck "Blue Intelligence ne répond plus sur $URL ($fails échecs consécutifs, pid $pid) — redémarrage"
sudo -n systemctl restart "$UNIT"
