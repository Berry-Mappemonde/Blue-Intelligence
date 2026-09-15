"""Sous-processus de parse HTML (trafilatura + Readability isolés).

Lancé via ``python -m app.core.html_worker IN.html OUT.json``.
Un crash natif lxml (``free(): invalid pointer``, SIGABRT) tue uniquement
ce process, pas l'API. Le parent n'importe pas trafilatura pour les gros
miroirs Jina / gazettes.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def parse_html_pair(html: str) -> dict:
    """Même couple N1/N2 que ``extract.parse_html_n1`` / ``parse_html_n2``."""
    n1 = ""
    try:
        import trafilatura
        n1 = (trafilatura.extract(html) or "").strip()
    except Exception:
        n1 = ""

    n2_text, title = "", ""
    try:
        from bs4 import BeautifulSoup
        from readability import Document as ReadabilityDoc

        doc = ReadabilityDoc(html)
        title = (doc.short_title() or "").strip()
        soup = BeautifulSoup(doc.summary(), "html.parser")
        text = re.sub(r"\s+", " ", soup.get_text(" ")).strip()
        if len(text) < 200:
            full = BeautifulSoup(html, "html.parser")
            text = re.sub(r"\s+", " ", full.get_text(" ")).strip()[:12000]
        n2_text = text
    except Exception:
        pass
    return {"n1": n1, "n2_text": n2_text, "title": title}


def extract_html_file(inp: str, out: str) -> None:
    html = Path(inp).read_text(encoding="utf-8", errors="replace")
    Path(out).write_text(
        json.dumps(parse_html_pair(html), ensure_ascii=False),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2:
        print("usage: python -m app.core.html_worker IN.html OUT.json",
              file=sys.stderr)
        return 2
    inp, out = argv[0], argv[1]
    try:
        extract_html_file(inp, out)
    except Exception as e:
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
