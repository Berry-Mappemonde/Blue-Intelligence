# État des lieux de `docs/` — ce qui est fait, ce qui reste, ce qu'on range

Version **1.0** — 20 septembre 2026 (soir, pendant la première nuit de lots).
Relecture de **tous** les documents du dossier. Trois colonnes : le rôle du
document aujourd'hui, ce qu'il décrit qui est **fait**, ce qu'il note qui
**n'est pas implémenté** (la mémoire à ne pas perdre). Le rangement proposé
(§ 3) se fera **après** la nuit de lots : les prompts des agents citent ces
chemins, on ne les déplace pas pendant qu'ils tournent.

Légende : **RÉF** = référence vivante (à tenir à jour) · **PLAN** = plan en
cours d'exécution · **HIST** = plan réalisé ou remplacé (à archiver, garder
pour la mémoire) · **CDC** = cahier des charges Blue Intelligence (référence
produit) · **AUDIT** = constat daté.

## 1. Documents un par un

| Document | Rôle | Fait | Reste / mémoire |
|---|---|---|---|
| `REGLES_WORKFLOW_AGENT.md` | **RÉF** | règles branches/PR/merge/recette/review automatique ; utilisé par 11 lots ce soir | ajouter § 5 : « un spec de lot tient sans API » (sonde `/voyage/official`), rejeu double `API_PROXY_TARGET=…:9`, `--workers=1` pour la suite complète (les agents l'ont constaté : timeouts en parallèle) |
| `LOTS_ORDRE_ET_PROMPTS.md` | **PLAN** | 33 lots, prompts ; P2, L1, M, N, O, F1, F2, L2, F3, F4, L3 exécutés le 20 sept. | tenir la colonne « fait » ; ajouter les lots W (workflow) et D0 (rangement docs) |
| `PLAN_LOTS_COMPLEMENTAIRE_SIMULATEUR.md` | **PLAN** | causes racines de la revue du 19–20 ; P2, M, N, O faits ce soir | S, T, U cette nuit ; Q/R remplacés par le plan film |
| `PLAN_FILM_REVOIR_EXPEDITION.md` | **PLAN** | F1–F4 faits ce soir (à recetter) | F5 cette nuit ; recette réelle du film 2:30 avec voix par le porteur |
| `PLAN_NEMOTRON_NEBIUS_TAVILY.md` | **PLAN** | L1, L2, L3 faits ce soir ; ordre de cascade corrigé (TF → NIM → OpenRouter → Claude) | L4–L6 cette nuit ; **prérequis** : `NEBIUS_API_KEY`, `TAVILY_API_KEY` sur le VPS et en local ; crédits Token Factory valides jusqu'au 15 déc. ; formulaire Devpost après usage réel |
| `PLAN_AUDIT_CALCULS.md` + `audits/CALCULS_ETAT_DE_L_ART.md` | **PLAN** | C1 fait (PR #207) ; état de l'art vérifié | C2–C7 cette nuit ; **prérequis C2** : `COPERNICUS_USERNAME/PASSWORD` (déjà), premier hindcast ≈ 40 min de tâche de fond |
| `PLAN_GLOBE_3D.md` v2 | **PLAN** | recherche MapLibre 6 ; Leaflet gardé | G0–G7 une autre nuit ; décision A/B au lot G0 |
| `HACKATHON_DEVPOST_SOUMISSION.md` | **PLAN** | textes EN, réponses du formulaire, plan vidéo | notes 1–10 après usage réel ; **1ʳᵉ soumission le 28 sept.** ; vidéo à tourner sur le film F1–F5 |
| `ESPRIT_DE_L_APPLICATION.md` | **RÉF** | chaîne de traitement, critique du diagramme généré, diagramme corrigé | ajouter l'onglet Globe quand il existera ; servir de base au README EN |
| `PLAN_GENERAL_DEVELOPPEMENT_SIMULATEUR.md` v2 | **RÉF/HIST** | réanalyse de chaque idée (18 sept.), décisions du porteur § 5, lots A–K faits | § 4 « ce qu'on ne fait pas » à relire : ordre vocal / dictée du journal, page carnet de bord (1.5) **non faits** ; LangSmith écarté ; sécurité P0 = secret admin partagé (compte utilisateur « plus tard ») |
| `PLAN_LOTS_AGENT_SIMULATEUR.md` v1.1 | **HIST** | lots P → K tous mergés (#189–#202) | rien ; à archiver avec un bandeau « réalisé » |
| `PLAN_CHANTIERS_STRUCTURANTS_SIMULATEUR.md` | **HIST** (16 l.) | pointeur vers le pipeline d'affichage | fusionner dans `PLAN_PIPELINE_AFFICHAGE_SIMULATEUR.md` puis supprimer |
| `PLAN_PIPELINE_AFFICHAGE_SIMULATEUR.md` | **HIST/mémoire** | P1 GRIB `pending` fait ; profil prod fait (lot J) | **non faits, à garder en mémoire** : catalogues spatiaux complets (tuiles vectorielles, clustering) si les données grossissent ; pipeline météo asynchrone partagé « tous fournisseurs » (statut durable + cache par cycle) ; Web Worker (conditionné au profil : pas nécessaire aujourd'hui) ; `useWakeLayer` tableaux complets à chaque tick |
| `PLAN_UI_PRODUIT_SIMULATEUR.md` | **HIST** | lots UI 1–9 faits | lot 10 « Recalculer l'itinéraire » **volontairement hors périmètre** (le bouton public reste ; G3 conseil de route en Suivre non fait) |
| `PLAN_IMPLEMENTATION_SKIPPER_VIRTUEL.md` v1.1 | **HIST** | S1 → S5 mergés ; S6 (contraintes recompute) et S7 faits dans les lots G/K | « S6+ : Confort (3 pills) » **non fait** ; ordre vocal non fait |
| `PLAN_IMPLEMENTATION_EVENEMENTS_ICI_LLM.md` v1.5 | **HIST** | juge NOW/FREE, dossier `ici()`, récit LLM, StoryJob, pré-génération (lots E1–E5 puis P/F) | E5 « file récit / extract côté serveur » : partiellement (story_cache) ; « NVIDIA / Tavily = TODO dernier moment » → devenu L1–L6 ; à archiver |
| `PLAN_IMPLEMENTATION_SIMULATOR_SUIVRE_ET_SIMULATION.md` v2 | **HIST** | les deux modes existent | à archiver |
| `PLAN_IMPLEMENTATION_SIMULATION_A.md` / `_B.md` | **HIST** | horloge climatologique (A) faite ; bateau virtuel (B) fait (recompute, `spliced`) | B « English : not yet » → i18n fait depuis ; à archiver |
| `PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md` (+ `.en`) | **HIST** | étape 1 livrée (13 sept.) | à archiver (1 200 lignes ×2) |
| `PLAN_IMPLEMENTATION_CLIMATOLOGIE.md` | **HIST/CDC BI** | mode climatologie BI (7ᵉ mode) livré ; atlas consommé par le simulateur | « **swell not shipped** » (houle climatologique non livrée) — mémoire ; à archiver côté BI |
| `PLAN_IMPLEMENTATION_FILIERES_CARTO.md` + `audits/2026-09-14-filieres-diagnostic.md` | **HIST/CDC BI** | filières contrôle/carte/hydro/satellite | « catalogue `candidat` (feux, roches, mouillages) pas encore dans un pipeline » — mémoire |
| `PROFIL_BUILD_PROD_2026-09-19.md` | **AUDIT** | profil prod (lot J) : React ≈ 2,5 s CPU / 60 s | refaire après U (zoom) ; sert de méthode |
| `ARCHITECTURE.md` | **RÉF périmée** | analyse de code de début septembre | **en retard** : `backend/server.py` n'a plus que 5 lignes, l'app est `backend/app/` (routers/services/core) ; le simulateur n'y est pas décrit → à réécrire à partir d'`ESPRIT_DE_L_APPLICATION.md` § 3 (diagramme corrigé) |
| `PRD.md` | **RÉF** | produit Blue Intelligence | P1 « PoE crowdsourcing » non fait ; à dater |
| `CAHIER_DES_CHARGES_POE.md` v1.4 | **CDC** | pipeline PoE, Gold, seeds, audits | gaps notés § 342/477 (`judge_one` n'exploite pas toute la page ; catalogue parser) ; carte monde des ZEE par statut non générée ; **auto-refresh désactivé le 20 sept.** (hotfix #221 : il bloquait le serveur) → à rendre non bloquant puis réactiver |
| `CAHIER_DES_CHARGES_PROJETS.md` v2.0 | **CDC** | projets marins, swarm | rien de neuf ; référence |
| `CAHIER_DES_CHARGES_REVIEW.md` v1.1 | **CDC** | onglet Review | § « Gaps — the 1.1 contract is not yet the UI » : écarts contrat/UI à reprendre |
| `CONTRATS_MODES.md`, `CONTRATS_REVIEW_PAR_MODE.md` | **CDC** | contrats des 7 modes BI | référence |
| `CATALOGUE_SEAMARK.md`, `ici-tout.md`, `REGLES_PARAMETRES.md` | **RÉF** | catalogue balisage ; familles `ici()` ; paramètres | `REGLES_PARAMETRES.md` : les lots C2/C4/C7 y ajoutent leurs constantes cette nuit (vérifier au matin) |
| `hackathon-nebius-nvidia.md` (+ `.en`) | **HIST** | cahier unique du 13–14 sept. (avant les lots) | § 8 « état du code » périmé (« pas commencé : sac ici, Tavily, Nemotron » — tout est fait ou en cours) ; les crédits (§ 7) restent utiles → **remplacé** par `PLAN_NEMOTRON_NEBIUS_TAVILY.md` + `HACKATHON_DEVPOST_SOUMISSION.md` ; à archiver avec bandeau |
| `HACKATHON_OPEN_AGENT_2026.md` | **HIST** | autre hackathon (synthèse) | archiver |
| `nvidia-llm-audit.md` | **HIST** | replis NIM par usage (avant Token Factory) | remplacé par la cascade L1 ; archiver |
| `poe-*.md` (4 fichiers, dont `poe-name-only-33.md` 2 125 l.) + `data/*.json` | **AUDIT BI** | dossiers d'audit PoE (GPS, seeds, name_only) | archiver ensemble dans `archives/poe/` |
| `audits/2026-09-10-tags.md` | **AUDIT** | audit des tags | garder dans `audits/` |
| `recette/` | **preuves** | captures des lots (C1 ; les lots de la nuit en ajoutent) | garder ; une sous-dossier par lot |

## 2. La mémoire : noté quelque part, pas implémenté

Liste consolidée (à reporter dans les plans vivants ou à décider « non ») :

1. Ordre **vocal** au skipper / dictée du journal (plan général § 1, skipper « plus tard »).
2. **Page carnet de bord** (chapitres 1.5) — le récit et le journal existent, pas la page dédiée.
3. **Confort** (3 pills, S6+) dans le panneau skipper.
4. **Conseil de route en Suivre** (G3) — recompute reste Simulation ; L5 en ajoute l'explication.
5. Pipeline météo **asynchrone partagé** pour tous les fournisseurs (statut durable, cache par cycle) — seul le GRIB est `pending`.
6. **Catalogues spatiaux** (tuiles vectorielles, clustering) — utile au globe (G3 PMTiles pour les ZEE en est le premier pas).
7. **Houle climatologique** (« swell not shipped ») côté atlas BI.
8. **Catalogue `candidat`** (feux, roches, mouillages) dans un pipeline BI.
9. **PoE** : `judge_one` sur toute la page, catalogue parser, carte monde des ZEE par statut, **auto-refresh à rendre non bloquant** (hotfix #221).
10. **Review BI** : écarts contrat 1.1 / UI.
11. **Compte utilisateur** (sécurité P0 = secret partagé).
12. **PoE crowdsourcing** (PRD P1).
13. **Dépôt public dédié** pour Devpost (`git subtree split`) — ou garder le mono-dépôt public actuel (MIT) : décision à prendre avant le 28.
14. **Onglet Globe** (G0–G7) et **Google Earth Studio** pour un plan B vidéo.

## 3. Rangement proposé (lot D0, après la nuit)

```
docs/
  README.md                      ← index : quoi lire pour quoi (nouveau)
  REGLES_WORKFLOW_AGENT.md  ESPRIT_DE_L_APPLICATION.md  REGLES_PARAMETRES.md  ARCHITECTURE.md (réécrit)
  plans/     LOTS_ORDRE_ET_PROMPTS, PLAN_LOTS_COMPLEMENTAIRE, PLAN_FILM, PLAN_NEMOTRON, PLAN_AUDIT_CALCULS, PLAN_GLOBE_3D, WORKFLOW_INDUSTRIEL
  hackathon/ HACKATHON_DEVPOST_SOUMISSION (+ crédits repris de hackathon-nebius-nvidia § 7)
  cdc/       CAHIER_DES_CHARGES_*, CONTRATS_*, PRD, CATALOGUE_SEAMARK, ici-tout
  audits/    CALCULS_ETAT_DE_L_ART, PROFIL_BUILD_PROD_*, 2026-09-*, poe/ (4 dossiers + data)
  recette/   captures par lot
  archives/  PLAN_GENERAL (v2 gelé), PLAN_LOTS_AGENT, PLAN_CHANTIERS, PLAN_PIPELINE_AFFICHAGE, PLAN_UI_PRODUIT, SKIPPER_VIRTUEL,
             EVENEMENTS_ICI_LLM, SUIVRE_ET_SIMULATION, SIMULATION_A/B, ETAPE1 (+en), CLIMATOLOGIE, FILIERES_CARTO,
             hackathon-nebius-nvidia (+en), HACKATHON_OPEN_AGENT_2026, nvidia-llm-audit
```

Règles du rangement : chaque fichier archivé reçoit en tête un bandeau
« **Archivé le … — réalisé / remplacé par …** » ; les liens des documents
vivants sont réécrits (`rg -n "docs/…"`) ; les prompts de
`LOTS_ORDRE_ET_PROMPTS.md` sont mis à jour dans le même commit ; `.cursor/rules`
qui citent des chemins sont vérifiés. Un seul PR, « aucun changement
visible », recette = les liens des documents vivants s'ouvrent.
