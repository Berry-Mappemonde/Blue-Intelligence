#!/usr/bin/env python3
"""Classifie un mail selon la taxonomie Berry-Mappemonde.

Ce script ne parle pas à Gmail : il applique `regles.json` à un expéditeur /
sujet / extrait. L'agent Cursor quotidien s'en sert comme source de vérité,
puis pose les libellés via le MCP Gmail (`label_thread` / `unlabel_thread`).

Usage :
  python3 scripts/gmail/classer.py --from 'amada@langchain.dev' \\
      --subject 'Re: Your LangSmith Credits'
  python3 scripts/gmail/classer.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

RULES_PATH = Path(__file__).resolve().parent / "regles.json"


@dataclass(frozen=True)
class Decision:
    rule_id: str
    labels: list[str]
    label_ids: list[str]
    archive: bool
    important: bool
    reason: str
    unmatched: bool = False
    from_self: bool = False


def load_rules(path: Path | None = None) -> dict:
    return json.loads((path or RULES_PATH).read_text(encoding="utf-8"))


def _norm(value: str | None) -> str:
    return (value or "").casefold()


def _contains_any(haystack: str, needles: list[str] | None) -> bool:
    if not needles:
        return False
    return any(_norm(n) in haystack for n in needles)


def _contains_all(haystack: str, needles: list[str] | None) -> bool:
    if not needles:
        return True
    return all(_norm(n) in haystack for n in needles)


def rule_matches(rule: dict, from_addr: str, subject: str, snippet: str) -> bool:
    from_l = _norm(from_addr)
    subj_l = _norm(subject)
    snip_l = _norm(snippet)

    if "from_contains" in rule and not _contains_any(from_l, rule["from_contains"]):
        return False
    if _contains_any(from_l, rule.get("from_not_contains")):
        return False
    if "subject_contains_any" in rule and not _contains_any(
        subj_l, rule["subject_contains_any"]
    ):
        return False
    if not _contains_all(subj_l, rule.get("subject_contains_all")):
        return False
    if _contains_any(subj_l, rule.get("subject_not_contains")):
        return False
    if "snippet_contains_any" in rule and not _contains_any(
        snip_l, rule["snippet_contains_any"]
    ):
        return False
    return True


def resolve_label_ids(rules: dict, names: list[str]) -> list[str]:
    table = rules["labels"]
    ids: list[str] = []
    seen: set[str] = set()
    for name in names:
        label_id = table[name]
        if label_id not in seen:
            ids.append(label_id)
            seen.add(label_id)
    return ids


def is_self(from_addr: str, rules: dict | None = None) -> bool:
    data = rules or {}
    from_l = _norm(from_addr)
    extras = tuple(data.get("aliases") or ())
    if any(_norm(frag) and _norm(frag) in from_l for frag in extras):
        return True
    domain = _norm(data.get("self_domain") or "")
    if not domain or "@" not in from_l:
        return False
    local, _, host = from_l.partition("@")
    if host != domain:
        return False
    excluded = {_norm(x) for x in data.get("team_local_parts", [])}
    return local not in excluded


def classify(
    from_addr: str,
    subject: str,
    snippet: str = "",
    rules: dict | None = None,
) -> Decision:
    data = rules or load_rules()
    if is_self(from_addr, data):
        return Decision(
            rule_id="from-self",
            labels=[],
            label_ids=[],
            archive=False,
            important=False,
            reason="Mail envoyé par Clément — ne pas alerter, classer selon le dernier message entrant du fil",
            from_self=True,
        )

    for rule in data["rules"]:
        if not rule_matches(rule, from_addr, subject, snippet):
            continue
        return Decision(
            rule_id=rule["id"],
            labels=list(rule["labels"]),
            label_ids=resolve_label_ids(data, rule["labels"]),
            archive=bool(rule["archive"]),
            important=bool(rule["important"]),
            reason=rule["reason"],
        )

    return Decision(
        rule_id="unmatched",
        labels=["Pertinence/Info seulement"],
        label_ids=resolve_label_ids(data, ["Pertinence/Info seulement"]),
        archive=False,
        important=False,
        reason="Aucune règle : garder en inbox, lire le fil, puis poser correspondant + thème + pertinence",
        unmatched=True,
    )


def should_alert(decision: Decision) -> bool:
    return bool(decision.important) and not decision.from_self


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="from_addr", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--snippet", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    decision = classify(args.from_addr, args.subject, args.snippet)
    payload = asdict(decision)
    payload["alert"] = should_alert(decision)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"règle     : {decision.rule_id}")
        print(f"libellés  : {', '.join(decision.labels) or '(aucun)'}")
        print(f"ids       : {', '.join(decision.label_ids) or '(aucun)'}")
        print(f"archiver  : {'oui' if decision.archive else 'non'}")
        print(f"important : {'oui' if decision.important else 'non'}")
        print(f"alerte    : {'oui' if should_alert(decision) else 'non'}")
        print(f"pourquoi  : {decision.reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
