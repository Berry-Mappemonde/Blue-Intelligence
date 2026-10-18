#!/usr/bin/env python3
"""Régénère les diffs ci.yml de la section 6.6 du plan de séparation.

Lecture seule sur le monodépôt : lit .github/workflows/ci.yml, écrit les
patches sur stdout ou dans des fichiers. Ne modifie pas le dépôt.

    python3 scripts/generate_split_ci_diffs.py --check
    python3 scripts/generate_split_ci_diffs.py bi > /tmp/bi-ci.patch
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / ".github/workflows/ci.yml"

BI_HEADER = """name: CI

#   - jest verrouille l'ordre des couches carte et le registre des fonds ;
#   - le build CRA attrape les régressions de bundling (maplibre chargé à la demande) ;
#   - le script d'audit des tags tourne en mode GeoJSON sur les seeds (stdlib pur) ;
#   - API Blue Intelligence : six shards pytest parallèles (Mongo + uvicorn isolés),
#     cache Overpass, venv et modèle HF en cache, puis agrégateur requis
#     « API Blue Intelligence — pytest » (ci_pytest_gate.py, exhaustivité).
# Copie Blue Intelligence. Les jobs simulateur ne sont pas dans ce dépôt.

"""

NG_HEADER = """name: CI

# Copie NAVIGUIDE. Frontend Blue Intelligence, audit des tags et le pytest
# de l'API Blue Intelligence ne sont pas dans ce dépôt. Le simulateur est
# testé si la PR le touche.

"""


def job_ranges(lines: list[str]) -> dict[str, tuple[int, int]]:
    jobs_idx = next(i for i, line in enumerate(lines) if line.strip() == "jobs:")
    starts: list[tuple[int, str]] = []
    for i in range(jobs_idx + 1, len(lines)):
        match = re.match(r"^  ([a-z][a-z0-9_-]*):\s*$", lines[i].rstrip("\n"))
        if match:
            starts.append((i, match.group(1)))
    ranges: dict[str, tuple[int, int]] = {}
    for j, (start, name) in enumerate(starts):
        end = starts[j + 1][0] if j + 1 < len(starts) else len(lines)
        ranges[name] = (start, end)
    return ranges


def build_ci(side: str, lines: list[str], ranges: dict[str, tuple[int, int]]) -> str:
    jobs_idx = next(i for i, line in enumerate(lines) if line.strip() == "jobs:")
    on_start = next(i for i, line in enumerate(lines) if line.startswith("on:"))
    header = BI_HEADER if side == "bi" else NG_HEADER
    pre = header + "".join(lines[on_start : jobs_idx + 1])
    if side == "bi":
        keep = [
            "frontend",
            "audit-tags",
            "backend-pytest-shard",
            "backend",
            "deploy-gate",
        ]
    else:
        keep = ["changes", "simulator", "simulator-e2e", "deploy-gate"]
    body = ""
    for name in keep:
        start, end = ranges[name]
        body += "".join(lines[start:end])
    if side == "bi":
        body = body.replace(
            "needs: [frontend, audit-tags, backend, changes, simulator, simulator-e2e]",
            "needs: [frontend, audit-tags, backend]",
        )
        body = body.replace(
            "for name in R_FRONTEND R_AUDIT R_BACKEND R_CHANGES R_SIMULATOR R_E2E; do",
            "for name in R_FRONTEND R_AUDIT R_BACKEND; do",
        )
        body = re.sub(
            r"          R_CHANGES: \$\{\{ needs\.changes\.result \}\}\n"
            r"          R_SIMULATOR: \$\{\{ needs\.simulator\.result \}\}\n"
            r"          R_E2E: \$\{\{ needs\.simulator-e2e\.result \}\}\n",
            "",
            body,
        )
        body = body.replace(
            "          bash -n infra/vps/naviguide/deploy-naviguide.sh\n"
            "          bash -n infra/vps/naviguide/deploy-simulator.sh\n",
            "",
        )
    else:
        body = body.replace(
            "needs: [frontend, audit-tags, backend, changes, simulator, simulator-e2e]",
            "needs: [changes, simulator, simulator-e2e]",
        )
        body = body.replace(
            "          R_FRONTEND: ${{ needs.frontend.result }}\n"
            "          R_AUDIT: ${{ needs.audit-tags.result }}\n"
            "          R_BACKEND: ${{ needs.backend.result }}\n",
            "",
        )
        body = body.replace(
            "for name in R_FRONTEND R_AUDIT R_BACKEND R_CHANGES R_SIMULATOR R_E2E; do",
            "for name in R_CHANGES R_SIMULATOR R_E2E; do",
        )
        body = body.replace(
            "          bash -n infra/vps/deploy-app.sh\n"
            "          bash -n infra/vps/bi-healthcheck.sh\n"
            "          bash -n infra/vps/install-memory-guards.sh\n"
            "          bash -n infra/vps/sync-public-nginx.sh\n",
            "",
        )
    return pre + body


def git_diff(base: str, patched: str) -> str:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        a = Path(tmp) / "a.yml"
        b = Path(tmp) / "b.yml"
        a.write_text(base, encoding="utf-8")
        b.write_text(patched, encoding="utf-8")
        proc = subprocess.run(
            ["git", "diff", "--no-index", "--", str(a), str(b)],
            text=True,
            capture_output=True,
        )
        if proc.returncode not in (0, 1):
            raise SystemExit(proc.stderr or proc.stdout)
        out = proc.stdout
        out = re.sub(
            r"diff --git a/.+ b/.+\n",
            "diff --git a/.github/workflows/ci.yml b/.github/workflows/ci.yml\n",
            out,
            count=1,
        )
        out = re.sub(r"^--- a/.*$", "--- a/.github/workflows/ci.yml", out, count=1, flags=re.M)
        out = re.sub(r"^\+\+\+ b/.*$", "+++ b/.github/workflows/ci.yml", out, count=1, flags=re.M)
        return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("side", nargs="?", choices=("bi", "ng", "both"), default="both")
    parser.add_argument("--check", action="store_true", help="git apply --check sur le ci.yml du dépôt")
    args = parser.parse_args()
    if not CI.is_file():
        raise SystemExit(f"absent : {CI}")
    lines = CI.read_text(encoding="utf-8").splitlines(keepends=True)
    base = "".join(lines)
    ranges = job_ranges(lines)
    sides = ("bi", "ng") if args.side == "both" else (args.side,)
    failed = False
    for side in sides:
        patched = build_ci(side, lines, ranges)
        diff = git_diff(base, patched)
        if args.check:
            proc = subprocess.run(
                ["git", "apply", "--check"],
                input=diff,
                text=True,
                cwd=ROOT,
                capture_output=True,
            )
            if proc.returncode != 0:
                print(proc.stderr, file=sys.stderr)
                failed = True
            else:
                print(f"{side}: git apply --check OK", file=sys.stderr)
        else:
            sys.stdout.write(diff)
            if args.side == "both" and side == "bi":
                sys.stdout.write("\n")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
