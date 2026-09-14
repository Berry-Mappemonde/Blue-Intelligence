# Scraping Cruisers Wiki pour Blue Intelligence

## Contexte

**Cruisers Wiki** (cruiserswiki.org) est un wiki MediaWiki contenant des instructions nautiques (ports, ancrages, dangers) avec coordonnées GPS. Le site est protégé par **Cloudflare**, ce qui bloque les requêtes serveur directes (403) et souvent Playwright (502).

## Architecture actuelle

Ordre des fallbacks : **FlareSolverr → Proxy → Playwright → TinyFish → Direct**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PHASE DÉCOUVERTE + BULK (même chaîne pour toutes les requêtes)             │
└─────────────────────────────────────────────────────────────────────────────┘

  Requête API MediaWiki (Category:Ports, categorymembers, page content...)
                    │
                    ▼
  ┌─────────────────────────────────────┐
  │  1. FlareSolverr (gratuit, Docker)   │  ← Priorité 1, sans limite
  │     localhost:8191                    │
  └─────────────────────────────────────┘
                    │
         ┌─────────┴─────────┐
         │ OK (JSON valide)  │ Échec
         ▼                   ▼
    [RETOUR]          ┌─────────────────────────────────────┐
                      │  2. Proxy (Scrape.do ou custom)     │
                      └─────────────────────────────────────┘
                                        │
                             ┌─────────┴─────────┐
                             │ OK                │ Échec
                             ▼                   ▼
                        [RETOUR]         ┌─────────────────────────────────────┐
                                         │  3. Playwright (stealth plugin)      │  ← Souvent 502
                                         └─────────────────────────────────────┘
                                                          │
                                              ┌───────────┴───────────┐
                                              │ OK                    │ Échec
                                              ▼                       ▼
                                         [RETOUR]         ┌─────────────────────────────────────┐
                                                          │  4. TinyFish (stealth + proxy US)   │  ← Fallback
                                                          └─────────────────────────────────────┘
                                                                           │
                                                                ┌──────────┴──────────┐
                                                                │ OK                  │ Échec
                                                                ▼                     ▼
                                                           [RETOUR]         ┌─────────────────────────────────────┐
                                                                            │  5. Direct (fetch) → 403            │
                                                                            └─────────────────────────────────────┘
```

## Options de configuration

| Méthode | Coût | Efficacité Cloudflare |
|---------|------|------------------------|
| **FlareSolverr** (Docker) | Gratuit, illimité | ✅ Bonne |
| **Scrape.do** | 1000 req/mois gratuites | ✅ Bonne |
| **TinyFish** (stealth + proxy) | Crédits API | ✅ Bonne (découverte) |
| **Playwright + stealth** | Gratuit | ⚠️ Souvent 502 |
| **Direct** | Gratuit | ❌ 403 |

## Configuration requise (.env)

Pour que le sync Nauticals fonctionne, **au moins une** des options suivantes :

### 1. FlareSolverr (recommandé, gratuit)

```bash
docker run -d -p 8191:8191 --restart unless-stopped ghcr.io/flaresolverr/flaresolverr:latest
```

Aucune clé API. Variable optionnelle : `FLARESOLVERR_URL=http://localhost:8191/v1`

### 2. TinyFish (découverte uniquement)

```env
TINYFISH_API_KEY=your_key
```

- Utilisé uniquement pour la phase découverte (subcats, listes de pages)
- Stealth + proxy US pour maximiser les chances face à Cloudflare
- Consomme des crédits TinyFish (~50–100 runs par sync)

### 3. Scrape.do (fallback)

```env
SCRAPE_DO_API_KEY=your_token
# ou
SCRAPE.DO_API_KEY=your_token
```

- **1000 crédits/mois gratuits** (plan Free)
- Utilisé pour toutes les requêtes si TinyFish échoue ou pour le bulk
- 1 crédit = 1 requête datacenter

### 4. Proxy personnalisé

```env
CRUISERSWIKI_PROXY_URL=https://api.scraperapi.com?api_key=KEY&url=
```

- Format : l’URL doit accepter `url=` en paramètre (URL encodée de la cible)
- Exemples : ScraperAPI, ScrapingBypass, etc.

## Structure Cruisers Wiki

- **API** : `https://www.cruiserswiki.org/api.php`
- **Catégories** : `Category:Ports` → sous-catégories `Category:Ports - Greece`, etc.
- **Pages** : une page par port/ancrage avec `{{coord|lat|lng}}` dans le wikitext
- **Sections** : Navigation, Entrance, Anchorages, Dangers, etc.

## Script structure (`npm run cruiserswiki:structure`)

Le script `scripts/cruiserswiki-structure-agent.ts` cartographie la structure des catégories via l’**API MediaWiki** (pas d’agent TinyFish). Il utilise `cruisersWikiFetch` (FlareSolverr en priorité) pour contourner Cloudflare.

**Flux :**
1. `list=categorymembers` : liste les sous-catégories de Ports, Marinas, Anchorages, Countries
2. `prop=categoryinfo` : récupère le nombre de pages et sous-catégories par catégorie
3. Page `World_Cruising_Guides` : extrait les régions de premier niveau
4. Sauvegarde dans `cruiserswiki-structure.json`

**Prérequis :** FlareSolverr (recommandé) ou Proxy/TinyFish en fallback. Plus besoin de `TINYFISH_API_KEY` pour ce script.

## Alternatives explorées

1. **MediaWiki Special:Export** : protégé par Cloudflare comme le reste du site
2. **Dump public** : Cruisers Wiki ne publie pas de dump XML
3. **playwright-extra + stealth** : aide mais Cloudflare détecte souvent Playwright
4. **TinyFish + proxy** : combinaison recommandée par la doc TinyFish pour les sites protégés

## Références

- [TinyFish Anti-Bot Guide](https://docs.tinyfish.ai/anti-bot-guide)
- [TinyFish Proxies](https://docs.tinyfish.ai/key-concepts/proxies)
- [Scrape.do Pricing](https://scrape.do/pricing/) (1000 crédits gratuits/mois)
- [MediaWiki API](https://www.mediawiki.org/wiki/API)
