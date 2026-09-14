# Table wayback_best_captures : pipeline en 3 étapes

## Objectif

Séparer le flux en trois étapes explicites :
1. **Trouver** la dernière archive valable pour chaque URL
2. **Extraire** le contenu complet et le stocker
3. **Remplir** la table nauticals à partir de ce contenu

---

## Nouvelle table : wayback_best_captures

```sql
CREATE TABLE wayback_best_captures (
  url TEXT PRIMARY KEY,
  timestamp TEXT NOT NULL,
  wayback_url TEXT NOT NULL,
  content_type TEXT NOT NULL,
  content TEXT NOT NULL,
  fetched_at TEXT NOT NULL
);
```

- `content_type` : `'wikitext'` (via action=edit)
- `content` : wikitext brut extrait de textarea#wpTextbox1

---

## Flux refactorisé

```
wayback_cdx_raw
    → populateWaybackBestCaptures (étapes 1+2)
        Pour chaque URL : timestamps → fetch action=edit → si valide → INSERT wayback_best_captures
    → wayback_best_captures
    → nauticalsFromBestCaptures (étape 3)
        SELECT → parse → NauticalInsertWayback[]
    → nauticals
```

---

## Modifications

### 1. server.ts — Création de la table

Après `wayback_cdx_raw` (ligne ~235) :

```sql
CREATE TABLE IF NOT EXISTS wayback_best_captures (
  url TEXT PRIMARY KEY,
  timestamp TEXT NOT NULL,
  wayback_url TEXT NOT NULL,
  content_type TEXT NOT NULL,
  content TEXT NOT NULL,
  fetched_at TEXT NOT NULL
);
```

### 2. server.ts — `populateWaybackBestCaptures(entries)`

- Entrée : `{ url: string; timestamp?: string }[]`
- Pour chaque URL : `getCdxTimestampsForUrlVariants(url)` → essayer timestamps du plus récent au plus ancien
- Fetch `editUrl = url + "?action=edit"` via `fetchWaybackHtml(editUrl, ts)`
- Si `isCloudflarePage(html)` → skip, essayer timestamp suivant
- `wikitext = extractWikitextFromEditPage(html)`
- Si wikitext && length > 100 → `INSERT OR REPLACE wayback_best_captures`
- Réutiliser WAYBACK_CONCURRENCY, WAYBACK_DELAY_MS

### 3. server.ts — `nauticalsFromBestCaptures()`

- `SELECT url, timestamp, wayback_url, content FROM wayback_best_captures`
- Pour chaque ligne : `parseCoordFromWikitext`, `parseDescriptionFromWikitext`, title dérivé de l'URL
- Retour : `NauticalInsertWayback[]`

### 4. server.ts — Refactoriser `fetchWaybackCruisersWikiNauticals`

Remplacer la boucle fetch HTML + parse (quand pas MediaWiki fallback) par :
1. `populateWaybackBestCaptures(entries)`
2. `nauticalsFromBestCaptures()`

Fallback MediaWiki : garder l'ancienne logique (fetchWaybackHtmlClosest + parse HTML).

### 5. Phase 3 Agent — Mise à jour wayback_best_captures

Quand `fetchWaybackWikitextForPage` trouve une archive valable : `INSERT OR REPLACE wayback_best_captures` avant de mettre à jour le nautical.

---

## Ordre d'implémentation

1. Créer la table wayback_best_captures
2. Implémenter populateWaybackBestCaptures
3. Implémenter nauticalsFromBestCaptures
4. Refactoriser fetchWaybackCruisersWikiNauticals
5. Adapter Phase 3 Agent pour mettre à jour wayback_best_captures
