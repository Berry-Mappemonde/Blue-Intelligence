#!/usr/bin/env python3
"""Commandes des sections 6.0, 6.4 et 6.5 du plan de séparation.

On lance ce script dans une copie filtrée, jamais dans le monodépôt.
Il ne pousse rien, n'ouvre aucun dépôt, et ne parle à aucun serveur.

    python3 scripts/split_post_filter.py shared --role bi --root /tmp/bi-work
    python3 scripts/split_post_filter.py shared --role ng --root /tmp/ng-work
    python3 scripts/split_post_filter.py public-name --role ng --root /tmp/ng-work --archive /tmp/archive
    python3 scripts/split_post_filter.py public-name --role bi --root /tmp/bi-work --archive /tmp/archive
    python3 scripts/split_post_filter.py film-discours --root /tmp/ng-work
    python3 scripts/split_post_filter.py repo-paths --root /tmp/ng-work
"""
from __future__ import annotations

import argparse
import io
import re
import subprocess
import sys
import tokenize
from pathlib import Path

PLAN_FILE = Path(__file__).resolve().parents[1] / "docs" / "PLAN_SEPARATION_DEPOTS.md"
SHA_510 = "15e41b4e546955b9d65a773cab5f4a2c63e7f5c2"
SHA_227 = "bef9f0f34c0bcdfdd93d3b7c26f1c93b095613d5"
FILM_OLD = "docs/FILM_DISCOURS_ETAT_2026-09-28.md"
FILM_NEW = "naviguide-simulator/server/tests/fixtures/FILM_DISCOURS_ETAT_2026-09-28.md"

NG_DOC_MOVES = (
    "docs/PLAN_AUDIT_CALCULS.md",
    "docs/PLAN_BATCH_2026-10-14.md",
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
    "docs/PLAN_ICI_JOURNAL_EXPERT.md",
    "docs/PLAN_LOTS_COMPLEMENTAIRE_SIMULATEUR.md",
    "docs/PLAN_MIGRATION_ANCIEN_NAVIGUIDE.md",
    "docs/SPECS_E2E_TRIAGE_2026-09-29.md",
)
BI_DOC_MOVES = (
    "docs/archives/ETAT_DES_LIEUX_DOCS.md",
    "docs/archives/PRD.md",
)

EXPLICIT_PUSH = """git push origin refs/heads/main:refs/heads/main
git push origin refs/tags/data-2026-09-14:refs/tags/data-2026-09-14
git push origin refs/tags/data-2026-09-21:refs/tags/data-2026-09-21
git push origin refs/tags/data-2026-09-28:refs/tags/data-2026-09-28
git push origin refs/tags/data-2026-10-05:refs/tags/data-2026-10-05
git push origin refs/tags/data-2026-10-12:refs/tags/data-2026-10-12"""


def die(msg: str) -> None:
    print(f"split_post_filter: {msg}", file=sys.stderr)
    raise SystemExit(1)


def read(path: Path) -> str:
    if not path.is_file():
        die(f"fichier absent : {path}")
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"écrit {path}")


def git(root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        die(f"git {' '.join(args)} : {proc.stderr.strip() or proc.stdout.strip()}")
    return proc.stdout


def strip_push_mirror(text: str) -> str:
    """Remplace un push de toutes les références par le push explicite.

    `git clone --mirror` reste : c'est la copie locale de l'archive,
    pas un envoi.
    """
    text = text.replace("git push --mirror origin", EXPLICIT_PUSH)
    text = text.replace("git push --mirror", EXPLICIT_PUSH.splitlines()[0])
    text = text.replace("un `git push --mirror`", "un envoi de toutes les références")
    text = text.replace("`git push --mirror`", "l'envoi de toutes les références")
    return text


def git_mv(root: Path, src: str, dst: str) -> None:
    source = root / src
    dest = root / dst
    if dest.exists() and not source.exists():
        print(f"déjà déplacé {src} -> {dst}")
        return
    if not source.exists():
        die(f"source absente : {src}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    git(root, "mv", src, dst)
    print(f"git mv {src} {dst}")


def rewrite_paths(root: Path, pairs: list[tuple[str, str]]) -> None:
    # Les plus longs d'abord : REVUE_21_SEPT.md est un préfixe de …_SOIR.md.
    pairs = sorted(pairs, key=lambda item: len(item[0]), reverse=True)
    # Ces fichiers sont réécrits par le diff 6.6, ou doivent rester tels
    # que le filtre les a copiés (31 tests). Un lien dedans casserait git apply.
    frozen = {
        ".github/workflows/ci.yml",
        ".github/workflows/deploy.yml",
        ".github/dependabot.yml",
        "infra/vps/ci/prepare-ssh.sh",
        "infra/vps/ci/plan_deploy.py",
        "infra/vps/ci/test_prod_jobs_busy.py",
    }
    for old, new in pairs:
        proc = subprocess.run(
            ["git", "-C", str(root), "grep", "-l", "-F", "-I", old],
            text=True,
            capture_output=True,
        )
        if proc.returncode not in (0, 1):
            die(f"git grep {old} : {proc.stderr.strip()}")
        for rel in proc.stdout.splitlines():
            if rel in frozen:
                continue
            path = root / rel
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeError:
                continue
            updated = text.replace(old, new)
            if updated != text:
                path.write_text(updated, encoding="utf-8")
                print(f"lien {rel} : {old} -> {new}")


# ── 6.0 ────────────────────────────────────────────────────────────────────


def shorten_regles(text: str) -> str:
    start = text.find("### 3.1 ")
    end = text.find("### 3.7 ")
    if start < 0 or end < 0 or end <= start:
        die("REGLES_PARAMETRES : sections 3.1 et 3.7 introuvables")
    pointer = (
        "### 3.1 à 3.6 — catalogue Blue Intelligence\n\n"
        "Ces sections vivent dans le dépôt Blue Intelligence, "
        "fichier `backend/data/run_rules.json` "
        "(et `docs/REGLES_PARAMETRES.md` de ce dépôt). "
        "On ne les recopie pas ici.\n\n"
    )
    return text[:start] + pointer + text[end:]


def ng_plan_text() -> str:
    if not PLAN_FILE.is_file():
        die(f"plan source absent : {PLAN_FILE}")
    full = strip_push_mirror(PLAN_FILE.read_text(encoding="utf-8"))
    parts = re.split(r"(?=^## )", full, flags=re.M)
    banner = (
        "Copie NAVIGUIDE. L'original entier est dans le dépôt "
        "Blue Intelligence (`docs/PLAN_SEPARATION_DEPOTS.md`). "
        "Cette copie garde les sections qui nomment ce dépôt, "
        "la preuve d'historique (`poe_pipeline.py`, août 2026) "
        "et les dix contrôles de la section 9. "
        "La procédure Mongo de l'OVH n'est pas recopiée.\n\n"
    )
    out = [banner + parts[0]]
    dropped = False
    for part in parts[1:]:
        title = part.splitlines()[0]
        if title.startswith("## 1."):
            if not dropped:
                out.append(
                    "## 1. Mongo sur l'OVH\n\n"
                    "La procédure (copie cohérente, comptes, redémarrage) "
                    "est dans le dépôt Blue Intelligence, "
                    "`docs/PLAN_SEPARATION_DEPOTS.md`, section 1. "
                    "On ne la lance pas depuis ce dépôt. "
                    "`blueintel_db` reste sur l'OVH. "
                    "On ne lance pas `sync-from-atlas.sh`.\n\n"
                )
            dropped = True
            continue
        out.append(part)
    text = "".join(out)
    if "poe_pipeline.py" not in text:
        die("copie NAVIGUIDE du plan : preuve d'historique absente")
    if not re.search(r"(?m)^10\. ", text):
        die("copie NAVIGUIDE du plan : les dix contrôles sont absents")
    if "git push --mirror" in text:
        die("copie NAVIGUIDE du plan : un push de toutes les références reste")
    return text


def shorten_hackathon(text: str) -> str:
    genai = "[PLAN_HACKATHON_GENAI_BLUE_INTELLIGENCE.md](PLAN_HACKATHON_GENAI_BLUE_INTELLIGENCE.md)"
    link = (
        "[dépôt Blue Intelligence](https://github.com/Berry-Mappemonde/Blue-Intelligence"
        "/blob/main/docs/PLAN_HACKATHON_GENAI_BLUE_INTELLIGENCE.md)"
    )
    if genai not in text and link in text:
        return text
    if genai not in text:
        die("HACKATHON_PLAN : ligne GenAI introuvable")
    return text.replace(genai, link)


def cmd_shared(role: str, root: Path) -> None:
    if role == "bi":
        video = root / ".cursor/rules/pas-de-verification-video.mdc"
        write(video, """---
description: Do not record or review videos to verify work
alwaysApply: true
---

# No video verification

- Pas de vidéo : pas d'enregistrement d'écran, pas de revue vidéo.
- La preuve est un test, un `curl`, ou une capture fixe.
- On ne demande pas de regarder une démo filmée.
""")
        write(root / "docs/README.md", """# Index court — Blue Intelligence

- Cahiers : `docs/CAHIER_DES_CHARGES_POE.md`, `docs/CAHIER_DES_CHARGES_PROJETS.md`, `docs/CAHIER_DES_CHARGES_REVIEW.md`
- Audit PoE : `docs/poe-confirmed-gps-audit.md` et `docs/audits/`
- Plan GenAI : `docs/PLAN_HACKATHON_GENAI_BLUE_INTELLIGENCE.md`
- Plan de séparation : `docs/PLAN_SEPARATION_DEPOTS.md`
""")
        write(root / "Archives/README.md", """# Archives — Blue Intelligence

Ce dossier n'est pas branché sur l'application en production.
Rien ici n'est importé par le backend ni le frontend.

`Archives/Blue-Intelligence/` : guides de croisière (Cruisers Wiki
et archives Wayback), pack d'extraction sans LLM, sources
Kartverket / Hidrografico, URLs de projets, score par domaine.
""")
        plan = root / "docs/PLAN_SEPARATION_DEPOTS.md"
        if plan.is_file() and "git push --mirror" in plan.read_text(encoding="utf-8"):
            write(plan, strip_push_mirror(plan.read_text(encoding="utf-8")))
        return

    if role != "ng":
        die(f"rôle inconnu : {role}")

    write(root / ".cursor/rules/base-de-donnees-vps.mdc", """---
description: Le simulateur n'a pas de Mongo
alwaysApply: true
---

base-de-donnees-vps :

- Le simulateur n'a pas de Mongo.
- `blueintel_db` reste sur l'OVH.
- On ne lance pas `sync-from-atlas.sh`.
""")
    env = root / ".cursor/rules/environnement-utilisateur.mdc"
    env_text = read(env)
    line = (
        "- Le simulateur est sur Contabo (`naviguide@13.140.164.185`). "
        "Blue Intelligence reste sur l'OVH.\n"
    )
    if "13.140.164.185" not in env_text:
        write(env, env_text.rstrip() + "\n" + line)
    write(root / "README.md", """# NAVIGUIDE

NAVIGUIDE est en ligne sur https://naviguide.fr.
Chaque merge sur `main` déploie cette version.

L'API Blue Intelligence reste https://blueintelligence.online/api.
""")
    hack = root / "docs/HACKATHON_PLAN.md"
    write(hack, shorten_hackathon(read(hack)))
    write(root / "docs/PLAN_SEPARATION_DEPOTS.md", ng_plan_text())
    regles = root / "docs/REGLES_PARAMETRES.md"
    write(regles, shorten_regles(read(regles)))
    write(root / "infra/vps/README.md", """# NAVIGUIDE — serveur

Le site live est https://naviguide.fr (le voyage, port 8010).
`www.naviguide.fr` et `simulator.naviguide.fr` répondent 301 vers
https://naviguide.fr.

Les unités de l'ancien planificateur sont des archives. On ne les lance pas.
La restauration Mongo est dans le dépôt Blue Intelligence
(`infra/vps/README.md`, procédure de l'OVH). On ne la recopie pas ici.

Le dossier d'application est `/home/naviguide/naviguide`.
""")
    for name in (
        ".cursor/rules/modeles-cursor-uniquement.mdc",
        ".cursor/rules/reparations-sur-github.mdc",
    ):
        if not (root / name).is_file():
            die(f"copie commune absente : {name}")
        print(f"entier {name}")


# ── 6.4 ────────────────────────────────────────────────────────────────────


NGINX_301 = """# Redirections seulement. Le site est nginx-simulator.conf
# (naviguide.fr, proxy vers 127.0.0.1:8010).
# www et simulator gardent les liens déjà publiés.
# Aucun proxy vers 9000, 9004 ou 9008.

server {
    listen 80;
    server_name naviguide.fr www.naviguide.fr simulator.naviguide.fr;
    return 301 https://naviguide.fr$request_uri;
}

server {
    listen 443 ssl;
    server_name www.naviguide.fr simulator.naviguide.fr;

    ssl_certificate /etc/letsencrypt/live/naviguide.fr/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/naviguide.fr/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    return 301 https://naviguide.fr$request_uri;
}
"""


def retarget_simulator_nginx(root: Path) -> None:
    path = root / "infra/vps/naviguide/nginx-simulator.conf"
    text = read(path)
    text = text.replace(
        "server_name simulator.naviguide.fr;",
        "server_name naviguide.fr;",
    )
    text = text.replace(
        "return 301 https://simulator.naviguide.fr$request_uri;",
        "return 301 https://naviguide.fr$request_uri;",
    )
    old_clim = """        proxy_pass http://127.0.0.1:8001/api/climatology/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;"""
    new_clim = """        proxy_pass https://blueintelligence.online/api/climatology/;
        proxy_ssl_server_name on;
        proxy_http_version 1.1;
        proxy_set_header Host blueintelligence.online;"""
    old_bi = """        proxy_pass http://127.0.0.1:8001/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;"""
    new_bi = """        proxy_pass https://blueintelligence.online/api/;
        proxy_ssl_server_name on;
        proxy_http_version 1.1;
        proxy_set_header Host blueintelligence.online;"""
    if old_clim not in text or old_bi not in text:
        if "blueintelligence.online/api/" not in text:
            die("nginx-simulator.conf : locations /bi/ introuvables")
    else:
        text = text.replace(old_clim, new_clim, 1).replace(old_bi, new_bi, 1)
    # Le port 80 des trois noms est dans nginx-naviguide.conf.
    marker = "\n# HTTP : challenge Let's Encrypt"
    if marker in text:
        text = text[: text.index(marker)]
        if not text.endswith("\n"):
            text += "\n"
    if "proxy_pass http://127.0.0.1:8010" not in text:
        die("nginx-simulator.conf : le proxy 8010 a disparu")
    if re.search(r"proxy_pass\s+http://127\.0\.0\.1:900[048]", text):
        die("nginx-simulator.conf : un proxy vers l'ancien planificateur reste")
    write(path, text)


def replace_calendar(text: str) -> str:
    lines = text.splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines) if line.startswith("## 4. Calendrier")), None)
    if start is None:
        die("WORKFLOW_INDUSTRIEL : section 4 absente")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    table = (
        "| Date | Objectif | Ce qui doit être vrai |\n"
        "|---|---|---|\n"
        "| à dater par le propriétaire | | |\n"
    )
    kept: list[str] = []
    inserted = False
    for line in lines[start + 1 : end]:
        if line.startswith("|"):
            if not inserted:
                kept.append("\n" + table)
                inserted = True
            continue
        kept.append(line)
    if not inserted:
        kept.insert(0, "\n" + table)
    return "".join(lines[: start + 1] + kept + lines[end:])


def show_file(archive: Path, sha: str, rel: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(archive), "show", f"{sha}:{rel}"],
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        die(f"git show {sha}:{rel} : {proc.stderr.strip()}")
    return proc.stdout


def append_rj(root: Path, archive: Path) -> None:
    lots_path = root / "docs/LOTS_ORDRE_ET_PROMPTS.md"
    lots = read(lots_path)
    if 'id="RJ1"' in lots and 'id="RJ2"' in lots:
        print("RJ1 et RJ2 déjà dans LOTS_ORDRE_ET_PROMPTS.md")
        return
    source = show_file(archive, SHA_510, "docs/LOTS_ORDRE_ET_PROMPTS.md")
    rows = [line for line in source.splitlines() if re.search(r"\|\s+RJ[12]\s+\|", line)]
    if len(rows) != 2:
        die(f"lignes de tableau RJ : {len(rows)}")

    def block(lot_id: str) -> str:
        start = source.find(f'<!-- LOT id="{lot_id}"')
        if start < 0:
            die(f"bloc {lot_id} absent du SHA {SHA_510}")
        fence = source.find("\n```\n", start)
        if fence < 0:
            die(f"fin du bloc {lot_id} absente")
        return source[start : fence + len("\n```\n")]

    body = "\n".join(rows) + "\n\n" + block("RJ1") + "\n" + block("RJ2")
    body = body.replace(
        "docs/PLAN_CORRECTIONS_2026-10-16-s7.md",
        "docs/archives/PLAN_CORRECTIONS_2026-10-16-s7.md",
    )
    marker = "\n## 2. Les prompts"
    if marker not in lots:
        lots = lots.rstrip() + "\n\n" + "\n".join(rows) + "\n"
    else:
        lots = lots.replace(marker, "\n" + "\n".join(rows) + "\n" + marker, 1)
    marker3 = "\n## 3. "
    blocks = block("RJ1") + "\n" + block("RJ2")
    blocks = blocks.replace(
        "docs/PLAN_CORRECTIONS_2026-10-16-s7.md",
        "docs/archives/PLAN_CORRECTIONS_2026-10-16-s7.md",
    )
    if marker3 in lots:
        lots = lots.replace(marker3, "\n" + blocks + "\n" + marker3, 1)
    else:
        lots = lots.rstrip() + "\n\n" + blocks
    if 'id="RJ1"' not in lots or 'id="RJ2"' not in lots:
        die("RJ1/RJ2 non reportés")
    write(lots_path, lots)


def move_docs(root: Path, paths: tuple[str, ...]) -> None:
    pairs = []
    for src in paths:
        dst = src.replace("docs/", "docs/archives/", 1)
        git_mv(root, src, dst)
        pairs.append((src, dst))
    rewrite_paths(root, pairs)


def cmd_public_name(role: str, root: Path, archive: Path) -> None:
    if not archive.exists():
        die(f"archive absente : {archive}")
    if role == "ng":
        src = root / "naviguide"
        dst = root / "Archives" / "naviguide-planificateur"
        if src.exists():
            git(root, "mv", "naviguide", "Archives/naviguide-planificateur")
            print("git mv naviguide Archives/naviguide-planificateur")
        elif not dst.is_dir():
            die("naviguide/ introuvable")
        notice = (
            "# Ancien planificateur\n\n"
            "Ce dossier est l'ancien planificateur "
            "(`www.naviguide.fr`, `csw6hpki.run.complete.dev`). "
            "L'adresse `https://csw6hpki.run.complete.dev` est celle de l'époque. "
            "Le site public ne le sert plus. Le site public est "
            "https://naviguide.fr.\n\n"
        )
        readme = dst / "README.md"
        current = readme.read_text(encoding="utf-8") if readme.is_file() else ""
        if "Ancien planificateur" not in current:
            write(readme, notice + current)
        retarget_simulator_nginx(root)
        write(root / "infra/vps/naviguide/nginx-naviguide.conf", NGINX_301)
        conf = (root / "infra/vps/naviguide/nginx-naviguide.conf").read_text(encoding="utf-8")
        if "proxy_pass" in conf:
            die("nginx-naviguide.conf proxy encore une application")
        for rel in (
            "README.md",
            "naviguide-simulator/README.md",
            "naviguide-simulator/scripts/amp-route.py",
            "naviguide-simulator/src/utils/adminSecret.test.js",
            "infra/agents/run_lots.py",
            "infra/agents/GROK_BOT_ROUTINE.md",
            "infra/agents/GROK_BOT_DEVPOST.md",
            "docs/MANUEL_UTILISATEUR.md",
            "docs/USER_MANUAL.md",
            "docs/README.md",
            "docs/HACKATHON_DEVPOST_SOUMISSION.md",
            "docs/PLAN_HACKATHON_NEBIUS_NAVIGUIDE.md",
            "docs/REGLES_WORKFLOW_AGENT.md",
            "docs/WORKFLOW_INDUSTRIEL.md",
            ".github/workflows/zap-baseline.yml",
        ):
            path = root / rel
            text = read(path)
            text = text.replace("https://simulator.naviguide.fr", "https://naviguide.fr")
            text = text.replace("recette.blueintelligence.online", "recette.naviguide.fr")
            if path.name == "WORKFLOW_INDUSTRIEL.md":
                text = replace_calendar(text)
            write(path, text)
        guard = root / "naviguide-simulator/server/admin_guard.py"
        guard_text = read(guard)
        old_cors = '''        "https://simulator.naviguide.fr",
        "https://www.naviguide.fr",
        "https://naviguide.fr",'''
        new_cors = '''        "https://naviguide.fr",
        "https://www.naviguide.fr",
        "https://simulator.naviguide.fr",'''
        if old_cors in guard_text:
            guard_text = guard_text.replace(old_cors, new_cors, 1)
        elif new_cors not in guard_text:
            die("admin_guard : liste CORS introuvable")
        write(guard, guard_text)
        test = root / "naviguide-simulator/server/tests/test_admin_guard.py"
        test_text = read(test)
        extra = '    assert cors_origins()[0] == "https://naviguide.fr"\n'
        anchor = '    assert "https://simulator.naviguide.fr" in cors_origins()\n'
        if extra not in test_text:
            if anchor not in test_text:
                die("test_admin_guard : assertion CORS introuvable")
            test_text = test_text.replace(anchor, anchor + extra, 1)
            write(test, test_text)
        vite = root / "naviguide-simulator/vite.config.js"
        vite_text = read(vite)
        if '".naviguide.fr"' not in vite_text:
            needle = '  ".blueintelligence.online",\n'
            if needle not in vite_text:
                die("vite.config.js : allowedHosts introuvable")
            vite_text = vite_text.replace(needle, needle + '  ".naviguide.fr",\n', 1)
            write(vite, vite_text)
        move_docs(root, NG_DOC_MOVES)
        plan_s7 = root / "docs/archives/PLAN_CORRECTIONS_2026-10-16-s7.md"
        if not plan_s7.is_file():
            write(plan_s7, show_file(archive, SHA_510, "docs/PLAN_CORRECTIONS_2026-10-16-s7.md"))
        append_rj(root, archive)
        return

    if role != "bi":
        die(f"rôle inconnu : {role}")
    move_docs(root, BI_DOC_MOVES)
    dest = root / "docs/archives/verify-fiche-urls"
    dest.mkdir(parents=True, exist_ok=True)
    copied = {
        "docs/VERIFY_FICHE_URLS.md": "VERIFY_FICHE_URLS.md",
        "scripts/verify_fiche_urls.py": "verify_fiche_urls.py",
        "scripts/fiche_url_extract.py": "fiche_url_extract.py",
        "backend/tests/test_verify_fiche_urls.py": "test_verify_fiche_urls.py",
    }
    for src, name in copied.items():
        target = dest / name
        if not target.is_file():
            write(target, show_file(archive, SHA_227, src))
    readme = dest / "README.md"
    if not readme.is_file():
        write(readme, f"""# Vérification des URL de fiches

Copie du texte de la PR #227, tête `{SHA_227}`.
On ne rejoue pas les hunks de `ci.yml`, `weekly-data-build.yml` et `README.md` :
ils visaient la CI du monodépôt. Le commit reste lisible sur l'archive.

Chemins d'origine :

- `docs/VERIFY_FICHE_URLS.md`
- `scripts/verify_fiche_urls.py`
- `scripts/fiche_url_extract.py`
- `backend/tests/test_verify_fiche_urls.py`
""")


# ── 6.5.1 ──────────────────────────────────────────────────────────────────


def cmd_film(root: Path) -> None:
    dest = root / FILM_NEW
    src = root / FILM_OLD
    if src.is_file():
        dest.parent.mkdir(parents=True, exist_ok=True)
        git(root, "mv", FILM_OLD, FILM_NEW)
    elif not dest.is_file():
        die(f"{FILM_OLD} absent")
    stub = root / FILM_OLD
    write(stub, f"""# Discours du film

Le texte entier est dans `{FILM_NEW}`.
Un marque-page qui ouvrait l'ancien chemin retrouve le document ici.
""")
    targets = [
        root / "docs/LOTS_ORDRE_ET_PROMPTS.md",
        root / "docs/archives/PLAN_CORRECTIONS_2026-09-28-film.md",
        root / "docs/PLAN_CORRECTIONS_2026-09-28-film.md",
        root / "naviguide-simulator/server/tests/test_film_discours.py",
        root / "naviguide-simulator/server/film_script.py",
        root / "docs/README.md",
    ]
    for path in targets:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if FILM_OLD in text:
            path.write_text(text.replace(FILM_OLD, FILM_NEW), encoding="utf-8")
            print(f"chemin du discours : {path.relative_to(root)}")
    checked = [
        root / "docs/LOTS_ORDRE_ET_PROMPTS.md",
        root / "docs/archives/PLAN_CORRECTIONS_2026-09-28-film.md",
        root / "naviguide-simulator/server/tests/test_film_discours.py",
        root / "naviguide-simulator/server/film_script.py",
    ]
    for path in checked:
        if path.is_file() and FILM_OLD in path.read_text(encoding="utf-8"):
            die(f"ancien chemin encore cité : {path.relative_to(root)}")


# ── 6.5.2 ──────────────────────────────────────────────────────────────────


REPO_PATHS = '''"""Réglages de la boucle de nuit pour ce dépôt.

Les scripts de ce dossier importent ces noms. On ne recopie pas la
même chaîne dans le texte d'un prompt.
"""
from __future__ import annotations

REPO_SLUG = "Berry-Mappemonde/NAVIGUIDE"
DEFAULT_REPO = "https://github.com/" + REPO_SLUG
BIM_REPO = REPO_SLUG
PROD_URL = "https://naviguide.fr"
RECETTE_HOST = "recette.naviguide.fr"
RECETTE_BRANCH = "recette"

PROMPTS_MD = "docs/LOTS_ORDRE_ET_PROMPTS.md"
REGLES_MD = "docs/REGLES_WORKFLOW_AGENT.md"
PLAN_REVUE_SOIR = "docs/PLAN_CORRECTIONS_REVUE_21_SEPT_SOIR.md"
WORKFLOW_INDUSTRIEL = "docs/WORKFLOW_INDUSTRIEL.md"
RECETTE_DIR = "docs/recette"
HACKATHON_DEVPOST = "docs/HACKATHON_DEVPOST_SOUMISSION.md"
ESPRIT = "docs/ESPRIT_DE_L_APPLICATION.md"
PLAN_DEUX_MODES = "docs/PLAN_DEUX_MODES_2026-09-29.md"
INFRA_VPS_README = "infra/vps/README.md"
PARCOURS_NAME = "PARCOURS_DE_REFERENCE.md"
SIMULATOR_DIR = "naviguide-simulator"
ENSURE_DEV = "naviguide-simulator/ensure-dev.sh"
APP_JSX = "naviguide-simulator/src/App.jsx"
E2E_LOTS = "naviguide-simulator/e2e/lots"
FILM_CINEMATIQUE = "naviguide-simulator/scripts/film-cinematique.mjs"
SERVER_ENV = "naviguide-simulator/server/.env"

FIXED_DOCS = (REGLES_MD, PROMPTS_MD, PLAN_REVUE_SOIR)
NPM_PROJECTS = ("naviguide-simulator", "frontend")
PIP_PROJECT = ("naviguide-simulator", "server/requirements.txt", ".venv/bin/python")
VOYAGE_ID = "berry-mappemonde-2026-officiel"
SHARED_CACHE_DIRS = ("voyage_data", "forecast_cache", "grib_data")
VOYAGE_DATA_FILES = (
    "eez_vliz_v12.geojson",
    "ici_thin_cache.json",
    "official_journal",
    "voyage_{id}.json",
)
'''

SPLICE_PAIRS = (
    ("https://github.com/Berry-Mappemonde/Blue-Intelligence", "repo_paths.DEFAULT_REPO"),
    ("https://github.com/Berry-Mappemonde/NAVIGUIDE", "repo_paths.DEFAULT_REPO"),
    ("https://simulator.naviguide.fr", "repo_paths.PROD_URL"),
    ("Berry-Mappemonde/Blue-Intelligence", "repo_paths.BIM_REPO"),
    ("Berry-Mappemonde/NAVIGUIDE", "repo_paths.BIM_REPO"),
    ("docs/LOTS_ORDRE_ET_PROMPTS.md", "repo_paths.PROMPTS_MD"),
    ("docs/REGLES_WORKFLOW_AGENT.md", "repo_paths.REGLES_MD"),
    ("LOTS_ORDRE_ET_PROMPTS.md", "repo_paths.PROMPTS_MD"),
    ("REGLES_WORKFLOW_AGENT.md", "repo_paths.REGLES_MD"),
    ("simulator.naviguide.fr", "repo_paths.PROD_URL"),
)


def _pos(lines: list[str], line: int, col: int) -> int:
    return sum(len(lines[i]) for i in range(line - 1)) + col


def _module_docstring(lines: list[str], start_line: int, start_col: int) -> bool:
    """Chaîne en colonne 0, précédée seulement d'un shebang ou de commentaires."""
    if start_col != 0:
        return False
    for index in range(start_line - 1):
        stripped = lines[index].strip()
        if stripped and not stripped.startswith("#"):
            return False
    return True


def _rewrite_string_token(raw: str, *, textual: bool = False) -> str:
    match = re.match(
        r"^(?P<pre>[fFrRbBuU]*)(?P<q>\'\'\'|\"\"\"|\'|\")(?P<body>.*)(?P=q)$",
        raw,
        re.S,
    )
    if not match:
        return raw
    pre = match.group("pre")
    quote = match.group("q")
    body = match.group("body")
    if textual:
        for literal, expr in SPLICE_PAIRS:
            body = body.replace(literal, expr)
        return pre + quote + body + quote
    is_f = "f" in pre.lower() or "F" in pre
    parts: list[tuple[str, bool]] = [(body, True)]
    for literal, expr in SPLICE_PAIRS:
        nxt: list[tuple[str, bool]] = []
        for text, is_str in parts:
            if not is_str or literal not in text:
                nxt.append((text, is_str))
                continue
            chunks = text.split(literal)
            for index, chunk in enumerate(chunks):
                nxt.append((chunk, True))
                if index != len(chunks) - 1:
                    nxt.append((expr, False))
        parts = nxt
    bits: list[str] = []
    first = True
    for text, is_str in parts:
        if not is_str:
            bits.append(text)
            continue
        if text == "" and not first:
            continue
        prefix = pre if first else ("f" if is_f else "")
        bits.append(prefix + quote + text + quote)
        first = False
    empty = {quote * 2, "f" + quote * 2, "F" + quote * 2}
    bits = [bit for bit in bits if bit not in empty]
    return " + ".join(bits) if bits else raw


def splice_source(src: str) -> str:
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except tokenize.TokenError as exc:
        die(f"tokenize : {exc}")
    lines = src.splitlines(keepends=True)
    edits: list[tuple[int, int, str]] = []
    f_middle = getattr(tokenize, "FSTRING_MIDDLE", None)
    for tok in tokens:
        if tok.type == tokenize.STRING and any(lit in tok.string for lit, _ in SPLICE_PAIRS):
            textual = _module_docstring(lines, tok.start[0], tok.start[1])
            rewritten = _rewrite_string_token(tok.string, textual=textual)
            edits.append((_pos(lines, *tok.start), _pos(lines, *tok.end), rewritten))
        elif f_middle is not None and tok.type == f_middle and any(lit in tok.string for lit, _ in SPLICE_PAIRS):
            middle = tok.string
            for literal, expr in SPLICE_PAIRS:
                middle = middle.replace(literal, "{" + expr + "}")
            edits.append((_pos(lines, *tok.start), _pos(lines, *tok.end), middle))
        elif tok.type == tokenize.COMMENT and any(lit in tok.string for lit, _ in SPLICE_PAIRS):
            comment = tok.string
            for literal, expr in SPLICE_PAIRS:
                comment = comment.replace(literal, expr)
            edits.append((_pos(lines, *tok.start), _pos(lines, *tok.end), comment))
    if not edits:
        return src
    edits.sort()
    out: list[str] = []
    last = 0
    for start, end, new in edits:
        out.append(src[last:start])
        out.append(new)
        last = end
    out.append(src[last:])
    return "".join(out)


def ensure_import(text: str) -> str:
    code_uses = any("repo_paths" in line.split("#", 1)[0] for line in text.splitlines())
    if not code_uses or re.search(r"(?m)^(?:import|from) repo_paths\b", text):
        return text
    needle = "from __future__ import annotations\n"
    if needle in text:
        return text.replace(needle, needle + "\nimport repo_paths\n", 1)
    return "import repo_paths\n" + text


def retarget_assignments(text: str) -> str:
    text = re.sub(
        r'^PROMPTS_MD = ROOT / "docs" / "LOTS_ORDRE_ET_PROMPTS\.md"',
        "PROMPTS_MD = ROOT / repo_paths.PROMPTS_MD",
        text,
        flags=re.M,
    )
    text = re.sub(
        r'^DEFAULT_REPO = "https://github.com/Berry-Mappemonde/(?:Blue-Intelligence|NAVIGUIDE)"',
        "DEFAULT_REPO = repo_paths.DEFAULT_REPO",
        text,
        flags=re.M,
    )
    text = re.sub(
        r'^PROD_URL = "https://(?:simulator\.)?naviguide\.fr"',
        "PROD_URL = repo_paths.PROD_URL",
        text,
        flags=re.M,
    )
    text = re.sub(
        r'^RECETTE_BRANCH = "recette"',
        "RECETTE_BRANCH = repo_paths.RECETTE_BRANCH",
        text,
        flags=re.M,
    )
    text = re.sub(
        r'^PARCOURS_MD = HERE / "PARCOURS_DE_REFERENCE\.md"',
        "PARCOURS_MD = HERE / repo_paths.PARCOURS_NAME",
        text,
        flags=re.M,
    )
    text = re.sub(
        r'^NPM_PROJECTS = \("naviguide-simulator", "frontend"\)',
        "NPM_PROJECTS = repo_paths.NPM_PROJECTS",
        text,
        flags=re.M,
    )
    text = re.sub(
        r'^PIP_PROJECT = \("naviguide-simulator", "server/requirements\.txt", "\.venv/bin/python"\)',
        "PIP_PROJECT = repo_paths.PIP_PROJECT",
        text,
        flags=re.M,
    )
    text = re.sub(
        r"^FIXED_DOCS = \([^)]*\)",
        "FIXED_DOCS = repo_paths.FIXED_DOCS",
        text,
        flags=re.M,
    )
    text = re.sub(
        r'REPO = os\.environ\.get\("BIM_REPO", "Berry-Mappemonde/(?:Blue-Intelligence|NAVIGUIDE)"\)',
        'REPO = os.environ.get("BIM_REPO", repo_paths.BIM_REPO)',
        text,
    )
    return text


def git_bytes(repo: Path, spec: str) -> bytes:
    proc = subprocess.run(
        ["git", "-C", str(repo), "show", spec],
        capture_output=True,
    )
    if proc.returncode != 0:
        die(f"git show {spec} : {proc.stderr.decode().strip()}")
    return proc.stdout


def cmd_cross_imports(root: Path, bi: Path) -> None:
    """Fichiers que main a rendus communs après l'écriture des diffs 6.6.

    ``public/route.geojson`` est un lien vers ``backend/data/``. Ce
    dossier n'est pas dans NAVIGUIDE : on pose le fichier lui-même.
    ``test_wind_float16.py`` importe ``app.services.climatology_wind``
    depuis ``parents[3] / backend``. On copie ce module et
    ``climatology_common.py``. Les tests ne sont pas modifiés.
    """
    if not (bi / ".git").exists() and not (bi / "HEAD").is_file():
        die(f"dépôt Blue Intelligence illisible : {bi}")
    link = root / "naviguide-simulator/public/route.geojson"
    payload = git_bytes(bi, "HEAD:backend/data/route.geojson")
    if link.is_symlink() or not link.is_file():
        link.unlink(missing_ok=True)
        link.write_bytes(payload)
        print(f"route.geojson : {len(payload)} octets à la place du lien")
    elif link.read_bytes() != payload:
        die("route.geojson existe et diffère de backend/data")
    else:
        print("route.geojson déjà le fichier")
    modules = (
        "backend/app/__init__.py",
        "backend/app/services/__init__.py",
        "backend/app/services/climatology_common.py",
        "backend/app/services/climatology_wind.py",
    )
    for rel in modules:
        dest = root / rel
        if dest.is_file() and dest.stat().st_size > 0 and not rel.endswith("__init__.py"):
            print(f"déjà copié {rel}")
            continue
        if rel.endswith("__init__.py"):
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                dest.write_text("", encoding="utf-8")
                print(f"paquet {rel}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(git_bytes(bi, f"HEAD:{rel}"))
        print(f"copié {rel} ({dest.stat().st_size} octets)")
    wind = root / "backend/data/climatology/wind"
    wind.mkdir(parents=True, exist_ok=True)
    for month in range(1, 13):
        rel = f"backend/data/climatology/wind/wind-{month:02d}.npz"
        dest = root / rel
        if dest.is_file():
            continue
        dest.write_bytes(git_bytes(bi, f"HEAD:{rel}"))
        print(f"copié {rel} ({dest.stat().st_size} octets)")


def cmd_repo_paths(root: Path) -> None:
    agents = root / "infra/agents"
    if not agents.is_dir():
        die("infra/agents absent")
    write(agents / "repo_paths.py", REPO_PATHS)
    for path in sorted(agents.glob("*.py")):
        if path.name == "repo_paths.py":
            continue
        text = retarget_assignments(path.read_text(encoding="utf-8"))
        text = splice_source(text)
        text = ensure_import(text)
        try:
            compile(text, str(path), "exec")
        except SyntaxError as exc:
            die(f"syntaxe {path.name}:{exc.lineno}: {exc.msg}")
        path.write_text(text, encoding="utf-8")
        print(f"réglages {path.name}")
    note = "Les chemins exécutables sont dans `infra/agents/repo_paths.py`.\n\n"
    for name in ("GROK_BOT_ROUTINE.md", "GROK_BOT_DEVPOST.md"):
        path = agents / name
        if not path.is_file():
            die(f"{name} absent")
        body = path.read_text(encoding="utf-8")
        if "repo_paths.py" not in body:
            write(path, note + body)
    pattern = re.compile(
        r"LOTS_ORDRE_ET_PROMPTS|REGLES_WORKFLOW_AGENT|"
        r"Berry-Mappemonde/Blue-Intelligence|simulator\.naviguide\.fr"
    )
    for path in sorted(agents.glob("*.py")):
        if path.name == "repo_paths.py":
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(line):
                die(f"chaîne encore en dur : {path.name}:{number}: {line.strip()}")
    compile((agents / "repo_paths.py").read_text(encoding="utf-8"), "repo_paths.py", "exec")
    print("repo_paths : syntaxe tenue, chaînes déplacées")


def self_check() -> None:
    sample = (
        'PROMPTS_MD = ROOT / "docs" / "LOTS_ORDRE_ET_PROMPTS.md"\n'
        'msg = f"lire docs/LOTS_ORDRE_ET_PROMPTS.md et {ROOT}"\n'
        'url = "https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/1"\n'
        "# voir docs/REGLES_WORKFLOW_AGENT.md\n"
    )
    out = splice_source(retarget_assignments(sample))
    if re.search(r"LOTS_ORDRE_ET_PROMPTS|REGLES_WORKFLOW_AGENT|Blue-Intelligence", out):
        die(f"self-check splice : {out}")
    compile(ensure_import(out), "<sample>", "exec")
    documented = (
        '"""voir docs/LOTS_ORDRE_ET_PROMPTS.md"""\n'
        "from __future__ import annotations\n"
        'note = "docs/REGLES_WORKFLOW_AGENT.md"\n'
    )
    documented_out = ensure_import(splice_source(documented))
    if re.search(r"LOTS_ORDRE_ET_PROMPTS|REGLES_WORKFLOW_AGENT", documented_out):
        die(f"self-check docstring : {documented_out}")
    compile(documented_out, "<doc>", "exec")
    regles = "préambule\n### 3.1 Projets\nsecret\n### 3.7 Horloge\nsuite\n"
    short = shorten_regles(regles)
    if "secret" in short or "### 3.7 Horloge" not in short:
        die("self-check regles")
    if "git push --mirror" in strip_push_mirror("git push --mirror origin\n"):
        die("self-check push")
    print("self-check tenu")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("shared", "public-name", "film-discours", "repo-paths", "cross-imports", "self-check"),
    )
    parser.add_argument("--role", choices=("bi", "ng"))
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--bi", type=Path, help="copie ou bare Blue Intelligence, pour cross-imports")
    args = parser.parse_args()
    if args.command == "self-check":
        self_check()
        return
    root = args.root.resolve()
    if not (root / ".git").exists():
        die(f"{root} n'est pas une copie git")
    if args.command == "shared":
        if not args.role:
            die("--role bi|ng")
        cmd_shared(args.role, root)
    elif args.command == "public-name":
        if not args.role or not args.archive:
            die("--role et --archive")
        cmd_public_name(args.role, root, args.archive.resolve())
    elif args.command == "film-discours":
        cmd_film(root)
    elif args.command == "cross-imports":
        if not args.bi:
            die("--bi")
        cmd_cross_imports(root, args.bi.resolve())
    else:
        cmd_repo_paths(root)


if __name__ == "__main__":
    main()
