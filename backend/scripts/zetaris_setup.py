"""One-off administrative setup, separate from the read-only application adapter.

Run from backend/: .venv/bin/python scripts/zetaris_setup.py
Dry run is the default. Only --apply sends SQL. Load ZETARIS_REST_URL,
ZETARIS_ORG_ID and ZETARIS_API_KEY into the environment before applying.
The REST URL defaults to http://localhost:8888/api/v1.0.

There are no automatic DDL retries or rollback. On failure, inspect the reported
statement and existing objects. --start-at N explicitly skips earlier statements
when an administrator has confirmed that they already succeeded.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from uuid import uuid4

import httpx

SQL_FILE = Path(__file__).with_name("zetaris_setup_poe.sql")
VERIFICATION = (
    "SELECT COUNT(*) FROM blue_intel.poe_ports",
    "SELECT name, zone_name, lat, lon FROM blue_intel.poe_ports LIMIT 5",
)


def statements() -> list[str]:
    """Split this trusted setup file, preserving semicolons inside SQL quotes."""
    sql = SQL_FILE.read_text(encoding="utf-8")
    tokens = re.findall(r'''--[^\n]*|'(?:''|[^'])*'|"(?:""|[^"])*"|;|[^;'"]''', sql)
    result, current = [], []
    for token in tokens:
        if token.startswith("--"):
            continue
        if token == ";":
            if "".join(current).strip():
                result.append("".join(current).strip())
            current = []
        else:
            current.append(token)
    if "".join(current).strip():
        result.append("".join(current).strip())
    return result


def execute(client: httpx.Client, url: str, key: str, org: str, sql: str) -> dict:
    response = client.post(
        url + "/sql-editor/sqls/run",
        headers={"Authorization": "Bearer " + key, "X-Org-ID": org,
                 "X-Request-ID": str(uuid4()), "Content-Type": "application/json"},
        json={"queryId": str(uuid4()), "sql": sql, "source": "SqlEditor", "limit": 1000},
    )
    try:
        payload = response.json()
    except ValueError:
        raise RuntimeError(f"HTTP {response.status_code}: non-JSON response") from None
    safe = json.dumps(payload, ensure_ascii=False).replace(key, "[REDACTED]")
    if not 200 <= response.status_code < 300:
        raise RuntimeError(f"HTTP {response.status_code}: {safe[:2000]}")
    if not isinstance(payload, dict):
        raise RuntimeError("Unexpected response: expected a JSON object")
    if payload.get("error") or str(payload.get("status", "")).lower() in {"error", "failed", "failure"}:
        raise RuntimeError(safe[:2000])
    print(safe[:2000])
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Execute the administrative SQL and verify the view")
    parser.add_argument("--start-at", type=int, default=1, help="First setup statement to run, numbered from 1")
    args = parser.parse_args()
    sqls = statements()
    if not 1 <= args.start_at <= len(sqls):
        parser.error(f"--start-at must be between 1 and {len(sqls)}")
    if not args.apply:
        print("DRY RUN: no requests will be sent. Use --apply for administrator execution.")
        for number, sql in enumerate(sqls, 1):
            if number >= args.start_at:
                print(f"\n-- Statement {number}\n{sql};")
        return 0
    key = os.environ.get("ZETARIS_API_KEY", "").strip()
    org = os.environ.get("ZETARIS_ORG_ID", "").strip()
    if not key or not org:
        print("Setup requires ZETARIS_API_KEY and ZETARIS_ORG_ID.", file=sys.stderr)
        return 1
    url = os.environ.get("ZETARIS_REST_URL", "http://localhost:8888/api/v1.0").rstrip("/")
    label = "setup"
    try:
        with httpx.Client(timeout=60.0) as client:
            for number, sql in enumerate(sqls, 1):
                if number < args.start_at:
                    continue
                label = f"statement {number}"
                print(f"Applying {label}:\n{sql};", flush=True)
                execute(client, url, key, org, sql)
            for sql in VERIFICATION:
                label = "verification"
                print(sql, flush=True)
                payload = execute(client, url, key, org, sql)
                if sql == VERIFICATION[0] and payload.get("data") not in ([[1169]], [["1169"]]):
                    raise RuntimeError("Expected exactly 1169 PoE rows; stopping")
    except httpx.RequestError:
        print(f"Stopped at {label}: connection or timeout error. Earlier DDL may have succeeded.", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"Stopped at {label}: {str(exc).replace(key, '[REDACTED]')}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
