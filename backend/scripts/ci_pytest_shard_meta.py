#!/usr/bin/env python3
"""Écrit meta.json (durée shard + tests les plus lents) depuis un junit.xml pytest."""
from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path


def _cases(path: Path) -> list[tuple[float, str]]:
    root = ET.parse(path).getroot()
    suites = root.findall("testsuite") if root.tag == "testsuites" else [root]
    out: list[tuple[float, str]] = []
    for suite in suites:
        classname = suite.get("name", "")
        for case in suite.findall("testcase"):
            t = float(case.get("time", 0) or 0)
            name = case.get("name", "")
            node = f"{classname}::{name}" if classname else name
            out.append((t, node))
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--duration-sec", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    cases = _cases(args.junit)
    slowest = sorted(cases, key=lambda x: -x[0])[:30]
    payload = {
        "pytest_duration_sec": args.duration_sec,
        "tests_executed": len(cases),
        "slowest": [{"duration": d, "nodeid": n} for d, n in slowest],
    }
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
