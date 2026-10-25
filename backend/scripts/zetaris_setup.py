"""One-off administrative setup, separate from the read-only application adapter.

Run from backend/: .venv/bin/python scripts/zetaris_setup.py [--part poe|registries|all]
Dry run is the default: it prints the plan and SQL and sends nothing. Only --apply
downloads, stages files and sends SQL. Load ZETARIS_REST_URL, ZETARIS_ORG_ID and
ZETARIS_API_KEY into the environment before applying. The REST URL defaults to
http://localhost:8888/api/v1.0.

Parts:
  poe         zetaris_setup_poe.sql: the Blue Intelligence seed as a REST table + view.
  registries  zetaris_setup_registries.sql: independent registries, UN/LOCODE (UNECE) and the
              World Port Index (NGA Pub 150). --apply downloads both from their publishers,
              keeps the fields used for validation, writes CSVs to backend/data/registries/
              (gitignored), copies them into Zetaris platform storage (docker cp into the
              local driver container by default; --stage none if the folder is already
              reachable by Zetaris) and registers file-store tables + schemastore views.
              --prepare-only stops after writing the CSVs; --fixtures also rewrites the
              committed SAMPLE_MODE subsets in backend/data/sample/zetaris/.

There are no automatic DDL retries or rollback. On failure, inspect the reported
statement and existing objects. --start-at N explicitly skips earlier statements
when an administrator has confirmed that they already succeeded.
The simple splitter separates semicolons outside quotes. BEGIN...END blocks
and $$ dollar-quoting are unsupported and explicitly rejected.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from uuid import uuid4

import httpx

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
from app.adapters import registry_sources as rs  # noqa: E402

SQL_FILE = Path(__file__).with_name("zetaris_setup_poe.sql")
REGISTRY_SQL_FILE = Path(__file__).with_name("zetaris_setup_registries.sql")
VERIFICATION = (
    "SELECT COUNT(*) FROM blue_intel.poe_ports",
    "SELECT name, zone_name, lat, lon FROM blue_intel.poe_ports LIMIT 5",
)
REGISTRY_DIR = BACKEND_DIR / "data" / "registries"  # gitignored
SAMPLE_DIR = BACKEND_DIR / "data" / "sample" / "zetaris"
ZETARIS_REGISTRY_DIR = "/home/zetaris/customer-data/shared/blue_intel"  # platform storage root/subdir
USER_AGENT = "Blue-Intelligence registry setup (+https://blueintelligence.online)"


def statements(sql_file: Path | None = None, values: dict | None = None) -> list[str]:
    """Split on semicolons outside quotes; reject BEGIN blocks and $$ quoting."""
    sql = (sql_file or SQL_FILE).read_text(encoding="utf-8")
    for name, value in (values or {}).items():
        sql = sql.replace("{" + name + "}", value)
    # This is a simple splitter, not a procedural SQL parser. Fail closed for
    # BEGIN...END and dollar-quoted bodies rather than execute partial blocks.
    if "$$" in sql:
        raise ValueError("Setup splitter does not support $$ dollar-quoting")
    tokens = re.findall(r'''--[^\n]*|'(?:\\[\s\S]|''|[^'\\])*'|"(?:\\[\s\S]|""|[^"\\])*"|[A-Za-z_][A-Za-z_0-9]*|[\s\S]''', sql)
    result, current = [], []
    for token in tokens:
        if token.startswith("--"):
            continue
        if token.upper() == "BEGIN":
            raise ValueError("Setup splitter does not support BEGIN...END blocks")
        if token in {"'", '"'}:
            raise ValueError("Setup splitter found an unterminated quoted literal")
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


def _download(url: str, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET", url, headers={"User-Agent": USER_AGENT}, timeout=120.0,
                      follow_redirects=True) as response:
        response.raise_for_status()
        with target.open("wb") as stream:
            for chunk in response.iter_bytes():
                stream.write(chunk)
    return target


def prepare_registries(unlocode_zip: Path | None, wpi_csv: Path | None, fixtures: bool) -> dict:
    """Download (unless local files are given), filter, write CSVs (and fixtures); return counts."""
    raw = REGISTRY_DIR / "raw"
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    unlocode_zip = unlocode_zip or _download(rs.UNLOCODE_URL, raw / "unlocode-latest.zip")
    wpi_csv = wpi_csv or _download(rs.WPI_URL, raw / "UpdatedPub150.csv")
    lines: list[str] = []
    with zipfile.ZipFile(unlocode_zip) as archive:
        for name in sorted(archive.namelist()):
            if re.search(r"/csv/UNLOCODE CodeListPart\d+\.csv$", name):
                lines += archive.read(name).decode("utf-8").splitlines()
    unlocode = rs.unlocode_ports(lines)
    wpi = rs.wpi_ports(wpi_csv.read_text(encoding="utf-8-sig"))
    counts = {
        "unlocode": rs.write_csv(unlocode, rs.UNLOCODE_COLUMNS, REGISTRY_DIR / "unlocode_ports.csv"),
        "wpi": rs.write_csv(wpi, rs.WPI_COLUMNS, REGISTRY_DIR / "wpi_ports.csv"),
    }
    print(f"UN/LOCODE port entries: {counts['unlocode']} "
          f"({sum(r['lat'] is not None for r in unlocode)} with coordinates)")
    print(f"World Port Index ports: {counts['wpi']}")
    if fixtures:
        n_u = rs.write_fixture(unlocode, rs.UNLOCODE_COLUMNS, "unlocode", SAMPLE_DIR / "unlocode_ports.json",
                               f"UN/LOCODE port entries (UNECE, {rs.UNLOCODE_URL}), sample-zone countries")
        n_w = rs.write_fixture(wpi, rs.WPI_COLUMNS, "wpi", SAMPLE_DIR / "wpi_ports.json",
                               "World Port Index, NGA Pub 150 (US public domain), sample-zone countries")
        print(f"Fixtures written: unlocode_ports.json ({n_u} rows), wpi_ports.json ({n_w} rows)")
    return counts


def stage_registries(stage: str, container: str, target_dir: str) -> list[list[str]]:
    """Commands that copy the CSVs into Zetaris platform storage."""
    if stage == "none":
        return []
    files = [REGISTRY_DIR / "unlocode_ports.csv", REGISTRY_DIR / "wpi_ports.csv"]
    return [["docker", "exec", container, "mkdir", "-p", target_dir],
            *[["docker", "cp", str(f), f"{container}:{target_dir}/{f.name}"] for f in files]]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="Download, stage, execute the SQL and verify")
    parser.add_argument("--start-at", type=int, default=1, help="First setup statement to run, numbered from 1")
    parser.add_argument("--part", choices=("poe", "registries", "all"), default="all")
    parser.add_argument("--prepare-only", action="store_true", help="registries: write the CSVs, skip Zetaris")
    parser.add_argument("--fixtures", action="store_true", help="registries: also rewrite the SAMPLE_MODE fixtures")
    parser.add_argument("--unlocode-zip", type=Path, help="local unlocode-latest.zip instead of downloading")
    parser.add_argument("--wpi-csv", type=Path, help="local UpdatedPub150.csv instead of downloading")
    parser.add_argument("--stage", choices=("docker", "none"), default="docker")
    parser.add_argument("--docker-container", default="zetaris-driver-1")
    parser.add_argument("--registry-dir", default=ZETARIS_REGISTRY_DIR,
                        help="registry folder as Zetaris sees it (inside its platform storage)")
    args = parser.parse_args()
    parts = ("poe", "registries") if args.part == "all" else (args.part,)
    try:
        sqls = []
        if "poe" in parts:
            sqls += statements()
        if "registries" in parts:
            sqls += statements(REGISTRY_SQL_FILE, {"registry_dir": args.registry_dir})
    except ValueError as exc:
        parser.error(str(exc))
    if not 1 <= args.start_at <= len(sqls):
        parser.error(f"--start-at must be between 1 and {len(sqls)}")
    staging = stage_registries(args.stage, args.docker_container, args.registry_dir) if "registries" in parts else []

    if not args.apply and not args.prepare_only:
        print("DRY RUN: no downloads, copies or requests. Use --apply for administrator execution.")
        if "registries" in parts:
            print(f"\n-- Download {rs.UNLOCODE_URL}\n-- Download {rs.WPI_URL}")
            print(f"-- Write {REGISTRY_DIR}/unlocode_ports.csv and wpi_ports.csv")
            for command in staging:
                print("-- Run " + " ".join(command))
        for number, sql in enumerate(sqls, 1):
            if number >= args.start_at:
                print(f"\n-- Statement {number}\n{sql};")
        return 0

    counts = {}
    if "registries" in parts:
        try:
            counts = prepare_registries(args.unlocode_zip, args.wpi_csv, args.fixtures)
        except (httpx.HTTPError, OSError, zipfile.BadZipFile) as exc:
            print(f"Registry download/preparation failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1
        if args.prepare_only:
            return 0
    key = os.environ.get("ZETARIS_API_KEY", "").strip()
    org = os.environ.get("ZETARIS_ORG_ID", "").strip()
    if not key or not org:
        print("Setup requires ZETARIS_API_KEY and ZETARIS_ORG_ID.", file=sys.stderr)
        return 1
    url = os.environ.get("ZETARIS_REST_URL", "http://localhost:8888/api/v1.0").rstrip("/")
    for command in staging:
        print("Running " + " ".join(command), flush=True)
        done = subprocess.run(command, capture_output=True, text=True)
        if done.returncode != 0:
            print(f"Staging failed: {done.stderr.strip()[:500]}", file=sys.stderr)
            return 1
    label = "setup"
    try:
        with httpx.Client(timeout=120.0) as client:
            for number, sql in enumerate(sqls, 1):
                if number < args.start_at:
                    continue
                label = f"statement {number}"
                print(f"Applying {label}:\n{sql};", flush=True)
                execute(client, url, key, org, sql)
            if "poe" in parts:
                for sql in VERIFICATION:
                    label = "verification"
                    print(sql, flush=True)
                    payload = execute(client, url, key, org, sql)
                    if sql == VERIFICATION[0] and payload.get("data") not in ([[1169]], [["1169"]]):
                        raise RuntimeError("Expected exactly 1169 PoE rows; stopping")
            for source, view in (("unlocode", "blue_intel.unlocode_ports"), ("wpi", "blue_intel.wpi_ports")):
                if source not in counts:
                    continue
                label = f"{source} verification"
                payload = execute(client, url, key, org, f"SELECT COUNT(*) FROM {view}")
                got = int(payload["data"][0][0])
                print(f"{view}: {got} rows (local CSV: {counts[source]})")
                if got != counts[source]:
                    raise RuntimeError(f"{view} has {got} rows, expected {counts[source]}; stopping")
    except httpx.RequestError:
        print(f"Stopped at {label}: connection or timeout error. Earlier DDL may have succeeded.", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"Stopped at {label}: {str(exc).replace(key, '[REDACTED]')}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
