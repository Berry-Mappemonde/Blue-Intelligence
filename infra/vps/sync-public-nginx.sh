#!/usr/bin/env bash
# Sync NAVIGUIDE + Blue Intelligence nginx vhosts from the monorepo reference
# copies, then reload nginx only if `nginx -t` passes.
#
# Called from deploy-app.sh and deploy-naviguide.sh (not simulator — separate vhost).
set -euo pipefail

APP="${APP:-$HOME/blue-intelligence-map}"

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

install_vhost naviguide "$APP/infra/vps/naviguide/nginx-naviguide.conf"
install_vhost blue-intelligence "$APP/infra/vps/nginx-blue-intelligence.conf"

# Ancien root dans le dépôt (incident try_files / www-data).
if grep -q 'root /home/ubuntu/blue-intelligence-map/naviguide/naviguide-app/dist;' \
     /etc/nginx/sites-available/naviguide 2>/dev/null; then
  sudo sed -i 's|root /home/ubuntu/blue-intelligence-map/naviguide/naviguide-app/dist;|root /var/www/naviguide;|' \
    /etc/nginx/sites-available/naviguide
fi

chmod o+x "$HOME" "$APP" 2>/dev/null || true

if sudo nginx -t 2>&1; then
  sudo systemctl reload nginx
  echo "sync-public-nginx: nginx -t OK, reload effectué"
else
  echo "sync-public-nginx: nginx -t en échec — pas de reload (restaurer *.bak-before-sync-* si besoin)" >&2
  exit 1
fi
