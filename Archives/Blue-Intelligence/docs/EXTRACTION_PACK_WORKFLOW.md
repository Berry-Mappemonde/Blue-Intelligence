# Workflow — pack d’extraction nauticals (hybride Claude + regex)

Ce document décrit comment **affiner** le fichier JSON du pack ([`data/nautical-extraction-pack.default.json`](../data/nautical-extraction-pack.default.json)) sans appeler Claude sur chaque page en production.

Référence vision : [`VISION_EXTRACTION_NAUTICALS_HYBRIDE.md`](VISION_EXTRACTION_NAUTICALS_HYBRIDE.md).

## Rôle du pack

Le pack définit :

- **Filtre** : listes blanche/noire sur le slug d’URL, score minimum, mots-clés pondérés, bonus de sections.
- **Extraction** : sections « wanted » (navigation, ancrages, …), sections « danger », longueur max du texte par section.

Le moteur [`lib/nautical-extraction-pack.ts`](../lib/nautical-extraction-pack.ts) applique ces règles au wikitext issu de `wayback_best_captures`.

## Variable d’environnement

- `NAUTICAL_EXTRACTION_PACK_PATH` : chemin absolu ou relatif au répertoire de travail vers un JSON de pack personnalisé. Si absent, le fichier default du dépôt est utilisé.

## 1. Exporter un échantillon de wikitext

Prérequis : base SQLite `blue_intelligence.db` à la racine du projet, table `wayback_best_captures` remplie (sync Wayback).

```bash
npx tsx scripts/export-wayback-wikitext-sample.ts --limit 50 --seed 42 --out data/wayback-wikitext-sample.ndjson
```

- Une ligne JSON par page (champs `url`, `timestamp`, `wayback_url`, `content_len`, `content`).
- `--seed` fixe l’échantillonnage pour comparer deux exports.

## 2. Boucle avec Claude (manuelle)

1. Ouvrir le NDJSON (ou un sous-ensemble) dans Claude / l’IDE.
2. Demander par exemple :
   - d’identifier les pages **non pertinentes** pour des instructions nautiques ;
   - de proposer des **sous-chaînes** pour `titleUrlBlacklist` / `titleUrlWhitelist` ;
   - d’ajuster `keywordWeights` et `sectionPresenceBonus` ;
   - d’enrichir `wantedSectionSubstrings` / `dangerSectionSubstrings` si des titres de section récurrents manquent.
3. Fusionner les propositions dans une **copie** du JSON (ex. `data/nautical-extraction-pack.custom.json`).
4. Tester avec le script de validation (étape 3) ou un sync sur un sous-ensemble.

**Prompt type** (à adapter) :

> Voici N extraits de wikitext Cruisers Wiki (ports/ancrages) au format JSON Lines. Pour chaque page, indique si elle relève d’instructions nautiques exploitables. Liste les motifs d’URL ou de titre à exclure. Propose des entrées concrètes pour un JSON `titleUrlBlacklist`, `keywordWeights` et éventuellement des sections manquantes dans `wantedSectionSubstrings`.

## 3. Fichier « gold » et validation

1. Copier [`data/extraction-gold.example.json`](../data/extraction-gold.example.json) vers un fichier réel (ex. `data/extraction-gold.json`).
2. Renseigner des URLs présentes dans `wayback_best_captures` avec :
   - `include` : `true` / `false` attendu ;
   - `lat` / `lng` optionnels (tolérance ~0,02° dans le script).
3. Lancer :

```bash
npx tsx scripts/validate-extraction-pack.ts --gold data/extraction-gold.json --pack data/nautical-extraction-pack.default.json
```

Sortie : compteurs `tp` / `fp` / `tn` / `fn`, `accuracy`, et si coords fournies `coordOk` / `coordCheck`.

**Critères d’arrêt** (à fixer en équipe) : par ex. `accuracy >= 0,95` sur le jeu gold + validation sur un hold-out non vu pendant le tuning.

## 4. Intégration prod

- Définir `NAUTICAL_EXTRACTION_PACK_PATH` pointant vers le JSON validé, ou remplacer le default après revue.
- Redémarrer le serveur : `getMemoizedExtractionPack()` charge le pack une fois au premier usage.

## 5. Tests automatisés

```bash
npm run test:nautical-pack
```

Vérifie le comportement du default pack, coords, filtre blacklist et seuil de score.

## Voir aussi

- Code : [`lib/nautical-extraction-pack.ts`](../lib/nautical-extraction-pack.ts)
- Sync : `nauticalsFromBestCaptures` dans [`server.ts`](../server.ts)
- CDX Wayback (mode bulk vs per-URL, depuis 2019, reprise) : [`WAYBACK_CDX.md`](WAYBACK_CDX.md)
