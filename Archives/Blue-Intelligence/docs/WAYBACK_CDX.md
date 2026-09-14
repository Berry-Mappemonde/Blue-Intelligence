# Wayback CDX — modes `bulk` et `per_url`

La phase 1 Wayback remplit `wayback_cdx_raw` puis dérive la dernière capture par URL pour le fetch HTML. Deux stratégies d’ingestion CDX sont disponibles.

## Mode `bulk` (défaut, `CDX_MODE=bulk`)

- Requête wildcard `cruiserswiki.org/wiki/*` par **tranches de dates** (`getCdxDateRanges`), avec `limit` + `offset` et `CDX_COLLAPSE` (défaut `timestamp:6`).
- Volume potentiel **très élevé** (millions de lignes) si l’historique complet est parcouru.
- `CDX_FROM_YEAR` : défaut **2005** si non défini (comportement historique).

## Mode `per_url` (`CDX_MODE=per_url`)

- **Liste des pages** (ordre configurable) puis **une requête CDX par URL exacte** pour remplir `wayback_cdx_raw`.
- Paramètres typiques : `CDX_FROM_YEAR=2019`, `CDX_PER_URL_LIMIT=12`.
- Ordre de grandeur `wayback_cdx_raw` : ≈ **≤ nombre d’URLs × limit** (plus les lignes sans `collapse` si vous en demandez plus côté API).
- **Délai / concurrence** : `CDX_PER_URL_DELAY_MS` (ex. 400–600), `CDX_PER_URL_CONCURRENCY` (1–3 recommandé derrière proxy).
- **Checkpoint** : `data/cdx_per_url_checkpoint.json` (`lastCompletedIndex`). Effacé avec `clearCdxCache` / `refreshCdx` sans reprise. Ignoré par git (voir `.gitignore`).

### Liste des URLs (mode per_url)

Pour éviter d’appeler `cruiserswiki.org` (Cloudflare) uniquement pour **l’inventaire** des pages, le serveur peut d’abord interroger le **CDX** sur le motif `cruiserswiki.org/wiki/*` avec `collapse` dédié (`urlkey` par défaut), puis enchaîner sur les requêtes CDX **par URL exacte** comme avant.

| Variable | Rôle |
|----------|------|
| `CRUISERSWIKI_URL_SOURCE` | `auto` (défaut) : CDX wildcard puis repli MediaWiki si 0 URL ou erreur · `cdx` : uniquement wildcard · `mediawiki` : uniquement API MediaWiki (comportement historique) |
| `CRUISERSWIKI_CDX_URL_FROM_YEAR` / `TO_YEAR` | Plage **années** pour paginer l’inventaire wildcard (défaut : `getCdxFromYear(per_url)` → année courante). Réduire la plage limite le volume. |
| `CRUISERSWIKI_CDX_URL_MAX_PAGES` | Nombre max de **requêtes paginées** CDX pour l’inventaire (défaut **5000** ; valeur ≤ 0 → 5000). Liste partielle possible à la limite. |
| `CDX_WILDCARD_COLLAPSE` | Collapse pour l’inventaire (défaut `urlkey`). Si l’API Internet Archive rejette la valeur, ajuster ou utiliser `CRUISERSWIKI_URL_SOURCE=mediawiki`. |

Les requêtes CDX passent par `getCdxFetchUrl` : **`CDX_NO_PROXY=1`** force l’accès direct à `web.archive.org` ; sinon un **proxy** (ex. Scrape.do) peut être utilisé comme pour le reste du CDX.

### Collapse et tri per-URL

- `CDX_PER_URL_COLLAPSE` : ex. `digest` pour des snapshots à contenu distinct ; laisser vide ou `none` pour ne pas imposer de collapse (comportement par défaut du code).
- `CDX_PER_URL_SORT_REVERSE=true` : utilise `sort=reverse` sur l’API CDX ; sinon le serveur demande plus de lignes, trie par timestamp décroissant et déduplique pour garder les **N** plus récentes.

## API sync (`POST /api/nauticals/sync`)

Champs optionnels du body (en plus de `refreshCdx`, `refreshWayback`, etc.) :

| Champ | Rôle |
|--------|------|
| `cdxMode` | `"bulk"` \| `"per_url"` (surcharge ponctuelle sans changer `.env`) |
| `cdxFromYear` | nombre (ex. `2019`) |
| `cdxPerUrlLimit` | nombre (ex. `12`) |
| `resumeCdxPerUrlIndex` | reprendre à l’index **N** dans la liste d’URLs (MediaWiki ou CDX wildcard, 0-based) ; ne pas combiner avec `refreshCdx` qui vide le cache |

## Procédure opérationnelle « depuis 2019 »

1. `.env` : `CDX_MODE=per_url`, `CDX_FROM_YEAR=2019`, `CDX_PER_URL_LIMIT=12` (ajuster délai/concurrence selon le proxy).
2. Sync avec `refreshCdx: true`, `refreshWayback: true`.
3. Vérifier le volume `wayback_cdx_raw` et la cohérence des URLs.

En cas d’interruption longue, relancer avec le même mode **sans** `refreshCdx` : le checkpoint reprend après le dernier index complété, ou passez `resumeCdxPerUrlIndex` explicitement.

## Impact sur la Phase 2 (`lib/wayback-phase2.ts`)

La phase 2 calcule `modification_frequency` / `modification_count` à partir des **digests** et timestamps dans `wayback_cdx_raw`. Avec **≤ 12 captures par URL** et une fenêtre **depuis 2019**, les métriques reflètent surtout l’activité récente : elles sont **moins représentatives** d’un passé lointain que le mode `bulk` complet. Le code Phase 2 ne nécessite pas de changement ; interpréter les scores en conséquence.
