#!/usr/bin/env bash
# (Re)deploy the application on the VPS: backend dependencies (Python 3.12
# via uv), Playwright Chromium, frontend build, systemd service, backup
# cron. Assumes the code is in ~/blue-intelligence-map and
# install-mongodb.sh already ran.
set -euo pipefail

APP="$HOME/blue-intelligence-map"
CONF_DIR="$HOME/.config/blue-intelligence"
UV="$HOME/.local/bin/uv"
SKIP_FRONTEND_BUILD="${SKIP_FRONTEND_BUILD:-0}"
SKIP_PIP="${SKIP_PIP:-0}"

command -v "$UV" >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh

cd "$APP/backend"
[ -d .venv ] || "$UV" venv --python 3.12 .venv
need_heavy=0
[ "$SKIP_PIP" = "1" ] || need_heavy=1
[ "$SKIP_FRONTEND_BUILD" = "1" ] || need_heavy=1
if [ "$need_heavy" -eq 1 ]; then
  free_mb=$(awk '/MemAvailable:/ {print int($2/1024)}' /proc/meminfo)
  if [ "$free_mb" -lt 1200 ]; then
    echo "RAM dispo ${free_mb} Mo — trop juste pour pip/npm. Lancer d'abord :"
    echo "  bash $APP/infra/vps/setup-memory.sh"
    echo "Puis relancer ce script, ou rsync + systemctl restart seulement."
    exit 1
  fi
fi
if [ "$SKIP_PIP" = "1" ] && [ -x .venv/bin/python ]; then
  echo "SKIP_PIP=1 — venv Python inchangé"
else
  "$UV" pip install --python .venv/bin/python -r requirements.txt \
    --extra-index-url https://download.pytorch.org/whl/cpu --index-strategy unsafe-best-match
  sudo .venv/bin/python -m playwright install-deps chromium >/dev/null 2>&1 || true
  .venv/bin/python -m playwright install chromium
fi

if [ ! -f .env ]; then
  . "$CONF_DIR/mongo.env"
  umask 077
  cat > .env <<ENV
MONGO_URL=$MONGO_URL_LOCAL
DB_NAME=$DB_NAME
CORS_ORIGINS=https://blueintelligence.online,https://www.blueintelligence.online
ENV
  echo "backend/.env créé — compléter les clés API (NVIDIA_API_KEY, OPENROUTER_API_KEY…)"
fi

cd "$APP/frontend"
if [ "$SKIP_FRONTEND_BUILD" = "1" ]; then
  if [ ! -f build/index.html ]; then
    echo "SKIP_FRONTEND_BUILD=1 but frontend/build/index.html is missing." >&2
    exit 1
  fi
  echo "SKIP_FRONTEND_BUILD=1 — reusing the GitHub bundle"
else
  {
    printf 'REACT_APP_BACKEND_URL=\n'
    # Self-hosted sea-chart mirror (infra/vps/seamap): if present, the build
    # points at it instead of the community tiles.openwaters.io service.
    if [ -f /srv/tiles/seamap/public/style.json ]; then
      printf 'REACT_APP_SEAMAP_STYLE_URL=https://blueintelligence.online/tiles/seamap/style.json\n'
    fi
  } > .env
  npm install --no-audit --no-fund
  CI=true npm run build
fi

sudo cp "$APP/infra/vps/blue-intelligence.service" /etc/systemd/system/blue-intelligence.service
sudo cp "$APP/infra/vps/blue-intelligence-backup.cron" /etc/cron.d/blue-intelligence-backup
sudo systemctl daemon-reload
sudo systemctl enable blue-intelligence >/dev/null 2>&1 || true
sudo systemctl restart blue-intelligence

code=000
for _ in $(seq 1 30); do
  code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/api/ || true)
  [ "$code" = "200" ] && break
  sleep 3
done
echo "Santé : HTTP $code — $(curl -s http://127.0.0.1:8001/api/)"
