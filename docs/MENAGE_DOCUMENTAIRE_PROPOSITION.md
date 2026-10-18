# Ménage documentaire — proposition avant la séparation

Proposition en lecture seule, le 17 octobre 2026, sur `main` au commit `563b79e4` (2026-10-17 09:32:47 -0400, « docs: update GenAI.works hackathon plan »). Remote vérifié : `github.com/Berry-Mappemonde/Blue-Intelligence`.

Ce fichier classe les documents. Il n’en déplace, n’en renomme et n’en supprime aucun. Le point de départ est la carte du 17 octobre au matin ; chaque chemin, chaque date et les contradictions utiles ont été revus dans l’arbre de `main`.

## Comment lire le tableau

Cinq destinations, une seule par document :

| Code | Destination | Sens |
|---|---|---|
| (a) | dépôt NAVIGUIDE | Document vivant du simulateur, de l’ancien planificateur, ou de l’outillage qui les pilote. |
| (b) | dépôt Blue Intelligence | Document vivant de la carte océanique, de ses cahiers, ou de l’infra qui la sert. |
| (c) | les deux | Les deux dépôts en ont besoin. La case dit qui garde l’original. L’autre dépôt reçoit une copie courte, ou la moitié qui le concerne. |
| (d) | `docs/archives/` | Obsolète, à garder. Le dossier existe déjà sous ce nom (avec un s). |
| (e) | à supprimer | Doublon octet pour octet. Aucun fichier vide n’a été trouvé. |

Règles de classement utilisées ici :

- Un plan dont les lots sont joués, ou qui porte un bandeau « remplacé », quitte la racine de `docs/` pour `docs/archives/` du dépôt qui possède le produit. La mémoire qu’il faut encore citer est nommée dans la raison.
- Un cahier, un manuel, une règle Cursor, un README de code vivant et un plan d’octobre encore ouvert restent (a), (b) ou (c), même si une phrase intérieure est en retard.
- L’arbre `Archives/` (A majuscule, rapatrié le 13 septembre 2026) est un instantané d’anciens dépôts. Ses textes suivent cet arbre, (a) ou (b). Ils ne sont pas versés dans `docs/archives/`.
- `docs/LOTS_ORDRE_ET_PROMPTS.md` reste à ce chemin dans le dépôt NAVIGUIDE tant que `infra/agents/run_lots.py` lit `docs/LOTS_ORDRE_ET_PROMPTS.md` (ligne `PROMPTS_MD` du script).

Date = jour de `git log -1 --format=%ci` (date du commit, pas la date écrite dans le texte). Heure et fuseau : relire avec la même commande. Périmètre : `*.md`, `*.mdc`, README et pitch en `.txt`, reçus `docs/recette/**/*.txt`. Hors tableau : `requirements.txt`, `robots.txt`, licences de données, images de recette, JSON.

**132 documents sur `main`.** Quatre textes cités par la carte du matin ne sont pas dans ce compte : ils ne sont pas sur `main` (voir la fin).

## 1. Règles Cursor (`.cursor/rules`)

| Document | Date du commit | Destination | Raison |
|---|---|---|---|
| `.cursor/rules/anti-regression-visuelle-simulateur.mdc` | 2026-10-15 | (a) NAVIGUIDE | Plancher d’écran du simulateur et décision DM9 du 14 oct. (onglets Tracer). |
| `.cursor/rules/base-de-donnees-vps.mdc` | 2026-09-14 | (c) les deux — original Blue Intelligence | Mongo vivant = VPS depuis le 10 sept. 2026, Atlas gelé, `sync-from-atlas.sh` interdit ; copie courte côté NAVIGUIDE tant que `naviguide_simulator` est sur le même mongod. |
| `.cursor/rules/environnement-utilisateur.mdc` | 2026-09-14 | (c) les deux — original Blue Intelligence | Mac du propriétaire et VPS OVH `135.125.226.16` ; la copie NAVIGUIDE ajoute `naviguide.fr`. |
| `.cursor/rules/modeles-cursor-uniquement.mdc` | 2026-09-16 | (c) les deux — original Blue Intelligence | Workers Cloud sur un modèle Cursor ; le chat Mac garde le modèle choisi par le propriétaire. |
| `.cursor/rules/naviguide-simulator-preview.mdc` | 2026-09-18 | (a) NAVIGUIDE | Prévisualisation locale du simulateur (`ensure-dev.sh`, port 5174) et deploy seulement via `main`. |
| `.cursor/rules/pas-de-verification-video.mdc` | 2026-09-16 | (c) les deux — original NAVIGUIDE | Preuve par tests, `curl` ou capture fixe ; copie courte dans Blue Intelligence. |
| `.cursor/rules/reparations-sur-github.mdc` | 2026-10-17 | (c) les deux — original Blue Intelligence | Un correctif se commit et se pousse sur la PR concernée dans la même session. |

Le filtre du 17 oct. (`docs/PLAN_SEPARATION_DEPOTS.md` § 3) envoie `.cursor/` entier vers NAVIGUIDE. Blue Intelligence perdrait alors la règle Mongo. Voir la décision 2.

## 2. Racine

| Document | Date du commit | Destination | Raison |
|---|---|---|---|
| `README.md` | 2026-10-15 | (c) les deux — original Blue Intelligence | Page du monodépôt (simulateur, carte, cascade Token Factory) ; le filtre le garde dans Blue Intelligence, NAVIGUIDE en reçoit une page simulateur seule. |

Le tableau des modes dit encore « Simulation » (FR ligne 35, EN ligne 119). `infra/agents/PARCOURS_DE_REFERENCE.md` (16 oct.) dit que cette pilule n’est plus un item d’écran.

## 3. `docs/` (racine du dossier)

| Document | Date du commit | Destination | Raison |
|---|---|---|---|
| `docs/ARCHITECTURE.md` | 2026-09-14 | (b) Blue Intelligence | Le plan de split l’indique au jury GenAI ; le § 1 décrit des fichiers plats absents, le § 3 décrit `backend/app/` qui existe : à réécrire, pas à archiver tant que le remplaçant n’est pas écrit. |
| `docs/CAHIER_DES_CHARGES_POE.md` | 2026-09-14 | (b) Blue Intelligence | Cahier des ports d’entrée cité par le plan GenAI ; contrat, pas description du code du 17 oct. |
| `docs/CAHIER_DES_CHARGES_PROJETS.md` | 2026-09-14 | (b) Blue Intelligence | Cahier des projets de conservation marine. |
| `docs/CAHIER_DES_CHARGES_REVIEW.md` | 2026-09-14 | (b) Blue Intelligence | Contrat de l’onglet Review (v1.1, 8 sept.) ; l’état des lieux du 22 sept. signale un écart contrat/écran, l’écran du 17 oct. n’a pas été rouvert. |
| `docs/CATALOGUE_SEAMARK.md` | 2026-09-22 | (b) Blue Intelligence | Tags seamark et port lus par les pipelines ; la version machine est `backend/data/seamark_catalog.json`. |
| `docs/CONTRATS_MODES.md` | 2026-09-14 | (b) Blue Intelligence | Contrats des familles Blue Intelligence ; la carte montre l’atlas, NAVIGUIDE l’interroge. |
| `docs/CONTRATS_REVIEW_PAR_MODE.md` | 2026-09-22 | (b) Blue Intelligence | Même geste Review pour chaque mode ; Formalités est le mode de référence. |
| `docs/ESPRIT_DE_L_APPLICATION.md` | 2026-09-20 | (a) NAVIGUIDE | Chaîne sources → écran du simulateur (20 sept., avant le mot Tracer) ; Blue Intelligence y est la mémoire des sources. |
| `docs/ETAT_DES_LIEUX_DOCS.md` | 2026-09-22 | (d) `docs/archives/` — dépôt Blue Intelligence | Inventaire du 22 sept. (lot D0), figé ; l’arbre `plans/` · `hackathon/` · `cdc/` qu’il propose n’a pas été appliqué. |
| `docs/FILM_DISCOURS_ETAT_2026-09-28.md` | 2026-09-28 | (a) NAVIGUIDE | Le gabarit § 4 est encore cité par `naviguide-simulator/server/film_script.py` et par `server/tests/test_film_discours.py` ; la transcription § 1 est une photo du 28 sept. |
| `docs/HACKATHON_DEVPOST_SOUMISSION.md` | 2026-09-29 | (a) NAVIGUIDE | Textes anglais à coller dans Devpost ; le plan Nebius du 17 oct. demande de les aligner sur Suivre / Tracer et de remesurer la part de code. |
| `docs/HACKATHON_PLAN.md` | 2026-10-17 | (c) les deux — original Blue Intelligence | Index d’une page des trois plans du 17 oct. (séparation, Nebius, GenAI). |
| `docs/LOTS_ORDRE_ET_PROMPTS.md` | 2026-10-15 | (a) NAVIGUIDE | File des lots lue par `infra/agents/run_lots.py` (539 710 octets) ; le chemin reste `docs/LOTS_ORDRE_ET_PROMPTS.md`. |
| `docs/MANUEL_UTILISATEUR.md` | 2026-09-22 | (a) NAVIGUIDE | Manuel écran par écran ; le chapitre 2 s’appelle encore Simulation. |
| `docs/PLAN_AUDIT_CALCULS.md` | 2026-09-20 | (d) `docs/archives/` — dépôt NAVIGUIDE | Plan des lots C1–C7 ; les formules vivantes sont dans `docs/audits/CALCULS.md`. |
| `docs/PLAN_BATCH_2026-10-14.md` | 2026-10-15 | (d) `docs/archives/` — dépôt NAVIGUIDE | Batch 2 (HC1, deux modes, film) ; le calendrier Devpost est repris par le plan Nebius du 17 oct. |
| `docs/PLAN_BATCH_SUIVANT_2026-09-29.md` | 2026-10-14 | (d) `docs/archives/` — dépôt NAVIGUIDE | Bandeau « remplacé le 14 octobre » par `PLAN_BATCH_2026-10-14.md`. |
| `docs/PLAN_CORRECTIONS_2026-09-22.md` | 2026-09-22 | (d) `docs/archives/` — dépôt NAVIGUIDE | Lots RB1–RB8, revue du matin du 22 sept. |
| `docs/PLAN_CORRECTIONS_2026-09-23.md` | 2026-09-24 | (d) `docs/archives/` — dépôt NAVIGUIDE | Lots RD1–RD9 ; Revue du plan en onglet gauche. |
| `docs/PLAN_CORRECTIONS_2026-09-26-s2.md` | 2026-09-26 | (d) `docs/archives/` — dépôt NAVIGUIDE | Lots RE1–RE7 ; RE1 (ouverture en Simulation) est remplacé plus tard par RF7. |
| `docs/PLAN_CORRECTIONS_2026-09-26-s4.md` | 2026-09-26 | (d) `docs/archives/` — dépôt NAVIGUIDE | Lots RF ; base Mongo du simulateur séparée de la base Blue Intelligence. |
| `docs/PLAN_CORRECTIONS_2026-09-27-s5.md` | 2026-09-27 | (d) `docs/archives/` — dépôt NAVIGUIDE | Lots RH1–RH2 ; RH1 est l’ancêtre du chat d’octobre, pas sa spec. |
| `docs/PLAN_CORRECTIONS_2026-09-28-film.md` | 2026-09-28 | (d) `docs/archives/` — dépôt NAVIGUIDE | Lots RG du film ; le gabarit pointe vers `FILM_DISCOURS_ETAT_2026-09-28.md`, qui reste vivant. |
| `docs/PLAN_CORRECTIONS_REVUE_21_SEPT.md` | 2026-09-21 | (d) `docs/archives/` — dépôt NAVIGUIDE | Lots R1–R13, première revue du 21 sept. |
| `docs/PLAN_CORRECTIONS_REVUE_21_SEPT_SOIR.md` | 2026-09-21 | (d) `docs/archives/` — dépôt NAVIGUIDE | Lots RA1–RA8 ; RA8 (vitesse du passé) est l’ancêtre de HC1. |
| `docs/PLAN_DEUX_MODES_2026-09-29.md` | 2026-09-29 | (d) `docs/archives/` — dépôt NAVIGUIDE | Décision Tracer à la place de Simulation ; l’écran vivant est décrit par `PARCOURS_DE_REFERENCE.md`. |
| `docs/PLAN_FILM_REVOIR_EXPEDITION.md` | 2026-09-20 | (d) `docs/archives/` — dépôt NAVIGUIDE | Plan F1–F5 du 20 sept., repris ensuite par les lots RG. |
| `docs/PLAN_GLOBE_3D.md` | 2026-09-20 | (a) NAVIGUIDE | Globe MapLibre en plus de Leaflet, lots G0–G7, pas commencés : aucun `maplibre` sous `naviguide-simulator/`. |
| `docs/PLAN_HACKATHON_GENAI_BLUE_INTELLIGENCE.md` | 2026-10-17 | (b) Blue Intelligence | Plan GenAI.works, fenêtre 22–27 oct. 2026 UTC, agent PoE après cette date. |
| `docs/PLAN_HACKATHON_NEBIUS_NAVIGUIDE.md` | 2026-10-17 | (a) NAVIGUIDE | Plan Nebius du 17 oct. ; le lien vers `PLAN_BATCH_2026-10-16.md` est mort sur `main`. |
| `docs/PLAN_ICI_JOURNAL_EXPERT.md` | 2026-09-21 | (d) `docs/archives/` — dépôt NAVIGUIDE | Plan du 21 sept. (Ici, journal, revue) ; l’écran a été amendé par les lots suivants. |
| `docs/PLAN_LOTS_COMPLEMENTAIRE_SIMULATEUR.md` | 2026-09-22 | (d) `docs/archives/` — dépôt NAVIGUIDE | Lots P2, M, N, O, S, T, U de la revue 19–20 sept. |
| `docs/PLAN_MIGRATION_ANCIEN_NAVIGUIDE.md` | 2026-09-21 | (d) `docs/archives/` — dépôt NAVIGUIDE | Lots N1–N4 ; à garder en mémoire : lire `naviguide/`, ne pas y porter le simulateur. |
| `docs/PLAN_NEMOTRON_NEBIUS_TAVILY.md` | 2026-09-22 | (a) NAVIGUIDE | Grille de prix et garde-fous encore cités par le plan Nebius du 17 oct. ; les lieux d’appel ont changé (clic, question, questionnaire). |
| `docs/PLAN_SEPARATION_DEPOTS.md` | 2026-10-17 | (c) les deux — original Blue Intelligence | Plan du week-end ; copie NAVIGUIDE des sections dépôt, historique et huit tests. Le filtre « tout `docs/` dans Blue Intelligence » est à réaligner sur ce tableau. |
| `docs/PRD.md` | 2026-09-14 | (d) `docs/archives/` — dépôt Blue Intelligence | PRD du 26 août (`llm_core.py`, Emergent) ; contrainte encore valable : pas de purge, upsert non destructif. |
| `docs/README.md` | 2026-10-17 | (c) les deux — original NAVIGUIDE | Index actuel, surtout simulateur, section « En cours » calée sur septembre ; Blue Intelligence reçoit un index court (CDC, PoE, plan GenAI). |
| `docs/REGLES_PARAMETRES.md` | 2026-09-22 | (c) les deux — original Blue Intelligence | Principe et seuils BI (`backend/data/run_rules.json`) ; NAVIGUIDE reçoit le principe et les § 3.7 et suivants (horloge, polaire). |
| `docs/REGLES_WORKFLOW_AGENT.md` | 2026-09-29 | (a) NAVIGUIDE | Contrat des agents du simulateur : plancher `main`, pas de chiffre inventé, pas de merge par le worker. |
| `docs/REVUE_PORTEUR_2026-10-14.md` | 2026-10-14 | (a) NAVIGUIDE | Revue orale du 14 oct. ; DM9 et l’option du panneau droit sont recopiés dans la règle anti-régression. |
| `docs/SPECS_E2E_TRIAGE_2026-09-29.md` | 2026-09-29 | (d) `docs/archives/` — dépôt NAVIGUIDE | Photo du 29 sept. (100 specs, 17 sans chemin à vide). |
| `docs/USER_MANUAL.md` | 2026-09-22 | (a) NAVIGUIDE | Manuel anglais, chapitre Simulation ; paire de `MANUEL_UTILISATEUR.md`, textes différents. |
| `docs/WORKFLOW_INDUSTRIEL.md` | 2026-09-29 | (a) NAVIGUIDE | Cycle nuit / matin encore utile ; le calendrier écrit (28 sept., 9 oct.) est passé. |
| `docs/ici-tout.md` | 2026-09-18 | (a) NAVIGUIDE | Familles de `ici()` au point bateau ; sept liens vers `/cursor/stores/…` hors dépôt. |
| `docs/poe-confirmed-gps-audit.md` | 2026-09-14 | (b) Blue Intelligence | Audit GPS cité par `backend/data/run_rules.json` (`cdc`) et par `backend/scripts/audit_confirmed_gps.py`. |
| `docs/poe-name-only-33.md` | 2026-09-14 | (b) Blue Intelligence | Dossier des 33 seeds `name_only` ; `poe_name_only_review.py` lit `docs/data/poe-name-only-33-verifications.json`. |
| `docs/poe-seeds-bottom-up.md` | 2026-09-14 | (b) Blue Intelligence | Vérification bottom-up reliée au dossier des 33 noms ; même contrainte de chemin. |

Onze fichiers de cette racine sont absents de `docs/README.md` : `FILM_DISCOURS_ETAT_2026-09-28.md`, `PLAN_BATCH_2026-10-14.md`, `PLAN_BATCH_SUIVANT_2026-09-29.md`, `PLAN_CORRECTIONS_2026-09-23.md`, `PLAN_CORRECTIONS_2026-09-26-s2.md`, `PLAN_CORRECTIONS_2026-09-26-s4.md`, `PLAN_CORRECTIONS_2026-09-27-s5.md`, `PLAN_CORRECTIONS_2026-09-28-film.md`, `PLAN_DEUX_MODES_2026-09-29.md`, `REVUE_PORTEUR_2026-10-14.md`, `SPECS_E2E_TRIAGE_2026-09-29.md`.

## 4. `docs/archives/` (déjà rangés le 22 septembre 2026)

Même commit pour les dix-huit : 2026-09-22. Ils restent dans `docs/archives/`. Au split, ils suivent le dépôt indiqué.

| Document | Date du commit | Destination | Raison |
|---|---|---|---|
| `docs/archives/HACKATHON_OPEN_AGENT_2026.md` | 2026-09-22 | (d) `docs/archives/` — dépôt Blue Intelligence | Lecture GenAI du 13 sept. ; le bandeau « autre hackathon » désigne le même événement que le plan du 17 oct., avec une autre fenêtre de code. |
| `docs/archives/PLAN_CHANTIERS_STRUCTURANTS_SIMULATEUR.md` | 2026-09-22 | (d) `docs/archives/` — dépôt NAVIGUIDE | Pointeur vers le plan pipeline, déjà archivé. |
| `docs/archives/PLAN_GENERAL_DEVELOPPEMENT_SIMULATEUR.md` | 2026-09-22 | (d) `docs/archives/` — dépôt NAVIGUIDE | Plan général v2, bandeau réalisé ; décisions de périmètre du 18 sept. |
| `docs/archives/PLAN_IMPLEMENTATION_CLIMATOLOGIE.md` | 2026-09-22 | (d) `docs/archives/` — dépôt Blue Intelligence | Plan du mode climatologie, bandeau réalisé ; la mémoire « swell not shipped » est contredite par le code (voir contradictions). |
| `docs/archives/PLAN_IMPLEMENTATION_EVENEMENTS_ICI_LLM.md` | 2026-09-22 | (d) `docs/archives/` — dépôt NAVIGUIDE | Plan `ici()` et récit, bandeau réalisé ; NVIDIA / Tavily renvoient vers `PLAN_NEMOTRON_NEBIUS_TAVILY.md`. |
| `docs/archives/PLAN_IMPLEMENTATION_FILIERES_CARTO.md` | 2026-09-22 | (d) `docs/archives/` — dépôt Blue Intelligence | Plan des filières carte, hydro et satellite, bandeau réalisé. |
| `docs/archives/PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.en.md` | 2026-09-22 | (d) `docs/archives/` — dépôt NAVIGUIDE | Étape 1 en anglais ; paire du français, pas une copie (45 262 contre 49 169 octets). |
| `docs/archives/PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md` | 2026-09-22 | (d) `docs/archives/` — dépôt NAVIGUIDE | Étape 1 en français, bandeau réalisé (13 sept.). |
| `docs/archives/PLAN_IMPLEMENTATION_SIMULATION_A.md` | 2026-09-22 | (d) `docs/archives/` — dépôt NAVIGUIDE | Horloge climatologique, bandeau réalisé. |
| `docs/archives/PLAN_IMPLEMENTATION_SIMULATION_B.md` | 2026-09-22 | (d) `docs/archives/` — dépôt NAVIGUIDE | Bateau virtuel, bandeau réalisé. |
| `docs/archives/PLAN_IMPLEMENTATION_SIMULATOR_SUIVRE_ET_SIMULATION.md` | 2026-09-22 | (d) `docs/archives/` — dépôt NAVIGUIDE | Deux modes d’avant le renommage Tracer. |
| `docs/archives/PLAN_IMPLEMENTATION_SKIPPER_VIRTUEL.md` | 2026-09-22 | (d) `docs/archives/` — dépôt NAVIGUIDE | Ordres skipper, bandeau réalisé ; confort et ordre vocal notés non faits au 22 sept. |
| `docs/archives/PLAN_LOTS_AGENT_SIMULATEUR.md` | 2026-09-22 | (d) `docs/archives/` — dépôt NAVIGUIDE | Lots P→K, bandeau mergés. |
| `docs/archives/PLAN_PIPELINE_AFFICHAGE_SIMULATEUR.md` | 2026-09-22 | (d) `docs/archives/` — dépôt NAVIGUIDE | Pipeline d’affichage, bandeau réalisé pour le GRIB `pending` et le profil prod. |
| `docs/archives/PLAN_UI_PRODUIT_SIMULATEUR.md` | 2026-09-22 | (d) `docs/archives/` — dépôt NAVIGUIDE | Lots UI 1–9 ; le lot 10 (recalcul public) était hors périmètre. |
| `docs/archives/hackathon-nebius-nvidia.en.md` | 2026-09-22 | (d) `docs/archives/` — dépôt NAVIGUIDE | Cahier Nebius anglais du 13–14 sept., bandeau « remplacé ». |
| `docs/archives/hackathon-nebius-nvidia.md` | 2026-09-22 | (d) `docs/archives/` — dépôt NAVIGUIDE | Cahier Nebius français, remplacé par le plan Nemotron et la soumission Devpost. |
| `docs/archives/nvidia-llm-audit.md` | 2026-09-22 | (d) `docs/archives/` — dépôt NAVIGUIDE | Ancien ordre de repli NIM ; l’ordre vivant est dans `README.md` et `PLAN_NEMOTRON_NEBIUS_TAVILY.md`. |

## 5. `docs/audits`

| Document | Date du commit | Destination | Raison |
|---|---|---|---|
| `docs/audits/2026-09-10-tags.md` | 2026-09-14 | (b) Blue Intelligence | Photo des tags OSM du 10 sept. ; le catalogue vivant est `CATALOGUE_SEAMARK.md`. |
| `docs/audits/2026-09-14-filieres-diagnostic.md` | 2026-09-22 | (b) Blue Intelligence | Diagnostic des filières, vague 0 du plan filières. |
| `docs/audits/CALCULS.md` | 2026-09-20 | (a) NAVIGUIDE | Cahier des calculs et de la parité JS/Python (lot C5) ; antérieur au lot HC1 (ERA5, 14 oct.). |
| `docs/audits/CALCULS_ETAT_DE_L_ART.md` | 2026-09-20 | (a) NAVIGUIDE | Comparaison à l’état de l’art, même date, même réserve HC1. |
| `docs/audits/PROFIL_BUILD_PROD_2026-09-19.md` | 2026-09-22 | (a) NAVIGUIDE | Profil de build du 19 sept. (lot J) ; les secondes mesurées sont celles de ce jour-là. |
| `docs/audits/PROFIL_ZOOM_2026-09-20.md` | 2026-09-22 | (a) NAVIGUIDE | Profil molette du 20 sept. ; les JSON `zoom-profile-before.json` et `zoom-profile-after.json` restent à côté. |

## 6. `docs/recette` (textes)

| Document | Date du commit | Destination | Raison |
|---|---|---|---|
| `docs/recette/lot-d0/liens.txt` | 2026-09-22 | (a) NAVIGUIDE | Reçu du 22 sept. (68 markdown, 0 lien mort) ; le contrôle du 17 oct. trouve un lien mort. |
| `docs/recette/lot-r13/redites-i18n.txt` | 2026-09-21 | (a) NAVIGUIDE | Relevé de libellés répétés dans `src/i18n/fr.js`, lot R13. |
| `docs/recette/lot-r13/redites-panneau-droit.txt` | 2026-09-21 | (a) NAVIGUIDE | Reçu du panneau droit ; mêmes octets que `redites-tracer.txt`, le nom du fichier est la preuve d’écran. |
| `docs/recette/lot-r13/redites-simulation.txt` | 2026-09-21 | (a) NAVIGUIDE | Reçu de l’écran alors nommé Simulation ; mêmes octets que `redites-suivre.txt`. |
| `docs/recette/lot-r13/redites-suivre.txt` | 2026-09-21 | (a) NAVIGUIDE | Reçu de l’écran Suivre, lot R13. |
| `docs/recette/lot-r13/redites-tracer.txt` | 2026-09-21 | (a) NAVIGUIDE | Reçu de l’écran Tracer, lot R13. |

Les 293 JPEG, le KML, le GeoJSON et les JSON de `docs/recette/` restent les preuves des lots. Ils ne sont pas dans le compte des 132.

## 7. `infra`

| Document | Date du commit | Destination | Raison |
|---|---|---|---|
| `infra/agents/GROK_BOT_DEVPOST.md` | 2026-10-15 | (a) NAVIGUIDE | Texte du bot Devpost ; le propriétaire clique Submit. |
| `infra/agents/GROK_BOT_ROUTINE.md` | 2026-09-29 | (a) NAVIGUIDE | Routine de pré-revue du 29 sept. ; le parcours du 16 oct. est `PARCOURS_DE_REFERENCE.md`. |
| `infra/agents/PARCOURS_DE_REFERENCE.md` | 2026-10-16 | (a) NAVIGUIDE | Parcours joué sur la tête de pile ; l’écran source est Suivre / Tracer. |
| `infra/vps/README.md` | 2026-10-16 | (c) les deux — original Blue Intelligence | Runbook OVH (Mongo, nginx, sauvegardes, interdiction Atlas) ; NAVIGUIDE en extrait les unités du simulateur. Le tableau dit encore `~/blue-intelligence-map/`. |
| `infra/vps/ci/README.md` | 2026-09-14 | (b) Blue Intelligence | Sonde de deploy ; User-Agent dédié parce que Cloudflare bloque `Python-urllib`. |
| `infra/vps/seamap/README.md` | 2026-09-14 | (b) Blue Intelligence | Miroir Open Waters Seamap (PMTiles) sur le VPS. |

## 8. `naviguide-simulator` et `naviguide`

| Document | Date du commit | Destination | Raison |
|---|---|---|---|
| `naviguide-simulator/README.md` | 2026-09-22 | (a) NAVIGUIDE | README du simulateur : la première phrase dit « hors production » et une publication « prévue », plus bas le même fichier décrit le deploy CI vers `simulator.naviguide.fr`. |
| `naviguide-simulator/e2e-archive/README.md` | 2026-09-28 | (a) NAVIGUIDE | Pourquoi `l3-juge` et `l4-veille` sont hors de `e2e/` depuis le 28 sept. (PR #401, surfaces retirées). |
| `naviguide-simulator/server/tests/fixtures/official_store.README.md` | 2026-10-15 | (a) NAVIGUIDE | Notice du stock officiel figé (lot RF11). |
| `naviguide-simulator/src/assets/brand/SOURCES.md` | 2026-10-15 | (a) NAVIGUIDE | Sources et règles d’usage des logos, relevé du 15 oct. |
| `naviguide/README.md` | 2026-09-12 | (a) NAVIGUIDE | README de l’ancien planificateur : URL `csw6hpki.run.complete.dev`, cascade qui commence par NVIDIA NIM. |
| `naviguide/naviguide-api/routing_ab/README.md` | 2026-09-14 | (a) NAVIGUIDE | Banc A/B de routage mer (searoute, scgraph) sans changer `GET /route`. |

## 9. Scripts et données Blue Intelligence

| Document | Date du commit | Destination | Raison |
|---|---|---|---|
| `backend/data/climatology/README.md` | 2026-09-14 | (b) Blue Intelligence | Atlas lus par l’API (cyclones, vent, vagues, courant) ; champ absent = null. |
| `scripts/climatology/README.md` | 2026-09-14 | (b) Blue Intelligence | Génération des atlas sur Mac ; le VPS ne fait que servir les fichiers. |
| `scripts/satellite/README.md` | 2026-09-14 | (b) Blue Intelligence | Guide Mac Sentinel (vague 4) ; à lancer sur le Mac, pas sur le VPS. |

## 10. `Archives/` (anciens dépôts, rapatriés le 13 septembre 2026)

Même commit pour tout l’arbre : 2026-09-13. Ces textes restent dans `Archives/`.

| Document | Date du commit | Destination | Raison |
|---|---|---|---|
| `Archives/README.md` | 2026-09-13 | (c) les deux — original NAVIGUIDE | Explique les trois arbres ; NAVIGUIDE garde les paragraphes naviguide, Blue Intelligence reçoit ceux de `Archives/Blue-Intelligence/`. |
| `Archives/Blue-Intelligence/.cursor/plans/wayback_best_captures.md` | 2026-09-13 | (b) Blue Intelligence | Plan Wayback en trois étapes, dans l’archive swarm. |
| `Archives/Blue-Intelligence/README-EN.txt` | 2026-09-13 | (b) Blue Intelligence | README anglais de l’ancien dépôt swarm, figé au rapatriement. |
| `Archives/Blue-Intelligence/README.ARCHIVE.md` | 2026-09-13 | (b) Blue Intelligence | Notice : ancien Blue Intelligence en swarm TypeScript, hors du backend actuel. |
| `Archives/Blue-Intelligence/README.md` | 2026-09-13 | (b) Blue Intelligence | README français court de l’ancien dépôt. |
| `Archives/Blue-Intelligence/README.txt` | 2026-09-13 | (b) Blue Intelligence | README français long, texte différent de `README.md`. |
| `Archives/Blue-Intelligence/data/gshhg/README.md` | 2026-09-13 | (b) Blue Intelligence | Notice du masque terre/mer copié avec l’archive. |
| `Archives/Blue-Intelligence/docs/BLUE_INTELLIGENCE_FIX.md` | 2026-09-13 | (b) Blue Intelligence | Correctif React `insertBefore` de l’ancien flux TinyFish. |
| `Archives/Blue-Intelligence/docs/CRUISERSWIKI_SCRAPING.md` | 2026-09-13 | (b) Blue Intelligence | Procédure CruisersWiki de l’ancien produit. |
| `Archives/Blue-Intelligence/docs/DEPLOIEMENT-VPS-OVH.md` | 2026-09-13 | (b) Blue Intelligence | Ancien guide OVH ; la procédure vivante est `infra/vps/README.md`. |
| `Archives/Blue-Intelligence/docs/EXTRACTION_PACK_WORKFLOW.md` | 2026-09-13 | (b) Blue Intelligence | Pack d’extraction (regex puis Claude) de l’ancien produit. |
| `Archives/Blue-Intelligence/docs/VISION_EXTRACTION_NAUTICALS_HYBRIDE.md` | 2026-09-13 | (b) Blue Intelligence | Même idée : URLs et captures jusqu’aux popups nautiques. |
| `Archives/Blue-Intelligence/docs/WAYBACK_CDX.md` | 2026-09-13 | (b) Blue Intelligence | Modes CDX ; l’historique complet représente des millions de lignes. |
| `Archives/Blue-Intelligence/docs/pitch-blue-intelligence.txt` | 2026-09-13 | (b) Blue Intelligence | Pitch de l’ancien produit ; le pitch GenAI vivant est le plan du 17 oct. |
| `Archives/Blue-Intelligence/public/docs/Blue-Intelligence-MANUAL_EN.md` | 2026-09-13 | (b) Blue Intelligence | Manuel anglais de l’ancienne interface publique. |
| `Archives/Blue-Intelligence/public/docs/Blue-Intelligence-MANUAL_FR.md` | 2026-09-13 | (b) Blue Intelligence | Manuel français de l’ancienne interface, texte différent. |
| `Archives/Blue-Intelligence/public/docs/Blue-Intelligence-README_EN.md` | 2026-09-13 | (b) Blue Intelligence | README anglais publié avec l’ancienne interface. |
| `Archives/Blue-Intelligence/public/docs/Blue-Intelligence-README_FR.md` | 2026-09-13 | (b) Blue Intelligence | README français publié avec l’ancienne interface. |
| `Archives/naviguide-navsecops/.cursor/rules/naviguide-duo-yaml.mdc` | 2026-09-13 | (a) NAVIGUIDE | Règle GitLab Duo de l’ancien dépôt ; elle ne s’applique pas à Cursor actuel. |
| `Archives/naviguide-navsecops/README.md` | 2026-09-13 | (a) NAVIGUIDE | Notice d’archive NavSecOps. |
| `Archives/naviguide-navsecops/README.source.md` | 2026-09-13 | (a) NAVIGUIDE | README d’origine collé dans l’archive ; le lien relatif `LICENSE` ne résout pas. |
| `Archives/naviguide-navsecops/docs/BERRY_MAPPEMONDE_ROUTE_DIGEST.md` | 2026-09-13 | (a) NAVIGUIDE | Digest de route pour ancrer l’ancien agent. |
| `Archives/naviguide-navsecops/docs/CHAT_CONTEXT_SPEC.md` | 2026-09-13 | (a) NAVIGUIDE | Contexte de l’ancien chat skipper ; le chat vivant est celui du simulateur. |
| `Archives/naviguide-navsecops/docs/DATA.md` | 2026-09-13 | (a) NAVIGUIDE | Données hors git ; le lien `../naviguide_workspace/start_local.sh` est absent. |
| `Archives/naviguide-navsecops/docs/MANUAL.md` | 2026-09-13 | (a) NAVIGUIDE | Manuel NavSecOps ; l’écran actuel a `docs/MANUEL_UTILISATEUR.md`. |
| `Archives/naviguide-navsecops/docs/NAVSECOPS_PR_MATRIX.md` | 2026-09-13 | (a) NAVIGUIDE | Matrice de PR de l’ancienne cible NavSecOps. |
| `Archives/naviguide-navsecops/docs/NAVSECOPS_TECHNICAL_ROADMAP.md` | 2026-09-13 | (a) NAVIGUIDE | Feuille de route Route-as-Code (25 053 octets), historique. |
| `Archives/naviguide-navsecops/docs/PLAN_DEV_NOVA.md` | 2026-09-13 | (a) NAVIGUIDE | Copie canonique du plan Nova (SHA-256 identique à la copie nova). |
| `Archives/naviguide-navsecops/docs/SETUP_NOVA_CREDITS.md` | 2026-09-13 | (a) NAVIGUIDE | Copie canonique de la mise en route des crédits Nova. |
| `Archives/naviguide-nova/README.md` | 2026-09-13 | (a) NAVIGUIDE | Différentiel nova (plan dégradé) ; il cite `docs/PLAN_DEV_NOVA.md` à côté de lui. |
| `Archives/naviguide-nova/docs/PLAN_DEV_NOVA.md` | 2026-09-13 | (e) supprimer | Mêmes octets que `Archives/naviguide-navsecops/docs/PLAN_DEV_NOVA.md` (3 063 octets). |
| `Archives/naviguide-nova/docs/SETUP_NOVA_CREDITS.md` | 2026-09-13 | (e) supprimer | Mêmes octets que la copie navsecops (8 072 octets). |

## 11. Synthèse

| Destination | Nombre |
|---|---:|
| (a) dépôt NAVIGUIDE | 46 |
| (b) dépôt Blue Intelligence | 35 |
| (c) les deux | 12 |
| (d) `docs/archives/` | 37 |
| (e) à supprimer | 2 |
| **Total sur `main`** | **132** |

Les 12 communs, et qui garde l’original :

| Original | Documents |
|---|---|
| Blue Intelligence (9) | `.cursor/rules/base-de-donnees-vps.mdc`, `environnement-utilisateur.mdc`, `modeles-cursor-uniquement.mdc`, `reparations-sur-github.mdc`, `README.md`, `docs/HACKATHON_PLAN.md`, `docs/PLAN_SEPARATION_DEPOTS.md`, `docs/REGLES_PARAMETRES.md`, `infra/vps/README.md` |
| NAVIGUIDE (3) | `.cursor/rules/pas-de-verification-video.mdc`, `docs/README.md`, `Archives/README.md` |

Les 37 archives, selon qu’elles sont déjà rangées :

| | Déjà dans `docs/archives/` | Encore à la racine de `docs/`, à y déplacer plus tard |
|---|---:|---:|
| Dépôt NAVIGUIDE | 15 | 17 |
| Dépôt Blue Intelligence | 3 | 2 |
| Total | 18 | 19 |

Les 19 à déplacer (dans une PR ultérieure, pas dans celle-ci) :

- Blue Intelligence : `docs/ETAT_DES_LIEUX_DOCS.md`, `docs/PRD.md`.
- NAVIGUIDE : `docs/PLAN_AUDIT_CALCULS.md`, `docs/PLAN_BATCH_2026-10-14.md`, `docs/PLAN_BATCH_SUIVANT_2026-09-29.md`, `docs/PLAN_CORRECTIONS_2026-09-22.md`, `docs/PLAN_CORRECTIONS_2026-09-23.md`, `docs/PLAN_CORRECTIONS_2026-09-26-s2.md`, `docs/PLAN_CORRECTIONS_2026-09-26-s4.md`, `docs/PLAN_CORRECTIONS_2026-09-27-s5.md`, `docs/PLAN_CORRECTIONS_2026-09-28-film.md`, `docs/PLAN_CORRECTIONS_REVUE_21_SEPT.md`, `docs/PLAN_CORRECTIONS_REVUE_21_SEPT_SOIR.md`, `docs/PLAN_DEUX_MODES_2026-09-29.md`, `docs/PLAN_FILM_REVOIR_EXPEDITION.md`, `docs/PLAN_ICI_JOURNAL_EXPERT.md`, `docs/PLAN_LOTS_COMPLEMENTAIRE_SIMULATEUR.md`, `docs/PLAN_MIGRATION_ANCIEN_NAVIGUIDE.md`, `docs/SPECS_E2E_TRIAGE_2026-09-29.md`.

`frontend/` et `seed/` n’ont aucun markdown. `docs/check_md_links.py` est un outil, pas un document.

## 12. Doublons

Doublons exacts (SHA-256 identique) :

| Fichiers | Octets | Proposition |
|---|---:|---|
| `Archives/naviguide-navsecops/docs/PLAN_DEV_NOVA.md` et `Archives/naviguide-nova/docs/PLAN_DEV_NOVA.md` | 3 063 | Supprimer la copie nova après avoir réécrit le lien de `Archives/naviguide-nova/README.md`. |
| `Archives/naviguide-navsecops/docs/SETUP_NOVA_CREDITS.md` et `Archives/naviguide-nova/docs/SETUP_NOVA_CREDITS.md` | 8 072 | Même traitement. |
| `docs/recette/lot-r13/redites-panneau-droit.txt` et `redites-tracer.txt` | 132 | Garder les deux : chaque nom est le reçu d’un écran. |
| `docs/recette/lot-r13/redites-simulation.txt` et `redites-suivre.txt` | 89 | Garder les deux, même raison. |

Paires de langue, tailles différentes, à garder ensemble : `MANUEL_UTILISATEUR.md` / `USER_MANUAL.md` ; `PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md` / `.en.md` ; `hackathon-nebius-nvidia.md` / `.en.md` ; manuels et README FR/EN dans `Archives/Blue-Intelligence/public/docs/` ; `README.txt` / `README-EN.txt`.

Aucun fichier de ce relevé n’est vide.

## 13. Documents qui se contredisent

1. **Nom du dépôt et nombre de commits.** `PLAN_SEPARATION_DEPOTS.md`, `HACKATHON_PLAN.md` et `PLAN_HACKATHON_GENAI_BLUE_INTELLIGENCE.md` parlent de `Berry-Mappemonde/Blue-Intelligence-Map` et de 1 249 commits au 16 oct. Le remote de ce clone est `Berry-Mappemonde/Blue-Intelligence`. `git rev-list --count HEAD` sur ce `main` donne **1 401** commits.
2. **Fenêtre de code GenAI.** `docs/archives/HACKATHON_OPEN_AGENT_2026.md` retient le 15 octobre 2026 à 09:00 UTC et son bandeau dit « autre hackathon ». `PLAN_HACKATHON_GENAI_BLUE_INTELLIGENCE.md` (17 oct.) retient le 22 octobre 00:00 UTC → 27 octobre 23:45 UTC pour le même événement (hackathon.genai.works). `docs/README.md` reprend le bandeau « Autre hackathon ».
3. **Le mot Simulation.** `README.md`, `docs/MANUEL_UTILISATEUR.md` et `docs/USER_MANUAL.md` décrivent un mode Simulation. `PLAN_DEUX_MODES_2026-09-29.md` décide que la pilule s’appelle Tracer. `PARCOURS_DE_REFERENCE.md` (16 oct.) dit qu’aucun mot « Simulation » ne doit être à l’écran.
4. **Simulateur en ligne.** `README.md` donne `simulator.naviguide.fr` comme adresse du simulateur. `naviguide-simulator/README.md` commence par « Off-production » et « Planned publication », puis décrit le déploiement CI vers la même adresse. Aucune URL n’a été appelée pour cette proposition.
5. **Ancien planificateur.** `naviguide/README.md` (12 sept.) pointe `https://csw6hpki.run.complete.dev` et une cascade qui commence par NVIDIA NIM. `README.md` (15 oct.) pointe `https://www.naviguide.fr` et met Token Factory en tête. Les deux pages n’ont pas été sondées.
6. **Index.** `docs/README.md` a été touché le 17 oct. pour les trois plans hackathon. Sa section « En cours » liste encore des plans du 20–22 sept. Onze fichiers de la racine de `docs/` n’y figurent pas (liste en section 3).
7. **Deux plans pour le même batch.** `PLAN_BATCH_SUIVANT_2026-09-29.md` dit être remplacé par `PLAN_BATCH_2026-10-14.md`. Les deux sont encore à la racine de `docs/`, et aucun n’est dans l’index.
8. **Architecture Blue Intelligence.** `docs/ARCHITECTURE.md` § 1 décrit `server.py` (~1 750 lignes) et `llm_core.py` à la racine de `backend/`. Le § 3 du même fichier dit que le rangement `backend/app/` est appliqué. Constat du 17 oct. : `backend/server.py` fait 5 lignes (shim), `backend/app/main.py` fait 205 lignes, `backend/llm_core.py` est absent, `backend/app/core/llm.py` existe (651 lignes). `frontend/src/components/MapView.js` existe (451 lignes). `docs/PRD.md` décrit encore `llm_core.py` et Emergent.
9. **Où vont les docs au split.** `PLAN_SEPARATION_DEPOTS.md` § 3 garde tout `docs/` dans Blue Intelligence, envoie `Archives/` et `.cursor/` entiers vers NAVIGUIDE, et dit en même temps que NAVIGUIDE emporte les docs du simulateur. Suivre le filtre tel quel met les plans simulateur dans les deux dépôts et envoie `Archives/Blue-Intelligence/` avec NAVIGUIDE.
10. **Cascade des modèles.** `docs/archives/nvidia-llm-audit.md` décrit des replis NIM et porte un bandeau « remplacé ». `PLAN_NEMOTRON_NEBIUS_TAVILY.md` et `README.md` mettent Token Factory en tête. `naviguide/README.md` commence encore par NIM.
11. **Hindcast.** `PLAN_AUDIT_CALCULS.md` (lot C2) décrit une fusion médiane Open-Meteo + Copernicus. `PLAN_BATCH_2026-10-14.md` (HC1) fait venir le passé du bateau d’ERA5 téléchargé une fois. `docs/audits/CALCULS.md` date du 20 sept. Le fichier `naviguide-simulator/server/hindcast.py` existe. L’écart de formule n’a pas été relu ligne à ligne.
12. **Globe et MapLibre.** `docs/README.md` classe `PLAN_GLOBE_3D.md` en « pas commencé ». Aucun fichier `maplibre` sous `naviguide-simulator/`. `frontend/package.json` dépend déjà de `maplibre-gl` 6.13 pour la carte plane Blue Intelligence (`@maplibre/maplibre-gl-leaflet`). Les deux usages sont distincts.
13. **Specs `l3` / `l4`.** `SPECS_E2E_TRIAGE_2026-09-29.md` attribue leur sortie de la CI à RG16. `naviguide-simulator/e2e-archive/README.md` date la sortie du 28 sept. et la motive par R8c et la PR #401. Les deux parlent des mêmes specs.
14. **Chemin sur le VPS.** `infra/vps/README.md` place le code dans `~/blue-intelligence-map/`. `PLAN_SEPARATION_DEPOTS.md` vise `~/blue-intelligence` et `~/naviguide`. Le disque du VPS n’a pas été ouvert. Les deux phrases peuvent décrire l’aujourd’hui et la cible.
15. **Houle.** Le bandeau de `docs/archives/PLAN_IMPLEMENTATION_CLIMATOLOGIE.md` dit « swell not shipped ». `backend/app/services/climatology_wave.py` existe, `backend/app/routers/climatology.py` l’importe, et le simulateur proxifie `/bi/climatology/wave/tiles/…` (`naviguide-simulator/server/tests/test_bi_proxy.py`). L’écran marin n’a pas été ouvert.

## 14. Chemins cités qui n’existent plus

`python3 docs/check_md_links.py` (87 markdown, dossier `Archives/` exclu) : **240 liens, 1 mort**.

- `docs/PLAN_HACKATHON_NEBIUS_NAVIGUIDE.md` → `PLAN_BATCH_2026-10-16.md`, absent de `main`. Le fichier est ajouté par la PR ouverte [#545](https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/545) (`docs/batch-3-plan`).

Contrôle élargi sur les 132 documents, y compris `Archives/` et les liens vers `/cursor/` : **10 cibles absentes**.

- Les 7 liens de `docs/ici-tout.md` vers `/cursor/stores/bc-4aa592e7-…/media/ici-tout-*.json` (artefacts d’éditeur, hors dépôt).
- `Archives/naviguide-navsecops/README.source.md` → `LICENSE` (à la racine du monodépôt : `LICENSE`, `LICENSE-MIT`, `LICENSE-APACHE`).
- `Archives/naviguide-navsecops/docs/DATA.md` → `../naviguide_workspace/start_local.sh`.

Fichiers nommés par `docs/ARCHITECTURE.md` § 1 et absents : `backend/llm_core.py`, `backend/pipeline.py`, `backend/poe.py`, `backend/poe_routes.py`, `backend/geo_core.py`, `backend/ai.py`, `backend/geo.py`. Les équivalents du § 3 existent (contrôle ponctuel : `backend/app/services/poe_pipeline.py`, `backend/app/services/swarm_pipeline.py`, `backend/app/routers/formalities.py`, `frontend/src/components/MapView.js`). `docs/PRD.md` cite la même génération de noms plats.

`scripts/verify_fiche_urls.py` est absent de `main`. Il était ajouté par la PR #227, fermée sans merge (section 15).

À laisser en place tant que le code les cite : `docs/poe-confirmed-gps-audit.md`, `docs/data/poe-confirmed-gps-audit.json`, `docs/data/poe-gps-arbitrated.json`, `docs/data/poe-name-only-33-verifications.json` (`backend/data/run_rules.json`, `backend/app/services/poe_gps_registry.py`, `backend/app/services/poe_name_only_review.py`, `backend/scripts/audit_confirmed_gps.py`).

## 15. Documents hors de `main`

Vérifiés avec `gh` le 17 octobre 2026 au soir. Ils ne sont pas dans les 132.

| PR | État | Fichier | Destination une fois le texte sur `main` |
|---|---|---|---|
| [#545](https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/545) `docs/batch-3-plan` | ouverte | `docs/PLAN_BATCH_2026-10-16.md` | (a) NAVIGUIDE. C’est la cible du lien mort. |
| [#545](https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/545) | ouverte | `.cursor/rules/specs-suivent-l-interface.mdc` | (a) NAVIGUIDE. Un changement de bouton met à jour les specs Playwright dans la même PR. |
| [#510](https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/510) | fermée le 17 oct. 2026 à 19:22 UTC, **sans merge** | `docs/PLAN_CORRECTIONS_2026-10-16-s7.md` | (a) NAVIGUIDE si le propriétaire récupère le texte (lots RJ1–RJ2). |
| [#227](https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/227) | fermée le 17 oct. 2026 à 19:14 UTC, **sans merge** | `docs/VERIFY_FICHE_URLS.md` | (b) Blue Intelligence, avec `scripts/verify_fiche_urls.py`, si le propriétaire rouvre le sujet. |

La carte du matin les présentait comme trois PR ouvertes. Au moment de cette relecture, seules les deux pièces de la #545 sont encore proposées au merge.

La #545 modifie aussi `docs/LOTS_ORDRE_ET_PROMPTS.md` et `docs/REGLES_WORKFLOW_AGENT.md`. La #510 modifiait `docs/LOTS_ORDRE_ET_PROMPTS.md`. Ces diffs n’ont pas été relus ligne à ligne. Plusieurs PR ouvertes de lots simulateur peuvent modifier `infra/agents/PARCOURS_DE_REFERENCE.md` ; ce parcours reste (a).

## 16. Décisions demandées au propriétaire

1. **Nom du dossier d’archive.** La mission parle de `docs/archive/`. Le dépôt a déjà `docs/archives/`. Recommandation : ranger dans le dossier existant, sans en créer un second.
2. **Réaligner le filtre de séparation.** `PLAN_SEPARATION_DEPOTS.md` met tout `docs/` dans Blue Intelligence et tout `Archives/` plus `.cursor/` dans NAVIGUIDE. Ce tableau fait l’inverse pour les plans simulateur, pour `Archives/Blue-Intelligence/` et pour les règles Mongo. Faut-il que la PR du plan de séparation suive ce tableau ?
3. **Nom des dépôts cibles et le chiffre 1 249.** Le remote s’appelle déjà `Blue-Intelligence` et compte 1 401 commits. Quel nom public pour chaque dépôt après le split ?
4. **Fenêtre GenAI à suivre.** Recommandation : celle du plan du 17 oct. (22–27 oct. UTC), et corriger le bandeau « autre hackathon » quand l’archive sera éditée.
5. **Supprimer les deux doublons nova.** `Archives/naviguide-nova/README.md` cite `docs/PLAN_DEV_NOVA.md` à côté de lui. Recommandation : supprimer les deux copies nova seulement après une ligne de renvoi dans ce README. Alternative : garder les deux pour ne pas trouer l’instantané du 13 sept.
6. **Reçus de recette identiques.** Recommandation : garder les quatre `redites-*.txt`. Confirmer.
7. **`FILM_DISCOURS_ETAT_2026-09-28.md`.** Le code cite le fichier. Recommandation : le laisser entier dans NAVIGUIDE. Le scinder (gabarit vivant / photo archivée) demande une édition de `film_script.py` et du test, dans une autre PR.
8. **`WORKFLOW_INDUSTRIEL.md`.** Recommandation : le garder vivant (a) et remplacer le calendrier 28 sept. / 9 oct. par celui des plans hackathon. Alternative : l’archiver (d) si le cycle nuit / matin n’est plus celui du propriétaire.
9. **`REGLES_PARAMETRES.md`.** Recommandation : l’original reste dans Blue Intelligence (le JSON `run_rules.json` et les cahiers le citent). NAVIGUIDE reçoit une copie du principe et des § 3.7 et suivants. Confirmer qu’on ne déplace pas le fichier.
10. **Index et manuels avant le split.** `docs/README.md` ignore onze fichiers. `README.md` et les deux manuels disent encore Simulation. Faut-il une PR de mise à jour avant les déplacements ?
11. **Phrase « en production » du simulateur.** `naviguide-simulator/README.md` dit à la fois hors production et déployé par la CI. Quelle phrase garder ? Aucun site n’a été appelé ici.
12. **URL de l’ancien planificateur.** `www.naviguide.fr` (README racine) ou `csw6hpki.run.complete.dev` (`naviguide/README.md`) ? À trancher par une visite, pas par ce texte.
13. **Où tourne NAVIGUIDE après le split.** `infra/vps/README.md` décrit `~/blue-intelligence-map/` sur le VPS OVH. Le plan de séparation vise `~/blue-intelligence` et `~/naviguide` sur la même machine. Le plan d’avant-split joint évoque Contabo pour NAVIGUIDE. Quelle phrase écrire dans le runbook ?
14. **Houle climatologique.** Le bandeau d’archive dit qu’elle n’est pas livrée ; le backend et le proxy simulateur ont un chemin vague. Faut-il retirer cette mémoire, après un coup d’œil à l’écran ?
15. **Textes des PR fermées.** Récupérer `PLAN_CORRECTIONS_2026-10-16-s7.md` (#510) et `VERIFY_FICHE_URLS.md` (#227) depuis les branches fermées, ou les laisser hors du dépôt ?
16. **`LOTS_ORDRE_ET_PROMPTS.md`.** Recommandation : il reste à `docs/LOTS_ORDRE_ET_PROMPTS.md` dans NAVIGUIDE, y compris les lots déjà mergés, tant que `run_lots.py` lit ce chemin. Confirmer.
17. **Règles communes.** Recommandation : original comme dans la section 1, avec une copie dans l’autre dépôt. Le filtre actuel enverrait les quatre règles communes uniquement à NAVIGUIDE.

## 17. Hors du compte

| Chemin | Rôle |
|---|---|
| `docs/check_md_links.py` | Contrôle des liens relatifs. Exécuté le 17 oct. : 1 lien mort. |
| `docs/data/poe-confirmed-gps-audit.json` | Export machine de l’audit GPS, cité par le script d’audit. |
| `docs/data/poe-gps-arbitrated.json` | Arbitrage GPS, lu par `poe_gps_registry.py`. |
| `docs/data/poe-name-only-33.json` | Export des 33 fiches. |
| `docs/data/poe-name-only-33-verifications.json` | Décisions de revue, lues par `poe_name_only_review.py`. |
| `docs/design_guidelines.json` | Thème du dashboard Blue Intelligence. Suit le frontend BI. |
| `docs/audits/zoom-profile-before.json`, `zoom-profile-after.json` | Chiffres du profil zoom, à laisser avec le markdown. |
| `docs/recette/**` (images, KML, GeoJSON, JSON) | Preuves de lots. |

## 18. Limites

- Les formules de `docs/audits/CALCULS.md` n’ont pas été comparées ligne à ligne à `hindcast.py` après HC1.
- L’écart cahier Review / écran n’a pas été revu dans l’interface.
- Aucune URL publique n’a été appelée. Le VPS n’a pas été ouvert.
- Les diffs des PR ouvertes qui modifient un markdown déjà sur `main` n’ont pas été relus ligne à ligne.
- `frontend/package-lock.json` était déjà modifié dans la copie de travail au début de cette lecture ; il n’entre pas dans cette proposition.
