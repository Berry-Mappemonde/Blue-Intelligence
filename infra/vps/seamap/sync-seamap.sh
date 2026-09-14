#!/usr/bin/env bash
# Self-hosted Open Waters: Seamap sea-chart mirror (CC-BY 4.0).
#
# Inspired by seamap: each planetary build is a dated, IMMUTABLE PMTiles
# archive (`<YYYY-MM-DD>.pmtiles`). This script discovers the current version,
# downloads the archive once (resume possible), atomically switches the
# `current.pmtiles` pointer, rewrites `style.json` to point at the
# mirror, and keeps only the last N archives.
#
# What is self-hosted: the seamark PMTiles archive (~26 GB), the style and the
# sprites — the part seamap builds. VersaTiles basemaps, Seascape
# bathymetry and fonts stay on their origin CDNs (tens of extra
# GB, outside the 75 GB VPS disk budget).
#
# Usage:
#   sync-seamap.sh --check        # show upstream version + local state, download nothing
#   sync-seamap.sh --assets-only  # style + sprites only (quick test, a few KB)
#   sync-seamap.sh                # full sync (dated archive + assets + pointer)
set -euo pipefail

# --------------------------------------------------------------- configuration
TILES_BASE="${TILES_BASE:-https://tiles.openwaters.io}"
DEST="${DEST:-/srv/tiles/seamap}"                 # archive/ (immutable) + public/ (served by nginx)
PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-https://blueintelligence.online/tiles/seamap}"
KEEP="${KEEP:-2}"                                 # number of dated archives to keep
CURL="curl -fsSL --retry 4 --retry-delay 5"

log() { printf '[seamap-sync] %s\n' "$*"; }

# ------------------------------------------------------- version discovery
# The tiles.json ETag is the current build date (e.g. "2026-09-07") — the
# same discovery mechanism as the seamap worker.
discover_version() {
  local etag
  etag=$($CURL -I "$TILES_BASE/seamap/tiles.json" \
    | tr -d '\r' | awk -F'"' 'tolower($1) ~ /^etag:/ { print $2 }')
  if [[ ! $etag =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    log "ETag inattendu (« $etag ») — impossible de découvrir la version" >&2
    return 1
  fi
  printf '%s' "$etag"
}

remote_size() { # bytes advertised by HEAD
  $CURL -I "$1" | tr -d '\r' | awk 'tolower($1) ~ /^content-length:/ { print $2 }'
}

# ------------------------------------------------------------- assets (light)
sync_assets() {
  local version="$1"
  mkdir -p "$DEST/public/sprites"

  for f in freenauticalchart.json freenauticalchart.png \
           freenauticalchart@2x.json freenauticalchart@2x.png; do
    $CURL "$TILES_BASE/seamap/sprites/$f" -o "$DEST/public/sprites/$f"
  done

  # Rewritten style.json: the seamark source reads the mirror archive via pmtiles://
  # (byte-range reads of a static file — nginx is enough) and the
  # nautical sprite comes from the mirror. The rest (VersaTiles, Seascape, fonts)
  # stays on the origin CDNs.
  $CURL "$TILES_BASE/seamap/style.json" -o "$DEST/public/style.upstream.json"
  python3 - "$DEST/public/style.upstream.json" "$DEST/public/style.json" \
           "$PUBLIC_BASE_URL" <<'PYEOF'
import json, sys
src, dst, base = sys.argv[1], sys.argv[2], sys.argv[3].rstrip("/")
style = json.load(open(src, encoding="utf-8"))
style["sources"]["seamap"] = {
    "type": "vector",
    "url": f"pmtiles://{base}/current.pmtiles",
    "attribution": style["sources"].get("seamap", {}).get("attribution", ""),
}
for sprite in style.get("sprite", []):
    if isinstance(sprite, dict) and sprite.get("id") == "freenauticalchart":
        sprite["url"] = f"{base}/sprites/freenauticalchart"
json.dump(style, open(dst, "w", encoding="utf-8"), ensure_ascii=False)
print(f"style.json réécrit → seamap = pmtiles://{base}/current.pmtiles")
PYEOF
  rm -f "$DEST/public/style.upstream.json"
  log "assets synchronisés (style + sprites) pour la version $version"
}

# ----------------------------------------------------- dated immutable archive
sync_archive() {
  local version="$1"
  local url="$TILES_BASE/seamap/$version.pmtiles"
  local archive="$DEST/archive/$version.pmtiles"
  mkdir -p "$DEST/archive"

  local expected
  expected=$(remote_size "$url")
  [ -n "$expected" ] || { log "taille amont inconnue pour $url" >&2; return 1; }

  if [ -f "$archive" ]; then
    log "archive $version.pmtiles déjà présente (immuable) — pas de retéléchargement"
  else
    local free need
    free=$(df --output=avail -B1 "$DEST" | tail -1)
    need=$((expected + expected / 5))
    if [ "$free" -lt "$need" ]; then
      log "espace disque insuffisant : $((free / 1024 / 1024 / 1024)) Go libres, ~$((need / 1024 / 1024 / 1024)) Go requis" >&2
      return 1
    fi
    log "téléchargement de $version.pmtiles ($((expected / 1024 / 1024 / 1024)) Go, reprise possible)…"
    $CURL -C - "$url" -o "$archive.part"
    local got
    got=$(stat -c %s "$archive.part")
    if [ "$got" != "$expected" ]; then
      log "taille inattendue ($got ≠ $expected) — .part conservé pour reprise" >&2
      return 1
    fi
    mv "$archive.part" "$archive"
    log "archive $version.pmtiles téléchargée et scellée"
  fi

  # atomic switch of the nginx-served pointer
  ln -sfn "$archive" "$DEST/public/current.pmtiles"
  printf '%s\n' "$version" > "$DEST/public/VERSION"
  log "current.pmtiles → $version.pmtiles"

  # prune: keep the last $KEEP dated archives
  # shellcheck disable=SC2012 # controlled names (YYYY-MM-DD.pmtiles), lexical sort = chronological sort
  ls -1 "$DEST/archive"/*.pmtiles 2>/dev/null | sort | head -n -"$KEEP" | while read -r old; do
    log "élagage de $(basename "$old")"
    rm -f -- "$old"
  done
}

# ------------------------------------------------------------------------ main
main() {
  local mode="${1:-full}"
  local version
  version=$(discover_version)
  log "version amont : $version"

  case "$mode" in
    --check)
      local local_v="(aucune)"
      [ -f "$DEST/public/VERSION" ] && local_v=$(cat "$DEST/public/VERSION")
      log "version locale : $local_v"
      # shellcheck disable=SC2012 # informational listing, controlled names
      log "archives locales : $(ls -1 "$DEST/archive" 2>/dev/null | tr '\n' ' ' || true)"
      ;;
    --assets-only)
      sync_assets "$version"
      ;;
    full)
      sync_assets "$version"
      sync_archive "$version"
      log "synchronisation terminée — style servi sur $PUBLIC_BASE_URL/style.json"
      ;;
    *)
      log "option inconnue : $mode (attendu : --check | --assets-only | rien)" >&2
      return 2
      ;;
  esac
}

main "${1:-full}"
