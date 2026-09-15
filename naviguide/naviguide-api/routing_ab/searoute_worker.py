"""Subprocess: compute a searoute route and write GeoJSON to stdout.

Used to compare searoute 1.4 and 1.6 without mixing two versions in
the same interpreter.
"""

from __future__ import annotations

import json
import sys


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: searoute_worker.py '[lon,lat]' '[lon,lat]'", file=sys.stderr)
        return 2
    start = json.loads(sys.argv[1])
    end = json.loads(sys.argv[2])
    import searoute as sr  # noqa: WPS433 — intentional local import (dedicated venv)

    route = sr.searoute((float(start[0]), float(start[1])), (float(end[0]), float(end[1])))
    json.dump(route, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
