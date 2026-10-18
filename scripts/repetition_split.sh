#!/usr/bin/env bash
# Répétition locale du split (PR #555). Ne crée ni ne pousse aucun dépôt GitHub.
# Usage : depuis la racine du clone, branche plan à jour :
#   bash scripts/repetition_split.sh
# Variables :
#   REPETITION_SKIP_TESTS=1  — seulement contrôles statiques et diffs CI
#   REPETITION_ROOT=/chemin  — racine du clone (défaut : parent de scripts/)
set -euo pipefail

ROOT="${REPETITION_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$ROOT"
export PATH="${HOME}/.local/bin:${PATH}"

REH="${REPETITION_DIR:-/tmp/split-rehearsal}"
MAIN_SHA="${REPETITION_MAIN_SHA:-$(git rev-parse origin/main 2>/dev/null || git rev-parse main)}"
PLAN_SHA="$(git rev-parse HEAD)"
FAIL=0
PASS=0
WARN=0

log() { printf '%s\n' "$*"; }
ok() { PASS=$((PASS + 1)); log "OK  $*"; }
bad() { FAIL=$((FAIL + 1)); log "KO  $*"; }
warn() { WARN=$((WARN + 1)); log "AVERT  $*"; }

run() {
  local title="$1"
  shift
  log "── $title"
  if "$@"; then
    ok "$title"
  else
    bad "$title"
    return 1
  fi
}

summary() {
  log ""
  log "======== RÉSUMÉ RÉPÉTITION ========"
  log "main cible     : $MAIN_SHA"
  log "branche plan   : $PLAN_SHA"
  log "PASS           : $PASS"
  log "FAIL           : $FAIL"
  log "AVERT (manuel) : $WARN"
  log "=================================="
  test "$FAIL" -eq 0
}

log "Répétition split — $(date -u +%Y-%m-%dT%H:%MZ)"

run "self-test check_split_coverage" \
  python3 scripts/check_split_coverage.py --self-test

run "classeur (0 non classé)" bash -c '
  out=$(python3 scripts/check_split_coverage.py 2>&1)
  printf "%s\n" "$out"
  echo "$out" | grep -q "non classés : 0"
'

run "generate_split_ci_diffs --check" \
  python3 scripts/generate_split_ci_diffs.py --check

run "split_post_filter self-check" \
  python3 scripts/split_post_filter.py self-check

warn "Devpost Q13 doit valoir https://github.com/Berry-Mappemonde/NAVIGUIDE (vérifié sur la page publique) — rappel manuel Berry, pas un échec de ce script."

# Noms d'environnement Contabo (§ 8.3) : présents dans le plan, jamais de valeurs.
run "noms env LLM dans le plan § 8.3" bash -c '
  for key in NEBIUS_API_KEY NVIDIA_API_KEY OPENROUTER_API_KEY ANTHROPIC_API_KEY \
    NAVIGUIDE_LLM_MODE TAVILY_API_KEY NAVIGUIDE_TAVILY_WATCH NAVIGUIDE_ICI_WARM BI_API_URL; do
    grep -q "^${key}=" docs/PLAN_SEPARATION_DEPOTS.md || exit 1
  done
'

run "migration MR1 journal (plan § 7–9)" bash -c '
  plan=docs/PLAN_SEPARATION_DEPOTS.md
  grep -q "naviguide.sqlite.bak-rekey-20261015" "$plan"
  grep -q "moments-restore-20261018T033021Z" "$plan"
  grep -q "lot \\*\\*MR1\\*\\*" "$plan"
  grep -q "1142" "$plan"
  grep -q "berry-mappemonde-2026-officiel" "$plan"
  grep -q "BLOQUANT.*MR1" "$plan"
  grep -q "accepté au split" "$plan"
'

# Diffs 6.6 embarqués = générateur
run "diffs ci.yml du plan = générateur" bash -c '
  tmp=$(mktemp -d)
  python3 scripts/generate_split_ci_diffs.py bi > "$tmp/bi.patch"
  python3 scripts/generate_split_ci_diffs.py ng > "$tmp/ng.patch"
  awk "/^git apply <<.END_BI_CI./,/^END_BI_CI/" docs/PLAN_SEPARATION_DEPOTS.md \
    | sed "1d;\$d" > "$tmp/plan-bi.patch"
  awk "/^git apply <<.END_NG_CI./,/^END_NG_CI/" docs/PLAN_SEPARATION_DEPOTS.md \
    | sed "1d;\$d" > "$tmp/plan-ng.patch"
  diff -q "$tmp/bi.patch" "$tmp/plan-bi.patch"
  diff -q "$tmp/ng.patch" "$tmp/plan-ng.patch"
'

if [[ "${REPETITION_SKIP_TESTS:-}" == "1" ]]; then
  summary
  exit 0
fi

git worktree prune 2>/dev/null || true
rm -rf "$REH"
mkdir -p "$REH"
BI_WORK="$REH/bi-work"
NG_WORK="$REH/ng-work"

run "préparer copies de travail (checkout main)" bash -c "
  git worktree add -f --detach \"$REH/main-tree\" \"$MAIN_SHA\"
"

cp -a "$REH/main-tree" "$BI_WORK"
cp -a "$REH/main-tree" "$NG_WORK"

apply_ci() {
  local work="$1" side="$2"
  (
    cd "$work"
    python3 "$ROOT/scripts/generate_split_ci_diffs.py" "$side" | git apply
    git add .github/workflows/ci.yml
  )
}

run "git apply ci.yml Blue Intelligence" apply_ci "$BI_WORK" bi
run "git apply ci.yml NAVIGUIDE" apply_ci "$NG_WORK" ng

run "test_prod_jobs_busy (mono)" python3 infra/vps/ci/test_prod_jobs_busy.py
run "test_simulator_deploy_manifest" python3 infra/vps/ci/test_simulator_deploy_manifest.py

for work in "$BI_WORK" "$NG_WORK"; do
  label=$(basename "$work")
  run "bash -n deploy-gate ($label)" bash -c "
    cd \"$work\"
    yaml=.github/workflows/ci.yml
    grep -A20 'Syntaxe bash' \"\$yaml\" | grep 'bash -n' | sed 's/^[[:space:]]*//' | while read -r line; do
      eval \"\$line\"
    done
  "
done

run "deploy-gate scripts ($BI_WORK)" bash -c "cd \"$BI_WORK\" && python3 infra/vps/ci/test_prod_jobs_busy.py"
run "deploy-gate scripts ($NG_WORK)" bash -c "cd \"$NG_WORK\" && python3 infra/vps/ci/test_prod_jobs_busy.py"

run "post_filter shared bi" python3 scripts/split_post_filter.py shared --role bi --root "$BI_WORK"
run "post_filter shared ng" python3 scripts/split_post_filter.py shared --role ng --root "$NG_WORK"

# Suites de tests : code = tête du clone (merge main + plan docs). ci.yml validé sur bi-work/ng-work.
SRC="$ROOT"
BACKEND_PY="${ROOT}/backend/.venv/bin/python"
if [[ ! -x "$BACKEND_PY" ]]; then
  bad "venv backend absent ($BACKEND_PY) — lancer pip install -r backend/requirements.txt"
else
  if ! pgrep -x mongod >/dev/null; then
    bad "mongod inactif — impossible de lancer pytest backend"
  else
    run "seed + enrich OSM (bi_ci)" bash -c "
      cd \"$SRC/backend\"
      export MONGO_URL=mongodb://127.0.0.1:27017 DB_NAME=bi_ci
      mkdir -p .ci-cache
      export CI_OSM_CACHE=\"\$PWD/.ci-cache/osm-ports.json\"
      \"$BACKEND_PY\" scripts/seed_ci_mongo.py
      if [[ ! -s \"\$CI_OSM_CACHE\" ]]; then
        \"$BACKEND_PY\" scripts/enrich_ci_osm.py
      else
        \"$BACKEND_PY\" scripts/enrich_ci_osm.py
      fi
    "
    if [[ ! -f /tmp/uvicorn-reh.pid ]] || ! kill -0 "$(cat /tmp/uvicorn-reh.pid)" 2>/dev/null; then
      run "uvicorn API locale :8001" bash -c "
        cd \"$SRC/backend\"
        export MONGO_URL=mongodb://127.0.0.1:27017 DB_NAME=bi_ci POE_AUTO_REFRESH=0
        \"$BACKEND_PY\" -m uvicorn app.main:app --host 127.0.0.1 --port 8001 >/tmp/uvicorn-reh.log 2>&1 &
        echo \$! >/tmp/uvicorn-reh.pid
        for _ in \$(seq 1 60); do curl -sf http://127.0.0.1:8001/api/ >/dev/null && exit 0; sleep 2; done
        exit 1
      "
    else
      ok "uvicorn API locale :8001 (déjà actif)"
    fi
    run "pytest backend/tests" bash -c "
      cd \"$SRC/backend\"
      cat > .env <<'EOF'
MONGO_URL=mongodb://127.0.0.1:27017
DB_NAME=bi_ci
CORS_ORIGINS=*
SEARXNG_URL=http://127.0.0.1:8888
EOF
      cat > ../frontend/.env <<'EOF'
REACT_APP_BACKEND_URL=http://127.0.0.1:8001
EOF
      export POE_AUTO_REFRESH=0 REACT_APP_BACKEND_URL=http://127.0.0.1:8001 PYTHONDONTWRITEBYTECODE=1
      out=\$(\"$BACKEND_PY\" -m pytest tests -q --tb=no 2>&1)
      echo \"\$out\" | tail -3
      echo \"\$out\" | grep -qE '[0-9]+ passed' && ! echo \"\$out\" | grep -qE '[0-9]+ failed'
    "
  fi
fi

run "npm ci + npm test naviguide-simulator" bash -c "
  cd \"$SRC/naviguide-simulator\"
  npm ci
  npm test 2>&1 | tee /tmp/ng-npm-test.log | tail -5
  grep -q '^# fail 0' /tmp/ng-npm-test.log
"

run "pytest naviguide-simulator/server" bash -c "
  cd \"$SRC/naviguide-simulator\"
  export NAVIGUIDE_POSTE_API=http://127.0.0.1:9 CI=true
  SIM_PY=\"$ROOT/naviguide-simulator/.venv/bin/python\"
  [[ -x \"\$SIM_PY\" ]] || { python3 -m venv .venv && .venv/bin/pip install -q -r server/requirements.txt && SIM_PY=\".venv/bin/python\"; }
  out=\$(\"\$SIM_PY\" -m pytest -q --tb=no 2>&1)
  echo \"\$out\" | tail -3
  echo \"\$out\" | grep -qE '[0-9]+ passed' && ! echo \"\$out\" | grep -qE '[0-9]+ failed'
"

run "npm ci + npm test frontend (Jest)" bash -c "
  cd \"$SRC/frontend\"
  npm ci
  npm test -- --watchAll=false 2>&1 | tee /tmp/bi-jest.log | tail -4
  grep -q 'Tests:.*40 passed' /tmp/bi-jest.log
"

run "node recetteAg.test.js" bash -c "
  cd \"$SRC/naviguide-simulator\"
  node --test src/utils/recetteAg.test.js 2>&1 | tail -3
  ! node --test src/utils/recetteAg.test.js 2>&1 | grep -q 'fail [1-9]'
"

run "import ci_pytest_gate" bash -c "
  cd \"$SRC/backend\"
  \"$BACKEND_PY\" -c 'import scripts.ci_pytest_gate as g; assert hasattr(g, \"main\")'
"

summary
