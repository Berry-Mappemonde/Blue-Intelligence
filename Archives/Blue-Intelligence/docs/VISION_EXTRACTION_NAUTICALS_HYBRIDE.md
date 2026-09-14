# Vision complète — Extraction nauticals hybride (regex + heuristiques + boucle Claude)

Document de synthèse : du moment où les **URLs** et les **captures d’archives** sont connues jusqu’à la **fabrication des popups nauticals** sur la carte.

---

## Schéma global

```mermaid
flowchart TB
  subgraph INPUT["Déjà acquis"]
    A[URLs Cruisers Wiki + historique CDX<br/>timestamps, digests]
  end

  subgraph CAPTURE["Sélection contenu brut"]
    B[Pour chaque URL : meilleure capture<br/>récente, sans Cloudflare]
    C[(wayback_best_captures<br/>wikitext brut)]
    A --> B --> C
  end

  subgraph BOUCLE["Boucle hors prod — Claude + échantillons tournants"]
    direction TB
    S1[Échantillon de wikitext réel]
    S2[Claude analyse : cas réussis / ratés]
    S3[Propose ou affine :<br/>• regex<br/>• heuristiques scores<br/>• listes blanche / noire]
    S4[Test sur autre échantillon]
    S5{Arrêt ?<br/>succès > X % ou<br/>plateau sur N itérations}
    S6[Validation finale hold-out<br/>→ performance réelle]
    S1 --> S2 --> S3 --> S4 --> S5
    S5 -->|non| S1
    S5 -->|oui| S6
  end

  subgraph ARTEFACTS["Ce que la boucle produit"]
    R[Pack extraction versionné :<br/>regex + règles + scores + listes]
    S6 --> R
  end

  subgraph PROD["Production — par page"]
    direction TB
    P1[Lire wikitext depuis wayback_best_captures]
    P2[Filtre nautique<br/>regex + scores + listes]
    P3{Pertinent ?}
    P4[Extraction structurée<br/>regex + heuristiques sections / templates]
    P5[Géolocalisation<br/>regex coord + fallbacks heuristiques]
    P6[Objet « formulaire popup »<br/>titre, description, caution, lat, lng, …]
    P1 --> P2 --> P3
    P3 -->|non| SKIP[Ignorer ou file basse priorité]
    P3 -->|oui| P4 --> P5 --> P6
    R -.->|applique| P2
    R -.->|applique| P4
    R -.->|applique| P5
  end

  C --> P1
  C -.->|alimente| S1

  subgraph CARTE["Popups nauticals"]
    N[(nauticals / GeoJSON)]
    UI[Carte : marqueurs + popup<br/>même structure que l’app actuelle]
    P6 --> N --> UI
  end

  subgraph MAJ["Optionnel — aligné produit actuel"]
    PH2[Phase 2 : priorisation<br/>modification_frequency]
    PH3[Phase 3 : re-sync périodique<br/>Wayback + ré-application du pack]
    N --> PH2 --> PH3
  end
```

---

## Lecture en langage naturel

1. **Entrée** : liste d’URLs et historique des captures (CDX) déjà construits.
2. **Sélection** : pour chaque URL, choix de la **meilleure archive** (pas Cloudflare, la plus récente) → stockage du **wikitext brut** (ex. `wayback_best_captures`).
3. **Boucle (hors ligne)** : sur des **échantillons tournants**, Claude aide à définir et affiner **regex + heuristiques** (scores, listes blanche/noire). Tests, mesure, **critères d’arrêt** (taux de succès > X % ou plateau sur N itérations), puis **validation finale** sur un hold-out → **pack d’extraction versionné**.
4. **Production** : pour chaque page, application **uniquement** du pack (peu ou pas d’appels Claude) : filtre « instructions nautiques », champs type formulaire popup, géolocalisation.
5. **Sortie** : persistance en base (`nauticals`) et affichage **popups** sur la carte comme aujourd’hui.
6. **En option** : **Phase 2** (priorisation) et **Phase 3** (mises à jour périodiques), en **ré-appliquant** le même pack sur le wikitext mis à jour.

---

## Rôle des briques

| Élément | Rôle |
|--------|------|
| **Regex** | Coordonnées, sections, templates, motifs répétitifs dans le wikitext. |
| **Scores** | Pondérer la pertinence (mots-clés, présence de sections attendues, etc.). |
| **Listes blanche / noire** | Titres, namespaces, préfixes de page, mots d’exclusion. |
| **Claude** | Surtout **dans la boucle** : proposer et affiner regex + heuristiques — **pas** sur chaque page en production (sauf filet de sécurité ou cas rares si on le décide plus tard). |

---

## Objectif économique

- **Boucle** : échantillon → Claude → regex/heuristiques → tests → amélioration → échantillon tournant → arrêt → validation réelle.
- **Prod** : **économiser les appels Claude** sur le traitement « filtrer / structurer / géolocaliser » en encodant le résultat de la boucle dans un **pack déterministe** (regex + règles).

---

## Note sur le rendu Mermaid

Les diagrammes Mermaid sont visibles dans GitHub, dans certains IDE (preview Markdown), et dans des outils comme [Mermaid Live Editor](https://mermaid.live).

## Implémentation et workflow opérationnel

- Moteur et schéma JSON : `lib/nautical-extraction-pack.ts`, `data/nautical-extraction-pack.default.json`
- Export d’échantillons, validation gold, prompts : **[EXTRACTION_PACK_WORKFLOW.md](EXTRACTION_PACK_WORKFLOW.md)**
