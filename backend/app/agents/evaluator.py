"""LangGraph checking node: score each PoE and decide pass / flag / retry.

After evaluate(), route "retry" through prepare_retry() before the retry step
and re-evaluation. Route "done" through finalise() before returning the ports.
The graph must preserve the full ports list when enriching retry candidates.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.services.poe_confidence import score_port

AGENT_NAME = "EvaluatorAgent"
RETRY_LIMIT = 2
DEFAULT_TRACE_LOG_DIR = Path(__file__).resolve().parents[3] / "logs"

_REASONS_EN = {
    "source d'État": "government source",
    "synthèse web sans page": "web synthesis without a source page",
    "source nationale non whitelistée": "national source not on the allowlist",
    "source indéterminée": "unknown source",
    "Claude et OpenRouter d'accord": "Claude and OpenRouter agree",
    "catalogue + LLM + NER": "catalogue + LLM + NER",
    "catalogue officiel": "official catalogue",
    "LLM ∩ NER ∩ Claude": "LLM, NER and Claude agree",
    "LLM et NER d'accord": "LLM and NER agree",
    "deux lecteurs LLM": "two LLM readers",
    "NER seul": "NER only",
    "tournure légale": "legal wording",
    "un seul extracteur": "single extractor",
    "non géocodé": "not geocoded",
    "hors ZEE et hors bord terrestre": "outside the EEZ and its land boundary",
    "dans la ZEE, géocodeurs d'accord": "inside the EEZ, geocoders agree",
    "bord terrestre de la ZEE, géocodeurs d'accord": "EEZ land boundary, geocoders agree",
    "port fluvial du pays, géocodeurs d'accord": "domestic river port, geocoders agree",
    "dans la ZEE": "inside the EEZ",
    "bord terrestre de la ZEE": "EEZ land boundary",
    "port fluvial hors ZEE (exception)": "river port outside the EEZ (exception)",
    "point accepté dans la zone": "position accepted within the zone",
    "position incertaine": "uncertain position",
    "connu du listing communautaire (PoE)": "known in the community listing (PoE)",
    "listing : autre port (pas un PoE)": "listing: other port (not a PoE)",
    "OSM : infrastructure portuaire / douane": "OSM: port infrastructure / customs",
    "OSM : correspondance faible": "OSM: weak match",
    "OSM : aucun tag proche": "OSM: no nearby tags",
    "vu dans plusieurs runs": "seen in multiple runs",
    "WPI commerce (contre-liste, pas une preuve PoE)":
        "WPI commercial port (cross-check list, not proof of PoE status)",
    "source non réelle (URLs vides ou synthèse seule)":
        "no direct source (empty URLs or synthesis only)",
    "carte incomplète (lat/lon manquants ou géocodeurs pas d'accord)":
        "incomplete map (missing lat/lon or geocoders disagree)",
    "non confirmé après le nombre maximal de tentatives": "unconfirmed after max retries",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reasons_en(reasons: list[str]) -> list[str]:
    return [_REASONS_EN.get(reason, reason) for reason in reasons]


def _with_run_id(state: dict) -> dict:
    """Copy state, generating a UUID if absent; require a filename-safe run ID."""
    out = dict(state)
    run_id = out.get("run_id")
    if run_id is None:
        run_id = str(uuid4())
    if not isinstance(run_id, str) or re.fullmatch(r"[A-Za-z0-9_-]+", run_id) is None:
        raise ValueError("run_id must contain only letters, digits, underscores or hyphens")
    out["run_id"] = run_id
    return out


def _trace_port(trace: list[dict], port: dict, retry_count: int, action: str,
                *, run_id: str, handoff: str | None = None) -> None:
    """Record one event in state, stdout and JSONL; propagate logging failures."""
    entry = {
        "timestamp": _now_iso(),
        "agent_name": AGENT_NAME,
        "run_id": run_id,
        "action": action,
        "port_name": port.get("name"),
        "input_summary": {"port_name": port.get("name"), "retry_count": retry_count},
        "verdict": port.get("verdict"),
        "reasons": list(port.get("reasons_en") or _reasons_en(port.get("reasons") or [])),
    }
    if handoff is not None:
        entry["handoff"] = {"from": AGENT_NAME, "to": handoff}
    line = json.dumps(entry, ensure_ascii=False)
    log_path = Path(os.environ.get("TRACE_LOG_PATH") or
                    DEFAULT_TRACE_LOG_DIR / f"trace-{run_id}.jsonl")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(line + "\n")
    print(line, flush=True)
    trace.append(entry)


def _has_real_source(port: dict) -> bool:
    urls = [u for u in (port.get("source_urls") or []) if u]
    return bool(urls) and not bool(port.get("from_synthesis"))


def _map_ok(port: dict) -> bool:
    has_geo = port.get("lat") is not None and port.get("lon") is not None
    return has_geo and port.get("geocode_agree") is True


def _verdict(confidence: int, checks_ok: bool) -> str:
    if confidence < 40:
        return "retry"
    if confidence > 60 and checks_ok:
        return "pass"
    return "flag"


def evaluate(state: dict) -> dict:
    """Annotate ports, fill needs_retry and emit one trace dict per port."""
    out = _with_run_id(state)
    ports_in = list(state.get("ports") or [])
    retry_count = int(state.get("retry_count") or 0)
    trace = list(state.get("trace") or [])
    out_ports: list[dict] = []
    needs_retry: list[dict] = []

    for raw in ports_in:
        port = dict(raw)
        scored = score_port(port)
        confidence = int(scored["confidence"])
        source_ok = _has_real_source(port)
        map_ok = _map_ok(port)
        checks_ok = source_ok and map_ok
        reasons = list(scored.get("reasons") or [])
        if not source_ok:
            reasons.append("source non réelle (URLs vides ou synthèse seule)")
        if not map_ok:
            reasons.append("carte incomplète (lat/lon manquants ou géocodeurs pas d'accord)")
        verdict = _verdict(confidence, checks_ok)
        port["confidence"] = confidence
        port["confidence_parts"] = scored.get("parts")
        port["verdict"] = verdict
        port["reasons"] = reasons
        port["reasons_en"] = _reasons_en(reasons)
        out_ports.append(port)
        if verdict == "retry":
            needs_retry.append(port)
        _trace_port(trace, port, retry_count, "evaluate_port", run_id=out["run_id"])

    out["ports"] = out_ports
    out["retry_count"] = retry_count
    out["needs_retry"] = needs_retry
    out["trace"] = trace
    return out


def route_after_evaluation(state: dict) -> str:
    """Route 'retry' to prepare_retry(), or 'done' to finalise()."""
    needs_retry = state.get("needs_retry") or []
    retry_count = int(state.get("retry_count") or 0)
    if needs_retry and retry_count < RETRY_LIMIT:
        return "retry"
    return "done"


def prepare_retry(state: dict) -> dict:
    """On the 'retry' route, increment the count before handing off to that step."""
    out = _with_run_id(state)
    out["retry_count"] = int(state.get("retry_count") or 0) + 1
    trace = list(state.get("trace") or [])
    for port in state.get("needs_retry") or []:
        _trace_port(trace, port, out["retry_count"], "prepare_retry",
                    run_id=out["run_id"], handoff="retry")
    out["trace"] = trace
    return out


def finalise(state: dict) -> dict:
    """Call when route_after_evaluation() returns 'done'; retain every port.

    Any remaining retry verdict becomes flag, with the English reason
    'unconfirmed after max retries' alongside its French equivalent.
    """
    out = _with_run_id(state)
    retry_count = int(state.get("retry_count") or 0)
    trace = list(state.get("trace") or [])
    ports = []
    for raw in state.get("ports") or []:
        port = dict(raw)
        if port.get("verdict") == "retry":
            port["verdict"] = "flag"
            port["reasons"] = list(port.get("reasons") or []) + [
                "non confirmé après le nombre maximal de tentatives",
            ]
            port["reasons_en"] = _reasons_en(port["reasons"])
            _trace_port(trace, port, retry_count, "finalise_port", run_id=out["run_id"])
        ports.append(port)
    out["ports"] = ports
    out["needs_retry"] = []
    out["trace"] = trace
    return out
