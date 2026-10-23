#!/usr/bin/env python3
"""Enchaîne les lots de repo_paths.PROMPTS_MD, un agent Cursor par lot, pour Blue Intelligence.

Deux façons de faire tourner l'agent :

  --runtime local (défaut) le CLI Cursor `agent -p --sandbox enabled` sur ce Mac, dans un
                             worktree git par lot, modèle meterless/auto (Nemotron via Meterless).
  --runtime cloud l'API Cloud Agents de Cursor (`POST /v1/agents`) : un agent
                             sur une machine Cursor.

Dans les deux cas : pile linéaire (chaque lot part de la branche du précédent),
attente de la fin, une relance sur échec, PR + CI (indifférente pour BI).

Blue Intelligence n'a pas de revue de film (film loop) ni de parcours complet NAVIGUIDE.
La fin de batch BI : proposition du batch suivant si activé.

Usage (voir repo_paths.PROMPTS_MD § 3) :
/opt/homebrew/bin/python3 infra/agents/run_lots_bi.py --check                       # vérifie l'environnement, ne lance rien
/opt/homebrew/bin/python3 infra/agents/run_lots_bi.py --only C1                     # un lot, en local
caffenate -i python3 infra/agents/run_lots_bi.py --from P2 --until L6
/opt/homebrew/bin/python3 infra/agents/run_lots_bi.py --runtime cloud --only C1     # via l'API (CURSOR_API_KEY)
/opt/homebrew/bin/python3 infra/agents/run_lots_bi.py --resume
/opt/homebrew/bin/python3 infra/agents/run_lots_bi.py --dry-run --from P2 --until O
/opt/homebrew/bin/python3 infra/agents/run_lots_bi.py --recette                     # poste de recette sur la dernière branche du state
/opt/homebrew/bin/python3 infra/agents/run_lots_bi.py --no-recette                  # pas de poste de recette

Modèle par défaut : meterless/auto (Nemotron via Meterless via l'env BIM_MODEL)
"""
from __future__ import annotations

import repo_paths

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

ROOT = repo_paths.bi_root()
PROMPTS_MD = Path(repo_paths.PROMPTS_MD)  # plan des lots : dans ce dépôt (BIM_PROMPTS_MD pour un autre)
HERE = Path(__file__).resolve().parent
# BIM_STATE_DIR : dossier de state.json et du journal (tests : ne pas toucher à ceux d'une nuit en cours).
STATE_DIR = Path(os.environ.get("BIM_STATE_DIR", str(HERE)))
STATE_JSON = STATE_DIR / "state.json"
LOG_FILE = STATE_DIR / "run_lots_bi.log"
WORKTREES = Path(os.environ.get("BIM_LOTS_DIR", str(Path.home() / "rw-push" / "local-lots" / "chain" / "wt")))

CURSOR_API = "https://api.cursor.com"
GITHUB_API = "https://api.github.com"
DEFAULT_REPO = repo_paths.DEFAULT_REPO
DEFAULT_MODEL = os.environ.get("BIM_MODEL") or "meterless/auto"   # Nemotron via Meterless (Clément, 18 oct.)
TERMINAL = {"FINISHED", "ERROR", "CANCELLED", "EXPIRED"}
# Identité des commits (Clément, 18 oct.) : imposée à tout git lancé par la chaîne et par ses agents.
GIT_NAME = "Clément Filisetti"
GIT_EMAIL = "clementfilisetti@berrymappemonde.org"
for _k, _v in (("GIT_AUTHOR_NAME", GIT_NAME), ("GIT_COMMITTER_NAME", GIT_NAME),
               ("GIT_AUTHOR_EMAIL", GIT_EMAIL), ("GIT_COMMITTER_EMAIL", GIT_EMAIL)):
    os.environ[_k] = _v
USAGE_LIMIT_EXIT = 7   # limite d'usage Cursor : arrêt net, worktrees gardés, aucune relance
AGENT_BIN = os.environ.get("BIM_AGENT_BIN") or shutil.which("agent") or str(Path.home() / ".local" / "bin" / "agent")

LOT_RE = re.compile(
    r'<!--\s*LOT\s+id="(?P<id>[^"]+)"\s+title="(?P<title>[^"]*)"\s+plan="(?P<plan>[^"]*)"'
    r'\s+size="(?P<size>[^"]*)"\s+deps="(?P<deps>[^"]*)"(?:\s+model="(?P<model>[^"]*)")?\s*-->\s*```text\n(?P<prompt>.*?)\n```',
    re.S,
)

@dataclass
class Lot:
    id: str
    title: str
    plan: str
    size: str
    deps: list[str]
    prompt: str
    # Modèle propre au lot (attribut optionnel model="…" de la balise) : le porteur confie les lots
    # risqués à un modèle fort (Claude Fable, CLI local) sans changer le modèle du batch (29 sept.).
    # Vide = modèle du batch (--model). Jamais un modèle Claude sur un worker Cloud (règle du dépôt).
    model: str = ""


def lot_model(lot: "Lot", args) -> str:
    """Le modèle qui code ce lot : le sien s'il en a un, sinon celui du batch."""
    m = (lot.model or "").strip()
    if not m:
        return args.model
    if getattr(args, "runtime", "local") == "cloud" and not m.startswith(("composer-", "cursor-", "muse-")):
        log(f"[{lot.id}] modèle {m!r} refusé sur un worker Cloud (modèles Cursor seulement) — modèle du batch {args.model!r}")
        return args.model
    return m


@dataclass
class State:
    done: dict = field(default_factory=dict)   # id -> {status, branch, pr, ci, ci_failures, …}
    last_branch: str = "main"
    last_lot: str = ""
    extra: dict = field(default_factory=dict)  # reviews (réviseur de nuit), queued, … — conservé tel quel

    @classmethod
    def load(cls) -> "State":
        if STATE_JSON.exists():
            d = json.loads(STATE_JSON.read_text(encoding="utf-8"))
            extra = {k: v for k, v in d.items() if k not in ("done", "last_branch", "last_lot")}
            return cls(done=d.get("done", {}), last_branch=d.get("last_branch", "main"), last_lot=d.get("last_lot", ""), extra=extra)
        return cls()

    def save(self) -> None:
        d = {**self.extra, "done": self.done, "last_branch": self.last_branch, "last_lot": self.last_lot}
        STATE_JSON.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")


def log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def sh(args: list[str], cwd: Path | None = None, timeout: int | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=str(cwd) if cwd else None, text=True, capture_output=True, timeout=timeout, check=check)


# ---------------------------------------------------------------- lots

def local_check() -> dict:
    info = {"agent": None, "logged": False, "models": []}
    if not Path(AGENT_BIN).exists():
        return info
    v = sh([AGENT_BIN, "--version"], check=False, timeout=30)
    info["agent"] = (v.stdout or v.stderr).strip()
    st = sh([AGENT_BIN, "status"], check=False, timeout=60)
    info["logged"] = "Not logged in" not in (st.stdout + st.stderr)
    if info["logged"]:
        m = sh([AGENT_BIN, "models"], check=False, timeout=60)
        info["models"] = [ln.strip() for ln in (m.stdout or "").splitlines() if ln.strip()]
    return info


def parse_lots_text(md: str) -> list[Lot]:
    """Balises <!-- LOT … --> + bloc ```text``` → lots. Liste vide si rien (queue.md du réviseur)."""
    lots = []
    for m in LOT_RE.finditer(md or ""):
        deps = [d.strip() for d in m.group("deps").split(",") if d.strip()]
        lots.append(Lot(m.group("id"), m.group("title"), m.group("plan"), m.group("size"), deps, m.group("prompt").strip(),
                        (m.group("model") or "").strip()))
    return lots


def parse_lots(md: str) -> list[Lot]:
    lots = parse_lots_text(md)
    if not lots:
        sys.exit(f"Aucun lot trouvé dans {PROMPTS_MD} (balises <!-- LOT … --> attendues)")
    return lots


QUEUE_MD = STATE_DIR / "queue.md"   # lots correctifs mis en file par le réviseur de nuit (review_agent.py)


def lot_done_anywhere(lot_id: str) -> bool:
    """FINISHED dans state.json OU dans une pile archivée (state.<ts>.json) : un lot correctif d'une nuit
    précédente, déjà mergé, ne doit jamais être rejoué."""
    for p in [STATE_JSON, *STATE_DIR.glob("state.*.json")]:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if ((d.get("done") or {}).get(lot_id) or {}).get("status") == "FINISHED":
            return True
    return False


def queued_lots(state: "State", exclude: set[str]) -> list[Lot]:
    """Lots de queue.md pas encore faits (dans cette pile ou une précédente) ni déjà en attente."""
    if not QUEUE_MD.exists():
        return []
    return [l for l in parse_lots_text(QUEUE_MD.read_text(encoding="utf-8"))
            if l.id not in state.done and l.id not in exclude and not lot_done_anywhere(l.id)]


def purge_queue() -> list[str]:
    """Retire de queue.md les blocs des lots déjà faits ; renvoie leurs ids."""
    if not QUEUE_MD.exists():
        return []
    text = QUEUE_MD.read_text(encoding="utf-8")
    gone: list[str] = []
    for m in list(LOT_RE.finditer(text)):
        if lot_done_anywhere(m.group("id")):
            gone.append(m.group("id"))
    for lid in gone:
        text = re.sub(r'<!--\s*LOT\s+id="' + re.escape(lid) + r'".*?-->\s*```text.*?```\s*', "", text, count=1, flags=re.S)
    if gone:
        QUEUE_MD.write_text(text, encoding="utf-8")
    return gone


def select(lots: list[Lot], args) -> list[Lot]:
    ids = [l.id for l in lots]
    if args.only:
        missing = [x for x in args.only if x not in ids]
        if missing:
            sys.exit(f"Lots inconnus : {missing}. Connus : {ids}")
        return [l for l in lots if l.id in args.only]
    start = ids.index(args.from_) if args.from_ else 0
    end = ids.index(args.until) if args.until else len(ids) - 1
    if start > end:
        sys.exit("--from est après --until")
    return lots[start:end + 1]


# ---------------------------------------------------------------- http

class Http:
    def __init__(self, cursor_key: str | None, github_token: str | None):
        self.cursor_headers = {"Content-Type": "application/json", "User-Agent": "bim-run-lots-bi"}
        if cursor_key:
            basic = base64.b64encode(f"{cursor_key}:".encode()).decode()
            self.cursor_headers["Authorization"] = f"Basic {basic}"
        self.github_headers = {"Accept": "application/vnd.github+json", "User-Agent": "bim-run-lots-bi", "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json"}
        if github_token:
            self.github_headers["Authorization"] = f"Bearer {github_token}"

    def _call(self, url: str, headers: dict, method: str = "GET", body: dict | None = None, retries: int = 4):
        data = json.dumps(body).encode() if body is not None else None
        for attempt in range(retries):
            req = urllib.request.Request(url, data=data, method=method, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    raw = resp.read().decode()
                    return json.loads(raw) if raw else {}
            except urllib.error.HTTPError as e:
                text = e.read().decode(errors="replace")[:400]
                if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                    wait = 15 * (attempt + 1)
                    log(f"HTTP {e.code} sur {method} {url} — nouvel essai dans {wait}s ({text})")
                    time.sleep(wait)
                    continue
                raise RuntimeError(f"HTTP {e.code} {method} {url}: {text}") from e
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt < retries - 1:
                    time.sleep(15 * (attempt + 1))
                    continue
                raise RuntimeError(f"réseau: {method} {url}: {e}") from e

    def cursor(self, path: str, method: str = "GET", body: dict | None = None):
        return self._call(f"{CURSOR_API}{path}", self.cursor_headers, method, body)

    def github(self, path: str, method: str = "GET", body: dict | None = None):
        return self._call(f"{GITHUB_API}{path}", self.github_headers, method, body)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        return None


def github_token_from_git() -> str | None:
    """Jeton GitHub éprouvé sur l'API (gh_token.py : variable, trousseau, fichier — le premier qui répond 200)."""
    sys.path.insert(0, str(HERE))
    from gh_token import token as _token  # noqa: PLC0415
    return _token(required=False)


# ---------------------------------------------------------------- github

def owner_repo(repo: str) -> str:
    return repo.replace("https://github.com/", "").rstrip("/")


# ---------------------------------------------------------------- CI (indifférente pour BI)

FAIL_LINE = re.compile(r"(✘|✖|##\[error\]|FAILED|failed|Error:|AssertionError|Expected:|Received:|\.spec\.js:\d+|test_[a-z_]+\.py::)")
# BI : CI indifférente, pas de vérification bloquante comme pour NAVIGUIDE
FAIL_NOISE = re.compile(r"^\s*(✓|✔|-\s+\[skipped\])|Received \d+ of \d+|Cache (restored|saved)|::(debug|group|endgroup)|\d+ passed \(")

def job_failures(http: Http, repo: str, check_run: dict) -> list[str]:
    """BI : lecture des échecs mais pas d'arrêt sur échec CI."""
    try:
        raw = http.github_text(f"/repos/{owner_repo(repo)}/actions/jobs/{check_run['id']}/logs")
    except RuntimeError:
        return []
    out: list[str] = []
    for line in raw.splitlines():
        line = re.sub(r"^\S+T\S+Z\s*", "", line).strip()            # horodatage GitHub
        line = re.sub(r"\x1b\[[0-9;]*m", "", line)                  # couleurs
        if FAIL_LINE.search(line) and not FAIL_NOISE.search(line) and len(line) < 240 and line not in out:
            out.append(line)
        if len(out) >= 25:
            break
    return out


def ci_status(http: Http, repo: str, sha: str) -> tuple[str, list[str], list[str]]:
    """BI : CI indifférente - on lit mais n'arrête pas la pile."""
    d = http.github(f"/repos/{owner_repo(repo)}/commits/{sha}/check-runs")
    runs = d.get("check_runs", [])
    if not runs:
        return "none", [], []
    # Pour BI, on ne considère pas les échecs CI comme bloquants
    # On retourne quand même le statut mais on n'arrête pas la pile
    failed = [r for r in runs if r.get("conclusion") in ("failure", "timed_out", "cancelled", "action_required")]
    pending = [r["name"] for r in runs if r.get("status") != "completed"]
    if failed:
        details: list[str] = []
        for r in failed:
            details += [f"[{r['name']}] {ln}" for ln in job_failures(http, repo, r)]
        return "failure", [r["name"] for r in failed], details
    if pending:
        return "pending", pending, []
    return "success", [], []


def wait_ci(http: Http, repo: str, branch: str, max_min: int) -> tuple[str, list[str], list[str], dict | None]:
    """BI : CI indifférente, on attend pas vraiment mais on lit l'état."""
    t0 = time.time()
    pr = None
    while time.time() - t0 < max_min * 60:
        pr = find_pr(http, repo, branch)
        if pr:
            status, names, details = ci_status(http, repo, pr["head"]["sha"])
            # Pour BI, on lit le statut mais on ne l'utilise pas pour arrêter
            return status, names, details, pr
        time.sleep(60)
    return "pending", [], [], pr


def new_failures(details: list[str], inherited: list[str]) -> list[str]:
    """BI : nouvelles erreurs par rapport à la base."""
    base = {re.sub(r"^\[[^\]]*\]\s*", "", d) for d in inherited}
    return [d for d in details if re.sub(r"^\[[^\]]*\]\s*", "", d) not in base]


def failure_keys(details: list[str], names: list[str]) -> frozenset:
    """BI : empreinte d'échec CI (littérale, pas de spec keys)."""
    keys = {m.group(1) for d in details for m in [re.search(r"(e2e/[\w./-]+\.spec\.js|\btest_[a-z0-9_]+\.py(?:::\w+)?)", d)] if m}
    return frozenset(keys) if keys else frozenset(f"job:{n}" for n in names)


# ---------------------------------------------------------------- revue BI

def review_final_film() -> None:
    """BI : pas de revue de film."""
    log("Pas de revue de film pour Blue Intelligence - workflow BI différent.")


def propose_next_batch(parent_dir: str, entries: list, model: str) -> str | None:
    """BI : proposition du batch suivant."""
    log("Proposition du batch suivant BI (non implémenté pour l'instant).")
    return None


def parse_next_batch(text: str) -> list[str] | None:
    """BI : parsing du bloc de proposition du batch suivant."""
    # BI n'a pas de bloc de proposition de batch structuré
    return None


# ---------------------------------------------------------------- places

def port_busy(port: int) -> bool:
    """Vérifie si un port Playwright est déjà utilisé."""
    try:
        result = subprocess.run(["lsof", "-i", f":{port}"], capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except Exception:
        return False


# ---------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=str(HERE / "slots_bi.json"))
    ap.add_argument("--dry-run", action="store_true", help="état, décisions et prochaines places ; ne lance rien")
    ap.add_argument("--only", help="Lancer un lot spécifique (id)")
    ap.add_argument("--from", dest="from_", help="Lancer depuis ce lot")
    ap.add_argument("--until", help="S'arrêter avant ce lot")
    ap.add_argument("--runtime", choices=["local", "cloud"], default="local", help="Exécution locale ou cloud")
    ap.add_argument("--model", help="Modèle à utiliser (défaut: meterless/auto)")
    ap.add_argument("--review-every", type=int, default=0, help="Nombre de lots entre chaque revue")
    ap.add_argument("--fix-rounds", type=int, default=0, help="Nombre de tours de correction")
    ap.add_argument("--no-parcours-complet", action="store_true", help="Ne pas faire le parcours complet NAVIGUIDE")
    ap.add_argument("--no-recette", action="store_true", help="Pas de poste de recette")
    ap.add_argument("--no-loop", action="store_true", help="Pas de boucle de correction")
    ap.add_argument("--no-watchdog", action="store_true", help="Pas de watchdog")
    ap.add_argument("--recette", action="store_true", help="Poste de recette sur la dernière branche")
    ap.add_argument("--recette --branch", dest="recette_branch", help="Poste de recette sur une branche spécifique")
    args = ap.parse_args()

    # Vérification environnement
    if args.runtime == "local":
        if not os.path.exists(ROOT):
            sys.exit(f"Dépôt principal absent : {ROOT}")
        # Vérifier que BLUE_INTELLIGENCE_ROOT est défini
        if "BLUE_INTELLIGENCE_ROOT" not in os.environ:
            if not Path.home().joinpath("blue-intelligence").exists():
                sys.exit("BLUE_INTELLIGENCE_ROOT manquant et ~/blue-intelligence introuvable")

    # Lecture du plan
    md = Path(repo_paths.PROMPTS_MD).read_text(encoding="utf-8")
    lots = parse_lots(md)

    # Filtrer si --only, --from, --until
    lots = select(lots, args)

    # Charger l'état
    state = State.load()

    # Si --recette, faire la recette
    if args.recette:
        recette_branch = args.recette_branch or state.last_branch
        log(f"Poste de recette sur la branche : {recette_branch}")
        # Pour BI, pas de recette film, juste vérifier l'état
        if not recette_branch:
            sys.exit("Aucune branche trouvée pour la recette BI")
        log(f"État actuel : {state.done}")
        # Pas de build/prod pour BI - juste affichage
        log("Recette BI : affichage de l'état, pas de build/prod nécessaire")
        return

    # Si --no-recette, s'assurer qu'on ne fera pas de recette
    # (déjà géré par l'absence de l'argument --recette)

    # Lancer chaque lot
    for i, lot in enumerate(lots):
        if i > 0:
            # Attendre que le lot précédent soit fini
            # Vérifier l'état du lot précédent
            prev_lot = lots[i-1]
            prev_state = state.done.get(prev_lot.id, {})
            if prev_state.get("status") != "FINISHED":
                log(f"Lot {prev_lot.id} n'est pas fini, en attente...")
                # Pour simplifier, on attend un peu
                time.sleep(10)

        log(f"Démarrage du lot {lot.id} : {lot.title}")

        # Créer le worktree
        wt_dir = WORKTREES / lot.id.lower()
        wt_dir.mkdir(parents=True, exist_ok=True)

        # Initialiser git et la branche
        # git checkout -b <id> main
        import shutil
        # On suppose que le dépôt est déjà cloné

        # Lancer l'agent Cursor
        model = lot_model(lot, args)

        # Préparer l'environnement
        env = {**os.environ,
               "BIM_STATE_DIR": str(STATE_DIR),
               "BIM_LOTS_DIR": str(WORKTREES),
               "BIM_PW_PORT": str(5199 + i),  # port Playwright par lot
               "BIM_PROMPTS_MD": str(repo_paths.PROMPTS_MD)}

        # Lancer l'agent
        agent_cmd = [sys.executable, str(HERE / "slots_bi.py"), "--only", lot.id,
                      "--runtime", args.runtime, "--model", model,
                      "--review-every", str(args.review_every),
                      "--fix-rounds", str(args.fix_rounds),
                      "--no-parcours-complet", "--no-recette", "--no-loop", "--no-watchdog"]

        log(f"Lancement de l'agent pour le lot {lot.id} avec modèle {model}")
        p = subprocess.Popen(agent_cmd, cwd=str(HERE), env=env, stdout=sys.stdout, stderr=sys.stderr)

        # Attendre la fin (simple version, pas la boucle complète)
        p.wait()
        log(f"Lot {lot.id} terminé avec code {p.returncode}")

        # Mettre à jour l'état
        state.done[lot.id] = {
            "status": "FINISHED" if p.returncode == 0 else "ERROR",
            "branch": lot.id.lower(),
            "pr": None,
            "ci": None,
            "returncode": p.returncode
        }
        state.save()


if __name__ == "__main__":
    main()