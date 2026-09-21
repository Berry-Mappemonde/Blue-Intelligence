# Vérification des URLs de fiches

Les fiches carte (popup Review et carte) exposent des liens vers les sources web
(projets, ports, marinas, ZEE, AMP, science, etc.). L’outil **`scripts/verify_fiche_urls.py`**
relève ces URLs, les teste en HTTP (HEAD puis GET si besoin, redirections suivies,
délais et retries configurables) et produit un rapport **OK / redirected / broken /
timeout / soft_fail** (401, 403, 429, page CAPTCHA).

User-Agent envoyé : `BlueIntelligence-FicheUrlChecker/1.0 (+https://blueintelligence.online; link-health audit)`.

## Commandes

```bash
# Seeds CI (Formalités ports + projets — URLs brutes des GeoJSON)
python3 scripts/verify_fiche_urls.py \
  --geojson seed/projects.geojson seed/ports_of_entry.geojson \
  --out docs/audits/$(date -u +%F)-fiche-urls-seed.md

# Exports publics de production (+ fiches ZEE « visibles » sur la carte)
python3 scripts/verify_fiche_urls.py \
  --api https://blueintelligence.online \
  --concurrency 4 --timeout 20 \
  --out docs/audits/$(date -u +%F)-fiche-urls-prod.md

# Mongo live (VPS) — inclut l’assemblage TD/BU des fiches ZEE
python3 scripts/verify_fiche_urls.py --mongo "$MONGO_URL" --db blue_intelligence

# Extraction sans réseau (tests / debug)
python3 scripts/verify_fiche_urls.py --geojson seed/projects.geojson --dry-run
```

Options utiles : `--concurrency`, `--timeout`, `--retries`, `--max-urls N`,
`--json-out rapport.json`, `--fail-on broken` (code de sortie 1).

## Couverture des champs

| Jeu / mode | Champs lus |
|------------|------------|
| Projects | `properties.url` |
| Formalités (ports) | `properties.source_urls[]` |
| Formalités (fiche ZEE) | `url_td`, `sources_td[]`, `url_bu`, `urls_bu[]`, `source_urls[]` (API `--api` ou Mongo) |
| Marinas | `website`, `maps_place_url` |
| Capitaineries | `website` |
| AMP | `manager_url`, `visit_url` |
| Science | `url` |
| Mouillages | `tags.website`, `tags.contact:website`, `tags.url` |

Les images (`image` des projets) ne sont pas des liens « source » et ne sont pas vérifiées.

## CI

- **`backend/tests/test_verify_fiche_urls.py`** — logique d’extraction et checker (HTTP mocké).
- **`.github/workflows/ci.yml`** — smoke `--dry-run` sur les seeds.
- **Build hebdo** — après téléchargement des exports, rapport URL dans l’artefact release.

Ce script est un **rapport**, pas un garde-fou bloquant par défaut (comme `audit_tags.py`).
