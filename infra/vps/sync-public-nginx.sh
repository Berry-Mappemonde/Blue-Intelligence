#!/usr/bin/env bash
# Sync the Blue Intelligence nginx vhost from the reference copy, then
# reload nginx only if `nginx -t` passes.
#
# Called from deploy-app.sh. NAVIGUIDE vhosts live in the NAVIGUIDE repository.
set -euo pipefail

APP="${APP:-$HOME/blue-intelligence}"

install_vhost() {
  local name="$1" src="$2"
  local dest="/etc/nginx/sites-available/$name"
  if [ ! -f "$src" ]; then
    echo "sync-public-nginx: fichier source absent: $src" >&2
    exit 1
  fi
  if [ -f "$dest" ]; then
    sudo cp -a "$dest" "${dest}.bak-before-sync-$(date -u +%Y%m%dT%H%M%SZ)"
  fi
  sudo cp "$src" "$dest"
  sudo ln -sf "$dest" "/etc/nginx/sites-enabled/$name"
}

install_vhost blue-intelligence "$APP/infra/vps/nginx-blue-intelligence.conf"

chmod o+x "$HOME" "$APP" 2>/dev/null || true

if sudo nginx -t 2>&1; then
  sudo systemctl reload nginx
  echo "sync-public-nginx: nginx -t OK, reload effectué"
else
  echo "sync-public-nginx: nginx -t en échec — pas de reload (restaurer *.bak-before-sync-* si besoin)" >&2
  exit 1
fi
