#!/usr/bin/env bash
# Si Blue Intelligence n'est plus joignable en local, on la relance.
# Une API coincée (event loop morte, cgroup) ne sert plus un Complet :
# la sonde ne cherche pas à « respecter » un run qu'on ne peut plus interroger.
set -euo pipefail

UNIT=blue-intelligence
URL=http://127.0.0.1:8001/api/

state="$(systemctl show -p SubState --value "$UNIT" 2>/dev/null || true)"
if [ "$state" != "running" ]; then
  exit 0
fi

if curl -fsS -m 8 -o /dev/null "$URL"; then
  exit 0
fi

logger -t bi-healthcheck "Blue Intelligence ne répond plus sur $URL — redémarrage"
sudo -n systemctl restart "$UNIT"
