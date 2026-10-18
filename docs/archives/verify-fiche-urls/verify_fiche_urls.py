#!/usr/bin/env python3
"""
HTTP verification of source URLs linked from map-point fiches.

Inspired by scripts/audit_tags.py: report-first tooling, stdlib-only network I/O,
runs locally on GeoJSON seeds/exports, on the public API, or against MongoDB.

Usage:
  python3 scripts/verify_fiche_urls.py --geojson seed/projects.geojson seed/ports_of_entry.geojson
  python3 scripts/verify_fiche_urls.py --api https://blueintelligence.online --out docs/audits/urls.md
  python3 scripts/verify_fiche_urls.py --mongo "$MONGO_URL" --db blue_intelligence

Exit code: 0 always (report tool). Use --fail-on broken to gate CI.
"""
from __future__ import annotations

import argparse
import json
import ssl
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from fiche_url_extract import (  # noqa: E402
    FicheUrlRef,
    dedupe_refs,
    extract_from_api,
    extract_from_geojson_file,
    extract_from_poe_zone_fiche,
    normalize_http_url,
)

USER_AGENT = (
    "BlueIntelligence-FicheUrlChecker/1.0 "
    "(+https://blueintelligence.online; link-health audit)"
)
CAPTCHA_HINTS = ("captcha", "cf-challenge", "g-recaptcha", "hcaptcha")


@dataclass
class UrlCheckResult:
    url: str
    status: str
    http_status: int | None
    final_url: str | None
    error: str | None
    elapsed_ms: int


def _ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context()


def _looks_like_captcha(body: bytes) -> bool:
    if not body:
        return False
    sample = body[:8000].lower()
    return any(hint.encode() in sample for hint in CAPTCHA_HINTS)


def _classify_http(code: int) -> str:
    if 200 <= code <= 299:
        return "ok"
    if 300 <= code <= 399:
        return "redirected"
    if code in (401, 403, 407, 429):
        return "soft_fail"
    if 400 <= code <= 499:
        return "broken"
    if code >= 500:
        return "broken"
    return "broken"


def _infer_status_from_error(message: str | None, http_status: int | None) -> str | None:
    if http_status is not None:
        return _classify_http(http_status)
    if not message:
        return None
    low = message.lower()
    if "too many requests" in low or "rate limit" in low:
        return "soft_fail"
    if "forbidden" in low or "unauthorized" in low:
        return "soft_fail"
    if "timeout" in low or "timed out" in low:
        return "timeout"
    return None


def check_one_url(
    url: str,
    *,
    timeout: float,
    retries: int,
    user_agent: str,
) -> UrlCheckResult:
    last_err: str | None = None
    for attempt in range(retries + 1):
        t0 = time.perf_counter()
        try:
            result = _probe_url(url, timeout=timeout, user_agent=user_agent)
            result.elapsed_ms = int((time.perf_counter() - t0) * 1000)
            return result
        except TimeoutError:
            last_err = "timeout"
        except URLError as exc:
            last_err = str(exc.reason if hasattr(exc, "reason") else exc)
        except HTTPError as exc:
            status = _classify_http(exc.code)
            return UrlCheckResult(
                url=url,
                status=status,
                http_status=exc.code,
                final_url=getattr(exc, "url", None),
                error=str(exc),
                elapsed_ms=int((time.perf_counter() - t0) * 1000),
            )
        except Exception as exc:  # pragma: no cover - defensive
            last_err = str(exc)
        if attempt < retries:
            time.sleep(0.6 * (attempt + 1))
    return UrlCheckResult(
        url=url,
        status=_infer_status_from_error(last_err, None) or (
            "timeout" if last_err == "timeout" else "broken"
        ),
        http_status=None,
        final_url=None,
        error=last_err,
        elapsed_ms=0,
    )


def _probe_url(url: str, *, timeout: float, user_agent: str) -> UrlCheckResult:
    headers = {
        "User-Agent": user_agent,
        "Accept": "*/*",
    }
    ctx = _ssl_context()
    for method in ("HEAD", "GET"):
        req = Request(url, method=method, headers=headers)
        try:
            with urlopen(req, timeout=timeout, context=ctx) as resp:
                code = resp.getcode()
                final = resp.geturl()
                if method == "GET":
                    chunk = resp.read(8192)
                    if _looks_like_captcha(chunk):
                        return UrlCheckResult(
                            url, "soft_fail", code, final, "captcha_wall", 0)
                status = _classify_http(code)
                if status == "redirected" and final and final.rstrip("/") != url.rstrip("/"):
                    status = "redirected"
                elif status == "redirected":
                    status = "ok"
                return UrlCheckResult(url, status, code, final, None, 0)
        except HTTPError as exc:
            if method == "HEAD" and exc.code in (405, 501):
                continue
            raise
    raise URLError("HEAD and GET both failed")


def check_urls_unique(
    urls: Iterable[str],
    *,
    concurrency: int,
    timeout: float,
    retries: int,
    user_agent: str,
    max_urls: int | None,
) -> dict[str, UrlCheckResult]:
    ordered = []
    seen: set[str] = set()
    for raw in urls:
        u = normalize_http_url(raw)
        if not u or u in seen:
            continue
        seen.add(u)
        ordered.append(u)
        if max_urls and len(ordered) >= max_urls:
            break
    results: dict[str, UrlCheckResult] = {}
    if not ordered:
        return results
    workers = max(1, min(concurrency, len(ordered)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {
            pool.submit(
                check_one_url, u, timeout=timeout, retries=retries, user_agent=user_agent
            ): u
            for u in ordered
        }
        for fut in as_completed(futs):
            res = fut.result()
            results[res.url] = res
    return results


def extract_mongo(mongo_url: str, db_name: str) -> list[FicheUrlRef]:
    from pymongo import MongoClient

    from app.services.poe_zone_fiche import assemble_zone_fiche  # type: ignore
    from fiche_url_extract import extract_from_geojson

    client = MongoClient(mongo_url, serverSelectionTimeoutMS=8000)
    db = client[db_name]
    refs: list[FicheUrlRef] = []

    for doc in db.projects.find({}, {"url": 1, "title": 1, "name": 1}):
        label = doc.get("title") or doc.get("name") or str(doc.get("_id"))
        refs.extend(
            extract_from_geojson(
                Path("projects.geojson"),
                {
                    "type": "FeatureCollection",
                    "metadata": {"dataset": "projects"},
                    "features": [{
                        "properties": {
                            "id": doc.get("_id"),
                            "title": label,
                            "url": doc.get("url"),
                        },
                    }],
                },
            )
        )

    for coll_name, dataset in (
        ("marinas", "marinas"),
        ("capitaineries", "capitaineries"),
        ("amp_sites", "amp"),
        ("science_items", "science"),
    ):
        coll = getattr(db, coll_name, None)
        if coll is None:
            continue
        for doc in coll.find({}):
            props = {
                "id": doc.get("_id") or doc.get("site_id") or doc.get("osm_id"),
                "name": doc.get("name"),
                "website": doc.get("website"),
                "maps_place_url": doc.get("maps_place_url"),
                "manager_url": doc.get("manager_url"),
                "visit_url": doc.get("visit_url"),
                "url": doc.get("url"),
            }
            refs.extend(
                extract_from_geojson(
                    Path(f"{dataset}.geojson"),
                    {
                        "type": "FeatureCollection",
                        "metadata": {"dataset": dataset},
                        "features": [{"properties": props}],
                    },
                )
            )

    for doc in db.poe_ports.find({}, {"source_urls": 1, "name": 1, "id": 1}):
        refs.extend(
            extract_from_geojson(
                Path("ports_of_entry.geojson"),
                {
                    "type": "FeatureCollection",
                    "metadata": {"dataset": "formalities_ports"},
                    "features": [{
                        "properties": {
                            "id": doc.get("id") or doc.get("_id"),
                            "name": doc.get("name"),
                            "source_urls": doc.get("source_urls") or [],
                        },
                    }],
                },
            )
        )

    for zone in db.eez_zones.find({}, {"geometry": 0}):
        mrgid = zone.get("mrgid")
        if not mrgid:
            continue
        ports = list(db.poe_ports.find({"mrgid": int(mrgid)}))
        fiche = assemble_zone_fiche(zone, ports)
        refs.extend(extract_from_poe_zone_fiche(fiche))

    return dedupe_refs(refs)


def render_markdown(
    refs: list[FicheUrlRef],
    by_url: dict[str, UrlCheckResult],
    *,
    generated_at: str,
    source_note: str,
) -> str:
    status_counts: Counter = Counter()
    for res in by_url.values():
        status_counts[res.status] += 1

    lines = [
        "# Audit des URLs de fiches",
        "",
        f"Généré le **{generated_at}** (UTC).",
        "",
        source_note,
        "",
        f"**{len(refs)}** références de fiches · **{len(by_url)}** URLs uniques vérifiées.",
        "",
        "## Synthèse par statut (URLs uniques)",
        "",
        "| statut | count |",
        "|---|---:|",
    ]
    for status in ("ok", "redirected", "broken", "timeout", "soft_fail"):
        if status_counts.get(status):
            lines.append(f"| `{status}` | {status_counts[status]} |")

    problem_urls = [
        u for u, r in by_url.items() if r.status in ("broken", "timeout")
    ]
    if problem_urls:
        refs_by_url: dict[str, list[FicheUrlRef]] = defaultdict(list)
        for ref in refs:
            if ref.url in by_url and by_url[ref.url].status in ("broken", "timeout", "soft_fail"):
                refs_by_url[ref.url].append(ref)
        lines.extend(["", "## Liens cassés ou expirés (échantillon)", ""])
        shown = 0
        for url in sorted(problem_urls):
            res = by_url[url]
            lines.append(f"### `{url}`")
            lines.append("")
            lines.append(
                f"- statut: **{res.status}**"
                + (f" · HTTP {res.http_status}" if res.http_status else "")
                + (f" · {res.error}" if res.error else "")
            )
            for ref in refs_by_url[url][:8]:
                lines.append(
                    f"- `{ref.dataset}` · **{ref.entity_label}** (`{ref.entity_id}`) "
                    f"— champ `{ref.field}`"
                )
            if len(refs_by_url[url]) > 8:
                lines.append(f"- … {len(refs_by_url[url]) - 8} fiche(s) de plus")
            lines.append("")
            shown += 1
            if shown >= 80:
                rest = len(problem_urls) - shown
                if rest > 0:
                    lines.append(f"_… et {rest} URL(s) problématique(s) non listée(s)._")
                break

    soft = [u for u, r in by_url.items() if r.status == "soft_fail"]
    if soft:
        lines.extend(["", "## Mur d’auth / rate-limit (soft_fail)", ""])
        for url in sorted(soft)[:40]:
            lines.append(f"- `{url}` — {by_url[url].error or by_url[url].http_status}")
        if len(soft) > 40:
            lines.append(f"- … {len(soft) - 40} de plus")

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify fiche source URLs (HTTP).")
    src = parser.add_mutually_exclusive_group()
    src.add_argument("--geojson", nargs="+", help="GeoJSON export(s) or seed file(s)")
    src.add_argument("--api", metavar="BASE_URL", help="Fetch public /api/export/* (+ PoE zone fiches)")
    src.add_argument("--mongo", metavar="MONGO_URL", help="Read live MongoDB (needs pymongo + backend)")
    parser.add_argument("--db", default="blue_intelligence", help="Mongo database name")
    parser.add_argument("--out", type=Path, help="Write Markdown report")
    parser.add_argument("--json-out", type=Path, help="Write machine-readable JSON summary")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--max-urls", type=int, default=0, help="Cap unique URLs checked (0 = all)")
    parser.add_argument("--no-zone-fiches", action="store_true", help="With --api, skip /poe/zones/{mrgid}")
    parser.add_argument("--fail-on", choices=("broken", "broken_or_timeout"), help="Exit 1 if any match")
    parser.add_argument("--dry-run", action="store_true", help="Extract only, no HTTP")
    args = parser.parse_args(argv)

    if not args.geojson and not args.api and not args.mongo:
        parser.error("one of --geojson, --api, or --mongo is required")

    refs: list[FicheUrlRef] = []
    source_note = ""
    if args.geojson:
        for raw in args.geojson:
            path = Path(raw)
            refs.extend(extract_from_geojson_file(path))
        source_note = "Sources : " + ", ".join(f"`{p}`" for p in args.geojson)
    elif args.api:
        refs = extract_from_api(
            args.api,
            user_agent=USER_AGENT,
            include_zone_fiches=not args.no_zone_fiches,
        )
        source_note = f"Sources : API `{args.api}` (exports publics + fiches ZEE visibles)."
    else:
        sys.path.insert(0, str(REPO_ROOT / "backend"))
        refs = extract_mongo(args.mongo, args.db)
        source_note = f"Sources : Mongo `{args.db}`."

    refs = dedupe_refs(refs)
    unique_urls = sorted({r.url for r in refs})
    max_urls = args.max_urls or None

    if args.dry_run:
        print(f"Extracted {len(refs)} refs, {len(unique_urls)} unique URLs.", file=sys.stderr)
        if args.json_out:
            args.json_out.write_text(
                json.dumps({"refs": [asdict(r) for r in refs], "unique_url_count": len(unique_urls)}, indent=2),
                encoding="utf-8",
            )
        return 0

    by_url = check_urls_unique(
        unique_urls,
        concurrency=args.concurrency,
        timeout=args.timeout,
        retries=args.retries,
        user_agent=USER_AGENT,
        max_urls=max_urls,
    )

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    md = render_markdown(refs, by_url, generated_at=generated_at, source_note=source_note)
    print(md)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(md, encoding="utf-8")
    if args.json_out:
        summary = {
            "generated_at": generated_at,
            "refs": len(refs),
            "unique_urls_checked": len(by_url),
            "status_counts": dict(Counter(r.status for r in by_url.values())),
            "results": {u: asdict(r) for u, r in sorted(by_url.items())},
        }
        args.json_out.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if args.fail_on:
        bad = {"broken", "timeout"} if args.fail_on == "broken_or_timeout" else {"broken"}
        if any(r.status in bad for r in by_url.values()):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
