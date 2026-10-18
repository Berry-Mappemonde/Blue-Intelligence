#!/usr/bin/env bash
# Copie le code d'un site vers le VPS (sans --delete dangereux à la racine).
# Usage : rsync-to-vps.sh blue-intelligence
# Env : VPS_HOST, VPS_SSH_IDENTITY, REMOTE_APP
set -euo pipefail

SITE="${1:?usage: rsync-to-vps.sh blue-intelligence}"
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
VPS="${VPS_HOST:?VPS_HOST manquant}"
REMOTE="${REMOTE_APP:-/home/ubuntu/blue-intelligence}"
IDENTITY="${VPS_SSH_IDENTITY:?VPS_SSH_IDENTITY manquant}"

RSH=(ssh -i "$IDENTITY" -o BatchMode=yes -o IdentitiesOnly=yes -o ConnectTimeout=20)

remote() {
  "${RSH[@]}" "$VPS" "$@"
}

rsync_to() {
  rsync -az --omit-dir-times -e "${RSH[*]}" "$@"
}

echo "→ rsync $SITE → $VPS:$REMOTE"
remote "mkdir -p $REMOTE/infra/vps/ci $REMOTE/backend $REMOTE/frontend"

# Toujours envoyer la sonde et apply-*.sh (rattrapage + premier déploiement).
rsync_to "$ROOT/infra/vps/ci/" "$VPS:$REMOTE/infra/vps/ci/"
remote "chmod +x $REMOTE/infra/vps/ci/*.sh $REMOTE/infra/vps/ci/*.py || true"

case "$SITE" in
  blue-intelligence)
    rsync_to \
      --exclude .venv \
      --exclude .env \
      --exclude __pycache__ \
      --exclude "*.pyc" \
      --exclude .pytest_cache \
      --exclude exports/ \
      --exclude data/.tld_cache/ \
      --exclude data/runs/ \
      --exclude data/cached_pdfs/ \
      --exclude data/.marinas_fc_cache.json \
      --exclude data/.marinas_fc_cache.json.tmp \
      --exclude "data/climatology/**/*.partial.npz" \
      --exclude "data/climatology/**/*.npz.tmp" \
      "$ROOT/backend/" "$VPS:$REMOTE/backend/"
    rsync_to --delete "$ROOT/frontend/build/" "$VPS:$REMOTE/frontend/build/"
    rsync_to \
      "$ROOT/infra/vps/deploy-app.sh" \
      "$ROOT/infra/vps/sync-public-nginx.sh" \
      "$ROOT/infra/vps/blue-intelligence.service" \
      "$ROOT/infra/vps/blue-intelligence-backup.cron" \
      "$ROOT/infra/vps/nginx-blue-intelligence.conf" \
      "$VPS:$REMOTE/infra/vps/"
    ;;
  *)
    echo "site inconnu: $SITE" >&2
    exit 1
    ;;
esac

# nginx / www-data doivent pouvoir traverser ~ubuntu et le dépôt.
remote "chmod o+x \"\$HOME\" $REMOTE"

echo "rsync $SITE OK"
