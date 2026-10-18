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
  rm -f "$STATE"
  exit 0
fi

if curl -fsS -m 8 -o /dev/null "$URL"; then
  rm -f "$STATE"
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

mkdir -p "$STATE_DIR"
if [ "$fails" -lt "$MAX_FAILS" ]; then
  echo "$pid $fails" > "$STATE"
  logger -t bi-healthcheck "Blue Intelligence ne répond pas sur $URL (échec $fails/$MAX_FAILS, pid $pid) — pas de relance"
  exit 0
fi

rm -f "$STATE"
logger -t bi-healthcheck "Blue Intelligence ne répond plus sur $URL ($fails échecs consécutifs, pid $pid) — redémarrage"
sudo -n systemctl restart "$UNIT"
