#!/usr/bin/env python3
"""Reprendre les AMP stockées en Point + moissonner Entry / Speed (ProtectedSeas).

Usage sur le VPS, depuis backend/ :

  .venv/bin/python scripts/repair_amp_polygons.py

Ne touche pas au chauffeur simulateur. Ne fait pas sync-from-atlas.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


async def main() -> int:
    from app.db import db
    from app.services import amp as amp_svc

    def log(msg: str) -> None:
        print(msg, flush=True)

    await amp_svc.ensure_amp_indexes(db)
    # 0.02° d'abord : offset=0 sur une ZEE (12 Mo) faisait rater tout le lot HTTP.
    poly = await amp_svc.repair_point_sites(db, log=log, offsets=(0.02, 0.08, 0.2))
    attrs = await amp_svc.backfill_entry_speed(db, log=log)
    print({"polygons": poly, "entry_speed": attrs}, flush=True)
    return 0 if int(poly.get("still_point") or 0) < int(poly.get("candidates") or 1) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
