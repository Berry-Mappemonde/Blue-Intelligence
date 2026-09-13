# Plan pour gagner — Nebius × NVIDIA Global AI Hackathon

**Produit :** NAVIGUIDE Simulator — on rejoue Berry-Mappemonde.  
**Track :** Best Apps and Agents  
**Dossier de code :** `naviguide-simulator/` (à créer, extractible)  
**Chantier immédiat :** [PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md](./PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md)  
**Orientations / crédits :** [hackathon-nebius-nvidia.md](./hackathon-nebius-nvidia.md)

**Deadline soumission :** vendredi 30 octobre 2026, 10:00 PT  
**Jugement :** 1–15 décembre 2026 · résultats vers le 11 janvier 2027  
**IRL :** Builders & Brews **Toronto, mardi 29 septembre 2026**

Version 1.0 — 13 septembre 2026.

Ce n’est pas une soumission Devpost. C’est le plan pour **gagner** : produit, architecture, étapes, vidéo, dépôt.

---

## 0. Thèse — comment on gagne

Les juges vont voir des centaines de chatbots Nemotron. On gagne si, en **20 secondes de vidéo**, ils comprennent :

> Un bateau avance sur une vraie circumnavigation. Il entre dans une ZEE. La carte montre les Ports d’entrée **Gold**. Tavily **revérifie cette fiche**, pas le monde. Nemotron Ultra **barre** ce qui n’est plus prouvé. Le récit vient d’un petit dossier « vu du cockpit », pas de la carte entière.

Quatre preuves, une chacune des critères à poids égal :

| Critère | Notre preuve |
|---|---|
| **Technological Implementation** | Token Factory runtime (pas NIM). Nano / Lightning **racontent**. Ultra **juge**. Tavily **ancré** sur une fiche. |
| **Design** | Un **film** (simulation Leaflet), un **briefing**, des **boutons de couches**. Pas 4 chats, pas la Console BI. |
| **Potential Impact** | Formalités plaisance réelles (ZEE / PoE), expédition Berry-Mappemonde, disclaimer honnête. |
| **Quality of the Idea** | Sac à dos `ici()`, pas un container. Tavily ne cherche pas « ports of entry ». Ultra n’est pas sur chaque clic. |

**Prix visés :** Grand Prize (20 000 $) + bonus Tavily (3 000 $). Un seul bonus : on privilégie Tavily plutôt que City (500 $), tout en allant à Toronto (crédits, mentors, réseau).

**NIM (`integrate.api.nvidia.com`) ne compte pas.** Toute l’inférence de soumission passe par Token Factory + au moins un Nemotron.

---

## 1. Le produit que le juge voit

On **rejoue** Berry-Mappemonde. Le bateau avance.

1. Il **entre dans une ZEE** (polygone déjà dans Blue Intelligence).  
2. Si elle est **Gold** : « Ports d’entrée pour cette zone » + lien officiel.  
3. **Tavily** ne cherche pas le monde : il **revérifie cette fiche** (liste encore bonne ? avis récent ?).  
4. **Ultra** barre ce qui n’est plus prouvé.  
5. La **climatologie** change : l’agent raconte **l’événement** (bulletin, cyclone nommé) — Copernicus reste les chiffres au point.  
6. Il passe près d’une **AMP** ou d’un **projet** : stretch « parc, saison, mouillage » — pas obligatoire pour la première soumission.

Ce n’est plus un chat. C’est un **voyage**.

Le long terme (méga-briefing éco-tourisme + toutes les couches) **est** ce produit : on le **sérialise**. La soumission = le film + le sac + PoE Gold + Tavily/Ultra. Le reste se branche sur le même bouton Briefing.

---

## 2. Architecture verrouillée

```
Skipper (cockpit Leaflet)
        │  bateau sur la route (useLegContext)
        ▼
ici(lat, lon)     ← sac à dos, PAS le globe
        │  1 ZEE, PoE de cette ZEE, 3–5 proches, vent au point…
        ▼
Événement ?  ──non──►  JSON seul (gratuit)
        │ oui
        ▼
Tavily (cette fiche / cet avis)  →  Nano raconte  →  Ultra juge la fiche
        ▼
Panneau Briefing (un récit) + pastilles sur la carte
```

**Film** = deux sidebars NAVIGUIDE, route, bateau, boutons, tracer.  
**Projecteur** = Leaflet (comme Blue Intelligence), plus MapLibre.  
**Légende** = 10 pastilles (ZEE, WPI, Balisage, Projets, Marinas, Capit., PoE, AMP, Science, Climatologie). Plusieurs allumées ensemble.  
**Moteur bateau** = searoute (le trait) + polar (VMG / vitesse), **sans chat**.  
**Moteur situation** = `ici()` — une fonction « qu’y a-t-il ici ? » **avant** Nemotron.  
**Le projet** = un Briefing d’événement, pas 4 agents.

### Sac à dos (contrat)

À la position du bateau (rayon 20–50 nm, et « quelle ZEE contient ce point ») :

| Couche | Dans le sac | Pas ça |
|---|---|---|
| ZEE | 1 polygone, nom, `mrgid`, Gold ou non | Les 285 textes |
| PoE | Ports **de cette ZEE**, URL officielle, statut | Tous les PoE du monde |
| AMP / Projets | Ceux **près** du trait | Tout le catalogue |
| Marinas / capit. / WPI | Les 3–5 plus proches | L’annuaire OSM |
| Balisage | De la zone | Le monde |
| Science | 0 ou 1 jeu localisé | Sextant entier |
| Vent / vague / courant | Chiffres **au point** | Le globe |
| Polaires | Vitesse / ETA **de cette jambe** | La grille 181×61 / le CSV |
| Tavily | Si événement : **cette** fiche ou **cet** avis | Search « ports of entry » |

Les boutons allument toute la couche sur la carte. Le LLM n’en voit qu’une poignée.

### Décisions produit (13 septembre, soir)

| Interdit | Pourquoi |
|---|---|
| 4 chats Ports / Sécurité / Météo / Cruisers | Remplacés par le Briefing |
| Chat polar | Le récit n’est pas un Q&A VMG |
| Import / export GeoJSON / KML | Route = Berry ou crayon + searoute |
| Console / Review / Swarm / 6 modes | UX opérateur BI |
| MapLibre / PMTiles « carte marine » | On change de projecteur |
| Recoller le simulateur à `naviguide-api:8000` | Cassera l’extraction hackathon |
| NIM comme cerveau de soumission | Hors règlement |

**Prod `naviguide.fr` / `blueintelligence.online` intouchées.**

---

## 3. Où ça vit

```
Blue-Intelligence-Map/
├── frontend/ backend/ naviguide/   # PROD — on lit, on n’édite pas
├── naviguide-simulator/            # NOUVEAU — extractible (hackathon)
└── docs/
    ├── PLAN_HACKATHON_GAGNER.md    # ce fichier
    └── PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md
```

Plus tard : `git subtree split` (ou copie propre) vers un dépôt public dédié (README anglais, licence MIT, historique pendant la période). Aucun `import` runtime depuis `../../frontend` ou `../../naviguide`.

---

## 4. Roadmap jusqu’au 30 octobre

| Étape | Quoi | Hackathon | Quand (ordre, pas un calendrier) |
|---|---|---|---|
| **1** | Cockpit : Leaflet, Berry, draw, polar sans chat, 10 boutons, stub `ici()` | Zéro Tavily / Nemotron | **Maintenant** — voir plan étape 1 |
| **2** | Remplir le sac (ZEE, PoE, proches, événement « on entre ») | Toujours pas Tavily | Dès A1–A7 + E1–E5 de l’étape 1 |
| **3** | Gold : route Berry-Mappemonde, voire 285 ZEE (skipper) | Carburant de la démo | En parallèle de 1–2 |
| **4** | Briefing raconte le JSON (texte local d’abord, puis Nano) | Token Factory apparaît | Après sac non vide |
| **5** | Tavily runtime **sur la fiche** de la ZEE courante | Bonus 3 000 $ | Après Gold sur les ZEE de démo |
| **6** | Ultra juge ; stretch AMP ; overlay climat ; vidéo + dépôt | Soumission | Gel avant le 30 octobre |

**Ne pas commencer 5–6 si 1 n’est pas recettable.** Un Nemotron collé sur un cockpit vide = wrapper = Stage 1 fail.

**Toronto (29 sept.) :** montrer le film (étape 1, idéalement sac amorcé). Recueillir feedback. Mentors Token Factory / Tavily.

---

## 5. Étape 1 — poser le cockpit (résumé)

Détail verrouillé : [PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md](./PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md).

**En une phrase :** `naviguide-simulator/` = cockpit NAVIGUIDE (route Berry, tracer, polaires, simulation) sur Leaflet + légende — sans 4 chats, sans chat polar, sans import/export, sans toucher la prod.

**Livrable skipper :**

```bash
cd naviguide-simulator
python3 -m venv .venv && source .venv/bin/activate
pip install -r server/requirements.txt
uvicorn server.main:app --host 127.0.0.1 --port 8010 --reload
# autre Terminal
npm install && npm run dev   # http://localhost:5174
```

On reconnaît NAVIGUIDE. Le bateau avance. Leopard 46 se charge. On trace 3 points searoute. Les pastilles existent. Le dossier cockpit est **presque vide** (honnête). Aucun chat.

**Backend 8010 :** `/route`, polar upload/get/summary (**pas** `/chat`), proxies ZEE/WPI/seamark, `/wind|/wave|/current`. Pas `/agents/*`.

**Critère de sortie :** recettes A1–A7, A11, E1–E5 du plan étape 1. Sinon pas d’étape 2.

---

## 6. Étapes 2 à 6 — ce qu’on livre pour gagner

### Étape 2 — le sac réel (`ici()`)

Route **du serveur simulateur** (pas la prod) : logique « quelle ZEE contient ce point » (shapely / extrait de `zee_crossings`), PoE de ce `mrgid`, 3–5 points dans 30 nm, événement `entered_eez` si le `mrgid` change.

Le Briefing peut déjà **afficher** le JSON en clair (sans LLM). Le juge technique qui ouvre le `<details>` voit le contrat.

### Étape 3 — Gold (travail skipper, hors code simulateur)

Tavily s’appuie sur **votre** carte, pas l’inverse.

- Minimum concours : ZEE de la **route Berry** (et de la jambe de démo) en Gold.  
- Ambition : les **285** si l’accélérateur tient le critère Gold (source + géométrie validées).  
- Un pin Gold **faux** est pire qu’un « probable ». Sinon : statut `accelerated` à côté de Gold.

Le simulateur **lit** `/bi/export/poe.geojson` (ou un export figé dans `public/` pour la démo hackathon autonome).

### Étape 4 — Nano / Lightning racontent

Adaptateur Token Factory **dans le dossier simulateur** (`NEBIUS_API_KEY` en env, jamais git).

- Lightning / Nano : 1 paragraphe skipper FR/EN depuis le JSON `ici()`.  
- Thinking OFF pour le JSON / le texte court.  
- HUD visible : modèle, région, latence, coût.  
- Ultra **pas encore**.

Sans clé : le texte local de l’étape 2 reste. La démo ne doit pas être noire.

### Étape 5 — Tavily, sentinelle de la fiche

Éligibilité bonus : **appel runtime** dans la solution.

| Faire | Ne pas faire |
|---|---|
| Extract (puis Search allowlist) sur **l’URL officielle de la ZEE** | `search("ports of entry")` |
| `time_range=week` pour un avis | `include_answer=true` (court-circuite Nemotron) |
| Research **mini** + `files=[leg.json]` si briefing sourcé | Research `pro` à chaque pas |
| Un run à l’**entrée de ZEE** ou au clic | Un Search à chaque « Suivant » |

Crédits (13 sept.) : Researcher 10 000 + add-on 3 125. Tenir ~30–80 crédits / run démo.

### Étape 6 — Ultra + soumission

- **Un** Ultra par action visible : cite-or-reject sur les PoE extraits. L’UI **montre** Nano « 12 ports » puis Ultra en barre 2.  
- IDs à pinger : `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, `nvidia/Nemotron-3_5-Lightning`, `nvidia/Nemotron-3-Ultra-550b-a55b` (`GET /v1/models?verbose=true`).  
- Deux `base_url` (eu-north1 vs us-central1).  
- Stretch : AMP « parc / saison / mouillage » ; bandeau climatologie.  
- **Pas** ConTree / track Coding en 2ᵉ soumission.  
- Extraire `naviguide-simulator/` → dépôt public, README **anglais**, licence MIT, démo URL, YouTube ≤ 3 min.

---

## 7. Vidéo 3 minutes (script de victoire)

Anglais, YouTube public, **projet qui tourne**. Pas de musique copyright.

| Temps | Plan | Le juge doit lire |
|---|---|---|
| 0:00–0:20 | Problème | Skipper, ZEE, formalités — **pas** un chatbot |
| 0:20–0:45 | Film | Bateau avance (Suivant), entre dans une ZEE, pastilles carte |
| 0:45–1:20 | Gold + Tavily | Fiche PoE + URL ; timeline Search/Extract ; sources .gouv |
| 1:20–1:55 | Ultra | HUD Ultra us-central1 ; **2 ports barrés** (citation absente) |
| 1:55–2:25 | Sac | JSON `ici()` à l’écran (1 ZEE, 4 PoE, 1 AMP, vent) — pas 4500 projets |
| 2:25–2:45 | Token Factory | Split ~90 % Lightning / 10 % Ultra, coût |
| 2:45–3:00 | Impact | Route Berry, disclaimer, repo |

Audio : nommer **Nebius Token Factory**, **Nemotron 3 Ultra vs Nano**, **Tavily on this EEZ fiche**.

---

## 8. Soumission Devpost

- Track **Best Apps and Agents** uniquement.  
- Demo URL du simulateur (VPS **séparé** ou preview — **pas** casser naviguide.fr).  
- Repo **public** + licence MIT visible.  
- README EN : install, où est Nemotron, où Token Factory accélère, où Tavily, **delta vs NAVIGUIDE/BI**.  
- Paragraphe « significantly updated / built during submission period ».  
- Feedback Nebius / NVIDIA (Most Valuable Feedback).  
- Matériel en **anglais**.  
- Testable jusqu’au **15 décembre 2026**.

Check-list anti-disqualification : pas de secrets ; pas de Mongo prod ; attribution VLIZ / OSM ; `NEBIUS_API_KEY` / `TAVILY_API_KEY` hors git.

---

## 9. Crédits et Toronto

| Service | Observé (13 sept.) | Rôle |
|---|---|---|
| Token Factory | ~60 $ + essai | Nano / Lightning / Ultra |
| Tavily Researcher | 10 000 + 3 125 add-on | Sentinelle de fiche |
| Toloka / Tendem | 50 $ + 50 $ | Hors soumission |

Discipline : **un Ultra par action visible**. Tavily **mini**, pas de crawl sans `limit`.

Toronto 29 sept. : film + sac si possible ; pas besoin d’Ultra pour l’IRL.

---

## 10. Recette « on peut gagner »

Un inconnu (juge) doit pouvoir :

1. Ouvrir la démo, reconnaître un **cockpit** (pas une Console).  
2. Avancer le bateau, **voir une ZEE**, des PoE, un lien.  
3. Voir Tavily **sur cette fiche** (sources, pas un slide).  
4. Voir Ultra **contredire** Nano une fois.  
5. Lire dans le README le **sac à dos** (contrat `ici()`).  
6. Relancer le repo avec `.env.example` et deux commandes.

Si l’un manque, on a un beau simulateur, pas encore une soumission gagnante.

---

## 11. Risques qui font perdre

| Risque | Parade |
|---|---|
| Wrapper Nemotron sur NAVIGUIDE tel quel | Dossier neuf + Token Factory au cœur + film |
| 4 chats « en attendant le projet » | Briefing = seul récit |
| Tavily hello-world | Extract de **l’URL Gold** |
| Tout Ultra | HUD split 90/10 |
| Sac = carte entière | `ici()` typé, testé |
| Recoller :8000 / :8001 en dur pour « aller plus vite » | Backend 8010 + `/bi` optionnel ; export figé pour la démo autonome |
| Gold massif faux | Statut honnête ; démo sur ZEE vraiment Gold |
| Vidéo de slides | Bateau qui bouge, popup sources |
| Toucher nginx / VPS prod | localhost puis hébergement **dédié** |
| Commencer l’étape 5 avant l’étape 1 | Critère de sortie étape 1 |

---

## 12. Prochaine action

1. **Skipper :** continuer Gold (route d’abord). Clé `NEBIUS_API_KEY` en env local. Toronto le 29.  
2. **Chantier :** exécuter le plan étape 1 — créer `naviguide-simulator/` (1.0 → 1.9), **sans** ouvrir `frontend/`, `backend/`, `naviguide/` en écriture.

Le code de l’étape 1 commence au premier `package.json` dans `naviguide-simulator/`. Pas avant : ce document et le plan étape 1 sont le contrat.
