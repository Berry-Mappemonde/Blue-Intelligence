# Plan d’implémentation — `naviguide-simulator/` étape 1

Document de chantier. Il fige comment poser le dossier dans ce dépôt, et quoi coder en premier.

**Version 3.0 — 13 septembre 2026.**

Plan de victoire (étapes 1–6, soumission, vidéo) : [PLAN_HACKATHON_GAGNER.md](./PLAN_HACKATHON_GAGNER.md).

Les étapes 2 à 6 (sac réel, événements ZEE, Gold, Tavily, Nemotron) sont rappelées pour **ne pas les commencer trop tôt**. Elles ne sont pas livrées ici.

---

## Ce que la 3.0 change par rapport à la 2.0

Le skipper a tranché le cockpit : on garde le moteur bateau et le film, on retire ce que le projet (briefing / sac `ici()`) va remplacer, et ce qui ne sert pas à une expédition simulée.

| Décision 2.0 (annulée) | Décision 3.0 (celle-ci) |
|---|---|
| Polar chat (`POST /polar/chat`, `PolarChatSection`) | Polar moteur + upload + VMG seulement. Le récit = le projet |
| 4 chats simulation (Ports / Sécurité / Météo / Cruisers) | Interdits. `AgentPanel` et `/agents/*` ne se copient pas |
| Import GeoJSON / KML + export GeoJSON / KML | Interdits. La route perso = draw + searoute |
| Backend qui recopie les 4 agents SSE | Backend = searoute + polar (sans chat) + proxies + vent |

**Ce qui ne change pas depuis la 2.0 :**

- sous-dossier extractible, Leaflet (plus de MapLibre) ;
- prod `naviguide.fr` / `blueintelligence.online` intouchées ;
- searoute pour Berry et pour « draw your own route » ;
- polar engine complet (parse, grille 181×61, VMG, upload) ;
- UI / UX NAVIGUIDE sauf les exclusions ci-dessus ;
- `ici()` encore un sac vide (étape 2).

---

## Sommaire

1. En une phrase  
2. Pourquoi cette étape existe  
3. Contrat skipper (dans / hors)  
4. Vocabulaire  
5. Décisions d’architecture (verrouillées)  
6. Arborescence cible  
7. Copier / adapter / inventer / jeter  
8. Backend du simulateur  
9. Polar engine (sans chat)  
10. UI / UX NAVIGUIDE (ce qui reste)  
11. BerryCard sans import  
12. Carte Leaflet et panes  
13. Film Berry : searoute, bateau, fallback  
14. Draw your own route  
15. Boutons de couches  
16. Stub `ici()`  
17. Données, ports, variables  
18. Ordre de chantier (1.0 → 1.9)  
19. Fichiers touchés / interdits  
20. Recette  
21. Risques  
22. Passage à l’étape 2  
23. Documents et fichiers dont ce plan hérite  

---

## 1. En une phrase

Créer `naviguide-simulator/` dans ce dépôt : le cockpit de NAVIGUIDE (route Berry, tracer sa route, polaires, simulation), projeté sur une carte Leaflet avec les boutons de couches — **sans** les 4 chats, **sans** chat polar, **sans** import/export de fichiers, **sans** toucher `naviguide.fr` ni `blueintelligence.online`.

---

## 2. Pourquoi cette étape existe

Le produit hackathon, ce n’est pas un deuxième Blue Intelligence. C’est le **film** : le bateau avance, on voit la carte du cockpit, et plus tard un petit dossier « vu d’ici » nourrit un récit.

Sans l’étape 1, il n’y a ni cockpit, ni position, ni boutons. Le moteur `ici()` (étape 2) n’aurait rien autour de quoi travailler.

Les 4 chats et le chat polar sont l’ancien cockpit parlé. Le projet les remplace. Les copier maintenant, c’est reconstruire ce qu’on a décidé d’abandonner.

L’import / export GeoJSON / KML sert l’opérateur. Ici la route vient de Berry ou du crayon + searoute.

L’étape 1 **n’appelle pas** Tavily ni Nemotron. Elle prépare :

- le projecteur (Leaflet + légende) ;
- le film (route Berry, bateau, tracer) ;
- le moteur bateau (searoute + polar), pour que l’ETA et le trait soient ceux du skipper, pas une ligne droite à 7 nœuds ;
- un emplacement Briefing (texte local), prêt à recevoir le récit.

---

## 3. Contrat skipper (dans / hors)

### On livre

À la fin de l’étape 1, en local :

```bash
cd naviguide-simulator
python3 -m venv .venv && source .venv/bin/activate
pip install -r server/requirements.txt
uvicorn server.main:app --port 8010 --reload   # un Terminal
npm install && npm run dev                     # un autre Terminal
```

Ouvrir http://localhost:5174. On reconnaît NAVIGUIDE, sur Leaflet :

- Deux panneaux 320 px : gauche (expédition) et droite (langue, thème, stats, polaires). FR / EN, sombre / clair.
- BerryCard : route Berry, draw your own route, continuer, terminer, supprimer, bascule Berry ↔ perso. **Pas** de boutons GeoJSON / KML.
- Route Berry calculée jambe par jambe via searoute (même logique d’escales que `App.jsx` : overland Berry↔La Rochelle, skip Marigot / Halifax, Halifax↔SPM maritime, Cayenne→Papeete). Spinner + pastille de progression.
- Mode simulation : Précédent / Suivant, bateau collé à la route (`useLegContext`), drag, flyTo. **Pas** d’`AgentPanel`.
- Polar engine complet : CSV Leopard 46 chargé tout seul, drop PDF / CSV / XLSX, grille 181×61 côté serveur, tableau VMG. **Pas** de chat polar.
- Draw your own route : clics carte → `GET /route` searoute (pas une corde), undo / redo, bandeau vert, Terminer → la route devient active.
- Dix boutons de couches (ZEE, WPI, Balisage, Projets, Marinas, Capit., PoE, AMP, Science, Climatologie) — dessin Leaflet, plusieurs allumées ensemble.
- Clic route → vent / vague / courant au point (`POST /wind|wave|current`).
- Briefing unique (cache local 24 h, orchestrateur optionnel, sinon texte local / hint de tracé). C’est l’emplacement du projet.
- Stub `ici()` branché à chaque pas (JSON typé, encore vide côté ZEE).
- `README.md` du dossier : lancer, ports, « prod intouchée », ce qui n’existe pas encore.

Si le backend simulateur est éteint : la route Berry se dessine quand même depuis `public/route.geojson` (copie interne de `backend/data/route.geojson`). Ce fichier n’est **pas** un import skipper. Le tracer, le polar et les proxies ZEE / WPI affichent une erreur honnête. Le film ne doit pas être noir.

La prod ne change pas.

### On ne livre pas

| Interdit en étape 1 | Pourquoi |
|---|---|
| 4 chats Ports / Sécurité / Météo / Cruisers (`AgentPanel`, `/agents/*`) | Remplacés par le projet (briefing / `ici()`) |
| Chat polar (`PolarChatSection`, `POST /api/v1/polar/chat`) | Le récit n’est pas un Q&A sur le tableau VMG |
| Import GeoJSON / KML (`parseGeoJSON`, `parseKML`, inputs fichier) | Inutile : Berry ou crayon |
| Export GeoJSON / KML (`buildGeoJSON`, `buildKML`, boutons Télécharger) | Inutile dans ce projet |
| Console, Review, Swarm, 6 modes opérateur | UX Blue Intelligence, pas le cockpit |
| Carte MapLibre / fond PMTiles « carte marine » | On change de projecteur |
| Isochrones weather-routing (port 3010) | Autre moteur, pas déployé en prod |
| Orchestrateur LangGraph **dans** le dossier | Le briefing appelle l’existant s’il tourne ; sinon texte local |
| `polar_agent.py` (Deploy AI / Claude Opus) | Chemin mort |
| Tavily, Nemotron, Token Factory | Étapes 5–6 |
| Requêtes spatiales « dans cette ZEE / 30 nm » | C’est `ici()` réel = étape 2 |
| Imports / exports opérateur BI | On lit les mêmes URLs, on n’écrit rien |
| Modifier `frontend/`, `backend/`, `naviguide/`, `infra/vps/` | La prod ne bouge pas |
| `react-leaflet` | Les hooks BI parlent à un `L.Map` nu |
| `searoute-js` (npm, jamais utilisé dans `App.jsx`) | Le moteur réel est Python `searoute==1.4.3` |
| `llm_cascade.py` | Plus de chat polar ni d’agents dans ce dossier |
| Coller 4 500 projets dans un prompt | Le LLM du sac n’existe pas encore ici |

### Nuance GeoJSON (à ne pas confondre avec l’import/export skipper)

| Oui (interne) | Non (skipper) |
|---|---|
| `customRoute` = FeatureCollection en mémoire après « Terminer » | Ouvrir un `.geojson` / `.kml` depuis le disque |
| `public/route.geojson` = secours si searoute est down | Bouton « Exporter » / « Importer » |
| Couches carte lues en GeoJSON (`/bi/export/*`) | Télécharger la route affichée |

---

## 4. Vocabulaire

| Mot | Sens ici |
|---|---|
| Film | Ce que le skipper voit : deux sidebars, route, bateau, boutons, tracer |
| Projecteur | La carte : Leaflet, plus MapLibre |
| Légende | Les pastilles ON/OFF (ZEE, WPI, Balisage, …) |
| Moteur bateau | searoute (le trait) + polar (la vitesse / le VMG) |
| Le projet | Plus tard : récit d’événement depuis `ici()`. En étape 1 : un panneau Briefing |
| Sac à dos / `ici()` | Petit JSON autour du bateau. Étape 1 = sac vide (sauf éventuellement nom du bateau si polar chargé) |
| Route officielle (fallback) | `backend/data/route.geojson` → `public/route.geojson` si searoute est down. Pas un import |
| Escale | Stop avec drapeau (La Rochelle, Ajaccio…). Un point intermédiaire n’en est pas une |
| Gold | Fiche Formalités relue. Inutile à l’étape 1 |
| Prod | `blueintelligence.online` et `naviguide.fr` |

---

## 5. Décisions d’architecture (verrouillées)

### 5.1 Un sous-dossier, pas un fork

```
Blue-Intelligence-Map/
├── frontend/                 # prod BI — interdite
├── backend/                  # prod API — interdite
├── naviguide/                # prod NAVIGUIDE — interdite
├── naviguide-simulator/      # NOUVEAU, extractible plus tard (hackathon)
└── docs/PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md
```

Plus tard : `git subtree split` (ou copie propre) vers le dépôt hackathon. Donc **aucune** import runtime du style `../../frontend/src/...` ou `../../naviguide/...` : on copie les modules, on n’attache pas les deux apps.

### 5.2 Pile technique

| Choix | Comme… | Pas comme… |
|---|---|---|
| Vite 7 + React 19 + Tailwind 4 | `naviguide/naviguide-app` | CRA de `frontend/` |
| Leaflet 1.9 nu (`L.map`) | `frontend/src/components/MapView.js` | MapLibre / react-map-gl |
| FastAPI dans le dossier (`server/`, port 8010) | extraits de `naviguide-api` + `polar_api` sans chat | appeler la prod, ports 8000 / 8004 |
| Port Vite 5174 | — | 5173 (NAVIGUIDE) et 3000 (CRA) |
| FR d’abord, EN ensuite | i18n NAVIGUIDE (clés utiles) | clés amputées au hasard |

Leaflet sans `react-leaflet` : Blue Intelligence crée déjà la carte à la main.

### 5.3 Route : searoute d’abord, GeoJSON officiel en secours

NAVIGUIDE aujourd’hui appelle `GET /route?start_lat=…` jambe par jambe (`App.jsx` ~L.523–676, lots de 4). C’est searoute + évitement des terres (`searoute_with_exact_end` → `avoid_land` → densify → sanitize).

L’étape 1 refait ce film :

- Les stops viennent de `ITINERARY_POINTS` (copie de `naviguide-app/src/constants/itineraryPoints.ts`).
- Les jambes sont les mêmes (skip Marigot / Halifax / SPM / Cayenne, inserts, overland Saint-Maur↔La Rochelle).
- Chaque jambe maritime = `GET /route` du backend **simulateur**.
- Orientation A→B (`orientCoords`) : searoute peut renvoyer B→A.
- Si le backend est down ou qu’une jambe échoue : fallback `public/route.geojson` via `routeFromOfficial.js`.

On **ne proxy pas** vers `:8000` « pour aller plus vite ».

### 5.4 Polar : le moteur vivant, pas le chat

| Fichier source | Rôle | Étape 1 |
|---|---|---|
| `naviguide/polar_agent/polar_engine.py` | Parse, interpolation, grille 181×61, VMG | Oui |
| `polar_api/main.py` — upload, GET `/{id}`, GET `/{id}/summary` | Persistance + résumé | Oui |
| `polar_api` — `POST /chat`, prompts | Q&A LLM | Non |
| `Sidebar.jsx` — `PolarChatSection` | UI chat | Non |
| `ExportSidebar.jsx` — drop + tableau VMG + auto-Leopard 46 | UI moteur | Oui |
| `polar_agent.py` | Deploy AI, Claude Opus | Non |
| `llm_cascade.py` | Cascade NIM | Non |

Le front ne télécharge pas la grille 181×61 : seulement `vmg_summary` (TWS 8 / 10 / 12 / 16 / 20 / 25).

ETA du film : `useLegContext` reste à 7 kt tant qu’il n’y a pas de vent au point. Dès que `POST /wind` répond, on lit `polar.speed(twa, tws)` et on passe `speedKnots` au hook. Sans polar chargé : 7 kt. Pas d’isochrone weather-routing.

### 5.5 Couches : mêmes URLs, nouveau dessin, pas les hooks « un mode »

Blue Intelligence n’affiche qu’un mode à la fois. On **ne les importe pas**. On vole styles / panes / popups / canvas, on réécrit la colle : bouton ON → fetch une fois → `map.addLayer`. Plusieurs couches allumées ensemble.

### 5.6 Simulation : comme NAVIGUIDE, sans les 4 agents

OFF au chargement. ON → `SimulationPanel` uniquement. Pas d’onglets Ports / Sécurité / Météo / Cruisers.

### 5.7 Un backend dans le dossier

Un seul FastAPI (`server/`, 8010) :

- `/route` (searoute + avoid-land) ;
- `/api/v1/polar/upload`, `GET /{id}`, `GET /{id}/summary` ;
- `/proxy/zee/wms`, `/proxy/zee`, `/proxy/ports`, `/proxy/seamark` ;
- `/wind`, `/wave`, `/current` (Copernicus si identifiants, sinon `_sim_*`).

Pas `/agents/*`. Pas `/api/v1/polar/chat`. Pas de second uvicorn polar sur 8004.

---

## 6. Arborescence cible

```
naviguide-simulator/
├── README.md
├── package.json                 # name: naviguide-simulator
├── vite.config.js               # port 5174, proxy /route /proxy /api /bi /wind…
├── index.html
├── public/
│   ├── route.geojson            # fallback interne
│   ├── Leopard46_Standard_Sails.csv
│   └── logo-*.png / flags/
├── server/
│   ├── requirements.txt
│   ├── main.py
│   ├── route_engine.py
│   ├── polar_engine.py
│   ├── polar_api.py             # sans chat
│   ├── mem_limits.py
│   ├── copernicus/
│   ├── polar_data/              # gitignore
│   └── geo_data/                # optionnel
├── src/
│   ├── main.jsx
│   ├── App.jsx
│   ├── engine/ici.js
│   ├── hooks/                   # useLegContext, useSimulatorMap, useMarkerOffsets
│   ├── layers/
│   ├── components/
│   │   ├── Sidebar.jsx          # PAS PolarChat ni AgentPanel
│   │   ├── ToolsSidebar.jsx     # PAS export
│   │   ├── SimulationPanel.jsx
│   │   ├── LayerFichePopup.jsx
│   │   ├── CatamaranMarker.js
│   │   └── WindDirectionArrow.jsx
│   └── utils/                   # PAS parse/build GeoJSON/KML
└── src/**/*.test.js
```

`ToolsSidebar.jsx` = `ExportSidebar.jsx` sans la section Télécharger. On ne crée pas `AgentPanel.jsx`.

---

## 7. Copier / adapter / inventer / jeter

### On copie (presque mot pour mot)

| Source | Destination | Note |
|---|---|---|
| `hooks/useLegContext.js` + tests | `src/hooks/` | Zéro API |
| `utils/simulationRoute.js`, `geo.js`, `escales.js`, `customRouteBriefing.js`, `waypointsFromCollection.js` + tests | `src/utils/` | `waypointsFromCollection` sert le Terminer du crayon |
| `SimulationPanel.jsx` | idem | |
| `i18n/fr.js`, `en.js`, `LangContext.jsx` | `src/i18n/` | Clés mortes OK |
| `constants/itineraryPoints.ts` + flags | `src/constants/` + `public/flags/` | `.js` suffit |
| `polar_engine.py` | `server/polar_engine.py` | |
| `polar_api/main.py` : upload / get / summary | `server/polar_api.py` | Couper le chat |
| `naviguide-api/main.py` : searoute, proxies, wind | `server/` | Extraire, pas 1500 lignes d’un bloc ; pas `/agents` |
| `frontend/.../map/constants.js`, `layerOrder.js`, `points.js` | `src/layers/` | + `TILE_URLS.light`, pane `boat` |
| `backend/data/route.geojson` | `public/route.geojson` | fallback interne |
| Leopard 46 CSV + logos | `public/` | |

### On adapte

| Idée prise chez | Ce qu’on change |
|---|---|
| `App.jsx` (~1800 lignes) | Même état route / draw / sim / briefing. Retirer l’import fichier. `<Map>` MapLibre → `useSimulatorMap` |
| `Sidebar.jsx` | BerryCard sans fichiers. Pas de PolarChat. Pas d’AgentPanel |
| `ExportSidebar.jsx` | → `ToolsSidebar.jsx` : jeter download / buildGeoJSON / buildKML |
| `CatamaranMarker.jsx` | `L.marker` + `L.divIcon` |
| `useMarkerOffsets` | `latLngToLayerPoint` |
| `MaritimeLayers.jsx` | hooks Leaflet + Science + Climatologie |
| Fetch polar | `VITE_API_URL=''` + proxy Vite, plus `localhost:8004` |

### On n’invente pas

Pas de nouveau format de route. Pas de nouvelle API publique prod. Pas de nouveau modèle Gold. Le stub `ici()` fixe la forme du JSON pour l’étape 2.

### On jette (ne pas copier, même « pour plus tard »)

- `AgentPanel.jsx`, `naviguide-api/agents/`
- `PolarChatSection` / `PolarChatBubble`
- `parseGeoJSON`, `parseKML`, `buildGeoJSON`, `buildKML`, `downloadFile`
- `polar_api` : `polar_chat`, prompts, fallback LLM
- `llm_cascade.py`, `polar_agent.py`

---

## 8. Backend du simulateur

Fichier unique `server/main.py`, port **8010**.

### 8.1 `GET /route`

Contrat identique à `naviguide-api` :

```
GET /route?start_lat=&start_lon=&end_lat=&end_lon=&check_wind=false
→ Feature | FeatureCollection
```

Pipeline : `sr.searoute` → préfixer/suffixer si > 1 km → `avoid_land` → densify 75 km → sanitize → second `avoid_land` → cache bidirectionnel.

Sans shapefiles NE : `global_land_mask` suffit. **Interdit** : charger `eez_world_map.geojson` (18 Mo) « pour aider searoute ».

### 8.2 Polar

Monté sous `/api/v1/polar/*` **sans** `/chat`. Voir §9.

### 8.3 Proxies et Copernicus

Copies de `naviguide-api/main.py` : `/proxy/zee/wms`, `/proxy/zee`, `/proxy/ports`, `/proxy/seamark/{z}/{x}/{y}.png` (repli ; le front essaie d’abord `tiles.openseamap.org`). `POST /wind|/wave|/current` — Copernicus si identifiants, sinon `_sim_*`.

### 8.4 Le backend n’expose pas

`POST /agents/*`, `POST /api/v1/polar/chat`, `POST /simulation/position` (le snap vit dans `useLegContext`).

---

## 9. Polar engine (sans chat)

Préserver : `PolarData.speed(twa, tws)`, `optimal_upwind` / `downwind` / `gybe`, `summary()` pour TWS 8–25, `generate_full_grid()` → 181×61, parse CSV / Excel / PDF / texte.

Dépendances : numpy, pandas, openpyxl, pdfplumber ; pytesseract + pdf2image optionnels. PDF image sans Tesseract → 422 honnête.

| Méthode | Chemin | Rôle |
|---|---|---|
| POST | `/api/v1/polar/upload` | multipart + `expedition_id` + `boat_name` |
| GET | `/api/v1/polar/{id}` | grille (le front ne la télécharge pas pour l’UI) |
| GET | `/api/v1/polar/{id}/summary` | VMG seul |

`expedition_id` défaut : `berry-mappemonde-2026`. Stockage : `server/polar_data/` (gitignore).

UI droite : auto-fetch Leopard 46, drop, tableau VMG. **Aucun** champ Chat.

Tests : `server/tests/test_polar_engine.py` (parse, `speed(90, 12) > 0`, summary, shape 181×61, TWA 0 → 0). Recette négative : `POST /chat` → 404.

---

## 10. UI / UX NAVIGUIDE (ce qui reste)

### 10.1 Colonne gauche — `Sidebar.jsx` (320 px)

1. Logo NAVIGUIDE  
2. BerryCard (sans GeoJSON / KML)  
3. Pastilles de couches  
4. Bouton simulation  
5. Si ON : `SimulationPanel` seulement  
6. Encadré « Pour commencer » s’il n’y a pas encore de plan  
7. Briefing  

Pas de Polar Chat entre 6 et 7. Toggle flottant `left-4` / `left-[322px]`.

### 10.2 Colonne droite — `ToolsSidebar.jsx` (320 px)

FR / EN, sombre / clair (Esri dark/light), stats de route, drop polaire + VMG. **Pas** de Télécharger.

### 10.3 Chrome carte

Overlay calcul des routes, pastille `routesProgress`, bandeau de tracé (undo/redo), drapeaux d’escales, popup satellite (Vent / Vague / Courant), popup fiche couche, édition nom d’un waypoint tracé.

### 10.4 Briefing — l’emplacement du projet

Berry : `POST …/expedition/plan/berry-mappemonde` **si** `VITE_ORCHESTRATOR_URL` répond ; sinon cache 24 h ; sinon « Pour commencer ».  
Perso : `POST …/expedition/plan` 8 s max, sinon `buildLocalCustomBriefing`.

On **ne copie pas** `naviguide_orchestrator/`. On n’ajoute pas 4 onglets pour remplir le vide.

---

## 11. BerryCard sans import

| État | Affichage |
|---|---|
| `berry-active` | Logo Berry + Dessiner votre route |
| `draw-mode` | Switcher s’il existe une perso ; Terminer ; pas de fichiers |
| `file-active` | Switcher Berry \| Route perso ; Continuer ; Supprimer |
| `berry-active-file-loaded` | Switcher (Berry allumé) + lien pour retracer |

Clic « Dessiner » → `onDrawStart` (pas d’`<input type="file">`). Terminer → FeatureCollection **mémoire**. Nom interne préféré : `drawnRoute`.

---

## 12. Carte Leaflet et panes

```js
L.map(el, {
  center: [22, 5],
  zoom: 3,
  zoomSnap: 0.25,
  minZoom: 2,
  maxZoom: 18,
  worldCopyJump: true,
});
```

Fond : `TILE_URLS.dark` par défaut, `.light` si `isLightMode`. Pas de MapLibre, pas de PMTiles.

| Pane | z-index | Contenu |
|---|---|---|
| tilePane | 200 | Fond Esri |
| zee-wms | 250 | Tuiles ZEE |
| balisage | 260 | OpenSeaMap |
| route | 380 | Polyligne Berry / perso / tracé |
| amp | 420 | Polygones AMP |
| points canvas | renderer | projets, marinas, … |
| markerPane | 600 | drapeaux, WPI |
| boat | 620 | catamaran |
| popupPane | 700 | popups |

Test `panes.test.js` (discipline de `layerOrder.test.js`). `flyTo` : **`[lat, lon]`** (Leaflet). CSS : `leaflet/dist/leaflet.css`. Pas d’icône par défaut Leaflet (`divIcon` / `circleMarker`).

---

## 13. Film Berry : searoute, bateau, fallback

`src/utils/berryLegs.js` : même `useEffect` que `App.jsx` L.523–676 (`nonMaritimeNames`, `skipFromNames`, inserts, `SEGMENT_BATCH_SIZE = 4`, `orientCoords`, `check_wind: false`).

Fallback `routeFromOfficial.js` si toutes les jambes du premier lot échouent. Bandeau : « Route officielle (searoute indisponible) ».

Simulation :

```
segments + stops → buildSimTargets() → simulationStartPos()
  → useLegContext(..., speedKnots, simulationStep)
```

`speedKnots` : 7, ou polar×vent si les deux sont là.

---

## 14. Draw your own route

Contrat = `App.jsx` L.287–445. Clic 2+ → `GET /route`. Undo/redo. Terminer → trait bleu + `customRoute`. Si searoute échoue : pointillés orange « corde temporaire », on n’abandonne pas le tracé.

Aucun import `.geojson` / `.kml`.

---

## 15. Boutons de couches

Même UI que `Sidebar.jsx` L.502–531. NAVIGUIDE a 8 pastilles ; le simulateur en ajoute Science + Climatologie.

| Clé | Libellé | Couleur | Source | Défaut |
|---|---|---|---|---|
| zee | ZEE | `#0e7490` | WMS VLIZ `/proxy/zee/wms` | ON |
| wpi | Ports WPI | `#f59e0b` | `/proxy/ports` | OFF |
| balisage | Balisage | `#10b981` | OpenSeaMap (proxy en repli) | OFF |
| projects | Projets | `#06b6d4` | `/bi/export/geojson` | OFF |
| marinas | Marinas | `#ef4444` | `/bi/export/marinas.geojson` | OFF |
| capitaineries | Capit. | `#7dd3fc` | `/bi/export/capitaineries.geojson` | OFF |
| poe | PoE | `#d97706` | `/bi/export/poe.geojson` | OFF |
| amp | AMP | `#22c55e` | `/bi/amp?bbox=` | OFF |
| science | Science | `#a78bfa` | `/bi/export/science.geojson` | OFF |
| climatology | Climat | `#38bdf8` | aucun fetch — bandeau stub | OFF |

Fetch au premier ON ; AMP bbox debounce 420 ms ; marinas / projets en canvas ; ZEE = WMS limites, **pas** le GeoJSON 18 Mo ; climatologie = pastille + bandeau (« régime de vent : étape 6 »).

---

## 16. Stub `ici()` — le sac vide

Fichier : `src/engine/ici.js`.

```js
export const ICI_RADIUS_NM = 30;

export function emptyDossier(lat, lon) {
  return {
    version: 1,
    at: { lat, lon },
    radiusNm: ICI_RADIUS_NM,
    zee: null,
    poe: [],
    amp: [],
    projects: [],
    nearby: { marinas: [], capitaineries: [], wpi: [] },
    marks: [],
    science: null,
    weather: null,
    polar: null, // { boat, vmgHint } SI chargé — jamais la grille
    event: null,
  };
}

export function ici(lat, lon, extras = {}) {
  const d = emptyDossier(lat, lon);
  if (extras.polarMeta) {
    d.polar = {
      boat: extras.polarMeta.boat_name,
      vmgHint: extras.polarMeta.vmg_summary?.["12"] ?? null,
    };
  }
  return d;
}
```

Appelé à chaque `legContext.snappedPosition`. Affichage : `<details>` « Dossier cockpit » sous le briefing. **Interdit** d’y coller les FeatureCollections allumées sur la carte.

---

## 17. Données, ports, variables

`vite.config.js` (dev) : proxy `/route`, `/proxy`, `/wind`, `/wave`, `/current`, `/api/v1` → `localhost:8010` ; `/bi` → `localhost:8001` rewrite `/api`. **Pas** de proxy `/agents`.

| Si… | Alors… |
|---|---|
| Backend simulateur down | Berry via `public/route.geojson`. Polar / draw / ZEE WMS / WPI = erreur honnête. Balisage OK |
| Simulateur up, BI down | Film + polar + searoute + ZEE/WPI OK. Pastilles BI = erreur |
| Les deux up | Toutes les couches lecture seule |

Variables : `VITE_API_URL=` (vide), `VITE_POLAR_API_URL=`, `VITE_BI_BASE=/bi`, `VITE_ORCHESTRATOR_URL=` optionnel, Copernicus optionnel. **Aucune** clé Tavily / LLM requise pour l’étape 1.

Ne jamais lancer `infra/vps/sync-from-atlas.sh`. Le simulateur ne parle pas à Mongo.

---

## 18. Ordre de chantier (1.0 → 1.9)

Ne pas commencer le polar (1.5) si searoute (1.2) n’avance pas. Ne pas commencer les couches (1.7) si l’UX (1.4) n’est pas posée.

| Jalon | Livrable | Recette |
|---|---|---|
| **1.0** | Squelette Vite + FastAPI + README | Page titre + `GET :8010/` → `{ "service": "naviguide-simulator" }` |
| **1.1** | Carte + fond + panes | Dark Esri, test ordre panes |
| **1.2** | searoute + Berry + fallback | LineString ≥ 2 pts ; pastille progression |
| **1.3** | Bateau | Suivant × 5 depuis Saint-Maur |
| **1.4** | UX allégée | Pas GeoJSON/KML, pas Export, pas chats |
| **1.5** | Polar sans chat | VMG Leopard 46 ; `POST /chat` → 404 |
| **1.6** | Draw | 3 clics, undo, Terminer, retour Berry |
| **1.7** | Pastilles | Balisage → … → Climatologie stub |
| **1.8** | Clic route | Popup 3 onglets vent/vague/courant |
| **1.9** | Stub `ici()` + disclaimer | `<details>` `zee: null` |

`package.json` : react, leaflet, lucide-react, tailwind 4. **Pas** de maplibre-gl / react-map-gl / searoute-js.

`server/requirements.txt` : fastapi, uvicorn, searoute, geographiclib, shapely, global-land-mask, numpy, pandas, openpyxl, pdfplumber, python-multipart, httpx, python-dotenv. Pas d’anthropic / langgraph « pour les agents ».

**Critère « étape 1 terminée » :** un skipper débutant lance les deux commandes, reconnaît NAVIGUIDE, avance le bateau, voit les polaires, trace 3 points, allume AMP (si BI local) ou une erreur claire, **ne trouve aucun chat ni import/export**, et comprend que le récit d’événement n’est pas là.

Une ligne dans le `README.md` racine seulement quand 1.0 existe.

---

## 19. Fichiers touchés / interdits

**On crée :** tout `naviguide-simulator/**`, ce document, [PLAN_HACKATHON_GAGNER.md](./PLAN_HACKATHON_GAGNER.md).

**On n’ouvre pas en écriture :** `frontend/src/**`, `backend/app/**`, `naviguide/naviguide-app/**`, `naviguide/naviguide-api/**`, `naviguide/polar_agent/**` (lecture pour copier seulement), `infra/vps/**`, CI prod.

Si l’étape 2 a besoin de `GET /api/ici?lat=&lon=`, ce sera une route du **serveur simulateur**, pas de la prod. Pas maintenant.

---

## 20. Recette

Machine : macOS, Terminal.

```bash
cd naviguide-simulator
python3 -m venv .venv && source .venv/bin/activate
pip install -r server/requirements.txt
uvicorn server.main:app --host 127.0.0.1 --port 8010 --reload
```

Autre onglet : `npm install && npm run dev` → http://localhost:5174

### A. Film + searoute + polar

| # | Action | Attendu |
|---|---|---|
| A1 | Page charge | Deux sidebars, carte sombre, spinner puis trait Berry |
| A2 | Polaires (droite) | Tableau VMG Leopard 46 |
| A3 | Simulation → Suivant × 3 | Bateau avance. Pas d’onglets Ports/Météo |
| A4 | Précédent | Un cran, pas de saut Cap-Vert |
| A5 | Dessiner 3 clics mer | Trait vert, undo |
| A6 | Terminer | Trait bleu, briefing local, sim sur cette route |
| A7 | « Berry-Mappemonde » | Retour searoute officielle |
| A8 | Panneau droit | Langue, thème, stats, polar — pas Export |
| A9 | BerryCard | Dessiner / Continuer / Supprimer — pas GeoJSON / KML |
| A10 | Clic sur le trait | Popup vent / vague / courant |
| A11 | `<details>` dossier | `zee: null`, `polar.boat` si chargé |
| A12 | Clair / FR | Esri light, libellés FR |
| A13 | Sidebar gauche | Briefing — pas de Chat polar |

### B. Backend simulateur éteint

Berry via `public/route.geojson` + bandeau. Draw / polar = erreur honnête.

### C. Couches BI (optionnel, `:8001`)

PoE ON → pastilles ambre. AMP ON, zoom Caraïbes → polygones. Marinas ON → canvas fluide.

### D. Tests auto

```bash
cd naviguide-simulator && npm test
.venv/bin/python -m pytest server/tests -q
```

Doivent passer : `berryLegs`, `routeFromOfficial`, `simulationRoute`, `geo`, `ici`, `panes`, `polar_engine`.

### E. Recettes négatives

| # | Action | Attendu |
|---|---|---|
| E1 | Chercher Ports / Sécurité / Météo / Cruisers | Absent |
| E2 | `POST /api/v1/polar/chat` | 404 |
| E3 | `POST /agents/meteo` | 404 |
| E4 | Bouton GeoJSON / KML / Exporter | Absent |
| E5 | `grep -R AgentPanel naviguide-simulator/src` | Aucun fichier |

---

## 21. Risques

| Risque | Gravité | Parade |
|---|---|---|
| Recopier `Sidebar.jsx` tel quel | Haute | Port chirurgical avant le premier commit UI |
| Recopier `useAmpLayer` avec `mode === "amp"` | Haute | Nouveaux hooks toggle |
| Recoller à `naviguide-api:8000` | Haute | Backend 8010 dans le dossier |
| `searoute-js` « pour aller plus vite » | Haute | Python uniquement |
| Remettre les 4 chats | Produit | Le Briefing est l’emplacement |
| Remettre l’import « au cas où » | Produit | Draw + Berry |
| Marinas ON par défaut | Moyenne | OFF + canvas |
| Charger `eez_world_map.geojson` | Haute | WMS limites |
| `flyTo([lon, lat])` | Haute | Leaflet = `[lat, lon]` |
| Import runtime depuis `frontend/` | Haute | copies |
| Toucher nginx / VPS | Bloquante | localhost seulement |
| Grille 181×61 dans `ici()` | Produit | `vmg_summary` seulement |
| Croire l’étape 1 prête pour Nemotron | Produit | sac vide = honnête |

---

## 22. Passage à l’étape 2

L’étape 2 commence **uniquement** si A1–A7, A11 et E1–E5 passent.

Alors on remplit le sac, **sans Tavily** : ZEE du point, PoE + URL, proches 20–30 nm, événement « on entre dans cette ZEE », polar de **cette** jambe. Le Briefing raconte ce JSON. Toujours **pas** 4 chats.

Nano / Tavily / Ultra = étapes 5–6 du [plan pour gagner](./PLAN_HACKATHON_GAGNER.md).

Rappel : les boutons allument toute la couche. Le LLM n’en voit qu’une poignée. Un pas = `ici()` gratuit. Tavily = entrée de ZEE, clic skipper, ou alerte.

---

## 23. Documents et fichiers dont ce plan hérite

- Discussion produit « simulation = film, `ici()` = moteur, boutons = carte » (septembre 2026).
- Arbitrage skipper 13 septembre matin (v2.0) et soir (v3.0) : polar sans chat, UX sans 4 agents, sans import/export.
- [hackathon-nebius-nvidia.md](./hackathon-nebius-nvidia.md), [PLAN_HACKATHON_GAGNER.md](./PLAN_HACKATHON_GAGNER.md).
- [ARCHITECTURE.md](./ARCHITECTURE.md) — `MapView.js` + un hook par couche.
- Code vivant : `naviguide/naviguide-app/src/App.jsx`, `Sidebar.jsx`, `ExportSidebar.jsx`, `useLegContext.js`, `MaritimeLayers.jsx` ; `polar_engine.py`, `polar_api/main.py` (sans chat) ; `naviguide-api/main.py` (`GET /route`) ; `frontend/src/components/MapView.js` + `map/*` ; `backend/data/route.geojson` ; `GET /api/export/*`, `GET /api/amp?bbox=`.
