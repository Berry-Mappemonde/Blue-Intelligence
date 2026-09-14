#!/usr/bin/env bash
# Build the frontend and start the unified app (UI + API) on port 8001.
# Usage: bash .cursor/preview.sh
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Build frontend (same-origin)"
cd "$REPO/frontend"
CI=true REACT_APP_BACKEND_URL= npm run build

echo "==> Starting backend + UI on http://0.0.0.0:8001"
cd "$REPO/backend"
# shellcheck disable=SC1091
. .venv/bin/activate
exec SERVE_FRONTEND=1 uvicorn server:app --host 0.0.0.0 --port 8001
