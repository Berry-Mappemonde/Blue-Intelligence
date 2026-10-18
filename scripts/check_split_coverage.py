#!/usr/bin/env python3
"""Classe chaque fichier suivi de main pour la séparation des dépôts.

Lecture seule : ne lance pas git filter-repo, n'écrit rien, ne pousse rien.

Depuis la racine du clone (après que ce script est sur la branche à filtrer) :

    python3 scripts/check_split_coverage.py
    python3 scripts/check_split_coverage.py --emit bi > /tmp/bi-paths.txt
    python3 scripts/check_split_coverage.py --emit ng > /tmp/ng-paths.txt
    git --git-dir=/tmp/bi-bare ls-tree -r --name-only HEAD \
        | python3 scripts/check_split_coverage.py --verify bi

Le code 0 veut dire : chaque fichier suivi a une classe, chaque fichier
supprimé ou renommé est couvert par le fichier de chemins du bon dépôt,
ou l'arbre vérifié ne contient que les chemins de ce dépôt. Le détail
des choix est dans docs/PLAN_SEPARATION_DEPOTS.md.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from typing import Iterable

# Un fichier a exactement une classe :
#   bi        dépôt Blue Intelligence seulement
#   ng        dépôt NAVIGUIDE seulement
#   both      les deux dépôts (copie)
#   excluded  ni l'un ni l'autre (reste dans l'archive)
#   uncovered erreur : le filtre ne sait pas où le mettre

EXCLUDED = {
    ".gitconfig": (
        "identité git emergent-agent-e1, pas un fichier de produit ; "
        "elle reste dans l'archive"
    ),
    "Archives/naviguide-nova/docs/PLAN_DEV_NOVA.md": (
        "doublon octet pour octet de la copie navsecops ; "
        "la classification documentaire le retire des dépôts neufs"
    ),
    "Archives/naviguide-nova/docs/SETUP_NOVA_CREDITS.md": (
        "doublon octet pour octet de la copie navsecops ; "
        "la classification documentaire le retire des dépôts neufs"
    ),
}

# Fichiers présents dans les deux dépôts. Contrôlés avant les préfixes,
# pour qu'un dossier NAVIGUIDE puisse quand même en prêter quelques-uns
# à Blue Intelligence.
BOTH_EXACT = {
    ".gitignore",
    ".nvmrc",
    "README.md",
    "LICENSE",
    "LICENSE-MIT",
    "LICENSE-APACHE",
    "Archives/README.md",
    "docs/PLAN_SEPARATION_DEPOTS.md",
    "docs/HACKATHON_PLAN.md",
    "docs/README.md",
    "docs/check_md_links.py",
    "docs/REGLES_PARAMETRES.md",
    "infra/vps/README.md",
    ".github/dependabot.yml",
    ".github/workflows/ci.yml",
    ".github/workflows/deploy.yml",
    "infra/vps/nginx-bi-climatology-cache.conf",
    "infra/vps/nginx-snippet-bi-climatology.conf",
    "infra/agents/.gitignore",
    "infra/agents/gh_token.py",
    "infra/agents/open_pr.py",
    "infra/agents/post_pr_comment.py",
    "infra/agents/review_collect.py",
    ".cursor/rules/base-de-donnees-vps.mdc",
    ".cursor/rules/environnement-utilisateur.mdc",
    ".cursor/rules/modeles-cursor-uniquement.mdc",
    ".cursor/rules/pas-de-verification-video.mdc",
    ".cursor/rules/reparations-sur-github.mdc",
}

BOTH_PREFIXES = (
    "infra/vps/ci/",
)

BI_EXACT = {
    ".cursor/environment.json",
    ".cursor/install.sh",
    ".cursor/preview.sh",
    ".cursor/start.sh",
    "infra/vps/blue-intelligence-backup.cron",
    "infra/vps/blue-intelligence.service",
    "infra/vps/bi-healthcheck.sh",
    "infra/vps/blue-intelligence-health.service",
    "infra/vps/blue-intelligence-health.timer",
    "infra/vps/install-memory-guards.sh",
    "infra/vps/nginx-bi-local-cache.conf",
    "infra/vps/deploy-app.sh",
    "infra/vps/install-mongodb.sh",
    "infra/vps/nginx-blue-intelligence.conf",
    "infra/vps/setup-memory.sh",
    "infra/vps/sync-from-atlas.sh",
    "infra/vps/sync-public-nginx.sh",
    ".github/workflows/weekly-data-build.yml",
}

BI_PREFIXES = (
    "backend/",
    "frontend/",
    "seed/",
    "scripts/",
    "Archives/Blue-Intelligence/",
    "infra/searxng/",
    "infra/vps/seamap/",
    "docs/data/",
    "prototype_ai_studio/",
    "test_reports/",
    "tests/",
    "app/",
    "src/",
)

# docs/ hors recette/ et data/ : liste fermée. Un fichier nouveau reste
# non classé, et ce script s'arrête, au lieu de partir dans le mauvais dépôt.
DOC_BI = {
    "docs/ARCHITECTURE.md",
    "docs/CAHIER_DES_CHARGES_POE.md",
    "docs/CAHIER_DES_CHARGES_PROJETS.md",
    "docs/CAHIER_DES_CHARGES_REVIEW.md",
    "docs/CATALOGUE_SEAMARK.md",
    "docs/CONTRATS_MODES.md",
    "docs/CONTRATS_REVIEW_PAR_MODE.md",
    "docs/ETAT_DES_LIEUX_DOCS.md",
    "docs/PLAN_HACKATHON_GENAI_BLUE_INTELLIGENCE.md",
    "docs/MASTER_PLAN_GENAI_HACKATHON_BI.md",
    "docs/MENAGE_DOCUMENTAIRE_PROPOSITION.md",
    "docs/PRD.md",
    "docs/design_guidelines.json",
    "docs/poe-confirmed-gps-audit.md",
    "docs/poe-name-only-33.md",
    "docs/poe-seeds-bottom-up.md",
    "docs/audits/2026-09-10-tags.md",
    "docs/audits/2026-09-14-filieres-diagnostic.md",
    "docs/archives/HACKATHON_OPEN_AGENT_2026.md",
    "docs/archives/PLAN_IMPLEMENTATION_CLIMATOLOGIE.md",
    "docs/archives/PLAN_IMPLEMENTATION_FILIERES_CARTO.md",
}

DOC_NG = {
    "docs/ESPRIT_DE_L_APPLICATION.md",
    "docs/FILM_DISCOURS_ETAT_2026-09-28.md",
    "docs/HACKATHON_DEVPOST_SOUMISSION.md",
    "docs/LOTS_ORDRE_ET_PROMPTS.md",
    "docs/MANUEL_UTILISATEUR.md",
    "docs/PLAN_AUDIT_CALCULS.md",
    "docs/PLAN_BATCH_2026-10-14.md",
    "docs/PLAN_BATCH_2026-10-16.md",
    "docs/PLAN_BATCH_SUIVANT_2026-09-29.md",
    "docs/PLAN_CORRECTIONS_2026-09-22.md",
    "docs/PLAN_CORRECTIONS_2026-09-23.md",
    "docs/PLAN_CORRECTIONS_2026-09-26-s2.md",
    "docs/PLAN_CORRECTIONS_2026-09-26-s4.md",
    "docs/PLAN_CORRECTIONS_2026-09-27-s5.md",
    "docs/PLAN_CORRECTIONS_2026-09-28-film.md",
    "docs/PLAN_CORRECTIONS_REVUE_21_SEPT.md",
    "docs/PLAN_CORRECTIONS_REVUE_21_SEPT_SOIR.md",
    "docs/PLAN_DEUX_MODES_2026-09-29.md",
    "docs/PLAN_FILM_REVOIR_EXPEDITION.md",
    "docs/PLAN_GLOBE_3D.md",
    "docs/PLAN_HACKATHON_NEBIUS_NAVIGUIDE.md",
    "docs/PLAN_ICI_JOURNAL_EXPERT.md",
    "docs/PLAN_LOTS_COMPLEMENTAIRE_SIMULATEUR.md",
    "docs/PLAN_MIGRATION_ANCIEN_NAVIGUIDE.md",
    "docs/PLAN_NEMOTRON_NEBIUS_TAVILY.md",
    "docs/REGLES_WORKFLOW_AGENT.md",
    "docs/REVUE_PORTEUR_2026-10-14.md",
    "docs/SPECS_E2E_TRIAGE_2026-09-29.md",
    "docs/USER_MANUAL.md",
    "docs/WORKFLOW_INDUSTRIEL.md",
    "docs/ici-tout.md",
    "docs/audits/CALCULS.md",
    "docs/audits/CALCULS_ETAT_DE_L_ART.md",
    "docs/audits/PROFIL_BUILD_PROD_2026-09-19.md",
    "docs/audits/PROFIL_ZOOM_2026-09-20.md",
    "docs/audits/zoom-profile-after.json",
    "docs/audits/zoom-profile-before.json",
    "docs/archives/PLAN_CHANTIERS_STRUCTURANTS_SIMULATEUR.md",
    "docs/archives/PLAN_GENERAL_DEVELOPPEMENT_SIMULATEUR.md",
    "docs/archives/PLAN_IMPLEMENTATION_EVENEMENTS_ICI_LLM.md",
    "docs/archives/PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.en.md",
    "docs/archives/PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md",
    "docs/archives/PLAN_IMPLEMENTATION_SIMULATION_A.md",
    "docs/archives/PLAN_IMPLEMENTATION_SIMULATION_B.md",
    "docs/archives/PLAN_IMPLEMENTATION_SIMULATOR_SUIVRE_ET_SIMULATION.md",
    "docs/archives/PLAN_IMPLEMENTATION_SKIPPER_VIRTUEL.md",
    "docs/archives/PLAN_LOTS_AGENT_SIMULATEUR.md",
    "docs/archives/PLAN_PIPELINE_AFFICHAGE_SIMULATEUR.md",
    "docs/archives/PLAN_UI_PRODUIT_SIMULATEUR.md",
    "docs/archives/hackathon-nebius-nvidia.en.md",
    "docs/archives/hackathon-nebius-nvidia.md",
    "docs/archives/nvidia-llm-audit.md",
}

NG_EXACT = {
    ".cursor/hooks.json",
    ".cursor/rules/anti-regression-visuelle-simulateur.mdc",
    ".cursor/rules/naviguide-simulator-preview.mdc",
    ".cursor/rules/specs-suivent-l-interface.mdc",
    ".github/workflows/zap-baseline.yml",
}

NG_PREFIXES = (
    "naviguide-simulator/",
    "naviguide/",
    "Archives/naviguide-nova/",
    "Archives/naviguide-navsecops/",
    ".zap/",
    ".vscode/",
    "docs/recette/",
    "infra/vps/naviguide/",
    "infra/agents/",
    ".cursor/hooks/",
)

# Dossiers purs : une ligne « dossier/ » dans le fichier de filtre garde aussi
# les fichiers autrefois dedans (renommés ou supprimés). filter-repo ne suit
# pas les renommages si l'ancien chemin n'est pas demandé.
BI_DIRS = (
    "backend/",
    "frontend/",
    "seed/",
    "scripts/",
    "Archives/Blue-Intelligence/",
    "infra/searxng/",
    "infra/vps/seamap/",
    "infra/vps/ci/",
    "docs/data/",
    "prototype_ai_studio/",
    "test_reports/",
    "tests/",
    "app/",
    "src/",
)
NG_DIRS = (
    "naviguide-simulator/",
    "naviguide/",
    "Archives/naviguide-navsecops/",
    ".zap/",
    ".vscode/",
    "docs/recette/",
    "infra/vps/naviguide/",
    "infra/agents/",
    ".cursor/hooks/",
)
BOTH_DIRS = ()
# Fichiers qui ne sont plus sur main, mais dont l'historique appartient
# encore à un dépôt. filter-repo ne suit pas les renommages : l'ancien
# chemin doit être une ligne à part, sauf s'il est déjà sous un dossier pur.
# backend/poe.py est couvert par backend/. Le PRD a vécu dans memory/PRD.md.
HIST_BI_FILES = (
    "backend_test.py",
    "test_result.md",
    "index.html",
    "package.json",
    "server.ts",
    "tsconfig.json",
    "vite.config.ts",
    "metadata.json",
    "scrape_inspect.ts",
    "scrape_test.ts",
    "design_guidelines.json",
    "ports_of_entry.geojson",
    "blue_intelligence_projects (7).geojson",
    "memory/PRD.md",
    "docs/HACKATHON_OPEN_AGENT_2026.md",
    "docs/PLAN_IMPLEMENTATION_CLIMATOLOGIE.md",
    "docs/PLAN_IMPLEMENTATION_FILIERES_CARTO.md",
)
HIST_NG_FILES = (
    "docs/PLAN_CHANTIERS_STRUCTURANTS_SIMULATEUR.md",
    "docs/PLAN_GENERAL_DEVELOPPEMENT_SIMULATEUR.md",
    "docs/PLAN_IMPLEMENTATION_EVENEMENTS_ICI_LLM.md",
    "docs/PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.en.md",
    "docs/PLAN_IMPLEMENTATION_NAVIGUIDE_SIMULATOR_ETAPE1.md",
    "docs/PLAN_IMPLEMENTATION_SIMULATION_A.md",
    "docs/PLAN_IMPLEMENTATION_SIMULATION_B.md",
    "docs/PLAN_IMPLEMENTATION_SIMULATOR_SUIVRE_ET_SIMULATION.md",
    "docs/PLAN_IMPLEMENTATION_SKIPPER_VIRTUEL.md",
    "docs/PLAN_LOTS_AGENT_SIMULATEUR.md",
    "docs/PLAN_PIPELINE_AFFICHAGE_SIMULATEUR.md",
    "docs/PLAN_UI_PRODUIT_SIMULATEUR.md",
    "docs/PROFIL_BUILD_PROD_2026-09-19.md",
    "docs/hackathon-nebius-nvidia.en.md",
    "docs/hackathon-nebius-nvidia.md",
    "docs/nvidia-llm-audit.md",
)
# Restent dans l'archive seulement. .env.example contenait une valeur de
# clé ; memory/test_credentials.md est un aide-mémoire de noms de clés.
# memory/PRD.md n'est pas dans cette liste : son historique va dans
# Blue Intelligence (renommé ensuite docs/PRD.md).
HIST_EXCLUDED_PREFIXES = (
    ".emergent/",
)
HIST_EXCLUDED_FILES = (
    ".env.example",
    "package-lock.json",
    "memory/test_credentials.md",
)

# Présence exigée après le filtre. Préfixe (terminé par /) ou chemin exact.
BI_REQUIRED = (
    "backend/",
    "frontend/",
    "seed/",
    "scripts/audit_tags.py",
    ".gitignore",
    ".nvmrc",
    ".github/workflows/ci.yml",
    ".github/workflows/deploy.yml",
    ".github/workflows/weekly-data-build.yml",
    ".cursor/environment.json",
    ".cursor/rules/base-de-donnees-vps.mdc",
    "infra/vps/deploy-app.sh",
    "infra/vps/ci/plan_deploy.py",
    "infra/vps/nginx-bi-climatology-cache.conf",
    "infra/agents/gh_token.py",
    "docs/PRD.md",
    "docs/PLAN_HACKATHON_GENAI_BLUE_INTELLIGENCE.md",
    "docs/PLAN_SEPARATION_DEPOTS.md",
    "docs/REGLES_PARAMETRES.md",
    "docs/data/",
    "Archives/Blue-Intelligence/",
    "LICENSE",
)

BI_FORBIDDEN = (
    "naviguide-simulator/",
    "naviguide/",
    "Archives/naviguide-nova/",
    "Archives/naviguide-navsecops/",
    ".zap/",
    ".vscode/",
    ".gitconfig",
    ".cursor/hooks.json",
    ".cursor/hooks/",
    ".cursor/rules/anti-regression-visuelle-simulateur.mdc",
    ".cursor/rules/specs-suivent-l-interface.mdc",
    "docs/PLAN_BATCH_2026-10-16.md",
    "infra/vps/naviguide/",
    "infra/agents/run_lots.py",
    "infra/agents/vl_film_review.py",
    "docs/recette/",
    "docs/LOTS_ORDRE_ET_PROMPTS.md",
    "docs/HACKATHON_DEVPOST_SOUMISSION.md",
    "docs/archives/nvidia-llm-audit.md",
    ".github/workflows/zap-baseline.yml",
)

NG_REQUIRED = (
    "naviguide-simulator/",
    "naviguide/",
    "infra/vps/naviguide/",
    "infra/vps/ci/plan_deploy.py",
    "infra/vps/nginx-bi-climatology-cache.conf",
    "infra/vps/nginx-snippet-bi-climatology.conf",
    "infra/agents/run_lots.py",
    "infra/agents/gh_token.py",
    ".zap/rules.tsv",
    ".gitignore",
    ".nvmrc",
    ".github/workflows/ci.yml",
    ".github/workflows/deploy.yml",
    ".github/workflows/zap-baseline.yml",
    ".cursor/hooks.json",
    ".cursor/hooks/",
    ".cursor/rules/anti-regression-visuelle-simulateur.mdc",
    ".cursor/rules/specs-suivent-l-interface.mdc",
    ".cursor/rules/base-de-donnees-vps.mdc",
    "docs/LOTS_ORDRE_ET_PROMPTS.md",
    "docs/PLAN_BATCH_2026-10-16.md",
    "docs/HACKATHON_DEVPOST_SOUMISSION.md",
    "docs/PLAN_HACKATHON_NEBIUS_NAVIGUIDE.md",
    "docs/PLAN_SEPARATION_DEPOTS.md",
    "docs/REGLES_PARAMETRES.md",
    "docs/recette/",
    "Archives/naviguide-nova/",
    "Archives/naviguide-navsecops/",
    "LICENSE",
)

NG_FORBIDDEN = (
    "backend/",
    "frontend/",
    "seed/",
    "scripts/",
    "Archives/Blue-Intelligence/",
    "infra/searxng/",
    "infra/vps/seamap/",
    "infra/vps/deploy-app.sh",
    "infra/vps/install-mongodb.sh",
    "infra/vps/sync-from-atlas.sh",
    ".gitconfig",
    ".cursor/environment.json",
    ".cursor/install.sh",
    "infra/vps/ci/README.md",
    "docs/ETAT_DES_LIEUX_DOCS.md",
    "docs/PRD.md",
    "Archives/naviguide-nova/docs/PLAN_DEV_NOVA.md",
    "Archives/naviguide-nova/docs/SETUP_NOVA_CREDITS.md",
    "docs/data/",
    "docs/PLAN_HACKATHON_GENAI_BLUE_INTELLIGENCE.md",
    ".github/workflows/weekly-data-build.yml",
    "prototype_ai_studio/",
    "test_reports/",
    "tests/",
    "app/",
    "src/",
    "backend_test.py",
    "memory/PRD.md",
)


def is_excluded(path: str) -> bool:
    return (
        path in EXCLUDED
        or path in HIST_EXCLUDED_FILES
        or _starts(path, HIST_EXCLUDED_PREFIXES)
    )


def classify(path: str) -> str:
    if is_excluded(path):
        return "excluded"
    # Le dossier ci/ est partagé, son README ne l'est pas (proposition #553).
    if path == "infra/vps/ci/README.md":
        return "bi"
    if path in BOTH_EXACT or _starts(path, BOTH_PREFIXES):
        return "both"
    if (
        path in BI_EXACT
        or path in DOC_BI
        or path in HIST_BI_FILES
        or _starts(path, BI_PREFIXES)
    ):
        return "bi"
    if (
        path in NG_EXACT
        or path in DOC_NG
        or path in HIST_NG_FILES
        or _starts(path, NG_PREFIXES)
    ):
        return "ng"
    return "uncovered"


def _starts(path: str, prefixes: Iterable[str]) -> bool:
    return any(path.startswith(prefix) for prefix in prefixes)


def tracked_files() -> list[str]:
    out = subprocess.check_output(
        ["git", "ls-files", "-z"],
        text=True,
    )
    return [p for p in out.split("\0") if p]


def _under(path: str, dirs: Iterable[str]) -> bool:
    return any(path.startswith(prefix) for prefix in dirs)


def emit(side: str, paths: Iterable[str]) -> list[str]:
    wanted = {"bi", "both"} if side == "bi" else {"ng", "both"}
    dirs = (BI_DIRS + BOTH_DIRS) if side == "bi" else (NG_DIRS + BOTH_DIRS)
    lines = list(dirs)
    lines.extend(HIST_BI_FILES if side == "bi" else HIST_NG_FILES)
    for path in paths:
        if classify(path) not in wanted:
            continue
        if _under(path, dirs):
            continue
        lines.append(path)
    return sorted(set(lines))


def covers(lines: Iterable[str], path: str) -> bool:
    for line in lines:
        if line == path:
            return True
        if line.endswith("/") and path.startswith(line):
            return True
    return False


def deleted_paths() -> list[str]:
    out = subprocess.check_output(
        ["git", "log", "--diff-filter=D", "--name-only", "--pretty=format:"],
        text=True,
    )
    return sorted({p for p in out.splitlines() if p})


def renamed_pairs() -> list[tuple[str, str]]:
    out = subprocess.check_output(
        ["git", "log", "--diff-filter=R", "--name-status", "--pretty=format:"],
        text=True,
    )
    pairs = []
    for line in out.splitlines():
        if not line.startswith("R"):
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        pairs.append((parts[1], parts[2]))
    return pairs


def history_gaps(deleted: Iterable[str], bi_lines: list[str], ng_lines: list[str]) -> list[str]:
    gaps = []
    for path in deleted:
        if is_excluded(path):
            continue
        if covers(bi_lines, path) or covers(ng_lines, path):
            continue
        gaps.append(path)
    return gaps


def rename_gaps(pairs: Iterable[tuple[str, str]], bi_lines: list[str], ng_lines: list[str]) -> list[str]:
    gaps = []
    for old, new in pairs:
        kind = classify(new)
        if kind == "excluded":
            if covers(bi_lines, old) or covers(ng_lines, old):
                gaps.append(f"exclu mais couvert : {old} => {new}")
            continue
        if kind == "uncovered":
            gaps.append(f"cible non classée : {old} => {new}")
            continue
        sides = ("bi", "ng") if kind == "both" else (kind,)
        for side in sides:
            lines = bi_lines if side == "bi" else ng_lines
            if not covers(lines, old):
                gaps.append(f"ancien chemin absent de {side} : {old} => {new}")
            if not covers(lines, new):
                gaps.append(f"nouveau chemin absent de {side} : {old} => {new}")
    return gaps


def placement_gaps(paths: Iterable[str], bi_lines: list[str], ng_lines: list[str]) -> list[str]:
    gaps = []
    for path in paths:
        kind = classify(path)
        in_bi = covers(bi_lines, path)
        in_ng = covers(ng_lines, path)
        if kind == "excluded" and (in_bi or in_ng):
            gaps.append(f"exclu mais émis : {path}")
        elif kind == "bi" and in_ng:
            gaps.append(f"Blue Intelligence émis dans NAVIGUIDE : {path}")
        elif kind == "bi" and not in_bi:
            gaps.append(f"Blue Intelligence absent de l'émission : {path}")
        elif kind == "ng" and in_bi:
            gaps.append(f"NAVIGUIDE émis dans Blue Intelligence : {path}")
        elif kind == "ng" and not in_ng:
            gaps.append(f"NAVIGUIDE absent de l'émission : {path}")
        elif kind == "both" and not (in_bi and in_ng):
            gaps.append(f"partagé incomplet : {path}")
    return gaps


def _present(paths: set[str], needle: str) -> bool:
    if needle in paths:
        return True
    for path in paths:
        if path.endswith("/") and needle.startswith(path):
            return True
        if needle.endswith("/") and path.startswith(needle):
            return True
    return False


def verify(side: str, paths: list[str]) -> list[str]:
    errors: list[str] = []
    allowed = {"bi", "both"} if side == "bi" else {"ng", "both"}
    required = BI_REQUIRED if side == "bi" else NG_REQUIRED
    forbidden = BI_FORBIDDEN if side == "bi" else NG_FORBIDDEN
    seen = set(paths)
    for path in paths:
        kind = classify(path)
        if kind not in allowed:
            errors.append(f"interdit dans {side} ({kind}) : {path}")
    for needle in required:
        if not _present(seen, needle):
            errors.append(f"manquant dans {side} : {needle}")
    for needle in forbidden:
        if _present(seen, needle):
            errors.append(f"encore présent dans {side} : {needle}")
    return errors


def self_test() -> int:
    cases = {
        ".gitconfig": "excluded",
        "backend/app/services/poe_pipeline.py": "bi",
        "frontend/src/index.js": "bi",
        "naviguide-simulator/server/main.py": "ng",
        "naviguide/naviguide-app/.env": "ng",
        ".github/workflows/ci.yml": "both",
        ".github/workflows/weekly-data-build.yml": "bi",
        ".github/workflows/zap-baseline.yml": "ng",
        ".gitignore": "both",
        ".nvmrc": "both",
        "Archives/Blue-Intelligence/docs/DEPLOIEMENT-VPS-OVH.md": "bi",
        "Archives/naviguide-nova/docs/PLAN_DEV_NOVA.md": "excluded",
        "Archives/naviguide-nova/docs/SETUP_NOVA_CREDITS.md": "excluded",
        "Archives/naviguide-nova/README.md": "ng",
        "Archives/naviguide-navsecops/docs/PLAN_DEV_NOVA.md": "ng",
        "Archives/README.md": "both",
        "infra/agents/run_lots.py": "ng",
        "infra/agents/gh_token.py": "both",
        "infra/agents/vl_film_review.py": "ng",
        "infra/vps/naviguide/deploy-simulator.sh": "ng",
        "infra/vps/deploy-app.sh": "bi",
        "infra/vps/bi-healthcheck.sh": "bi",
        "infra/vps/install-memory-guards.sh": "bi",
        "docs/MASTER_PLAN_GENAI_HACKATHON_BI.md": "bi",
        "docs/MENAGE_DOCUMENTAIRE_PROPOSITION.md": "bi",
        "infra/vps/ci/plan_deploy.py": "both",
        "infra/vps/ci/README.md": "bi",
        "infra/vps/nginx-bi-climatology-cache.conf": "both",
        "infra/searxng/docker-compose.yml": "bi",
        "docs/recette/lot-f1/a.jpg": "ng",
        "docs/data/poe-gps-arbitrated.json": "bi",
        "docs/PRD.md": "bi",
        "docs/REGLES_PARAMETRES.md": "both",
        "docs/LOTS_ORDRE_ET_PROMPTS.md": "ng",
        "docs/PLAN_BATCH_2026-10-16.md": "ng",
        ".cursor/rules/specs-suivent-l-interface.mdc": "ng",
        "docs/ici-tout.md": "ng",
        "docs/PLAN_SEPARATION_DEPOTS.md": "both",
        ".cursor/environment.json": "bi",
        ".cursor/hooks/simulator-ensure-dev.sh": "ng",
        ".cursor/rules/base-de-donnees-vps.mdc": "both",
        "docs/ETAT_DES_LIEUX_DOCS.md": "bi",
        "docs/archives/nvidia-llm-audit.md": "ng",
        "docs/nvidia-llm-audit.md": "ng",
        ".cursor/rules/pas-de-verification-video.mdc": "both",
        ".zap/rules.tsv": "ng",
        ".vscode/tasks.json": "ng",
        "seed/ports_of_entry.geojson": "bi",
        "scripts/audit_tags.py": "bi",
        "quelque-chose-de-nouveau": "uncovered",
        "backend/poe.py": "bi",
        "memory/PRD.md": "bi",
        "memory/test_credentials.md": "excluded",
        ".env.example": "excluded",
        "package-lock.json": "excluded",
        "frontend/package-lock.json": "bi",
        ".emergent/emergent.yml": "excluded",
        "prototype_ai_studio/index.html": "bi",
        "src/App.tsx": "bi",
        "app/scrape_inspect2.ts": "bi",
        "test_result.md": "bi",
        "backend_test.py": "bi",
        "docs/PLAN_IMPLEMENTATION_CLIMATOLOGIE.md": "bi",
        "docs/archives/PLAN_IMPLEMENTATION_CLIMATOLOGIE.md": "bi",
        "docs/PLAN_UI_PRODUIT_SIMULATEUR.md": "ng",
        "docs/archives/PLAN_UI_PRODUIT_SIMULATEUR.md": "ng",
        "blue_intelligence_projects (7).geojson": "bi",
        "ports_of_entry.geojson": "bi",
    }
    failed = 0
    for path, expected in cases.items():
        got = classify(path)
        if got != expected:
            print(f"self-test : {path} classé {got}, attendu {expected}", file=sys.stderr)
            failed += 1
    overlap = (DOC_BI & DOC_NG) | (DOC_BI & BOTH_EXACT) | (DOC_NG & BOTH_EXACT)
    if overlap:
        print(f"self-test : docs classés deux fois : {sorted(overlap)}", file=sys.stderr)
        failed += 1
    bi_lines = emit("bi", ["docs/PRD.md", "docs/design_guidelines.json", "seed/projects.geojson"])
    ng_lines = emit("ng", ["docs/archives/PLAN_UI_PRODUIT_SIMULATEUR.md"])
    held = {
        "backend/poe.py": ("bi", True),
        "memory/PRD.md": ("bi", True),
        "memory/test_credentials.md": ("bi", False),
        ".env.example": ("bi", False),
        "src/App.tsx": ("bi", True),
        "docs/PLAN_UI_PRODUIT_SIMULATEUR.md": ("ng", True),
        "docs/PLAN_IMPLEMENTATION_CLIMATOLOGIE.md": ("bi", True),
        "Archives/Blue-Intelligence/docs/DEPLOIEMENT-VPS-OVH.md": ("ng", False),
        "naviguide-simulator/server/main.py": ("bi", False),
    }
    for path, (side, wanted) in held.items():
        lines = bi_lines if side == "bi" else ng_lines
        if covers(lines, path) != wanted:
            print(f"self-test : couverture {side} de {path} inattendue", file=sys.stderr)
            failed += 1
    sample = rename_gaps(
        [
            ("backend/poe.py", "backend/app/services/poe_pipeline.py"),
            ("memory/PRD.md", "docs/PRD.md"),
            ("docs/PLAN_UI_PRODUIT_SIMULATEUR.md", "docs/archives/PLAN_UI_PRODUIT_SIMULATEUR.md"),
        ],
        bi_lines,
        ng_lines,
    )
    if sample:
        print(f"self-test : renommages d'exemple non couverts : {sample}", file=sys.stderr)
        failed += 1
    if failed:
        return 1
    print(f"self-test : {len(cases)} cas tenus")
    return 0


def report(paths: list[str], out=sys.stdout) -> int:
    buckets = {"bi": [], "ng": [], "both": [], "excluded": [], "uncovered": []}
    for path in paths:
        buckets[classify(path)].append(path)
    print(f"fichiers suivis : {len(paths)}", file=out)
    print(f"Blue Intelligence seul : {len(buckets['bi'])}", file=out)
    print(f"NAVIGUIDE seul : {len(buckets['ng'])}", file=out)
    print(f"les deux : {len(buckets['both'])}", file=out)
    print(f"exclus (archive seulement) : {len(buckets['excluded'])}", file=out)
    print(f"non classés : {len(buckets['uncovered'])}", file=out)
    if buckets["excluded"]:
        print("exclus :", file=out)
        for path in buckets["excluded"]:
            reason = EXCLUDED.get(path, "archive seulement")
            print(f"  {path} — {reason}", file=out)
    bi_lines = emit("bi", paths)
    ng_lines = emit("ng", paths)
    print(f"lignes du fichier de chemins Blue Intelligence : {len(bi_lines)}", file=out)
    print(f"lignes du fichier de chemins NAVIGUIDE : {len(ng_lines)}", file=out)
    deleted = deleted_paths()
    pairs = renamed_pairs()
    gaps = []
    gaps.extend(history_gaps(deleted, bi_lines, ng_lines))
    gaps.extend(rename_gaps(pairs, bi_lines, ng_lines))
    watched = list(paths)
    watched.extend(deleted)
    for old, new in pairs:
        watched.append(old)
        watched.append(new)
    gaps.extend(placement_gaps(sorted(set(watched)), bi_lines, ng_lines))
    print(f"écarts d'historique : {len(gaps)}", file=out)
    if buckets["uncovered"]:
        print("non classés (à trancher avant le filtre) :", file=sys.stderr)
        for path in buckets["uncovered"]:
            print(f"  {path}", file=sys.stderr)
        return 1
    if gaps:
        print("historique non couvert (à classer avant le filtre) :", file=sys.stderr)
        for gap in gaps[:80]:
            print(f"  {gap}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--emit",
        choices=("bi", "ng"),
        help="écrit sur la sortie les chemins à passer à git filter-repo",
    )
    parser.add_argument(
        "--verify",
        choices=("bi", "ng"),
        help="lit des chemins sur l'entrée standard et vérifie l'arbre filtré",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="vérifie les cas fixes du classeur, sans lire le dépôt",
    )
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.verify:
        incoming = [line.strip() for line in sys.stdin if line.strip()]
        errors = verify(args.verify, incoming)
        if errors:
            print(f"vérification {args.verify} : {len(errors)} écart(s)", file=sys.stderr)
            for err in errors[:50]:
                print(f"  {err}", file=sys.stderr)
            return 1
        print(f"vérification {args.verify} : {len(incoming)} chemins tenus")
        return 0
    paths = tracked_files()
    if args.emit:
        if report(paths, out=sys.stderr) != 0:
            return 1
        for path in emit(args.emit, paths):
            print(path)
        return 0
    return report(paths)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
