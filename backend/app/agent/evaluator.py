"""LangGraph checking node: score each PoE and decide pass / flag / retry."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from app.services.poe_confidence import score_port

AGENT_NAME = "EvaluatorAgent"
RETRY_LIMIT = 2


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    """Checking node. Annotates ports, fills needs_retry, appends one trace JSON per port."""
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
        out_ports.append(port)
        if verdict == "retry":
            needs_retry.append(port)
        trace.append(json.dumps({
            "timestamp": _now_iso(),
            "agent_name": AGENT_NAME,
            "action": "evaluate_port",
            "port_name": port.get("name"),
            "verdict": verdict,
            "reasons": reasons,
        }, ensure_ascii=False))

    out = dict(state)
    out["ports"] = out_ports
    out["retry_count"] = retry_count
    out["needs_retry"] = needs_retry
    out["trace"] = trace
    return out


def route_after_evaluation(state: dict) -> str:
    needs_retry = state.get("needs_retry") or []
    retry_count = int(state.get("retry_count") or 0)
    if needs_retry and retry_count < RETRY_LIMIT:
        return "retry"
    return "done"
