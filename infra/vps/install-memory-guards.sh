#!/usr/bin/env bash
# Garde-fous mémoire / climatologie (incident 15 oct. 2026).
# À lancer sur le VPS. Idempotent. Relance BI + simulateur à la fin
# (les nouveaux plafonds systemd ne s'appliquent qu'après restart).
set -euo pipefail

APP="${APP:-$HOME/blue-intelligence}"
SRC="$APP/infra/vps"

if [ ! -f "$SRC/bi-healthcheck.sh" ]; then
  echo "Fichiers infra introuvables dans $SRC" >&2
  exit 1
fi

sudo install -d -o www-data -g www-data -m 750 /var/cache/nginx/bi-climatology
sudo install -m 644 "$SRC/nginx-bi-climatology-cache.conf" \
  /etc/nginx/conf.d/bi-climatology-cache.conf
sudo install -m 644 "$SRC/nginx-snippet-bi-climatology.conf" \
  /etc/nginx/snippets/bi-climatology-cache.conf
sudo install -m 644 "$SRC/nginx-bi-local-cache.conf" \
  /etc/nginx/sites-available/bi-local-cache
sudo ln -sf /etc/nginx/sites-available/bi-local-cache \
  /etc/nginx/sites-enabled/bi-local-cache

sudo nginx -t
sudo systemctl reload nginx

sudo install -m 755 "$SRC/bi-healthcheck.sh" /usr/local/sbin/bi-healthcheck
sudo install -m 644 "$SRC/blue-intelligence-health.service" \
  /etc/systemd/system/blue-intelligence-health.service
sudo install -m 644 "$SRC/blue-intelligence-health.timer" \
  /etc/systemd/system/blue-intelligence-health.timer
sudo install -m 644 "$SRC/blue-intelligence.service" \
  /etc/systemd/system/blue-intelligence.service
sudo install -m 644 "$SRC/naviguide/naviguide-simulator.service" \
  /etc/systemd/system/naviguide-simulator.service

ENVF="$HOME/.config/naviguide/simulator.env"
if [ -f "$ENVF" ]; then
  if grep -qE '^BI_API_URL=' "$ENVF"; then
    sed -i.bak-biurl 's|^BI_API_URL=.*|BI_API_URL=http://127.0.0.1:8002/api|' "$ENVF"
  elif grep -qE '^#BI_API_URL=' "$ENVF"; then
    sed -i.bak-biurl 's|^#BI_API_URL=.*|BI_API_URL=http://127.0.0.1:8002/api|' "$ENVF"
  else
    printf '\nBI_API_URL=http://127.0.0.1:8002/api\n' >> "$ENVF"
  fi
  rm -f "$ENVF.bak-biurl"
fi

# Un ancien `systemctl set-property MemoryHigh=2G` survit dans
# system.control/ et réimpose le plafond souple qui a coincé l'API.
sudo rm -f /etc/systemd/system.control/blue-intelligence.service.d/50-MemoryHigh.conf \
  /etc/systemd/system.control/blue-intelligence.service.d/50-MemoryMax.conf
sudo rmdir /etc/systemd/system.control/blue-intelligence.service.d 2>/dev/null || true

sudo systemctl daemon-reload
sudo systemctl enable --now blue-intelligence-health.timer >/dev/null
sudo systemctl restart blue-intelligence
sudo systemctl restart naviguide-simulator

echo "Garde-fous installés. BI via 127.0.0.1:8002 + sonde chaque minute."
