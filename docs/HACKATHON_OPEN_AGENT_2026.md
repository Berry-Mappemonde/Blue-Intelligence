# Open Agent Hackathon 2026 — synthèse et plan Blue Intelligence

Document de travail interne. Synthèse de la recherche sur le hackathon
GenAI.Works, du **règlement officiel** (page événement, capture du
13 septembre 2026) et des orientations retenues pour Blue Intelligence /
Berry-Mappemonde.

- Site : https://hackathon.genai.works
- Page événement : https://hackathon.genai.works/event/open-agent-hackathon-2026
- Help Center : https://help.genai.works/en/
- Support (ticket) : https://genai.works/help
- Dernière lecture du règlement : **13 septembre 2026**

Ce document n’est **pas** le code de soumission. Il prépare le hackathon
sans violer la fenêtre de construction (règles 4.1–4.2 et 5.2).

---

## 0. Décision d’horaire — commencer à coder

Deux horaires se contredisent **sur la même page officielle** :

| Source | Début du code |
|---|---|
| Encadré « 6 dates that matter » | 15 octobre 2026, **00:00 UTC** |
| **Règle 4.1** (texte des Official Rules) | 15 octobre 2026, **09:00 UTC** |

**Décision interne jusqu’à clarification Discord :** on commence à
**09:00 UTC le 15 octobre 2026**.

Pourquoi celui-là : si on code dès 00:00 UTC et que 09:00 UTC fait foi,
ces 9 heures de commits sont **inéligibles** (règle 4.2). Si on attend
09:00 UTC et que 00:00 UTC faisait foi, on perd seulement 9 heures, mais
on reste éligible.

Au Québec (heure d’été EDT, UTC−4 jusqu’au 1er novembre 2026) :

**jeudi 15 octobre 2026, 5 h 00 du matin.**

Fin de fenêtre (règle 4.1 + deadline dure du tableau) :
**20 octobre 2026, 23:45 UTC** = **mardi 20 octobre, 19 h 45** au Québec.

Règle **4.3** : les fuseaux n’allongent rien. Tout est en UTC.

### Mail du 13 septembre 2026 — sans réponse

Le 13 septembre 2026 à 16:51 (heure affichée dans la messagerie
de l’expédition), Clément FILISETTI a écrit à
`hackathons@genai.works` pour demander quel horaire fait foi.

**Le message n’est pas arrivé.** Google a renvoyé *Address not found* /
*The email account that you tried to reach does not exist* (SMTP 5.1.3,
13 sept. 2026 13:51 PDT). L’adresse publiée dans la règle **10.3**
(`hackathons@genai.works`) est donc **invalide** à cette date.

Prochaine action : **poser la même question sur le Discord officiel**
(salle de l’événement) et, si besoin, un ticket sur
https://genai.works/help. Garder la réponse écrite.

---

## 1. Qu’est-ce que ce hackathon

Événement **100 % en ligne** organisé par GenAI Works. Gratuit.
Ouvert dès **16 ans** au début de la fenêtre (règle 1.1). Équipes de
**1 à 5**. Un compte par personne : un double compte **disqualifie
toute l’équipe** (1.3).

Le brief : construire un **agent qui fait un vrai travail** pour un
vrai utilisateur, une industrie ou une communauté. Pas un chatbot.
Pas une démo-jouet.

L’agent doit :

1. accéder à de l’information pertinente ;
2. comprendre le contexte et les relations ;
3. raisonner en plusieurs étapes ;
4. garder une mémoire utile ;
5. produire un résultat concret.

Le lieu réel de l’événement est le **Discord** (annonces, salles par
track, Team Finder, mentors, ateliers, résultats). Kickoff, office
hours, judging et résultats sont en ligne. Pas de voyage.

Historique utile de l’organisateur :

- Build with AI 2024 — agents / RAG — 4 511 participants
- #LeadWithAIAgents 2025 — ~3 500 participants, ~200 équipes
- World Wide Vibes 2026 — apps civiques Montgomery

Le bandeau de la page dit **144 hours** ; un footer marketing dit
encore **72 Hours**. Entre le 15 oct. 09:00 et le 20 oct. 23:45 UTC,
compter **environ 139 heures**, pas 72.

---

## 2. Dates, prix, éligibilité

| Élément | UTC | Québec (EDT, UTC−4) |
|---|---|---|
| Fin des inscriptions | **13 oct. 2026, 00:00** (dure) | **lundi 12 oct., 20 h 00** |
| **Début du code (règle 4.1)** | **15 oct. 2026, 09:00** | **jeudi 15 oct., 5 h 00** |
| Ouverture du judging | 20 oct. 2026, 00:00 | lundi 19 oct., 20 h 00 |
| **Fin des soumissions** | **20 oct. 2026, 23:45** (dure) | **mardi 20 oct., 19 h 45** |
| Résultats | 30 oct. 2026, 16:00 | vendredi 30 oct., 12 h 00 |
| Inscrits (13 sept. 2026) | ~1 200 | |
| Format | 100 % en ligne | |
| Taille d’équipe | 1–5 | |
| Cagnotte | jusqu’à **20 000 $** + primes par track | |

Le judging **ouvre avant** la deadline de soumission. En cas d’égalité
d’Impact, c’est l’**heure de soumission** qui départage (règle 7.3) :
soumettre tôt, pas à 19 h 44.

Ancien calendrier encore visible sur Google / article NCSA Illinois
(7–9 octobre, 72 h) : **ne plus s’y fier**.

### Prix globaux (règle 08)

| Place | Montant | Note |
|---|---|---|
| 1er | 8 000 $ | meilleur score toutes tracks + showcase communauté |
| 2e | 4 000 $ | partagé également entre les membres par défaut |
| 3e | 2 000 $ | en cas d’égalité, départage Impact puis timestamp |

- Salariés de l’organisateur ou d’un sponsor-juge : participation OK,
  **pas d’argent** (1.2).
- Virement sous **30 jours** après l’annonce des résultats (8.1) —
  plus court que les vieux T&Cs d’avril 2025 (~3 mois).
- Split égal, sauf accord écrit de l’équipe (8.2).
- Impôts et frais locaux à la charge du gagnant (8.3).
- La France n’est pas un pays sous embargo US. Vérifier tout de même
  l’éligibilité personnelle.

### Propriété intellectuelle (règle 09 — plus protecteur que les T&Cs 2025)

- **9.1** Tu **gardes tous les droits** sur ce que tu construis. Rien
  ne transfère la propriété à l’organisateur ou aux sponsors.
- **9.2** En soumettant, tu donnes à l’organisateur une licence pour
  montrer **démo, captures et description** dans la couverture de
  l’événement.
- **9.3** Les soumissions d’un track sponsor donnent au sponsor la
  même licence promotionnelle, non exclusive.

Les T&Cs génériques d’avril 2025
(https://help.genai.works/en/articles/11051932-hackathon-terms-and-conditions)
parlaient encore d’une licence plus large et d’Oracle DevRel. **Pour
cet événement, c’est la section 09 de la page 2026 qui prime.** On
soumet quand même un **dépôt dédié**, pas le monorepo de production
(secrets, infra VPS, historique).

---

## 3. Tracks

Chaque soumission choisit **exactement un** track principal (3.1).
On peut **changer de track** jusqu’à la deadline (3.2). Un projet
peut toucher plusieurs tracks, mais **ce n’est pas noté deux fois**
(3.3). Le track détermine le panel de juges et l’éventuelle bounty
sponsor.

| # | Track | Brief |
|---|---|---|
| 01 | Enterprise Intelligence | Infos d’entreprise fragmentées → insights, décisions, rapports |
| 02 | Autonomous Investigation | Enquête multi-sources, réponses **avec preuves** |
| 04 | Persistent Memory Agents | Mémoire, état, travail qui continue dans le temps |
| 05 | Real-World Industry Agents | Un métier / une communauté, un problème opérationnel réel |
| 06 | Connected Data Agents | Découverte et requête à travers APIs, bases, systèmes déconnectés |

(Il n’y a pas de track 03 sur la page du 13 septembre 2026.)

---

## 4. Grille de notation — règle 7.1

**100 points** + **jusqu’à 30 points bonus**.

| Critère | Points | Ce que les juges veulent voir |
|---|---|---|
| **Impact** | 30 | Problème réel, utilisateur nommé, résultat utile |
| **Technique** | 20 | Agent multi-étapes + outils, pas un wrapper GPT |
| **Innovation** | 15 | Angle non évident |
| **Démo** | 15 | Vidéo ≤ 3 min : l’agent *fait* le travail |
| **Produit & UX** | 10 | Un non-dev pourrait s’en servir demain |
| **Techno sponsor** | **10** | Stack partenaire vraiment branchée |
| **Bonus** | ≤ 30 | Open source + evals + modes de panne dont les autres peuvent apprendre |

Sans bonus on joue à 100. Avec bonus on joue à 130. Les 30 points
bonus peuvent inverser le classement.

- Au moins **trois juges** par soumission (7.2).
- Les bounties sponsors sont décidées par le panel du sponsor (7.2).
- Égalité : score Impact, puis **timestamp de soumission** (7.3).

Ce qui fait perdre, très souvent :

- chatbot RAG générique ;
- 12 features à 40 %, zéro parcours complet ;
- santé / RH / Jira sans utilisateur ni données réelles ;
- démo qui plante, ou slides sans agent ;
- gros modèle, zéro eval, zéro citation ;
- soumettre l’app Blue Intelligence existante sans nouvel agent ;
- deux comptes, ou code copié sans le déclarer.

---

## 5. Règles officielles (les 10 sections)

### 01 Eligibility

- 1.1 Ouvert dans le monde à toute personne de 16 ans ou plus au
  début de la fenêtre.
- 1.2 Salariés organisateur / sponsors-juges : pas de prix cash.
- 1.3 Un compte par participant. Doublon = équipe entière hors jeu.

### 02 Teams

- 2.1 Un à cinq. Le solo joue dans le **même** classement.
- 2.2 L’équipe **se fige au premier envoi** de soumission ; avant,
  on peut joindre, quitter ou fusionner librement.
- 2.3 Un participant = **une seule** équipe. Un mentor peut conseiller
  plusieurs équipes.

### 03 Tracks

Voir section 3 ci-dessus.

### 04 Build window

- 4.1 Construction : **15 octobre 2026, 09:00 UTC** → **20 octobre
  2026, 23:45 UTC**.
- 4.2 Travail commité **avant** l’ouverture : **inéligible**, sauf
  composants préexistants **clairement déclarés**.
- 4.3 Pas d’extension pour fuseau. Tout est UTC.

### 05 What you can use

- 5.1 N’importe quel langage, framework, modèle ou cloud, y compris
  APIs fermées et crédits sponsors.
- 5.2 Librairies open source préexistantes : OK. **Le code produit
  préexistant doit être déclaré dans le formulaire de soumission.**
- 5.3 Le code généré (IA) est **autorisé et attendu**. On en est
  propriétaire et **responsable**.

FAQ officielle : « Just declare anything pre-existing in your
submission so judges can see what you built during the window. »

### 06 Submission requirements — les trois sont obligatoires

1. Un dépôt **public**, **ou** un dépôt privé avec accès pour le jury.
2. Un **déploiement qui tourne**, **ou** une image conteneur +
   instructions en **une commande**.
3. Une **vidéo de 3 minutes maximum**, **et** une **description
   écrite des modes de panne** trouvés.

`FAILURES.md` n’est plus seulement un bonus : c’est **exigé**. Le
bonus (≤ 30) récompense en plus l’open source, les evals, et la
qualité de cette doc d’échecs.

### 07 Judging

Voir section 4.

### 08 Prizes

Voir section 2.

### 09 Intellectual property

Voir section 2.

### 10 Schedule & changes

- 10.1 L’organisateur peut ajuster le calendrier ; annonces sur la
  page et sur Discord.
- 10.2 Les disqualifications sont définitives, avec un motif au
  team lead.
- 10.3 La page indique `hackathons@genai.works` (réponse sous un
  jour ouvré). **Cette adresse a rejeté le mail du 13 sept. 2026.**
  Utiliser Discord + https://genai.works/help.

---

## 6. Ce qui a déjà gagné chez GenAI.Works

Hackathon **#LeadWithAIAgents 2025** :

1. **Minizica** — a gagné **deux fois**. Pas un chat : une équipe
   d’agents qui automatise un vrai flux métier
   (Jira → GitHub → Confluence), branchée sur **GenAI AgentOS**
   (runtime de l’organisateur), open source.
   Repo : https://github.com/param-kasana/Minizica-genai-agentos
2. **2e** — matching anonyme dossier patient ↔ essais cliniques, avec
   recommandation des essais les plus proches si aucun match.
3. Pattern des projets placés : **plusieurs agents + outils réels +
   un métier précis**, pas « ChatGPT avec une UI ».

Le discours produit de GenAI.Works va dans le même sens : mémoire
persistante, traces d’audit, evals, permissions dans le *harness*
(le cadre autour du modèle), pas seulement un prompt.

---

## 7. Orientations retenues pour Blue Intelligence

### 7.1 Idée à construire (pendant la fenêtre uniquement)

**Un nouvel agent skipper**, pas l’application actuelle recopiée.

- Track principal : **05 Real-World Industry Agents** (maritime /
  plaisance).
- Pied dans **02 Autonomous Investigation** (réponses citées) et
  **06 Connected Data** (APIs / bases déjà en prod) — **sans**
  double score (3.3).
- Un seul utilisateur, un seul livrable.
- Track changeable jusqu’à la deadline si un bounty sponsor colle
  mieux (3.2).

Scénario juge-proof (vidéo ≤ 3 min, viser ~90 s de démo réelle) :

> Un skipper prépare une traversée. L’agent : (1) prend la route,
> (2) croise ZEE et ports d’entrée officiels, (3) flag les AMP et
> les règles de visite, (4) propose marinas / capitaineries avec
> sources, (5) sort un **dossier de formalités avec citations**
> (URL, date, confiance OSM). Il **se souvient** de la route d’un
> jour à l’autre. Il dit clairement ce qu’il **ne sait pas**.

Phrase unique à figer avant le 15 octobre :

*Pour qui ? Quel travail ? Quel livrable ?*

### 7.2 Ce que l’agent n’est pas

- Pas un wrapper autour de `blueintelligence.online`.
- Pas NAVIGUIDE recollé. NAVIGUIDE est un atout (preuve d’un vrai
  utilisateur : expédition Berry-Mappemonde, 36 000+ milles, 45+
  escales) **et** un risque : il fait déjà du briefing multi-agents.
  Le projet hackathon doit faire un travail **visiblement différent**
  (enquête douanes / formalités / AMP, dossier cité, mémoire de
  voyage — ce que NAVIGUIDE ne fait pas).

### 7.3 Où vit le code du hackathon

**Nouveau dépôt dédié, créé le 15 octobre 2026 à 09:00 UTC
(5 h Québec). Pas une branche de `blue-intelligence`.**

Raisons :

1. Soumission publique (ou privée avec accès jury). Le monorepo
   actuel contient des informations d’exploitation (VPS,
   architecture interne). On ne rend pas publique « juste une
   branche ».
2. L’historique git est une preuve. Un premier commit **après**
   09:00 UTC le 15 octobre montre que le projet a été construit
   dans la fenêtre (4.2).
3. Licence MIT/Apache + licence promo GenAI : ça doit couvrir le
   petit dépôt hackathon, **pas** la production.
4. Un juge a quelques minutes. Un dépôt de ~50 fichiers se lit ;
   le monorepo, non.

Schéma :

```
blue-intelligence (privé, prod)
        │
        │  expose des APIs déclarées « préexistantes » (5.2)
        ▼
nouveau dépôt (créé le 15/10 à 09:00 UTC)
        │
        └── agent + evals + FAILURES.md + vidéo + (déploiement ou Docker)
```

Le dépôt hackathon **n’existe pas avant le 15 octobre 09:00 UTC**.
D’ici là, il n’existe que dans des notes hors git de soumission.

### 7.4 Ligne rouge : ce qui compte comme « bosser »

**Interdit avant le 15 octobre 2026, 09:00 UTC** (commits inéligibles
sauf composants déclarés, règle 4.2) :

- écrire le code de l’agent, même un squelette ;
- créer le dépôt hackathon, même « vide » ;
- coder le harness d’evals ;
- écrire les prompts finaux dans des fichiers destinés à la
  soumission.

**Autorisé** (préparation, pas soumission) :

- recherche, croquis, apprentissage des outils / stack sponsor ;
- préparation de nos propres données et services existants sur
  `main` (produit Blue Intelligence, utile même sans hackathon) ;
- notes hors dépôt (scénario, cas d’eval, storyboard vidéo).

**Déclaration obligatoire le jour J (5.2 + FAQ) :** dans le
formulaire **et** le README : *APIs / données Blue Intelligence =
préexistantes ; agent + evals + démo + FAILURES.md = fenêtre.*

La question « peut-on utiliser nos APIs de prod comme outils, en les
déclarant ? » est déjà tranchée par **5.2** : oui, si c’est déclaré.
La question encore ouverte est seulement **l’heure exacte de début**.
La poser sur Discord, pas à `hackathons@genai.works`.

### 7.5 Comment coller à la grille

**Impact (30)**  
Utilisateur nommé (skipper de l’expédition ou plaisancier tiers).
Avant / après mesurable : « 4 heures de recherche douanière →
4 minutes + sources ». Idéalement 2 phrases de témoignage dans la
vidéo.

**Technique (20)**  
Plan → outils (APIs Blue Intelligence, OSM, Ifremer, ProtectedSeas,
etc.) → agrégation → **citations** → action (PDF, GeoJSON,
checklist). Boucle si une source échoue. Pas un seul prompt.

**Innovation (15)**  
Croisement **route × droit d’entrée × AMP × science**, avec
provenance. Pas « cinq agents qui se parlent ».

**Démo (15)**  
Vidéo **≤ 3 min** (règle 6.3), écran réel, zéro slide au milieu :

1. le problème (15 s) ;
2. l’agent **fait** le travail (60–90 s) ;
3. une preuve (citation, trace, eval) ;
4. un échec assumé + la suite.

**UX (10)**  
Un écran qu’un non-dev comprend. Bouton, carte, dossier. Pas un
terminal.

**Sponsor (10)**  
Dès l’annonce Discord : brancher la stack partenaire **pour de vrai**,
même pour un seul outil. Ce n’est plus 5 points : c’est **10**.

**Bonus (≤ 30) + livrable 6.3**

1. licence MIT ou Apache, README propre ;
2. dossier `evals/` : ~20 cas, attendu vs obtenu
   (ex. « ce port est-il un PoE ? ») ;
3. `FAILURES.md` **obligatoire** : ce que l’agent invente, sources
   mortes, hallucinations, garde-fous.

Plus : déploiement live **ou** Docker + une commande (6.2).

### 7.6 Équipe

2 à 4 personnes, idéalement :

- 1 profil produit / métier (le skipper dans la tête) ;
- 1–2 profils build (agent + outils) ;
- 1 profil démo + README + vidéo + `FAILURES.md` (15 + 10 UX,
  souvent négligé).

S’inscrire solo si besoin (FAQ : Team Finder ; la plupart des équipes
se forment le premier soir). Un compte par personne. L’équipe se
fige au **premier** clic de soumission (2.2) : ne pas « soumettre
pour tester » trop tôt si l’équipe n’est pas close.

---

## 8. Préparation jusqu’au 14 octobre

### 8.1 Sur `main` (travail produit légitime)

Ce n’est **pas** le code de soumission. C’est Blue Intelligence qui
devient un meilleur *outil externe* pour l’agent.

**Données — Impact et démo**

- Avancer le backlog déjà listé dans `docs/PRD.md` : ré-import des
  ~695 PoE non géocodés, validation OSM sur les nouveaux, exports
  hebdo à jour.
- Vérifier que les réponses API portent la **provenance** partout
  (`source_url`, date, `osm_confidence`) : c’est ce qui transforme
  une réponse d’agent en réponse prouvée.
- S’assurer que le workflow des releases immuables
  `data-AAAA-MM-JJ` tourne sans erreur d’ici octobre.

**API — Technique**

- La doc OpenAPI existe déjà (`backend/app/main.py`, `/api/docs`).
  Relire les endpoints que l’agent appellera (PoE par ZEE, marinas,
  AMP, capitaineries, profondeur) : descriptions claires, schémas
  propres.
- Décider (et si besoin mettre en place) un **accès lecture seule**
  utilisable de l’extérieur : sous-ensemble d’endpoints, clé API,
  rate-limit, CORS. Pendant le judging (20–30 octobre), une démo
  live peut être ouverte : le VPS doit tenir sans exposer l’admin.
- Document d’inventaire sur `main` (ex. `docs/HACKATHON_OUTILS.md`) :
  liste des APIs / données disponibles comme outils externes, avec
  exemples d’appels. Documentation produit, pas code de soumission.

**Infra**

- Vérifier la rotation des sauvegardes MongoDB quotidiennes du VPS
  (`~/backups/mongodb/`, 14 jours) et faire un test de restauration
  avant octobre. Ne **jamais** lancer `infra/vps/sync-from-atlas.sh`.
- Aucun batch lourd (swarm, validation OSM mondiale) pendant la
  fenêtre de démo / judging.

### 8.2 Hors dépôt

1. S’inscrire **avant le lundi 12 octobre 20 h Québec**
   (13 oct. 00:00 UTC).
2. Rejoindre le Discord (bouton sur la page événement).
3. **Relancer la question d’horaire sur Discord** (le mail à
   `hackathons@genai.works` a échoué).
4. Monter l’équipe (Team Finder).
5. Figer le scénario en une phrase, puis le storyboard minute par
   minute (quelle traversée réelle de l’expédition, avec ZEE / PoE /
   AMP intéressants).
6. Préparer l’histoire Impact (témoignage skipper / plaisancier).
7. Apprendre la stack sponsor dès son annonce (tutos, crédits).
   Apprendre ≠ construire.
8. Lister ~20 cas d’eval **en notes** (pas en code), réponses
   attendues tirées des données Gold.
9. Matériel vidéo : OBS, micro, résolution d’écran propre.
10. Préparer le texte type de déclaration 5.2 (formulaire + README).

### 8.3 Calendrier

| Quand | Quoi |
|---|---|
| Maintenant → fin septembre | Inscription, Discord, question d’horaire, équipe |
| Fin septembre → 10 octobre | Sur `main` : données PoE, provenance, accès lecture seule, doc d’inventaire, test de charge léger |
| 10–14 octobre | Scénario figé, cas d’eval en notes, stack sponsor apprise, setup vidéo, **geler `main`** |
| **15 octobre 09:00 UTC (5 h Québec)** | Création du dépôt, premier commit, construction |
| 15–19 octobre | Cœur de l’agent (preuves, mémoire, multi-sources) |
| Avant-dernier jour | Geler les features ; evals + `FAILURES.md` + Docker ou URL live |
| Dernières 8 h | Vidéo ≤ 3 min, README, soumettre **avant** 20 oct. 19 h 45 Québec |

---

## 9. Pendant la fenêtre — rappel

Jour 1 : scénario + premier outil qui marche de bout en bout.  
Jours suivants : cœur (preuves, mémoire, multi-sources).  
Avant-dernier jour : plus de features ; evals + `FAILURES.md` +
déploiement ou Docker.  
Dernières 8 h : vidéo et soumission, **pas** la dernière minute
(timestamp départage les égalités).

En une phrase : **gagner l’Impact + une démo qui marche + les 10
points sponsor + les 30 bonus**, avec un agent skipper qui enquête
sur formalités / AMP / marinas **avec sources**, mémoire de voyage,
evals et un `FAILURES.md` obligatoire.

---

## 10. Sources

- Page événement / Official Rules (capture 13 sept. 2026) :
  https://hackathon.genai.works/event/open-agent-hackathon-2026
- Mail du 13 sept. 2026, Clément FILISETTI → `hackathons@genai.works`
  (non délivré, adresse inexistante)
- https://hackathon.genai.works
- https://help.genai.works/en/
- https://genai.works/help
- T&Cs génériques (contexte, pas la règle 09 de cet événement) :
  https://help.genai.works/en/articles/11051932-hackathon-terms-and-conditions
- https://github.com/param-kasana/Minizica-genai-agentos
- Posts LinkedIn #LeadWithAIAgents (Minizica 1er ; matching essais
  cliniques 2e)
- Dépôt interne : `README.md`, `docs/PRD.md`, `naviguide/README.md`,
  `backend/app/main.py`
