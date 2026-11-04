#!/bin/bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== 1. Vérification MongoDB ==="
if ! nc -z 127.0.0.1 27017 2>/dev/null; then
    echo "Démarrage de MongoDB..."
    brew services start mongodb-community 2>/dev/null || brew services start mongodb/brew/mongodb-community 2>/dev/null || true
    sleep 2
fi

if ! nc -z 127.0.0.1 27017 2>/dev/null; then
    echo "Erreur: MongoDB ne répond pas sur 127.0.0.1:27017"
    exit 1
fi
echo "MongoDB OK."

echo "=== 2. Nettoyage des ports 8002 et 3002 ==="
PID_BACK=$(lsof -ti:8002 2>/dev/null || true)
[ -n "$PID_BACK" ] && kill -9 $PID_BACK 2>/dev/null || true

PID_FRONT=$(lsof -ti:3002 2>/dev/null || true)
[ -n "$PID_FRONT" ] && kill -9 $PID_FRONT 2>/dev/null || true

echo "=== 3. Lancement du Backend (Port 8002) ==="
cd "$DIR/backend"
python -m uvicorn app.main:app --port 8002 --reload > /tmp/backend_v2.log 2>&1 &
BACKEND_PID=$!

READY=0
for i in {1..15}; do
    if nc -z 127.0.0.1 8002 2>/dev/null; then
        READY=1
        break
    fi
    sleep 1
done

if [ $READY -ne 1 ]; then
    echo "Erreur Backend :"
    cat /tmp/backend_v2.log
    kill -9 $BACKEND_PID 2>/dev/null || true
    exit 1
fi
echo "Backend actif sur http://localhost:8002 (PID $BACKEND_PID)."

cleanup() {
    echo -e "\nArrêt du backend V2 (PID $BACKEND_PID)..."
    kill -9 $BACKEND_PID 2>/dev/null || true
    exit 0
}
trap cleanup INT TERM EXIT

echo "=== 4. Lancement du Frontend (Port 3002) ==="
cd "$DIR/frontend"
PORT=3002 npm start
