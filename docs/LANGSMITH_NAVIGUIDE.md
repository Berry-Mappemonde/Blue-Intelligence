# LangSmith — microscope Naviguide (sur ton Mac seulement)

Ce guide t’accompagne pas à pas. Tu n’as rien à installer sur le VPS.
LangSmith sert à **voir** ce que font les agents (prompts, nœuds, erreurs), pas à les héberger.

**Règle d’or :** microscope local. Jamais un tuyau de production.

---

## Ce que tu auras à la fin

1. Un plafond de dépense dans LangSmith (tes 100 $ restent un filet, pas un robinet ouvert).
2. Plusieurs **projets** séparés (`naviguide-meteo-dev`, `naviguide-orchestrator-dev`, …).
3. Une clé collée dans le `.env` de **ton Mac**.
4. Quelques **trajets or** envoyés comme traces, que tu ouvres dans le navigateur.

Durée : environ 20 minutes pour les clics LangSmith + 5 minutes de Terminal.

---

## Ce que tu ne feras pas

- Allumer Engine, Fleet, Sandboxes, ou « Deployment ».
- Mettre `LANGSMITH_TRACING=true` sur le VPS.
- Garder les traces 400 jours (laisse **14 jours**).
- Envelopper `backend/app/core/nvidia.py` : un batch ports / marinas = des milliers de traces.

Le code refuse le tracing s’il manque `LANGSMITH_LOCAL=1`, ou s’il détecte le VPS / une URL `naviguide.fr`.

---

## Étape 1 — Plafonds dans LangSmith (navigateur)

1. Ouvre [https://smith.langchain.com](https://smith.langchain.com) et connecte-toi.
2. En bas à gauche (ou l’engrenage) : **Settings**.
3. Onglet **Billing** / **Usage** / **Usage limits** (le libellé bouge un peu).
4. Pose un plafond, au choix :
   - **5 000 traces / mois** et **0 $ de dépassement**, ou
   - un **plafond à 20 $** si tu préfères un filet en dollars.
5. Rétention par défaut : **base, 14 jours** (pas « extended » / 400 jours).
6. Si tu vois **Engine** : **Disable** / désactive. N’ouvre pas Fleet, Sandboxes, Deployment.

Si tu ne trouves pas le plafond du premier coup : cherche « usage limits » dans Settings. Sans plafond, n’ajoute une carte bancaire **que** si tu es sûr de ce plafond — la carte ouvre le pay-as-you-go.

---

## Étape 2 — Créer les projets (pas un fourre-tout)

Toujours dans LangSmith, à gauche : **Projects** → **+ New Project**.

Crée-les **un par un**, noms exacts :

| Nom du projet | À quoi il sert |
|---|---|
| `naviguide-orchestrator-dev` | Graphe complet (agent 1 → agent 3 → briefing) |
| `naviguide-meteo-dev` | Agent météo + IBTrACS |
| `naviguide-guard-dev` | Agent sûreté |
| `naviguide-custom-dev` | Agent formalités / port |
| `naviguide-pirate-dev` | Agent rumours communauté |

Tu pourras couper un projet sans éteindre les autres.

---

## Étape 3 — Créer ta clé API

1. Settings → **API Keys** → **Create API Key**.
2. Copie la clé (elle commence souvent par `lsv2_`).
3. Garde-la pour l’étape 4. Ne la commite jamais, ne l’envoie pas sur le VPS.

---

## Étape 4 — Coller la clé dans le `.env` du Mac

Ouvre **Terminal** (Spotlight : `Terminal`).

Place-toi à la racine du dépôt (adapte le chemin si besoin) :

```bash
cd ~/Documents/Blue-Intelligence-Map
```

Si le fichier `naviguide/naviguide-api/.env` **n’existe pas encore** :

```bash
cp naviguide/naviguide-api/.env.example naviguide/naviguide-api/.env
```

Ouvre-le avec TextEdit :

```bash
open -e naviguide/naviguide-api/.env
```

Vérifie / complète **exactement** ces lignes :

```bash
LANGSMITH_LOCAL=1
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=colle_ta_cle_ici
LANGSMITH_PROJECT=naviguide-meteo-dev
LANGSMITH_TRACING_SAMPLING_RATE=1
```

- `LANGSMITH_LOCAL=1` est **obligatoire**. Sans lui, le code ignore le tracing.
- `LANGSMITH_TRACING=true` allume le microscope. Remets `false` quand tu as fini la séance.
- Le script des trajets or envoie chaque trajet dans **son** projet (météo, garde, …), même si `LANGSMITH_PROJECT` vaut `naviguide-meteo-dev`.

Enregistre (cmd+S) et ferme TextEdit.

Tu peux aussi lancer `./naviguide/naviguide_workspace/start_local.sh` : s’il manque le bloc LangSmith dans un ancien `.env`, le script l’ajoute (tracing encore `false`). Dans ce cas, rouvre le fichier et passe `LANGSMITH_TRACING` à `true`, puis colle la clé.

---

## Étape 5 — Vérifier que le garde-fou est content

Toujours dans Terminal, à la racine du dépôt :

```bash
python3 naviguide/scripts/langsmith_golden_legs.py --check
```

Tu dois voir quelque chose comme :

```
activé     : oui
raison     : enabled
projet     : naviguide-meteo-dev
clé        : présente
```

### Si `activé : non`

| Message | Que faire |
|---|---|
| `missing_local_flag` | Ajoute `LANGSMITH_LOCAL=1` dans le `.env`, enregistre, relance. |
| `tracing_not_requested` | Passe `LANGSMITH_TRACING=true`. |
| `production_host` / `production_url` / `production_env` | Tu es sur le VPS ou une URL de prod a fuité dans le `.env`. **S’arrête.** Enlève les variables LangSmith de ce `.env`. |
| clé MANQUANTE | Colle `LANGSMITH_API_KEY=…` |

Liste des trajets (sans rien lancer) :

```bash
python3 naviguide/scripts/langsmith_golden_legs.py --list
```

---

## Étape 6 — Enchaîner les trajets or

Les 5 trajets « agents » (météo ×2, garde, formalités, pirate) suffisent pour la première séance. **Pas** le tour du monde Berry-Mappemonde.

```bash
python3 naviguide/scripts/langsmith_golden_legs.py
```

Un seul trajet :

```bash
python3 naviguide/scripts/langsmith_golden_legs.py --only meteo-mayotte-reunion-janvier
```

Plus tard, les 2 graphes orchestrateur (plus lents, searoute) :

```bash
python3 naviguide/scripts/langsmith_golden_legs.py --with-orchestrator
```

Sans clé LLM (`NVIDIA_API_KEY` / `OPENROUTER_API_KEY` / `ANTHROPIC_API_KEY`), les agents tournent quand même : tu vois le graphe et le prompt, la réponse peut être le texte de secours. C’est déjà utile.

Chaque trajet imprime **quoi regarder** dans LangSmith.

---

## Étape 7 — Lire une trace

1. Retourne sur [https://smith.langchain.com](https://smith.langchain.com).
2. Ouvre le projet du trajet (ex. `naviguide-meteo-dev`).
3. Clique la **dernière** ligne (la plus récente).

Pour chaque run, coche :

1. **Quel nœud a pris du temps** (barre / waterfall).
2. **Le vrai prompt** envoyé au modèle (souvent la surprise).
3. Sur l’orchestrateur : si l’**agent 1 a échoué**, l’agent 3 ne doit **pas** avoir tourné.
4. Sur Mayotte → Réunion en janvier : le prompt contient l’entier **IBTrACS** ; le LLM ne doit pas inventer une « saison cyclone » à la place.

C’est ça la valeur : voir le graphe, pas « monitorer la prod ».

Remets ensuite `LANGSMITH_TRACING=false` dans le `.env` pour ne pas tracer tes clics du quotidien dans l’app locale.

---

## Étape 8 — Plus tard : petit jeu d’évaluation (à la main)

Ne le lance **pas** en boucle. Chaque eval = encore des traces.

Les cas figés sont dans `naviguide/data/langsmith_golden_legs.json`, clé `eval_cases` :

- citer l’entier IBTrACS, ne pas inventer une saison cyclone ;
- ne pas inventer un vent / une Hs hors StormGlass ;
- si l’agent 1 échoue, pas de rapport de risque agent 3.

Dans LangSmith : **Datasets** → nouveau jeu → ajoute 3 à 10 exemples à la main → lance **une** comparaison de prompts quand tu changes vraiment un texte. Pas tous les matins.

---

## Staging / production (rappel)

| Endroit | Réglage |
|---|---|
| Ton Mac, séance microscope | `LANGSMITH_LOCAL=1` et `LANGSMITH_TRACING=true` |
| Staging plus tard | échantillon `0.05` ou `0.1` — **pas maintenant** |
| VPS / production | variables **absentes** ou `LANGSMITH_TRACING=false`, **jamais** `LANGSMITH_LOCAL=1` |

---

## Fichiers touchés par ce microscope

| Fichier | Rôle |
|---|---|
| `naviguide/langsmith_local.py` | Garde-fou (coupe le tracing hors Mac) |
| `naviguide/naviguide-api/.env` | Tes secrets locaux (gitignoré) |
| `naviguide/scripts/langsmith_golden_legs.py` | Envoie les trajets or |
| `naviguide/data/langsmith_golden_legs.json` | Catalogue + cas d’éval |
