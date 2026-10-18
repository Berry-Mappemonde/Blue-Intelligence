#!/usr/bin/env python3
"""Vérifie que la somme des tests exécutés par les shards égale pytest --collect-only."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
SPLITS = int(os.environ.get("PYTEST_SPLITS", "4"))


def _junit_tests(path: Path) -> int:
    root = ET.parse(path).getroot()
    if root.tag == "testsuites":
        return sum(int(s.get("tests", 0)) for s in root.findall("testsuite"))
    return int(root.get("tests", 0))


def _collect_only_total() -> int:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests", "--collect-only", "-q"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    blob = (proc.stdout + proc.stderr).strip()
    if proc.returncode != 0:
        print(blob, file=sys.stderr)
        raise SystemExit(proc.returncode)
    collected_line = next(
        (ln for ln in reversed(blob.splitlines()) if re.search(r"\d+\s+tests?\s+collected", ln)),
        "",
    )
    m = re.search(r"(\d+)\s+tests?\s+collected", collected_line)
    if not m:
        raise SystemExit(f"impossible de lire le collect-only: {collected_line!r}")
    if proc.returncode not in (0, 5):
        print(blob, file=sys.stderr)
        raise SystemExit(proc.returncode)
    return int(m.group(1))


def main() -> None:
    artifacts = Path(os.environ.get("SHARD_ARTIFACTS_DIR", "shard-artifacts"))
    executed = 0
    shard_rows: list[tuple[int, int, float | None]] = []
    slowest: list[tuple[float, str]] = []

    for group in range(1, SPLITS + 1):
        meta_path = artifacts / f"shard-{group}" / "meta.json"
        junit_path = artifacts / f"shard-{group}" / "junit.xml"
        if not junit_path.is_file():
            print(f"manquant: {junit_path}", file=sys.stderr)
            raise SystemExit(1)
        n = _junit_tests(junit_path)
        executed += n
        duration = None
        if meta_path.is_file():
            meta = json.loads(meta_path.read_text())
            duration = meta.get("pytest_duration_sec")
            for item in meta.get("slowest", []):
                slowest.append((float(item["duration"]), item["nodeid"]))
        shard_rows.append((group, n, duration))

    collected = _collect_only_total()

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        slowest.sort(key=lambda x: -x[0])
        lines = [
            "## API Blue Intelligence — pytest (exhaustivité)",
            "",
            f"- **Tests collectés (ensemble)** : {collected}",
            f"- **Tests exécutés (somme {SPLITS} shards)** : {executed}",
            "",
            "| Shard | Exécutés | Durée pytest (s) |",
            "| --- | ---: | ---: |",
        ]
        for group, n, dur in shard_rows:
            dur_s = f"{dur:.1f}" if dur is not None else "—"
            lines.append(f"| {group}/{SPLITS} | {n} | {dur_s} |")
        lines.extend(["", "### 10 tests les plus lents (tous shards)", ""])
        for dur, node in slowest[:10]:
            lines.append(f"- `{dur:.2f}s` — {node}")
        with open(summary_path, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")

    print(f"collectés={collected} exécutés={executed}")
    if collected != executed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
