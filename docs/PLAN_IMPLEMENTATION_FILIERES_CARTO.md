# Plan d’implémentation — Filières carto (contrôle, carte, hydro, satellite)

Document de cadrage. Il remet en ordre un tas d’idées utiles mais
**mélangées** : ontologie OSM, SHOM/NOAA, Review / Gold, GeoJSON
versionné, géocodage, VLM, Seamap, tippecanoe, EMODnet, NOAA ENC,
IENC, GEBCO, Sentinel.

Écrit en langage simple : c’est le contrat de ce que l’on cherche, et
de ce que l’on refuse. Chaque brique a **un métier**. On ne lui en
colle pas un second.

Version **1.0** — 14 septembre 2026.

Hérite de : `README.md` (fonds Seamap, exports, catalogue),
`docs/CATALOGUE_SEAMARK.md`, `docs/CONTRATS_MODES.md`,
`docs/CONTRATS_REVIEW_PAR_MODE.md`, `docs/CAHIER_DES_CHARGES_REVIEW.md`,
`docs/PLAN_IMPLEMENTATION_CLIMATOLOGIE.md`,
`docs/PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md`,
`docs/hackathon-nebius-nvidia.md`, `infra/vps/seamap/README.md`.

**Sommaire**

1. En une phrase
2. Pourquoi ce travail existe
3. Ce que l’on veut obtenir
4. Ce que l’on ne veut pas
5. Vocabulaire
6. Les quatre filières (la remise en ordre)
7. Partage Blue Intelligence / NAVIGUIDE simulator
8. État actuel et écarts
9. Filière 1 — Contrôle (objets et preuves)
10. Filière 2 — Carte (fond + overlays + avertissement)
11. Filière 3 — Hydrographie officielle (API, pas des fichiers S-57)
12. Filière 4 — Satellite (pilotes corridor Berry)
13. Ordre de chantier
14. Fichiers touchés
15. Recette
16. Risques
17. Hors périmètre
18. Documents dont ce plan hérite

---

## 1. En une phrase

Séparer **quatre métiers** qui ne se recouvrent pas : (1) **contrôler**
un objet extrait contre un référentiel et une relecture humaine,
(2) **afficher** Seamap + nos overlays + EMODnet avec un vrai
« NOT FOR NAVIGATION », (3) **étendre** les objets officiels déjà
branchés **par API**, (4) **piloter** Sentinel sur le corridor Berry
dans le mode Science — sans jamais transformer Blue Intelligence en
encodeur S-101 ni NAVIGUIDE en ECDIS.

---

## 2. Pourquoi ce travail existe

Les briques sont déjà là. Ce qui manque, c’est de **ne pas les
confondre**.

Aujourd’hui on a :

- un catalogue `seamark:*` et un audit de tags ;
- SHOM (SMCFAC / BUISGL) et NOAA ENC Direct **déjà** collés sur les
  capitaineries ;
- Review / Gold (file humaine) ;
- des GeoJSON versionnés + sha256 + un PMTiles hebdo **publié mais
  jamais affiché** ;
- `geo.py` (Nominatim ∥ GeoNames) ;
- `vision_msg.py` + NIM / Nemotron (juge de documents) ;
- Seamap (OSM + PMTiles + MapLibre) comme fond « Carte marine » ;
- EMODnet en WMS **et** en point, **seulement** en mode Science ;
- un bandeau « Ne convient pas à la navigation », **pas** une
  fenêtre d’acceptation.

Si on mélange ces rôles, on part dans de mauvaises implémentations :

| Confusion | Ce qu’elle produirait |
|-----------|------------------------|
| Catalogue OSM = encodeur S-101 | Un produit hydrographique que nous ne sommes pas |
| SHOM/NOAA = source à recopier telle quelle | Un ponton de croquis promu « officiel » |
| `geo.py` = calage d’image | Un géoréférenceur pixel dont nous n’avons pas besoin |
| VLM = recaler des pixels | Un usage vision hors contrat (et hors VPS) |
| EMODnet WMS = seulement Science | Un fond utile caché aux autres modes |
| GEBCO = profondeur de port | Un chiffre trop gros pour un bassin |
| Sentinel = carte marine | Une image satellite présentée comme un sondage |

NAVIGUIDE (prod et simulateur) est un **SADP** : aide à la décision
plaisancière. Blue Intelligence est une **base géospatiale + carte**.
Ni l’un ni l’autre n’est un ECDIS. Ce plan garde cette frontière.

---

## 3. Ce que l’on veut obtenir

Quatre livrables, **dans cet ordre de dépendances** (pas quatre
projets parallèles qui s’ignorent).

1. **Contrôle.** Un objet BI (ponton, bureau, feu, zone de
   profondeur extraite) a une **identité**, un **référentiel de
   contrôle** s’il existe (SHOM / NOAA / catalogue OSM), et passe
   par **Review / Gold** avant d’entrer dans un run certifié.
2. **Carte.** Seamap reste le fond. Dessus : overlay hebdomadaire
   tippecanoe, WMS EMODnet **aussi hors Science**, isobathe de
   sécurité si les tuiles portent une profondeur, **fenêtre
   d’acceptation** « NOT FOR NAVIGATION » (le bandeau ne suffit pas).
3. **Hydro officielle par API.** Étendre NOAA ENC Direct (feux,
   bouées, isobathes US) **via l’API ArcGIS déjà utilisée**, jamais
   via des fichiers S-57. GEBCO seulement **au large**, pour
   NAVIGUIDE. IENC / VNF **hors périmètre**.
4. **Pilotes Sentinel.** Corridor Berry seulement. Trait de côte +
   estran + SDB simple, export GeoJSON OSM-shaped, affichage **mode
   Science** avec le même avertissement. Calcul **hors VPS**.

Phrase de partage (comme la climatologie) :

**Blue Intelligence montre, contrôle et versionne. Le simulateur
NAVIGUIDE s’en sert pour le film, sans inventer une deuxième carte.**

---

## 4. Ce que l’on ne veut pas

- Encoder ou exporter du **S-101** / ingérer des **fichiers S-57**.
- Recaler une image (croquis, Sentinel, PDF) avec `geo.py` ou un VLM.
- Faire du VLM un moteur de bathymétrie ou de géoréférencement.
- Gold silencieux, Gold sans clic, Gold qui change la carte sans
  « Afficher la review » (`docs/CONTRATS_REVIEW_PAR_MODE.md` §0 et §8).
- Review / Gold des modes Science et Climatologie en V1 (C8).
- Isobathes **vectorielles** EMODnet sur le VPS (GDAL + trop de
  calcul).
- GEBCO comme profondeur d’approche d’un port.
- IENC / VNF (fleuves) dans le périmètre actuel.
- ACOLITE / CoastSat / ICESat-2 **sur le VPS** (4 vCores, 8 Go,
  ~26 Go déjà pris par Seamap).
- Présenter un produit Sentinel comme une carte marine.
- Un 8ᵉ mode BI. Science absorbe les pilotes satellite.
- Copier le C++ GPL de Seamap / OpenCPN. On consomme le `style.json`
  CC-BY et on réécrit.

---

## 5. Vocabulaire

| Mot | Sens ici |
|-----|----------|
| **Filière** | Une chaîne avec un métier unique. Quatre filières, pas un fourre-tout « carto ». |
| **Contrôle** | Comparer un objet extrait à un référentiel **déjà publié**, puis à un œil humain. |
| **Référentiel** | SHOM WFS, NOAA ENC Direct, Marine Regions, catalogue `seamark:*`. Pas un LLM. |
| **SMCFAC** | Objet S-57 « small craft facility » (ponton / installation plaisance). Le WFS SHOM le sert en **point**. |
| **BUISGL** | Bâtiment. `FUNCTN=2` = bureau de capitainerie. |
| **Overlay 250 m** | Coller SHOM/NOAA sur OSM **par distance seule**, pas par nom (`find_building`). |
| **Review / Gold** | File humaine → clic Gold → **run certifié**. La carte ne le montre que si « Afficher la review » est coché. |
| **GeoJSON versionné** | Format **intermédiaire** : `metadata.version` = `AAAA-MM-JJ.<sha25612>`. Pas une carte, pas une ENC. |
| **Gazetteer** | Annuaire de **toponymes** (où est ce nom ?). Amorce = `geo.py`. |
| **Juge VLM** | Oui / non sur une **mention** (« est-ce une règle de navigation ? »). Pas un calage pixel. |
| **Seamap** | Fond vectoriel Open Waters (OSM + PMTiles + MapLibre). Pile du fond « Carte marine ». |
| **Overlay tippecanoe** | PMTiles **de nos** 7 exports, construit chaque lundi. Calque **par-dessus** Seamap, pas à la place. |
| **S-52 allégée** | Colorer une isobathe de sécurité si un attribut de profondeur existe. Pas un moteur S-52. |
| **SDB** | Bathymétrie par satellite (formule de Stumpf). Produit de recherche, pas un sondage. |
| **Estran** | Zone découverte à marée basse. MNDWI / CoastSat le dessinent ; ce n’est pas une ENC. |
| **CDSE** | Copernicus Data Space Ecosystem (images Sentinel). **Autre compte** que CMEMS (modèles mer). |
| **Corridor Berry** | Bande le long de la route officielle. Seul périmètre des pilotes Sentinel. |

---

## 6. Les quatre filières (la remise en ordre)

```
  1. CONTRÔLE                         2. CARTE
  objet + preuve + humain             fond + overlay + avertissement
  ┌─────────────────────┐             ┌──────────────────────────┐
  │ catalogue OSM       │             │ Seamap (OSM+PMTiles+ML)  │
  │   = cible export    │             │ + overlay tippecanoe     │
  │ SHOM / NOAA         │             │ + WMS EMODnet (tous      │
  │   = référentiel     │────────────▶│   modes, pas seulement   │
  │ Review / Gold       │  GeoJSON    │   Science)               │
  │   = file humaine    │  + sha256   │ + isobathe sécurité      │
  │ geo.py              │             │ + fenêtre NOT FOR NAV    │
  │   = gazetteer       │             └──────────────────────────┘
  │ VLM                 │
  │   = juge de mention │
  └─────────────────────┘
            │
            │  exports versionnés (même contrat)
            ▼
  3. HYDRO OFFICIELLE                 4. SATELLITE (pilotes)
  API seulement                       corridor Berry, hors VPS
  ┌─────────────────────┐             ┌──────────────────────────┐
  │ NOAA ENC Direct     │             │ Sentinel-2 via CDSE      │
  │   feux / bouées /   │             │ ACOLITE + MNDWI/CoastSat │
  │   isobathes  (US)   │             │ SDB Stumpf ± ICESat-2    │
  │ GEBCO au large      │             │ vs EMODnet (erreur)      │
  │ EMODnet : WMS+point │             │ GeoJSON OSM-shaped       │
  │ IENC/VNF : NON      │             │ → mode Science seulement │
  │ S-57 / S-101 : NON  │             └──────────────────────────┘
  └─────────────────────┘
```

Les flèches sont des **contrats**, pas des copies de code. Le GeoJSON
versionné est le **seul** format qui traverse les quatre filières.

---

## 7. Partage Blue Intelligence / NAVIGUIDE simulator

Même esprit que « BI montre l’atlas. NAVIGUIDE s’en sert »
(`docs/PLAN_IMPLEMENTATION_CLIMATOLOGIE.md` §6). Ici :

```
              GeoJSON versionné + sha256
              (+ PMTiles overlay le lundi)
                         │
          ┌──────────────┴──────────────┐
          ▼                             ▼
  Blue Intelligence              NAVIGUIDE simulator
  7 modes + Review/Gold          film Leaflet (étape 1)
  fond Seamap MapLibre           pastilles déjà là
  overlay + EMODnet + modal      mêmes exports /bi/*
  Science = catalogues +         ici() : 0 ou 1 objet
    pilotes Sentinel             localisé, pas le monde
          │                             │
          │                      prod naviguide.fr
          │                      INTTOUCHÉE par ce plan
          └─────────────────────────────┘
```

| Idée | Blue Intelligence | Simulateur NAVIGUIDE | Prod `naviguide.fr` |
|------|-------------------|----------------------|---------------------|
| Catalogue OSM + audit | Cible d’export, badges, audit lundi | Rien à peindre ; les tags déjà dans les exports | Inchangée |
| SHOM / NOAA contrôle | Overlay 250 m + fiche Review | Un bureau Gold dans `ici()` / Briefing, pas un dump US | Inchangée |
| Review / Gold | File indispensable ; interrupteur Map | Consomme le **run certifié** (étape Gold du hackathon), jamais le dump brut comme « officiel » | Inchangée |
| GeoJSON + sha256 | Intermédiaire + snapshots + release `data-*` | Fetch `/bi/export/*` déjà en place ; vérifier `metadata.version` | Proxy `/bi` déjà là |
| Gazetteer (`geo.py`) | P / PoE / futurs toponymes Berry | Noms d’escales, sac `ici()` | Inchangée |
| VLM juge | Formalités / AMP / enrich : « est-ce une règle ? » | Nemotron Ultra **barre** une mention non prouvée (cahier hackathon) — même question, autre écran | Inchangée |
| Seamap fond | Déjà le fond « Carte marine » | Leaflet + tuiles OpenSeaMap raster (balisage). **Pas** MapLibre/PMTiles en étape 1 | MapLibre + Seamap déjà |
| Overlay tippecanoe | À **afficher** (aujourd’hui seulement publié) | Option plus tard : une pastille « overlay BI » ; d’abord les GeoJSON | Hors ce plan |
| EMODnet WMS hors Science | Interrupteur carte, tous modes | Pastilles Science déjà prévues (bathy / fonds / câbles) | Hors ce plan |
| Fenêtre NOT FOR NAV | Premier usage fond mer + Science satellite | Premier allumage balisage / Science | Hors ce plan |
| Isobathe sécurité | Si attribut de profondeur dans Seamap | Inutile en Leaflet raster ; le simulateur n’a pas Seascape | Hors ce plan |
| NOAA ENC feux/bouées | Mode Capitaineries / couche US, API | Un feu **proche de `ici()`** sur une jambe US | Hors ce plan |
| GEBCO | Inutile en port ; ne pas peindre sur BI | Moteur / no-go **au large** (pas une pastille port) | Déjà des zones GEBCO manuscrites dans le workspace routing |
| Sentinel | Mode Science, bandeau, export | 0 ou 1 trait de côte **local** dans le sac, jamais les 8 catalogues | Inchangée |
| IENC / VNF | Non | Non | Non |

**Règle simulateur.** L’étape 1 est Leaflet, sans MapLibre, sans
import/export fichier, prod intouchée
(`docs/PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md`). Ce plan
**n’annule pas** ça. Le simulateur profite surtout des **exports**,
du **Gold**, du **juge**, d’**EMODnet en pastilles**, et plus tard
d’**un** objet satellite dans `ici()`. Il ne reçoit pas Seamap
PMTiles ni l’isobathe S-52.

---

## 8. État actuel et écarts

### Déjà en place (ne pas reconstruire)

| Brique | Où | Métier réel aujourd’hui |
|--------|----|-------------------------|
| `backend/data/seamark_catalog.json` + `scripts/audit_tags.py` | Catalogue + rapport | Ce que les pipelines **lisent** dans OSM |
| `capitainerie_world.py` | SHOM WFS + NOAA ENC Direct `FUNCTN=2` | Overlay bureaux, pas un encodeur |
| `review_queue.py` / `review_gold.py` / onglet Review | File humaine | Formalités le plus avancé ; Marinas trop « pré-Gold » ; Capitaineries / AMP Gold trop large ou absent |
| `export_meta.py` + `POST /api/export/snapshot` | GeoJSON + sha25612 | Intermédiaire stable |
| `.github/workflows/weekly-data-build.yml` | 7 GeoJSON → tippecanoe → release `data-*` | Archive **publiée**, overlay **non chargé** dans le frontend |
| `backend/app/core/geo.py` | Nominatim ∥ GeoNames | Géocodage de **noms**, pas d’images |
| `vision_msg.py` + `review_doc_picker.py` | JPEG → NIM / Claude | Juge de **documents** Formalités |
| Seamap miroir VPS | `infra/vps/seamap/` | Fond ~26 Go, cron lundi |
| Bandeau nautique | `MapView.js` `data-testid="nautical-disclaimer"` | Toujours visible si fond mer ; **pas** de clic d’acceptation |
| EMODnet WMS | `useScienceWms.js` | **`mode === "science"` seulement** |
| EMODnet point | `GET /api/depth` | Popups marinas / mouillages |
| Simulateur | `useToggleLayers.js` | GeoJSON BI + OpenSeaMap raster + stub climatologie |

### Trous (ce que ce plan comble)

| Trou | Filière |
|------|---------|
| PMTiles `blue-intelligence-*.pmtiles` jamais référencé dans le frontend | 2 |
| EMODnet WMS verrouillé au mode Science | 2 |
| Pas de fenêtre d’acceptation (bandeau seulement) | 2 |
| Pas d’isobathe de sécurité locale (on s’en remet au style Seamap) | 2 |
| « Afficher la review » : i18n prêt, **bouton Map absent** | 1 |
| Gold capitainerie / AMP : contrat écrit, code trop large ou incomplet | 1 |
| Types `candidat` du catalogue (feux, roches, mouillages) pas encore dans un pipeline | 1 |
| NOAA ENC : seulement `FUNCTN=2` (bureaux), pas feux / bouées / isobathes | 3 |
| GEBCO : zones dessinées à la main dans le routing, pas une grille | 3 |
| Sentinel / CDSE / ACOLITE / CoastSat / ICESat-2 : **zéro code** | 4 |
| Compte CDSE vs CMEMS : **à vérifier** (humain + secrets) | 4 |

---

## 9. Filière 1 — Contrôle (objets et preuves)

C’est la filière **déjà commencée**. On la nomme pour arrêter de lui
demander d’être une carte ou un encodeur.

### 9.1 Catalogue OSM → champs BI (cible d’export OpenSeaMap)

**Métier.** Dire noir sur blanc quels tags on lit, lesquels sont
`candidat`, et produire un GeoJSON **dans le vocabulaire OSM /
OpenSeaMap** (`leisure=marina`, `seamark:type=…`). Ce n’est **pas**
un encodeur S-101.

**Déjà là.** `docs/CATALOGUE_SEAMARK.md`, `seamark_catalog.json`,
`audit_tags.py` (lundi, dans le workflow hebdo). Badges marinas via
`SERVICE_TAG_QUESTIONS`.

**À faire.**

| Id | Travail | Critère |
|----|---------|---------|
| C1 | Promouvoir en `exploite` les tags qu’un pipeline lit vraiment (mouillages `anchorage` / `mooring` dès que `anchorage_build.py` les garde) | Audit : plus de « candidat alors que le dump les porte » |
| C2 | Documenter le **mapping inverse** : champ slim BI → tag OSM d’export (ex. badge Avitaillement → `fuel=yes` / `seamark:small_craft_facility:category=fuel`) | Une table dans le catalogue ; un test sur un fixture |
| C3 | Quand un pilote satellite exporte (`natural=coastline`, `seamark:type=depth_area`), **ajouter ces clés** au catalogue **avant** le premier dump | Pas de tag hors catalogue sans entrée `candidat` |

**Interdit.** Générer des attributs S-101 (`DRVAL1`, `CATSCF`…)
depuis OSM. Le sens autorisé est OSM → champs BI → GeoJSON OSM.
SHOM/NOAA restent un **calque de contrôle**, pas la cible d’export.

### 9.2 SHOM / NOAA comme référentiel de contrôle

**Métier.** Un ponton lu dans un croquis, un site web ou un tag OSM
**n’est pas** un SMCFAC. Un bureau OSM **n’est pas** un BUISGL
`FUNCTN=2` tant que l’overlay 250 m n’a pas collé le même bâtiment.

**Déjà là.** Capitaineries : OSM monde → SHOM `buisgl_point` +
`smcfac_point` → NOAA ENC Direct `FUNCTN=2` (points + centroïdes).
Fiche Review : garder / détacher l’overlay. Marinas : dump OSM
seulement ; SHOM documenté dans `marina_build.py`, pas branché.

**À faire.**

| Id | Travail | Critère |
|----|---------|---------|
| C4 | Sur la fiche **Marina**, montrer s’il existe un SMCFAC / CATHAF à ≤ 250 m : « référentiel publié » vs « seulement OSM ». **Pas** de fusion automatique des bassins | Le réviseur voit les deux points ; Gold n’exige pas le SMCFAC (une marina n’est pas un décret) |
| C5 | Garder NOAA / SHOM **orphelin** visible (déjà le cas capitaineries) : un bureau sans OSM reste un candidat, pas une vérité carte | Test d’identité existant inchangé |
| C6 | Ne pas étendre `merge_km` au-delà de 0,25 km | Contrat `find_building` |

**Phrase de test.** Un ponton extrait d’un texte, sans SMCFAC ni tag
`leisure=marina`, **ne peut pas** être Gold comme marina.

### 9.3 Review / Gold — file indispensable

**Métier.** L’œil humain. Sans cette file, les filières 2–4 peignent
du brut.

Le code et les contrats existent (`CAHIER_DES_CHARGES_REVIEW.md`,
`CONTRATS_REVIEW_PAR_MODE.md`). Ce plan **n’invente pas** une
« Culture Review » à côté : c’est **le même** onglet Review.

**À faire (écarts déjà écrits, à coder).**

| Id | Travail | Critère |
|----|---------|---------|
| C7 | Bouton Map **Afficher la review** (i18n `reviewShowReview` déjà là) | Gold seul ne change pas la carte ; coché = run certifié |
| C8 | Capitaineries : plus de `gold_on: true` par défaut ; Gold après acceptation **bâtiment** | Phrase de test du méta-contrat §0 |
| C9 | AMP : liste des candidats `visit_url` ; Gold refuse `visit_url == manager_url` | Contrat §6 |
| C10 | Marinas : OSM ≠ pré-Gold automatique | Contrat §4.5 |

Science / Climatologie / pilotes Sentinel : **pas** de file Review
V1. Le bandeau + la fenêtre d’acceptation portent l’avertissement.

### 9.4 GeoJSON versionné + sha256 — format intermédiaire

**Métier.** Porter un jeu d’une filière à l’autre **sans** perdre la
date, l’empreinte et l’avertissement.

**Déjà là.** `versioned_fc()`, snapshots immuables, release lundi
avec `SHA256SUMS-*.txt`.

**À faire.**

| Id | Travail | Critère |
|----|---------|---------|
| C11 | Tout **nouveau** jeu (feux NOAA, coastline Sentinel, depth_area) passe par `versioned_fc()` | Même `metadata` que les 7 exports |
| C12 | Le workflow lundi **ajoute** les nouveaux exports s’ils sont publics (sinon release à part, même discipline sha256) | `gh release create` échoue si le tag existe : immuabilité |

### 9.5 Gazetteer (`geo.py`) — amorce, pas un calage d’image

**Métier.** « Où est ce **nom** ? » Nominatim ∥ GeoNames, cache
Mongo, tests d’espace ensuite (havre vs polygone VLIZ).

**À faire (plus tard, après C7–C10).**

| Id | Travail | Critère |
|----|---------|---------|
| C13 | Extraire une table `toponyms` (nom, lat/lon, source, `mrgid` si ZEE) alimentée par les succès de géocodage + noms VLIZ | Un nom déjà vu ne reconsomme pas le quota |
| C14 | `project_geocode.py` (CDC Projets) s’il devient nécessaire : **juge de lieu**, toujours via `geocode_name` | Pas de nouveau client HTTP « image → GPS » |

**Interdit.** Utiliser `snap_to_ocean` pour « coller » un trait de
côte Sentinel. Le satellite a son propre GPS (filière 4).

### 9.6 VLM — juge de mention, pas de pixels

**Métier.** Sur une page, un PDF, une capture : « cette phrase est-elle
une **règle de navigation** (VHF, interdiction de mouiller, port
d’entrée, tirant) ou du tourisme ? »

**Déjà là.** `vision_msg.py` envoie des JPEG ; Formalités s’en sert
pour **choisir le bon PDF**, pas pour lire une carte.

**À faire.**

| Id | Travail | Critère |
|----|---------|---------|
| C15 | Un juge JSON `navigation_rule: true\|false` + `quote` (extrait) branché sur `complete_json_cascade`, rôle `judge` | Fixture : « VHF 09 à l’entrée » → true ; « restaurant avec vue mer » → false |
| C16 | Branchement : enrichissement marina / capitainerie (ne pas inventer un VHF), candidats AMP visite, plus tard Briefing simulateur (Ultra barre) | Champ vide si false ; on n’écrit pas un faux canal |

**Interdit.** Demander au VLM les coins d’une image, une homographie,
ou une profondeur.

---

## 10. Filière 2 — Carte (fond + overlays + avertissement)

C’est le chantier **le plus visible**, et le plus petit en code.
Seamap **reste** le fond : OSM + PMTiles + MapLibre
(`useNauticalBasemap.js`, miroir `infra/vps/seamap/`).

### 10.1 Overlay hebdomadaire tippecanoe

**Déjà là.** Chaque lundi 05:00 UTC, tippecanoe construit
`blue-intelligence-$STAMP.pmtiles` (projets, marinas, mouillages,
capitaineries, AMP, PoE, route) et le publie sur la release GitHub
`data-$STAMP`.

**À faire.**

| Id | Travail | Critère |
|----|---------|---------|
| M1 | Servir l’overlay : URL de la **dernière** release (ou copie nginx `/tiles/bi-overlay/current.pmtiles` si on veut éviter GitHub à l’exécution) | Une variable `REACT_APP_BI_OVERLAY_URL` |
| M2 | Couche MapLibre **par-dessus** le style Seamap (source `pmtiles://…`, layers par `-L` tippecanoe) | Fond Seamap visible ; overlay éteignable |
| M3 | Interrupteur « Données BI (semaine) » dans le chrome carte, **tous modes**, défaut **on** une fois le fond mer accepté | `data-testid="overlay-bi-toggle"` |
| M4 | Pane / z-index : overlay **au-dessus** du GL Seamap (190), **sous** la route (380) et les clusters | Étendre `layerOrder.js` + test jest |
| M5 | Simulateur : **ne pas** porter PMTiles en étape 1. Les pastilles GeoJSON suffisent. Noter M1–M4 comme étape simulateur **ultérieure** | Étape 1 Leaflet intacte |

Budget disque : l’overlay tippecanoe est **petit** (points + route),
sans rapport avec les 26 Go Seamap. Copie VPS possible sans `KEEP`
agressif.

### 10.2 EMODnet WMS hors mode Science

**Déjà là.** Trois étages (bathy, substrat, câbles), panes 250 / 310
/ 370, persistance `bi.scienceWms`. Le hook refuse tout si
`mode !== "science"`.

**À faire.**

| Id | Travail | Critère |
|----|---------|---------|
| M6 | Retirer le garde `mode === "science"` ; le hook ne dépend plus que de `enabled` | WMS allumable en Marinas / Formalités / etc. |
| M7 | Déplacer (ou **dupliquer**) les trois boutons hors du seul `SciencePanel` : chrome carte commun (à côté du fond sombre / clair / mer) | Test : mode Marinas + bathy ON → tuiles `mean_multicolour` |
| M8 | Conflit z-index avec climatologie (aussi 250) : bathy EMODnet **sous** l’atlas si mode Climatologie | Ajuster `SCIENCE_WMS_PANES` / `PANES` et le test d’ordre |
| M9 | Simulateur : pastilles Science déjà au cahier hackathon (Bathymétrie / Fonds / Câbles). Brancher les **mêmes** URL WMS que `useScienceWms.js` | Pas un proxy VPS ; tuiles chez EMODnet |

Le sondage ponctuel `GET /api/depth` **reste** dans les popups
marinas / mouillages (déjà hors Science). On ne le déplace pas.

### 10.3 Fenêtre d’acceptation « NOT FOR NAVIGATION »

**Déjà là.** Bandeau bas si `nauticalActive`. Textes
`seaMapDisclaimerTitle` / `Body`. `basemaps.sea.notForNavigation`.

**À faire.**

| Id | Travail | Critère |
|----|---------|---------|
| M10 | Modale **bloquante** au premier passage sur le fond mer **ou** à l’allumage d’un WMS / overlay / couche satellite : titre, corps, case « Je comprends : ne convient pas à la navigation », bouton Accepter | Sans acceptation : fond mer refusé (repli sombre/clair), WMS off |
| M11 | Persistance `localStorage` `bi.notForNav.accepted` + date + `content_sha256` du texte (si le texte change, on redemande) | Rechargement : plus de modale, **bandeau conservé** |
| M12 | Même geste simulateur à l’allumage Balisage ou Science WMS (`naviguide-simulator`) | `data-testid="not-for-nav-modal"` |
| M13 | Les exports gardent `disclaimer` / `disclaimer_fr` (déjà) | Pas de changement de contrat JSON |

Le bandeau **reste**. La fenêtre est l’**acceptation**. Les deux
coexistent.

### 10.4 Isobathe de sécurité (S-52 allégée)

**Condition.** Seulement si les tuiles Seamap / Seascape exposent un
attribut de profondeur interrogeable (nom exact à confirmer dans le
`style.json` miroir : souvent une couche bathymétrie raster
**sans** attribut par pixel côté client).

**À faire d’abord : un diagnostic, pas une peinture.**

| Id | Travail | Critère |
|----|---------|---------|
| M14 | Lire le `style.json` Seamap (miroir ou CDN) : lister les layers dont `source-layer` / `paint` parlent de depth / contour / DEPARE | Note dans ce dossier ou `docs/audits/` : **attribut oui/non** |
| M15 | **Si oui** : expression MapLibre — seuil skipper (défaut **2 m**, réglable 2 / 5 / 10) ; aplat ou ligne d’isobathe **au-dessus** du fond, sous l’overlay BI | Test visuel + `data-testid="safety-isobath"` |
| M16 | **Si non** (cas probable : Seascape reste sur CDN, raster) : **ne pas** inventer une isobathe. Garder EMODnet WMS + `GET /api/depth`. Documenter le refus ici | Une phrase dans le README fonds de carte |

**Interdit.** Recoder S-52 (symboles IALA, lights sectors, safety
contour ECDIS). On colore **une** limite, on n’écrit pas un ECDIS.

---

## 11. Filière 3 — Hydrographie officielle (API, pas des fichiers S-57)

### 11.1 NOAA ENC Direct — étendre ce qui est déjà branché

**Couverture.** Eaux US seulement. Même MapServer :

`https://gis.charttools.noaa.gov/arcgis/rest/services/encdirect`

**Déjà là.** Couches harbour / approach / coastal / berthing,
`FUNCTN=2` seulement (`NOAA_ENC_LAYERS` dans
`capitainerie_world.py`).

**À faire.**

| Id | Travail | Critère |
|----|---------|---------|
| H1 | Inventaire des `layer_id` publics : feux (`LIGHTS`), bouées / balises (`BOY*`, `BCN*`), isobathes / DEPARE si le service les expose en GeoJSON | Tableau `docs/` ou commentaire + test d’un `query` bbox |
| H2 | Fetch tuilé (même discipline que l’overlay capitaineries) : upsert `noaa:{service}:{layer}:{fid}`, slim GeoJSON via `versioned_fc` | Licence NOAA + disclaimer déjà cités |
| H3 | Affichage : couche optionnelle **US**, pas mondiale. BI : interrupteur dans Capitaineries **ou** chrome carte. Simulateur : seulement si `ici()` est dans une bbox US | Zéro objet hors bbox ENC Direct |
| H4 | Contrôle (filière 1) : un feu OSM `seamark:type=light` **proche** d’un LIGHTS NOAA = même geste 250 m que le bureau | Pas de fusion 500 m `same_site` |

**Interdit.** Télécharger des cellules S-57 `.000`. Parser un ENC.
Encoder du S-101.

### 11.2 EMODnet — rester au WMS + point

Déjà branché. Le saut vers des isobathes **vectorielles** demande
GDAL et un cube trop gros pour le VPS. **Refusé** (voir §4).

Si un jour on veut du vecteur : calcul **hors VPS**, snapshot
GeoJSON versionné, servi comme la climatologie. Pas dans ce plan.

### 11.3 GEBCO — au large, pour NAVIGUIDE

**Métier.** No-go / isochrone **offshore**. Inutile pour un port
(résolution trop grossière ; EMODnet + OSM + `GET /api/depth`
gagnent à quai).

**Déjà là.** Zones rectangulaires manuscrites dans
`naviguide/.../bathymetry.py` (workspace routing). Pas dans BI.

**À faire (simulateur / moteur, pas la carte BI).**

| Id | Travail | Critère |
|----|---------|---------|
| H5 | Grille GEBCO **précalculée hors VPS** (comme les snapshots climatologie), lookup point pour l’isochrone / `ici().depth_offshore` | `null` près des côtes (seuil à écrire, ex. 20 M du rivage) |
| H6 | **Ne pas** peindre GEBCO sur Blue Intelligence | Pas de layer GEBCO dans `layerOrder.js` |

Prod `naviguide.fr` : hors ce plan (même règle que l’étape 1
simulateur). On prépare le lookup dans le simulateur / le workspace
routing **copié**, on ne colle pas les deux dépôts.

### 11.4 IENC / VNF

Intéressant pour les **fleuves**. Hors périmètre : la route Berry et
les 7 modes sont **maritimes**. Une ligne dans §17 suffit. Pas de
ticket, pas de prototype.

---

## 12. Filière 4 — Satellite (pilotes corridor Berry)

**Métier.** Voir l’erreur d’un trait de côte / d’une profondeur
**estimée**, la comparer à EMODnet, l’exporter en GeoJSON OSM-shaped,
l’afficher en **Science** avec le bandeau. Ce n’est pas une ENC.

**Périmètre.** Uniquement le corridor de `backend/data/route.geojson`
(buffer à fixer, ex. 30 M). Pas le monde.

**Calcul.** Mac de l’opérateur ou machine hors ligne. Le VPS **sert**
le GeoJSON, comme les snapshots climatologie.

### 12.0 Compte CDSE (bloquant humain)

CMEMS (vent, houle, courant, climatologie) **n’est pas** CDSE
(images Sentinel-2).

| Id | Travail | Critère |
|----|---------|---------|
| S0 | Vérifier le compte Copernicus : a-t-on un accès **CDSE** (dataspace.copernicus.eu) distinct du login CMEMS déjà utilisé par `scripts/climatology/cmems_auth.py` ? | Note dans `scripts/satellite/README.md` : oui/non + qui possède le login. **Pas de secret dans git** |

Sans S0, on n’écrit pas de downloader.

### 12.1 Chaîne proposée (hors VPS)

| Étape | Outil | Sortie |
|-------|-------|--------|
| S1 | Sentinel-2 L1C/L2A sur scènes qui couvrent le corridor (CDSE STAC) | Scènes datées, liste sha256 |
| S2 | ACOLITE (correction atmosphérique côtière) | Réflectances |
| S3 | MNDWI et/ou CoastSat | Polyligne `natural=coastline` + polygone estran |
| S4 | SDB Stumpf **si** une trace ICESat-2 ATL03/ATL24 croise la scène | `seamark:type=depth_area` (classes peu profondes, pas un DTM 1 m) |
| S5 | Comparer à EMODnet (`depth_sample` + WMS) | Champs `error_m`, `n`, DOI / date des deux produits |
| S6 | `versioned_fc()` → `coastline.geojson` / `depth_areas.geojson` | `metadata.disclaimer` obligatoire |
| S7 | Mode Science : filtre « Satellite (pilote) » + mêmes boutons WMS + bandeau / modale M10 | Review **off** (placeholder) |

**Interdit.** Recaler l’image avec le VLM. Inventer une profondeur
sans ICESat-2 **et** sans le dire (`null` + `method: "stumpf-uncalibrated"`
si on affiche quand même un essai — par défaut on **n’affiche pas**).

### 12.2 Ce que le simulateur en fait

Le cahier hackathon : Science = **0 ou 1 jeu localisé** dans le sac
`ici()`, pas les catalogues entiers. Un trait de côte pilote entre
dans `ici().science` **si** le bateau est dans le corridor **et**
si un export existe. Sinon `null`. Nano raconte ; Ultra ne prend
pas une côte satellite pour une ENC.

---

## 13. Ordre de chantier

Pas de calendrier en jours. L’ordre est **technique** : d’abord ce
qui débloque l’affichage et le contrat Review, ensuite l’API NOAA,
ensuite le satellite (bloqué par S0).

### Vague 0 — Diagnostic (aucun secret, peu de code)

| Id | Livrable |
|----|----------|
| M14 | Attribut de profondeur Seamap : oui / non |
| S0 | Compte CDSE : oui / non |
| H1 | Liste des layers ENC Direct utiles (feux, bouées, DEPARE) |

### Vague 1 — Carte visible (filière 2) + interrupteur Review

Dépend de M14 seulement pour M15 (sinon on saute M15–M16).

| Id | Livrable | Où |
|----|----------|-----|
| M10–M13 | Fenêtre d’acceptation + bandeau conservé | BI + simulateur |
| M6–M8 | EMODnet WMS tous modes | BI |
| M9 | WMS EMODnet en pastilles Science | simulateur |
| M1–M4 | Overlay tippecanoe sur Seamap | BI |
| C7 | Afficher la review | BI Map |
| M15 | Isobathe **si** M14 positif | BI |

**Recette vague 1.** Fond mer → modale → accepter → bandeau. Allumer
bathy en mode Marinas. Voir l’overlay de la semaine. Gold sans
« Afficher la review » : carte inchangée.

### Vague 2 — Contrôle (filière 1, écarts déjà contractés)

| Id | Livrable |
|----|----------|
| C8–C10 | Gold capitaineries / AMP / marinas selon contrat |
| C4 | SMCFAC voisin sur fiche Marina |
| C1–C3 | Catalogue : `exploite` / mapping export / clés satellite en `candidat` |
| C15–C16 | Juge « règle de navigation ? » |

**Recette vague 2.** Phrase de test CONTRATS §0 verte pour chaque
kind. Un VHF inventé par le juge `false` n’est pas écrit.

### Vague 3 — NOAA étendu + GEBCO large (filière 3)

| Id | Livrable |
|----|----------|
| H2–H4 | Feux / bouées US par API, overlay 250 m vs OSM |
| H5–H6 | Lookup GEBCO offshore dans le **simulateur / routing**, pas sur BI |

**Recette vague 3.** Bbox Méditerranée : 0 objet NOAA. Bbox
Chesapeake : au moins un feu ou une bouée. Point à 5 M d’un port :
GEBCO `null`. Point au milieu de l’Atlantique : une profondeur.

### Vague 4 — Pilotes Sentinel (filière 4)

Bloquée par S0 = oui.

| Id | Livrable |
|----|----------|
| S1–S6 | Scripts `scripts/satellite/` hors VPS + 1–2 scènes Berry + exports |
| S7 | Affichage Science |
| `ici().science` | 0 ou 1 trait si le bateau est dessus |

**Recette vague 4.** Une scène, un GeoJSON avec `metadata.version`,
erreur vs EMODnet écrite, bandeau visible, aucun Review Gold.

Les vagues 1 et 2 peuvent **avancer en parallèle** (carte vs
Review). La vague 4 ne commence pas avant S0. La vague 3 peut
chevaucher 2 (même pattern overlay que les capitaineries).

---

## 14. Fichiers touchés

### Vague 1 (carte + Review interrupteur)

| Fichier | Rôle |
|---------|------|
| `frontend/src/components/map/NotForNavModal.js` | **Nouveau** — modale |
| `frontend/src/components/MapView.js` | Modale + bandeau |
| `frontend/src/components/map/useScienceWms.js` | Plus de garde `mode === "science"` |
| `frontend/src/components/map/useBiOverlay.js` | **Nouveau** — PMTiles overlay |
| `frontend/src/components/map/layerOrder.js` | Pane overlay + évent. isobathe |
| `frontend/src/components/map/__tests__/layerOrder.test.js` | Figer l’ordre |
| `frontend/src/App.js` / chrome carte | Boutons WMS + overlay hors SciencePanel |
| `frontend/src/i18n.js` | Clés modale / overlay / isobathe |
| `frontend/src/components/Header.js` ou chrome Map | Interrupteur « Afficher la review » (C7) |
| `infra/vps/seamap/` ou `deploy-app.sh` | Option : `REACT_APP_BI_OVERLAY_URL` |
| `naviguide-simulator/src/components/` | Modale + WMS EMODnet (M9, M12) |

### Vague 2 (contrôle)

| Fichier | Rôle |
|---------|------|
| `backend/app/services/review_gold.py` | Plus de pré-Gold automatique |
| `backend/app/services/review_queue.py` | Candidats AMP ; SMCFAC voisin marina |
| `frontend/src/components/review/*` | Fiches alignées contrat |
| `backend/data/seamark_catalog.json` + `docs/CATALOGUE_SEAMARK.md` | C1–C3 |
| `backend/app/core/judge.py` + tests | C15 |
| `backend/tests/test_review*.py` / `test_capitaineries.py` | Phrases de test §0 |

### Vague 3 (NOAA / GEBCO)

| Fichier | Rôle |
|---------|------|
| `backend/app/services/capitainerie_world.py` ou `noaa_enc.py` | H2 (nouveau module **si** le fichier dépasse le bureau) |
| `backend/app/routers/` | Export feux / bouées US |
| `naviguide-simulator` / copie routing | H5 lookup GEBCO |
| `backend/tests/test_capitaineries.py` | Patterns NOAA à étendre |

### Vague 4 (satellite)

| Fichier | Rôle |
|---------|------|
| `scripts/satellite/README.md` | S0 + recette Mac |
| `scripts/satellite/*.py` | STAC CDSE, exports ; **pas** ACOLITE vendu dans l’image VPS |
| `backend/app/services/science_build.py` / router | Ingérer le GeoJSON pilote (`source: sentinel-pilot`) |
| `frontend/src/components/SciencePanel.js` | Filtre Satellite |
| `naviguide-simulator/src/engine/ici.js` | Champ science local |

**Interdit de toucher** (ce plan) : `naviguide/naviguide-app/` prod,
`infra/vps/sync-from-atlas.sh`, cubes NetCDF sur le VPS.

---

## 15. Recette

Recette **globale** une fois les quatre vagues faites. Chaque vague
a la sienne au §13.

1. Fond mer : modale → accepter → bandeau toujours là.
2. Mode Marinas : allumer EMODnet bathy **sans** passer par Science.
3. Overlay de la semaine visible ; `metadata.version` de l’export =
   stamp de la release `data-*`.
4. Gold d’une capitainerie : Map inchangée tant que « Afficher la
   review » est décoché.
5. Fiche marina : un SMCFAC à 200 m s’affiche comme **contrôle**,
   pas comme identité.
6. Juge : citation VHF → `true` ; pub resto → `false`.
7. Chesapeake : feu ou bouée NOAA. Golfe de Gascogne : **zéro** NOAA.
8. Atlantique large : GEBCO répond dans le simulateur. Dans un port :
   `null`.
9. Science + pilote : trait de côte + `error_m` vs EMODnet + bandeau.
   Onglet Review = placeholder.
10. Prod `blueintelligence.online` / `naviguide.fr` : ce plan ne les
    déploie **pas** tout seul. Vague 1–2 = PR BI. Vague 3–4
    simulateur = PR `naviguide-simulator/` seulement.

---

## 16. Risques

| Risque | Mitigation |
|--------|------------|
| Seascape sans attribut → isobathe impossible | M14 d’abord ; sinon EMODnet + depth point |
| Release GitHub injoignable pour l’overlay | Copie VPS `current.pmtiles` (petit) |
| WMS EMODnet partout : perf / lisibilité | Défaut **off** ; panes `pointer-events: none` déjà |
| Confondre CDSE et CMEMS | S0 bloquant ; deux README |
| ACOLITE trop lourd | Jamais sur le VPS ; 1–2 scènes |
| Gold trop facile (OSM ⇒ Gold) | C8–C10 avant d’afficher plus d’objets NOAA |
| Présenter SDB comme un sondage | `kind` / `method` / disclaimer ; Review off |
| Étendre NOAA au monde | Filtre bbox ENC Direct ; test Méditerranée = 0 |
| Coller GEBCO sur un port | `null` sous le seuil côtier |
| VLM « qui voit la carte » | Prompt + tests : mention textuelle seulement |

---

## 17. Hors périmètre

- Encodeur / décodeur **S-101** ou lecture de fichiers **S-57**.
- **IENC / VNF** (navigation intérieure).
- Isobathes **vectorielles** EMODnet sur le VPS.
- GEBCO comme couche portuaire ou fond BI.
- Géoréférencement d’image (croquis, PDF carte, Sentinel) par VLM
  ou par `geo.py`.
- Moteur **S-52** complet (symboles, secteurs de feux, safety
  contour ECDIS).
- Review / Gold Science, Climatologie, pilotes Sentinel (V1).
- Modifier `naviguide.fr` (prod) ou fusionner simulateur ↔ prod.
- Fleuves, lacs, hors corridor pour Sentinel.
- StormGlass / Windy / cartes payantes comme source.

---

## 18. Documents dont ce plan hérite

| Document | Ce qu’on en garde |
|----------|-------------------|
| `README.md` | Fond Seamap, exports sha256, catalogue, avertissement |
| `docs/CATALOGUE_SEAMARK.md` | OSM → champs BI ; audit ; pas d’invention |
| `docs/CONTRATS_MODES.md` | 7 modes ; Science = API structurées ; géocodage = noms |
| `docs/CONTRATS_REVIEW_PAR_MODE.md` | Méta-contrat Gold ; « Afficher la review » ; pas Science/Climat |
| `docs/CAHIER_DES_CHARGES_REVIEW.md` | File humaine Formalités |
| `docs/PLAN_IMPLEMENTATION_CLIMATOLOGIE.md` | BI montre / NAVIGUIDE s’en sert ; hors VPS ; `null` honnête |
| `docs/PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md` | Leaflet ; prod intouchée ; pastilles ; `ici()` |
| `docs/hackathon-nebius-nvidia.md` | Gold + Tavily + Ultra ; Science = 0 ou 1 local ; disclaimer |
| `infra/vps/seamap/README.md` | Miroir PMTiles ; cron lundi ; pas de GPL Seamap |
| `.github/workflows/weekly-data-build.yml` | Overlay déjà construit |

En cas de conflit :

- **objet d’un mode** → `CONTRATS_MODES.md` ;
- **Gold / carte** → `CONTRATS_REVIEW_PAR_MODE.md` §0 et §8 ;
- **fond mer / overlay** → ce plan, vague 1 ;
- **simulateur vs prod** → plan étape 1 (Leaflet, prod intouchée) ;
- **S-101 / S-57 / calage pixel** → §4 de ce plan (refusé).
