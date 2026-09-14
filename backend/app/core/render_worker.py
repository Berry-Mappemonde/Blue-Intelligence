"""Sous-processus Chromium (Playwright isolé).

Lancé via ``python -m app.core.render_worker URL OUT.html [timeout_s] [settle_ms]``.
Un crash natif (munmap_chunk, SIGABRT) tue uniquement ce process — le Complet
continue. La RAM Chromium est rendue à la sortie, comme ``pdf_worker``.
"""
from __future__ import annotations

import sys
from pathlib import Path

UA_BROWSER = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

CHROMIUM_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-extensions",
    "--renderer-process-limit=1",
    "--js-flags=--max-old-space-size=256",
]


def render_url_to_file(url: str, out: str, timeout_s: int = 45,
                      settle_ms: int = 2500) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=CHROMIUM_ARGS)
        try:
            context = browser.new_context(
                user_agent=UA_BROWSER, viewport={"width": 1366, "height": 900},
                locale="en-US")
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_s * 1000)
            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                page.wait_for_timeout(settle_ms)
            Path(out).write_text(page.content() or "", encoding="utf-8")
        finally:
            browser.close()


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2:
        print("usage: python -m app.core.render_worker URL OUT.html "
              "[timeout_s] [settle_ms]", file=sys.stderr)
        return 2
    url, out = argv[0], argv[1]
    timeout_s = int(argv[2]) if len(argv) > 2 else 45
    settle_ms = int(argv[3]) if len(argv) > 3 else 2500
    try:
        render_url_to_file(url, out, timeout_s, settle_ms)
    except ImportError as e:
        print(f"playwright missing: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
