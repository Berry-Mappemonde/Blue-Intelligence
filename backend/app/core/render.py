"""
render_core — Rendu navigateur local (Playwright + Chromium headless).

``render_html`` (cascade Complet / PoE) lance Chromium dans un *sous-processus*
(``app.core.render_worker``). Un crash natif (munmap_chunk sous MemoryHigh=2G)
tue uniquement l'enfant : le Complet continue, la RAM est rendue.

``render_screenshot`` (vision Review) reste in-process : un appel ponctuel,
pas une rafale de 200 pages.

Dégradation propre : si playwright ou son navigateur n'est pas installé,
render_html retourne None et la cascade continue sans rendu.
Installation : pip install playwright && playwright install chromium
"""
import asyncio
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from app.config import BACKEND_DIR

UA_BROWSER = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

_pw = None
_browser = None
_lock = asyncio.Lock()
# Un Chromium à la fois : l'API idle ~1,3 Go, MemoryHigh=2G.
_sem = asyncio.Semaphore(1)
_unavailable = False
RENDER_SUBPROCESS_GRACE_S = 20


class RenderUnavailable(Exception):
    """Playwright / navigateur absent — désactive les rendus suivants."""


def _render_worker_env() -> dict:
    env = os.environ.copy()
    backend = str(BACKEND_DIR)
    current = env.get("PYTHONPATH", "")
    parts = [p for p in current.split(os.pathsep) if p]
    if backend not in parts:
        env["PYTHONPATH"] = os.pathsep.join([backend, *parts]) if parts else backend
    return env


def _run_render_worker(url: str, timeout_s: int, settle_ms: int) -> str | None:
    """Spawn ``app.core.render_worker`` — hookable depuis les tests."""
    with tempfile.TemporaryDirectory(prefix="bi-render-") as tmp:
        out = Path(tmp) / "page.html"
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "app.core.render_worker",
                 url, str(out), str(timeout_s), str(settle_ms)],
                timeout=timeout_s + RENDER_SUBPROCESS_GRACE_S,
                capture_output=True,
                env=_render_worker_env(),
                cwd=str(BACKEND_DIR),
            )
        except subprocess.TimeoutExpired:
            return None
        if proc.returncode == 2:
            err = (proc.stderr or b"").decode("utf-8", "replace")[:200]
            raise RenderUnavailable(err or "playwright missing")
        if proc.returncode != 0 or not out.is_file():
            return None
        text = out.read_text(encoding="utf-8")
        return text or None


async def _get_browser(log):
    """Navigateur partagé (screenshots Review seulement). None si Playwright absent."""
    global _pw, _browser, _unavailable
    if _unavailable:
        return None
    async with _lock:
        if _browser is not None and _browser.is_connected():
            return _browser
        try:
            from playwright.async_api import async_playwright
            if _pw is None:
                _pw = await async_playwright().start()
            _browser = await _pw.chromium.launch(
                headless=True, args=["--no-sandbox", "--disable-dev-shm-usage",
                                     "--disable-gpu", "--renderer-process-limit=1"])
            return _browser
        except Exception as e:
            _unavailable = True
            log(f"render: Playwright indisponible ({type(e).__name__}: {str(e)[:80]}) — rendu désactivé")
            return None


async def render_html(url: str, timeout_s: int = 45, settle_ms: int = 2500, log=None) -> str | None:
    """HTML rendu par Chromium isolé (DOM après JavaScript), ou None."""
    global _unavailable
    log = log or (lambda m: None)
    if _unavailable:
        return None
    async with _sem:
        try:
            return await asyncio.to_thread(
                _run_render_worker, url, timeout_s, settle_ms)
        except RenderUnavailable as e:
            _unavailable = True
            log(f"render: Playwright indisponible ({e}) — rendu désactivé")
            return None
        except Exception as e:
            log(f"render {url[:70]}: échec ({type(e).__name__}: {str(e)[:60]})")
            return None


async def render_screenshot(url: str, timeout_s: int = 45, settle_ms: int = 2500,
                            log=None) -> bytes | None:
    """Capture JPEG pleine page (vision Review), ou None."""
    from app.core.extract import should_skip_screenshot
    log = log or (lambda m: None)
    skip = should_skip_screenshot(url)
    if skip:
        log(f"screenshot {url[:70]}: sauté ({skip})")
        return None
    browser = await _get_browser(log)
    if browser is None:
        return None
    async with _sem:
        context = None
        try:
            context = await browser.new_context(
                user_agent=UA_BROWSER, viewport={"width": 1280, "height": 900},
                locale="en-US")
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded",
                            timeout=timeout_s * 1000)
            try:
                await page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                await page.wait_for_timeout(settle_ms)
            try:
                return await page.screenshot(
                    full_page=True, type="jpeg", quality=65)
            except Exception:
                return await page.screenshot(type="jpeg", quality=65)
        except Exception as e:
            log(f"screenshot {url[:70]}: échec ({type(e).__name__}: {str(e)[:60]})")
            return None
        finally:
            if context is not None:
                try:
                    await context.close()
                except Exception:
                    pass


async def shutdown_render():
    """Fermeture propre (appelée au shutdown de l'app)."""
    global _pw, _browser
    try:
        if _browser is not None:
            await _browser.close()
        if _pw is not None:
            await _pw.stop()
    except Exception:
        pass
    _browser = None
    _pw = None
