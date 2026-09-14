"""
render_core — Local browser render (Playwright + headless Chromium).

``render_html`` (Complet / PoE cascade) launches Chromium in a *subprocess*
(``app.core.render_worker``). A native crash (munmap_chunk under MemoryHigh=2G)
kills only the child: Complet continues, RAM is released.

``render_screenshot`` (Review vision) stays in-process: a one-off call,
not a burst of 200 pages.

Clean degradation: if playwright or its browser is not installed,
render_html returns None and the cascade continues without render.
Install: pip install playwright && playwright install chromium
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
# One Chromium at a time: idle API ~1.3 GB, MemoryHigh=2G.
_sem = asyncio.Semaphore(1)
_unavailable = False
RENDER_SUBPROCESS_GRACE_S = 20


class RenderUnavailable(Exception):
    """Playwright / browser missing — disable subsequent renders."""


def _render_worker_env() -> dict:
    env = os.environ.copy()
    backend = str(BACKEND_DIR)
    current = env.get("PYTHONPATH", "")
    parts = [p for p in current.split(os.pathsep) if p]
    if backend not in parts:
        env["PYTHONPATH"] = os.pathsep.join([backend, *parts]) if parts else backend
    return env


def _run_render_worker(url: str, timeout_s: int, settle_ms: int) -> str | None:
    """Spawn ``app.core.render_worker`` — hookable from tests."""
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
    """Shared browser (Review screenshots only). None if Playwright is missing."""
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
    """HTML rendered by isolated Chromium (DOM after JavaScript), or None."""
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
    log = log or (lambda m: None)
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


async def render_screenshot(url: str, timeout_s: int = 45, settle_ms: int = 2500,
                            log=None) -> bytes | None:
    """Capture JPEG pleine page (vision Review), ou None."""
    log = log or (lambda m: None)
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
    """Clean shutdown (called on app shutdown)."""
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
