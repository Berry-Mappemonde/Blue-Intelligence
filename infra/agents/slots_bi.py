#!/usr/bin/env python3
"""Ordonnanceur à places pour Blue Intelligence : garde N lots en codage sur ce Mac, en permanence.

Chaque place se remplit dès qu'elle se libère, sans attendre les autres : une place est libre
dès que le cursor-agent qui l'occupe a fini de coder. La suite du lot (push unique, PR, CI,
relance de correction) continue en arrière-plan dans son run_lots_bi.py, sans tenir la place.
Une relance de correction reprend une place tant que son agent tourne.

Occupent une place :
- tout cursor-agent `-p` lancé à la main (processus vivant, repéré par ps) ;
- tout lot lancé par l'ordonnanceur tant que son premier passage d'agent n'est pas fini,
  ou tant qu'un agent tourne dans son worktree (relance).

Un lot du plan (repo_paths.PROMPTS_MD) part quand :
- il est dans une section BLUE INTELLIGENCE (slots_bi.json : sections, extra_lots) ;
- il n'est ni exclu, ni en attente (hold), ni pris (taken), ni déjà lancé par l'ordonnanceur ;
- ses dépendances (balise deps + extra_deps) sont mergées sur GitHub ;
- aucun lot en cours (pas encore mergé) n'est dans son never_with, ni lui dans le leur ;
- il ne touche aucun des fichiers d'un lot en cours (fichiers cités dans les prompts,
  fichiers modifiés dans les worktrees), sauf lot accepté à la main (slots_bi.json « share_ok ») ;
- son not_before (UTC) est passé.
Les départs sont décalés de stagger_s (verrous git). Limite d'usage Cursor : tout s'arrête
(agents de la chaîne arrêtés, worktrees gardés), rien n'est relancé, code 7.
Fichier STOP (~/lots-live/STOP ou <chain>/slots/STOP) : plus aucun départ, sortie propre.

Priorité : --priority-lots (liste « A,B,C » ou fichier, un id par ligne, # pour commenter ; sinon
slots_bi.json « priority ») passe avant l'ordre du plan ; --only-priority ignore tous les autres lots.
Un id de priorité absent des lots BI du plan est signalé et ignoré.

Usage :
/opt/homebrew/bin/python3 infra/agents/slots_bi.py --dry-run     # état, décisions, 3 prochaines places
/opt/homebrew/bin/python3 infra/agents/slots_bi.py --dry-run --priority-lots ~/lots-live/priorite.txt --only-priority
nohup /opt/homebrew/bin/python3 infra/agents/slots_bi.py >> ~/lots-live/slots_bi.out 2>&1 &
"""
from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHAIN = Path(os.environ.get("BIM_CHAIN_DIR", str(Path.home() / "rw-push" / "local-lots" / "chain")))
SLOTS_DIR = CHAIN / "slots"
SLOTS_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BLUE_INTELLIGENCE_ROOT", str(Path.home() / "rw-push" / "local-lots" / "bi-root"))
os.environ["BIM_STATE_DIR"] = str(SLOTS_DIR)
os.environ.setdefault("BIM_LOTS_DIR", str(CHAIN / "wt"))
sys.path.insert(0, str(HERE))

import repo_paths  # noqa: E402
import run_lots_bi as rl  # noqa: E402

MANUAL_DIR = Path.home() / "rw-push" / "local-lots"
CHAIN_WT = Path(os.environ["BIM_LOTS_DIR"])
LIVE_LOG = Path.home() / "lots-live" / "lots_bi.log"
REGISTRY = SLOTS_DIR / "registry.json"
STOP_FILES = (Path.home() / "lots-live" / "STOP", SLOTS_DIR / "STOP")
AGENT_RE = re.compile(r"/\.local/bin/(?:cursor-)?agent\s.*\s-p(?:\s|$)")
PATH_RE = re.compile(r"(?<![\w/.-])((?:[\w.-]+/)*[\w-][\w.-]*\.(?:jsx|js|mjs|cjs|ts|tsx|py|css|scss|json|ya?ml|html|sh|toml|conf))\b")
POLL_S = 20


def log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} [places-bi] {msg}"
    print(line, flush=True)
    LIVE_LOG.parent.mkdir(parents=True, exist_ok=True)
    for f in (LIVE_LOG, SLOTS_DIR / "slots_bi.log"):
        with f.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")


EXCLUS_FILE = Path.home() / "lots-live" / "exclus.txt"


def read_exclus() -> list[str]:
    try:
        lines = EXCLUS_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    return [l.split("#", 1)[0].strip() for l in lines if l.split("#", 1)[0].strip()]


def load_cfg(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_registry() -> dict:
    try:
        return json.loads(REGISTRY.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_registry(reg: dict) -> None:
    REGISTRY.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")


def alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
    except (OSError, ValueError):
        return False
    st = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
    return bool(st) and not st.startswith("Z")


# ---------------------------------------------------------------- plan

def section_of_lines(md: str) -> list[tuple[int, str]]:
    out, cur = [], ""
    for i, ln in enumerate(md.splitlines()):
        if ln.startswith("## "):
            cur = ln
        out.append((i, cur))
    return out


def pool_lots(cfg: dict) -> list:
    md = Path(repo_paths.PROMPTS_MD).read_text(encoding="utf-8")
    lots = rl.parse_lots(md)
    sec_by_line = section_of_lines(md)
    pos = {}
    for m in rl.LOT_RE.finditer(md):
        line = md.count("\n", 0, m.start())
        pos[m.group("id")] = sec_by_line[line][1]
    keep = []
    for l in lots:
        sec = pos.get(l.id, "")
        if any(sec.startswith(s) for s in cfg.get("sections", [])) or l.id in cfg.get("extra_lots", []):
            keep.append(l)
    return keep


def prompt_files(lots: list) -> dict[str, set[str]]:
    raw = {l.id: {Path(x).name for x in PATH_RE.findall(l.prompt)} for l in lots}
    # Les fichiers cités par la plupart des prompts (règles recopiées dans chaque lot) ne disent rien.
    counts: dict[str, int] = {}
    for s in raw.values():
        for f in s:
            counts[f] = counts.get(f, 0) + 1
    common = {f for f, n in counts.items() if n >= max(3, len(lots) // 4)}
    return {k: v - common for k, v in raw.items()}


def worktree_files(wt: Path) -> set[str]:
    if not wt.exists():
        return set()
    names: set[str] = set()
    for args in (["diff", "--name-only", "origin/main...HEAD"], ["status", "--porcelain"]):
        p = subprocess.run(["git", "--no-optional-locks", "-C", str(wt), *args], capture_output=True, text=True, timeout=60)
        for ln in p.stdout.splitlines():
            ln = ln[3:] if args[0] == "status" else ln
            if ln.strip():
                names.add(Path(ln.strip().split(" -> ")[-1]).name)
    return names


# ---------------------------------------------------------------- GitHub

class Merged:
    def __init__(self, repo: str):
        self.repo = repo
        self.http = rl.Http(None, rl.github_token_from_git())
        self.heads: set[str] = set()
        self.at = 0.0

    def refresh(self, force: bool = False) -> set[str]:
        if not force and time.time() - self.at < 300:
            return self.heads
        heads: set[str] = set()
        for page in (1, 2, 3):
            prs = self.http.github(f"/repos/{self.repo}/pulls?state=closed&per_page=100&sort=updated&direction=desc&page={page}")
            heads |= {p["head"]["ref"] for p in prs if p.get("merged_at")}
            if len(prs) < 100:
                break
        self.heads, self.at = heads, time.time()
        return heads


# ---------------------------------------------------------------- processus

def agent_workspaces() -> dict[int, str]:
    """pid -> dossier de travail des cursor-agent `-p` vivants (hors agents de l'éditeur)."""
    out = subprocess.run(["ps", "-axo", "pid=,command="], capture_output=True, text=True).stdout
    res = {}
    for ln in out.splitlines():
        ln = ln.strip()
        pid_s, _, cmd = ln.partition(" ")
        if "Application Support" in cmd or "cursorsandbox" in cmd or not AGENT_RE.search(cmd):
            continue
        m = re.search(r"--workspace\s+(\S+)", cmd)
        ws = m.group(1) if m else ""
        if not ws:
            q = subprocess.run(["lsof", "-a", "-p", pid_s, "-d", "cwd", "-Fn"], capture_output=True, text=True).stdout
            ws = next((x[1:] for x in q.splitlines() if x.startswith("n")), "")
        res[int(pid_s)] = ws
    return res


class Child:
    def __init__(self):
        self.procs: dict[str, subprocess.Popen] = {}
        self.offsets: dict[str, int] = {}

    def forward_logs(self, reg: dict) -> None:
        for lid, e in reg.items():
            f = Path(e["state_dir"]) / "run_lots_bi.log"
            if not f.exists():
                continue
            off = self.offsets.get(lid, e.get("log_offset", 0))
            with f.open("r", encoding="utf-8", errors="replace") as fh:
                fh.seek(off)
                new = fh.read()
                self.offsets[lid] = e["log_offset"] = fh.tell()
            if new.strip():
                with LIVE_LOG.open("a", encoding="utf-8") as out:
                    for ln in new.splitlines():
                        out.write(f"[{lid}] {ln}\n")


def first_pass_done(e: dict) -> bool:
    f = Path(e["state_dir"]) / "run_lots_bi.log"
    try:
        t = f.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return "    agent: " in t or "RATÉ" in t or "pré-vol : ÉCHEC" in t


def usage_limit_seen(reg: dict, children: Child) -> str | None:
    for lid, e in reg.items():
        if (Path(e["state_dir"]) / "USAGE_LIMIT").exists():
            return f"lot {lid} de la chaîne"
        p = children.procs.get(lid)
        if p is not None and p.poll() == rl.USAGE_LIMIT_EXIT:
            return f"lot {lid} de la chaîne (code {rl.USAGE_LIMIT_EXIT})"
    now = time.time()
    for f in MANUAL_DIR.glob("*-run.err"):
        try:
            if now - f.stat().st_mtime > 900:
                continue
            tail = f.read_text(encoding="utf-8", errors="replace")[-4000:]
        except OSError:
            continue
        if rl.USAGE_LIMIT_RE.search(tail):
            return f"lot manuel ({f.name})"
    return None


def stop_chain(reg: dict, why: str) -> None:
    log(f"LIMITE D'USAGE Cursor ({why}) : arrêt de la chaîne, worktrees gardés, rien n'est relancé. Prévenir Amiral.")
    for lid, e in reg.items():
        if alive(e.get("pid")):
            try:
                os.killpg(int(e["pid"]), signal.SIGTERM)
                log(f"    {lid} : run_lots_bi arrêté (pid {e['pid']})")
            except OSError:
                pass
    for pid, ws in agent_workspaces().items():
        if ws.startswith(str(CHAIN_WT)):
            try:
                os.killpg(pid, signal.SIGTERM)
            except OSError:
                try:
                    os.kill(pid, signal.SIGTERM)
                except OSError:
                    pass
            log(f"    agent de la chaîne {pid} arrêté ({ws})")
    (Path.home() / "lots-live" / "USAGE_LIMIT").write_text(time.strftime("%Y-%m-%d %H:%M:%S") + f" {why}\n", encoding="utf-8")


# ---------------------------------------------------------------- décision

def resolve_model(cfg: dict) -> str:
    info = rl.local_check()
    if not info["agent"] or not info["logged"]:
        sys.exit("CLI Cursor absent ou non connecté")
    ids = [m.split()[0] for m in info["models"]]
    want = cfg.get("model") or rl.DEFAULT_MODEL
    if want in ids:
        return want
    # Pour BI on utilise meterless/auto (Nemotron via Meterless)
    cands = [i for i in ids if "meterless" in i.lower() or "nemotron" in i.lower()]
    if not cands:
        sys.exit("Aucun modèle Meterless/Nemotron dans `agent models` : arrêt (rien lancé)")
    return cands[0]


def read_priority(spec: str | None, cfg: dict) -> list[str]:
    """--priority-lots : « A,B,C » ou chemin d'un fichier (un id par ligne, # = commentaire)."""
    if not spec:
        return [str(x) for x in cfg.get("priority", [])]
    p = Path(spec).expanduser()
    text = p.read_text(encoding="utf-8") if p.exists() else spec
    ids: list[str] = []
    for ln in text.splitlines():
        ln = ln.split("#", 1)[0]
        ids += [x.strip() for x in ln.split(",") if x.strip()]
    return list(dict.fromkeys(ids))


class Planner:
    def __init__(self, cfg: dict, merged: Merged, priority: list[str] | None = None, only_priority: bool = False):
        self.cfg = cfg
        self.merged = merged
        pool = pool_lots(cfg)
        self.pfiles = prompt_files(pool)   # fichiers « communs » jugés sur tout le plan, pas sur la seule priorité
        self.full_pool = pool
        self.only_priority = only_priority
        self._wt_cache: dict[str, tuple[float, set[str]]] = {}
        self.set_priority(priority or [])

    def set_priority(self, priority: list[str]) -> None:
        """Lots prioritaires d'abord (dans l'ordre donné), puis l'ordre du plan. Rappelé à chaque
        changement du fichier de priorité, sans redémarrer l'ordonnanceur."""
        ids = {l.id for l in self.full_pool}
        self.priority = [x for x in priority if x in ids]
        self.unknown_priority = [x for x in priority if x not in ids]
        rank = {x: i for i, x in enumerate(self.priority)}
        pool = [l for l in self.full_pool if l.id in rank] if self.only_priority else list(self.full_pool)
        self.pool = sorted(pool, key=lambda l: (0, rank[l.id]) if l.id in rank else (1, 0))
        self.by_id = {l.id: l for l in self.pool}

    def branch_of(self, lid: str, reg: dict) -> str | None:
        if lid in self.cfg.get("taken", {}):
            return self.cfg["taken"][lid]
        e = reg.get(lid)
        if e:
            try:
                d = json.loads((Path(e["state_dir"]) / "state.json").read_text(encoding="utf-8"))
                return ((d.get("done") or {}).get(lid) or {}).get("branch")
            except (OSError, json.JSONDecodeError):
                return None
        return None

    def is_merged(self, lid: str, reg: dict) -> bool:
        if lid in self.cfg.get("merged", []):
            return True
        b = self.branch_of(lid, reg)
        return bool(b) and b in self.merged.refresh()

    def active(self, reg: dict) -> list[str]:
        """Lots en cours : pris ou lancés, pas encore mergés."""
        ids = list(self.cfg.get("taken", {})) + list(reg)
        return [x for x in dict.fromkeys(ids) if not self.is_merged(x, reg)]

    def files_of(self, lid: str, reg: dict) -> set[str]:
        files = set(self.pfiles.get(lid, set()))
        wt = None
        if lid in self.cfg.get("worktrees", {}):
            wt = MANUAL_DIR / self.cfg["worktrees"][lid]
        elif lid in reg:
            wt = CHAIN_WT / lid.lower()
        if wt is not None:
            ts, cached = self._wt_cache.get(lid, (0.0, set()))
            if time.time() - ts > 120:
                try:
                    cached = worktree_files(wt)
                except Exception:  # noqa: BLE001
                    cached = set()
                self._wt_cache[lid] = (time.time(), cached)
            files |= cached
        return files

    def decide(self, reg: dict, extra_active: list[str] | None = None) -> list[tuple[str, str]]:
        """[(id, raison)] pour chaque lot restant ; raison vide = peut partir."""
        act = self.active(reg) + list(extra_active or [])
        act_files = {a: self.files_of(a, reg) for a in act}
        nw = self.cfg.get("never_with", {})
        now = datetime.now(timezone.utc)
        out = []
        for l in self.pool:
            lid = l.id
            if lid in self.cfg.get("exclude", {}):
                continue
            if lid in self.cfg.get("taken", {}) or lid in reg or lid in (extra_active or []):
                continue
            if lid in self.cfg.get("merged", []):
                continue
            if lid in self.cfg.get("hold", {}):
                out.append((lid, "en attente : " + self.cfg["hold"][lid]))
                continue
            nb = self.cfg.get("not_before", {}).get(lid)
            if nb and now < datetime.fromisoformat(nb.replace("Z", "+00:00")):
                out.append((lid, f"pas avant {nb}"))
                continue
            deps = list(dict.fromkeys(l.deps + self.cfg.get("extra_deps", {}).get(lid, [])))
            missing = [d for d in deps if not self.is_merged(d, reg)]
            if missing:
                out.append((lid, "dépendances non mergées : " + ", ".join(missing)))
                continue
            clash = [a for a in act if a in nw.get(lid, []) or lid in nw.get(a, [])]
            if clash:
                out.append((lid, "jamais en même temps que " + ", ".join(clash)))
                continue
            mine = self.pfiles.get(lid, set())
            # share_ok (slots_bi.json) : lots en cours dont le partage de fichiers est accepté à la main
            # (par exemple un lot qui ne fait que lire des extraits d'un fichier modifié par un lot fini).
            ok = set(self.cfg.get("share_ok", {}).get(lid, []))
            shared = {a: sorted(mine & f) for a, f in act_files.items() if mine & f and a not in ok}
            if shared:
                out.append((lid, "mêmes fichiers que " + " ; ".join(f"{a} ({', '.join(v[:3])})" for a, v in shared.items())))
                continue
            out.append((lid, ""))
        return out

    def next_picks(self, reg: dict, n: int) -> list[str]:
        picks: list[str] = []
        for _ in range(n):
            ok = [lid for lid, why in self.decide(reg, picks) if not why]
            if not ok:
                break
            picks.append(ok[0])
        return picks


# ---------------------------------------------------------------- places

def busy_slots(reg: dict) -> tuple[int, list[str]]:
    ws = agent_workspaces()
    ids = {lid.lower() for lid in reg}
    # Un agent de la chaîne dont le worktree est ailleurs (BIM_LOTS_DIR changé) reste un agent de la chaîne.
    manual = sorted({w for w in ws.values() if not w.startswith(str(CHAIN_WT)) and Path(w).name not in ids})
    chain_named = {Path(w).name for w in ws.values() if Path(w).name in ids}
    chain_busy = []
    chain_ws = {w for w in ws.values() if w.startswith(str(CHAIN_WT))}
    for lid, e in reg.items():
        mine = str(CHAIN_WT / lid.lower())
        if mine in chain_ws or lid.lower() in chain_named or (alive(e.get("pid")) and not first_pass_done(e)):
            chain_busy.append(lid)
    who = [Path(w).name or w for w in manual] + chain_busy
    return len(manual) + len(chain_busy), who


def free_port(cfg: dict, reg: dict) -> int:
    used = {e.get("port") for e in reg.values() if alive(e.get("pid"))}
    for p in cfg.get("ports", [5199, 5201, 5203]):
        if p not in used and not rl.port_busy(p):
            return p
    return cfg.get("ports", [5199])[-1] + 2


def launch(lid: str, model: str, cfg: dict, reg: dict, children: Child) -> None:
    sd = CHAIN / "state" / lid
    sd.mkdir(parents=True, exist_ok=True)
    port = free_port(cfg, reg)
    env = {**os.environ, "BIM_STATE_DIR": str(sd), "BIM_LOTS_DIR": str(CHAIN_WT), "BIM_PW_PORT": str(port),
           "BIM_PROMPTS_MD": str(repo_paths.PROMPTS_MD)}
    cmd = [sys.executable, str(HERE / "run_lots_bi.py"), "--runtime", "local", "--only", lid, "--stack", "none",
           "--model", model, "--review-every", "0", "--fix-rounds", "0", "--no-parcours-complet",
           "--no-recette", "--no-tunnel", "--no-loop", "--no-watchdog"]
    out = (sd / "child.out").open("a", encoding="utf-8")
    p = subprocess.Popen(cmd, cwd=str(HERE), env=env, stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
    children.procs[lid] = p
    reg[lid] = {"pid": p.pid, "port": port, "state_dir": str(sd), "started": time.strftime("%Y-%m-%d %H:%M:%S"), "model": model}
    save_registry(reg)
    log(f"{lid} lancé (pid {p.pid}, port Playwright {port}, modèle {model}) — journal {sd / 'run_lots_bi.log'}")


def close_batch(reg: dict, model: str) -> None:
    """Fin de batch BI : pas de parcours complet NAVIGUIDE, pas de film."""
    log("Tous les lots BI lancés et terminés — fin du batch Blue Intelligence.")
    # Pour BI, on ne fait pas de revue de film ni de parcours complet NAVIGUIDE
    # L'agent de fin de batch BI peut proposer le batch suivant si activé


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=str(HERE / "slots_bi.json"))
    ap.add_argument("--dry-run", action="store_true", help="état, décisions et prochaines places ; ne lance rien")
    ap.add_argument("--slots", type=int, help="nombre de places (défaut : slots_bi.json)")
    ap.add_argument("--priority-lots", help="lots prioritaires, avant l'ordre du plan : « A,B,C » ou fichier (un id par ligne)")
    ap.add_argument("--only-priority", action="store_true", help="ne lancer que les lots prioritaires")
    args = ap.parse_args()
    cfg = load_cfg(Path(args.config))
    n = args.slots or int(cfg.get("slots", 3))
    model = resolve_model(cfg)
    merged = Merged(cfg.get("repo", rl.owner_repo(rl.DEFAULT_REPO)))
    prio = read_priority(args.priority_lots, cfg)
    if args.only_priority and not prio:
        sys.exit("--only-priority sans liste de priorité (--priority-lots ou slots_bi.json « priority ») : rien à lancer")
    planner = Planner(cfg, merged, prio, args.only_priority)
    if planner.unknown_priority:
        log(f"priorité : ignorés (absents des lots BI du plan) : {', '.join(planner.unknown_priority)}")
    reg = load_registry()
    children = Child()
    if args.dry_run:
        busy, who = busy_slots(reg)
        print(f"Modèle : {model}")
        print(f"Plan : {repo_paths.PROMPTS_MD} — {len(planner.pool)} lots BLUE INTELLIGENCE")
        print(f"Dépôt principal : {rl.ROOT}")
        print(f"Places : {n} — occupées {busy} ({', '.join(who) or 'aucune'})")
        print(f"Priorité : {', '.join(planner.priority) or 'aucune'}" + (" — seulement ces lots" if args.only_priority else "")
              + (f" ; ignorés (hors plan BI) : {', '.join(planner.unknown_priority)}" if planner.unknown_priority else ""))
        print(f"Lots en cours (pas mergés) : {', '.join(planner.active(reg))}")
        print("Décisions :")
        for lid, why in planner.decide(reg):
            print(f"  {lid:6} {'PEUT PARTIR' if not why else why}")
        print(f"Prochaines places, dans l'ordre : {', '.join(planner.next_picks(reg, n)) or 'aucune'}")
        return
    if not rl.ROOT.exists():
        sys.exit(f"Dépôt principal absent : {rl.ROOT}")
    log(f"démarrage BI : {n} places, modèle {model}, plan {repo_paths.PROMPTS_MD}, dépôt {rl.ROOT}, pid {os.getpid()}"
        + (f", priorité {', '.join(planner.priority)}" if planner.priority else "") + (" (seulement elle)" if args.only_priority else ""))
    last_start = 0.0
    last_state = ""
    prio_file = Path(args.priority_lots).expanduser() if args.priority_lots and Path(args.priority_lots).expanduser().exists() else None
    prio_mtime = prio_file.stat().st_mtime if prio_file else 0.0
    base_exclude = dict(planner.cfg.get("exclude", {}))
    excl_mtime = -1.0
    while True:
        # Le fichier de priorité est relu dès qu'il change, avant chaque remplissage de place.
        if prio_file is not None:
            try:
                m = prio_file.stat().st_mtime
            except OSError:
                m = prio_mtime
            if m != prio_mtime:
                prio_mtime = m
                planner.set_priority(read_priority(str(prio_file), cfg))
                log(f"priorité relue : {', '.join(planner.priority) or 'aucune'}"
                    + (f" ; ignorés (hors plan BI) : {', '.join(planner.unknown_priority)}" if planner.unknown_priority else ""))
        # Liste d'exclusion relue à chaud (~/lots-live/exclus.txt : un id par ligne, « # » = commentaire) :
        # lots pris ailleurs (agents cloud…), jamais lancés en local.
        try:
            ex_m = EXCLUS_FILE.stat().st_mtime
        except OSError:
            ex_m = 0.0
        if ex_m != excl_mtime:
            excl_mtime = ex_m
            extra = read_exclus()
            planner.cfg["exclude"] = {**base_exclude, **{x: "exclus.txt (pris ailleurs)" for x in extra}}
            log(f"exclusion relue : {', '.join(extra) or 'aucune'}")
        children.forward_logs(reg)
        save_registry(reg)
        why = usage_limit_seen(reg, children)
        if why:
            stop_chain(reg, why)
            save_registry(reg)
            sys.exit(rl.USAGE_LIMIT_EXIT)
        if any(f.exists() for f in STOP_FILES):
            log("fichier STOP : plus aucun départ ; les lots déjà partis continuent seuls. Sortie.")
            return
        for lid, p in list(children.procs.items()):
            code = p.poll()
            if code is not None:
                reg[lid]["exit"] = code
                log(f"{lid} : run_lots_bi terminé (code {code})")
                children.procs.pop(lid)
        busy, who = busy_slots(reg)
        try:
            decisions = planner.decide(reg)
        except Exception as e:  # noqa: BLE001 — GitHub injoignable : on réessaie au tour suivant
            log(f"décision impossible ({type(e).__name__}: {e}) — nouvel essai dans {POLL_S * 3} s")
            time.sleep(POLL_S * 3)
            continue
        ready = [lid for lid, w in decisions if not w]
        state = f"{busy}/{n} occupées ({', '.join(who) or '-'}) ; prêts : {', '.join(ready) or '-'}"
        if state != last_state:
            log(state)
            last_state = state
        if busy < n and ready and time.time() - last_start >= int(cfg.get("stagger_s", 120)):
            launch(ready[0], model, cfg, reg, children)
            last_start = time.time()
            time.sleep(15)   # le temps que le run_lots_bi du lot apparaisse comme occupé
            continue
        if not decisions and not any(alive(e.get("pid")) for e in reg.values()):
            log("plus aucun lot à lancer et plus rien ne tourne : fin du codage BI.")
            close_batch(reg, model)
            return
        time.sleep(POLL_S)


if __name__ == "__main__":
    main()