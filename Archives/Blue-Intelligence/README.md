<div align="center">

# Blue Intelligence

**Maritime AI OSINT Swarm** — Autonomous mapping of marine conservation projects

CONFIRMATION CODE : Sailwithpirates2028

www.blueintelligence.online

<br />

<table>
  <tr>
    <td align="center" width="33%">
      <a href="https://www.blueintelligence.online" target="_blank" rel="noreferrer">
        <img src="public/logo-blue-intelligence.svg" alt="Blue Intelligence" width="80" height="80" />
      </a>
      <br />
      <strong>Blue Intelligence</strong>
      <br />
      <sub>Maritime OSINT</sub>
    </td>
    <td align="center" width="33%">
      <a href="https://www.naviguide.fr" target="_blank" rel="noreferrer">
        <img src="public/logo-naviguide.png" alt="NAVIGUIDE" width="80" height="80" />
      </a>
      <br />
      <strong>NAVIGUIDE</strong>
      <br />
      <sub>Intelligent navigation</sub>
    </td>
    <td align="center" width="33%">
      <a href="https://www.berry-mappemonde.org" target="_blank" rel="noreferrer">
        <img src="public/logo-berry-mappemonde.png" alt="Berry-Mappemonde" width="80" height="80" />
      </a>
      <br />
      <strong>Berry-Mappemonde</strong>
      <br />
      <sub>Maritime expedition</sub>
    </td>
  </tr>
</table>

<br />

*Impact module of the NAVIGUIDE ecosystem — 45,000 nautical miles, 13 overseas territories*

</div>

---

## About

**Blue Intelligence** transforms the living web of maritime data into an executable geospatial database. The application deploys AI agents (TinyFish + Claude) to discover, extract, and map marine conservation projects worldwide.

- 🗺️ **Interactive map** — GeoJSON projects, clusters, filters by funder
- 🤖 **ETL Swarm** — Autonomous discovery via MasterSeeds + DeepLinkCache
- 🌊 **3-stage pipeline** — Haiku gatekeeper → Sonnet extract → S_ocean scoring
- 📍 **Coastal snapping** — Coordinates recalculated to maritime zones
- 🔄 **100% local** — SQLite, runs entirely on your machine
- ⚙️ **Parameters** — Stored in browser (localStorage), sent to server on swarm deploy

---

## Quick start

**Prerequisites:** Node.js 18+

```bash
# 1. Installer les dépendances
npm install

# 2. Vérifier l'environnement (TensorFlow, better-sqlite3)
npm run verify-setup

# 3. Configurer les clés API (copier .env.example vers .env)
# - TINYFISH_API_KEY (requis pour l'extraction)
# - CLAUDE_API_KEY ou ANTHROPIC_API_KEY (requis pour l'analyse)
# - BLUEINTEL_CONFIRM_CODE (optionnel) : si défini, les actions sensibles (Swarm, Clear, Force Extract) exigent ce code. Utile pour hackathons/démo.

# 4. Lancer l'application (GSHHG intégré, pas de téléchargement)
npm run dev
```

> **Note :** TensorFlow utilise `@tensorflow/tfjs` (CPU pur JS) — pas de compilation native, fonctionne avec Node 25 et chemins avec espaces.

Open [http://localhost:3000](http://localhost:3000).

### Dépannage

| Problème | Solution |
|----------|----------|
| `Cannot find package '@tensorflow/...'` | `npm install` puis `npm run verify-setup` |
| Erreur better-sqlite3 | Node 20 LTS recommandé : installer [nvm](https://github.com/nvm-sh/nvm) puis `nvm install 20 && nvm use 20` |

---

## Links

| | |
|---|---|
| **Blue Intelligence Discord** | [discord.gg/zQcPgxpH](https://discord.gg/zQcPgxpH) |
| **NAVIGUIDE Discord** | [discord.gg/UPTWWGtE](https://discord.gg/UPTWWGtE) |
| **Berry-Mappemonde Discord** | [discord.gg/NsWrxXUQ](https://discord.gg/NsWrxXUQ) |
| **NAVIGUIDE** | [naviguide.fr](https://naviguide.fr) |
| **Berry-Mappemonde** | [berry-mappemonde.org](https://berry-mappemonde.org) |
| **GitHub** | [NAVIGUIDE-for-Berry-Mappemonde/Blue-Intelligence](https://github.com/NAVIGUIDE-for-Berry-Mappemonde/Blue-Intelligence) |

---

<div align="center">

*Blue Intelligence — Maritime OSINT Swarm for NAVIGUIDE and Berry-Mappemonde*

</div>
