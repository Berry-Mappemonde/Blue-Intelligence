# Blue Intelligence

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE-MIT)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE-APACHE)
[![NVIDIA Nemotron](https://img.shields.io/badge/NVIDIA-Nemotron-76B900.svg)](https://www.nvidia.com/en-us/ai-data-science/foundation-models/nemotron/)
[![Nebius Token Factory](https://img.shields.io/badge/Nebius-Token%20Factory-0B1F3A.svg)](https://tokenfactory.nebius.com/)

A [Berry-Mappemonde](https://berrymappemonde.org) project. Code is **MIT or Apache-2.0**.

> [!WARNING]
> **Ne convient pas à la navigation / Not for navigation.**
> Les cartes et les chiffres viennent de sources publiques et de calculs.
> Ce n’est pas une carte marine officielle. Vérifiez toujours les publications
> gouvernementales avant une décision en mer.

**Blue Intelligence** ([blueintelligence.online](https://blueintelligence.online))
is the memory of maritime sources: Ports of Entry per EEZ, marinas,
harbour offices (capitaineries), marine protected areas, ocean science and
marine projects. Each record keeps its official source. An unknown field
stays empty; no figure is invented.

The live voyage application **NAVIGUIDE** is a separate repository:
[github.com/Berry-Mappemonde/NAVIGUIDE](https://github.com/Berry-Mappemonde/NAVIGUIDE)
([naviguide.fr](https://naviguide.fr)). It reads Blue Intelligence over its
public API, `https://blueintelligence.online/api`. The history of both
products before 18 October 2026 is in the read-only archive
[Blue-Intelligence-Map](https://github.com/Berry-Mappemonde/Blue-Intelligence-Map).

## GenAI.works — Open Agent Hackathon: pre-existing and new

Graded code starts on **22 October 2026 at 00:00 UTC**. Everything in this
repository before that time is pre-existing (production since 2026, history
preserved by the split).

| | Path | Status |
|---|---|---|
| Pre-existing | `backend/` (FastAPI + MongoDB API, PoE pipeline, marinas, science, projects), `frontend/` (React map), `infra/`, `scripts/`, `seed/`, `docs/` | in production on blueintelligence.online |
| New (planned) | `backend/app/agent_poe/` | not in the tree yet — see [docs/PLAN_HACKATHON_GENAI_BLUE_INTELLIGENCE.md](docs/PLAN_HACKATHON_GENAI_BLUE_INTELLIGENCE.md) |

## Dependencies

| Part | Runtime | Dependencies |
|---|---|---|
| API (`backend/`) | Python **3.12** | `backend/requirements.txt` (FastAPI, Motor/PyMongo, httpx, trafilatura, PyMuPDF, shapely…) |
| Database | **MongoDB** (local or Atlas) | database name from `DB_NAME` |
| Map (`frontend/`) | Node.js (version in `.nvmrc`) | `frontend/package.json` (React, Create React App, MapLibre/Leaflet, Tailwind) |
| Optional AI and search | — | NVIDIA NIM (Nemotron), OpenRouter, Anthropic, TinyFish, Serper, SearXNG, GeoNames. Without keys the API still runs; AI steps fall back to rules or are skipped. |

## Installation (macOS / Linux)

```bash
git clone https://github.com/Berry-Mappemonde/Blue-Intelligence.git
cd Blue-Intelligence

# API
cd backend
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
cat > .env <<'EOF'
MONGO_URL=mongodb://127.0.0.1:27017
DB_NAME=blueintel_db
CORS_ORIGINS=*
EOF
cd ..

# Map
cd frontend
npm ci
cd ..
```

Keys go in `backend/.env` only, never in git: `NVIDIA_API_KEY`,
`OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, `TINYFISH_API_KEY`,
`SERPER_API_KEY`, `SEARXNG_URL`, `GEONAMES_USERNAME`, `ADMIN_KEY`.
`LLM_PROVIDER=nvidia|openrouter|auto` selects the model provider.

Optional sample data (the same seed the CI uses):

```bash
cd backend
MONGO_URL=mongodb://127.0.0.1:27017 DB_NAME=blueintel_db .venv/bin/python scripts/seed_ci_mongo.py
```

## Usage

```bash
# API on http://127.0.0.1:8001/api/
cd backend && .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001

# Map on http://localhost:3000 (another terminal)
cd frontend && REACT_APP_BACKEND_URL=http://127.0.0.1:8001 npm start
```

Tests:

```bash
cd backend && .venv/bin/python -m pytest tests -q      # needs MongoDB and the API running
cd frontend && npm test                                # Jest
```

Production runs on an OVH VPS (`infra/vps/README.md`): every merge on
`main` passes CI (`.github/workflows/ci.yml`) and deploys
blueintelligence.online (`.github/workflows/deploy.yml`).

Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
Documentation index: [docs/README.md](docs/README.md).

## Licence

Code is **MIT or Apache License 2.0** (`LICENSE-MIT`, `LICENSE-APACHE`).
Data (OpenStreetMap, Marine Regions, EMODnet…) keeps its original licence.
Nemotron weights remain under the NVIDIA licence.

---

## Français (résumé)

**Blue Intelligence** est la mémoire des sources maritimes (ports d'entrée
par ZEE, marinas, capitaineries, aires protégées, science, projets), en
production sur [blueintelligence.online](https://blueintelligence.online).
Le voyage en direct **NAVIGUIDE** est dans son propre dépôt :
[github.com/Berry-Mappemonde/NAVIGUIDE](https://github.com/Berry-Mappemonde/NAVIGUIDE).
Installation et usage : voir les sections ci-dessus (Python 3.12, MongoDB,
Node.js ; `backend/.env` pour `MONGO_URL`, `DB_NAME` et les clés).

### Licence

Le code est sous **MIT ou Apache License 2.0** (`LICENSE-MIT`,
`LICENSE-APACHE`). Les données (OpenStreetMap, Marine Regions, EMODnet…)
gardent leur licence d’origine. Les poids Nemotron restent sous licence
NVIDIA.

Index des plans : [docs/README.md](docs/README.md).
