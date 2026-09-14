"""Leçons HITL Formalités : Proposer vs Gold humain.

Le lot Proposer écrit ``review_suggest`` (proposition).
Le clic Gold écrit ``review_lessons`` (vérité humaine + écarts).
Le prochain lot relit ces leçons (few-shot + score de chemin).
Le rapport de review affiche « Proposer s'est trompé ici ».
N'écrit jamais ``poe_ports`` / live.
"""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse, unquote

from app.services.review_choices import (
    dropped_official_urls,
    kept_official_urls,
)

LESSON_FEWSHOT = 5
_SKIP_TOKENS = frozenset({
    "html", "htm", "php", "asp", "aspx", "cms", "index", "en", "fr", "es",
    "www", "http", "https", "pdf", "doc", "docx", "page", "pages", "file",
    "files", "public", "upload", "uploads", "content", "node", "sites",
    "default", "home", "accueil", "index.php", "wp-content", "uploads",
})


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sid(value) -> str:
    return "" if value is None else str(value)


def proposal_key(entity_id: str) -> str:
    return f"eez:{_sid(entity_id)}"


def lesson_key(entity_id: str) -> str:
    return f"eez:{_sid(entity_id)}"


def path_tokens(url: str | None) -> list[str]:
    raw = (url or "").strip()
    if not raw:
        return []
    try:
        path = unquote(urlparse(raw).path or "").lower()
    except Exception:
        return []
    parts = []
    for chunk in path.replace(".", "/").replace("-", "/").replace("_", "/").split("/"):
        tok = chunk.strip()
        if len(tok) < 4 or tok in _SKIP_TOKENS or tok.isdigit():
            continue
        if tok not in parts:
            parts.append(tok)
    return parts[:8]


def compare_verdicts(human_keep: list[str], human_drop: list[str],
                     prop_keep: list[str], prop_drop: list[str]) -> dict:
    """Écarts keep/drop. ``omit`` = le juge n'a pas tranché cette URL."""
    human: dict[str, str] = {}
    for url in human_keep or []:
        if url:
            human[url] = "keep"
    for url in human_drop or []:
        if url and url not in human:
            human[url] = "drop"
    prop: dict[str, str] = {}
    for url in prop_keep or []:
        if url:
            prop[url] = "keep"
    for url in prop_drop or []:
        if url and url not in prop:
            prop[url] = "drop"
    errors, agreed = [], []
    for url in sorted(set(human) | set(prop)):
        h, p = human.get(url), prop.get(url)
        if h and p and h == p:
            agreed.append(url)
            continue
        if h == "keep" and p != "keep":
            errors.append({
                "url": url, "proposer": p or "omit", "human": "keep",
            })
        elif h == "drop" and p == "keep":
            errors.append({
                "url": url, "proposer": "keep", "human": "drop",
            })
    return {
        "errors": errors,
        "agreed": agreed,
        "error_count": len(errors),
        "agreed_count": len(agreed),
    }


def had_real_proposal(proposal: dict | None) -> bool:
    if not proposal:
        return False
    engine = str(proposal.get("engine") or "").strip()
    if engine in ("", "none"):
        return False
    return bool(proposal.get("keep") or proposal.get("drop"))


async def save_proposal(db, entity_id: str, picked: dict,
                        fiche: dict | None = None) -> dict:
    eid = _sid(entity_id)
    fiche = fiche or {}
    doc = {
        "_id": proposal_key(eid),
        "kind": "eez",
        "entity_id": eid,
        "keep": list(picked.get("keep") or []),
        "drop": list(picked.get("drop") or []),
        "local_keep": list(picked.get("local_keep") or []),
        "engine": picked.get("engine") or "local",
        "list_kind": picked.get("list_kind") or "none",
        "comment": str(picked.get("comment") or "")[:1200],
        "label": (fiche.get("label") or fiche.get("name") or eid),
        "iso2": fiche.get("iso2") or "",
        "sovereign": fiche.get("sovereign") or "",
        "proposed_at": now_iso(),
    }
    await db.review_suggest.update_one({"_id": doc["_id"]}, {"$set": doc}, upsert=True)
    return doc


async def get_proposal(db, entity_id: str) -> dict | None:
    try:
        return await db.review_suggest.find_one({"_id": proposal_key(entity_id)})
    except Exception:
        return None


async def record_gold_lesson(db, fiche: dict, choices: dict, comment: str = "") -> dict:
    """Vérité Gold + écart vs dernière proposition. Pas de Gold silencieux."""
    fiche = fiche or {}
    eid = _sid(fiche.get("mrgid") or fiche.get("id") or "")
    human_keep = kept_official_urls(fiche, choices, comment)
    human_drop = dropped_official_urls(fiche, choices)
    proposal = await get_proposal(db, eid)
    prop_keep = list((proposal or {}).get("keep") or [])
    prop_drop = list((proposal or {}).get("drop") or [])
    cmp = compare_verdicts(human_keep, human_drop, prop_keep, prop_drop)
    if not had_real_proposal(proposal):
        cmp = {
            "errors": [],
            "agreed": [],
            "error_count": 0,
            "agreed_count": 0,
        }
    doc = {
        "_id": lesson_key(eid),
        "kind": "eez",
        "entity_id": eid,
        "label": fiche.get("label") or fiche.get("name") or eid,
        "iso2": fiche.get("iso2") or "",
        "sovereign": fiche.get("sovereign") or "",
        "human_keep": human_keep,
        "human_drop": human_drop,
        "human_comment": (comment or "")[:1200],
        "proposer_keep": prop_keep,
        "proposer_drop": prop_drop,
        "local_keep": list((proposal or {}).get("local_keep") or []),
        "engine": (proposal or {}).get("engine") or "none",
        "proposer_comment": ((proposal or {}).get("comment") or "")[:1200],
        "errors": cmp["errors"],
        "agreed": cmp["agreed"],
        "error_count": cmp["error_count"],
        "agreed_count": cmp["agreed_count"],
        "had_proposal": had_real_proposal(proposal),
        "golded_at": now_iso(),
    }
    await db.review_lessons.update_one({"_id": doc["_id"]}, {"$set": doc}, upsert=True)
    return doc


async def load_lessons(db) -> list[dict]:
    try:
        docs = await db.review_lessons.find({"kind": "eez"}).to_list(2000)
    except Exception:
        return []
    return [d for d in (docs or []) if isinstance(d, dict)]


def pick_fewshot(lessons: list[dict], fiche: dict | None = None,
                 exclude_id: str | None = None, n: int = LESSON_FEWSHOT) -> list[dict]:
    fiche = fiche or {}
    eid = _sid(exclude_id or fiche.get("mrgid") or "")
    iso = (fiche.get("iso2") or "").strip().upper()
    sov = (fiche.get("sovereign") or "").strip().casefold()
    ranked = []
    for les in lessons or []:
        if _sid(les.get("entity_id")) == eid:
            continue
        if not (les.get("human_keep") or les.get("human_drop")):
            continue
        score = 0
        if iso and (les.get("iso2") or "").strip().upper() == iso:
            score += 4
        if sov and (les.get("sovereign") or "").strip().casefold() == sov:
            score += 2
        if les.get("error_count"):
            score += 2
        if les.get("had_proposal"):
            score += 1
        score += min(3, len(les.get("human_keep") or []))
        ranked.append((score, _sid(les.get("golded_at")), les))
    ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [row[2] for row in ranked[:n]]


def format_lessons_for_prompt(lessons: list[dict]) -> str:
    if not lessons:
        return "(aucune leçon Gold encore.)"
    blocks = []
    for les in lessons:
        keep = ", ".join(les.get("human_keep") or []) or "—"
        drop = ", ".join(les.get("human_drop") or []) or "—"
        label = les.get("label") or les.get("entity_id")
        iso = les.get("iso2") or ""
        line = f"- {label} ({iso}) : garder {keep} ; écarter {drop}"
        misses = []
        for err in les.get("errors") or []:
            misses.append(
                f"{err.get('url')} (Proposer={err.get('proposer')}, "
                f"humain={err.get('human')})"
            )
        if misses:
            line += "\n  Écarts : " + " ; ".join(misses)
        blocks.append(line)
    return "\n".join(blocks)


def token_scores_from_lessons(lessons: list[dict]) -> dict[str, float]:
    scores: dict[str, float] = {}
    for les in lessons or []:
        for url in les.get("human_keep") or []:
            for tok in path_tokens(url):
                scores[tok] = scores.get(tok, 0.0) + 0.15
        for url in les.get("human_drop") or []:
            for tok in path_tokens(url):
                scores[tok] = scores.get(tok, 0.0) - 0.2
    return scores


def url_lesson_delta(url: str, token_scores: dict[str, float] | None) -> float:
    if not url or not token_scores:
        return 0.0
    try:
        path = unquote(urlparse(url).path or "").lower()
    except Exception:
        return 0.0
    return sum(w for tok, w in token_scores.items() if tok in path)


def code_hints_from_lessons(lessons: list[dict]) -> list[dict]:
    """Jetons de chemin à ajouter au code (list vs junk)."""
    keep_n: dict[str, int] = {}
    drop_n: dict[str, int] = {}
    for les in lessons or []:
        seen_k, seen_d = set(), set()
        for url in les.get("human_keep") or []:
            for tok in path_tokens(url):
                if tok not in seen_k:
                    keep_n[tok] = keep_n.get(tok, 0) + 1
                    seen_k.add(tok)
        for url in les.get("human_drop") or []:
            for tok in path_tokens(url):
                if tok not in seen_d:
                    drop_n[tok] = drop_n.get(tok, 0) + 1
                    seen_d.add(tok)
    try:
        from app.services.poe_pipeline import _JUNK_PATH_TOKENS, _LIST_PATH_TOKENS
        listed = set(_LIST_PATH_TOKENS)
        junked = set(_JUNK_PATH_TOKENS)
    except Exception:
        listed, junked = set(), set()
    hints = []
    for tok, n in sorted(drop_n.items(), key=lambda x: -x[1]):
        if n < 2 or tok in junked or keep_n.get(tok, 0) >= n:
            continue
        hints.append({
            "token": tok,
            "human": "drop",
            "n": n,
            "target": "_JUNK_PATH_TOKENS",
            "hint": f"jeton `{tok}` écarté {n}× par le réviseur — candidat _JUNK_PATH_TOKENS",
        })
    for tok, n in sorted(keep_n.items(), key=lambda x: -x[1]):
        if n < 2 or tok in listed or drop_n.get(tok, 0) >= n:
            continue
        hints.append({
            "token": tok,
            "human": "keep",
            "n": n,
            "target": "_LIST_PATH_TOKENS",
            "hint": f"jeton `{tok}` gardé {n}× par le réviseur — candidat _LIST_PATH_TOKENS",
        })
    return hints[:20]


def report_rows_from_lessons(lessons: list[dict], titles: dict[str, str] | None = None) -> dict:
    errors, agreed = [], []
    titles = titles or {}
    for les in lessons or []:
        if not les.get("had_proposal"):
            continue
        eid = _sid(les.get("entity_id"))
        base = {
            "kind": "eez",
            "id": eid,
            "title": titles.get(eid) or les.get("label") or eid,
        }
        for err in les.get("errors") or []:
            errors.append({**base, **err})
        for url in les.get("agreed") or []:
            agreed.append({**base, "url": url})
    return {
        "proposer_errors": errors,
        "proposer_agreed": agreed,
        "proposer_code_hints": code_hints_from_lessons(lessons),
        "proposer_error_count": len(errors),
        "proposer_agreed_count": len(agreed),
    }


async def ensure_lesson_indexes(db) -> None:
    try:
        await db.review_suggest.create_index("kind")
        await db.review_suggest.create_index("entity_id")
        await db.review_lessons.create_index("kind")
        await db.review_lessons.create_index("entity_id")
        await db.review_lessons.create_index("iso2")
    except Exception:
        pass
